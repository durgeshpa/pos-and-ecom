# python imports
import datetime
import logging
import math
from io import StringIO
import csv

from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Prefetch

# app imports
from .models import PriceSlab, Product, ProductCapping, DiscountedProductPrice, ProductPrice
from wms.models import Bin, WarehouseInventory, BinInventory, InventoryType, InventoryState, In
from wms.common_functions import CommonBinInventoryFunctions, CommonWarehouseInventoryFunctions
from global_config.models import GlobalConfig
from global_config.views import get_config

# logger configuration
info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')


def deactivate_capping():
    """
        Cron job for set status False in ProductCapping model if end date is less then current date
        :return:
        """
    try:
        cron_logger.info('cron job for deactivate the capping|started')
        today = datetime.datetime.today()
        capping_obj = ProductCapping.objects.filter(status=True, end_date__lt=today.date())
        if capping_obj:
            capping_obj.update(status=False)
            cron_logger.info('object is successfully updated from Product Capping model for status False')
        else:
            cron_logger.info('no object is getting from Product Capping model for status False')
    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Exception in capping status deactivated cron')


def packing_sku_inventory_alert():
    """
        Cron
        Email alert for packing skus having inventory below set threshold
    """
    try:
        cron_logger.info('cron packing material inventory alert | started')
        threshold = GlobalConfig.objects.filter(key='packing_sku_inventory_threshold_kg').last()
        threshold_kg_weight = threshold.value if threshold else 50

        w_invs = WarehouseInventory.objects.filter(sku__repackaging_type='packing_material',
                                                   inventory_state__inventory_state='total_available',
                                                   inventory_type__inventory_type='normal',
                                                   weight__lt=threshold_kg_weight * 1000)

        if not w_invs.exists():
            cron_logger.info('cron packing material inventory alert | none below threshold')
            return

        sku_ids = w_invs.distinct('sku_id').values_list('sku_id', flat=True)
        warehouse_ids = w_invs.distinct('warehouse_id').values_list('warehouse_id', flat=True)

        bin_inventories = BinInventory.objects.filter(sku_id__in=sku_ids, warehouse__id__in=warehouse_ids). \
            order_by('warehouse_id', 'sku_id', 'bin_id', 'batch_id')

        if bin_inventories.exists():
            f = StringIO()
            writer = csv.writer(f)

            headings = [
                'Warehouse ID', 'Parent ID', 'Parent Name', 'SKU ID', 'SKU Name', 'Product Status', 'Batch ID',
                'Bin Id', 'MRP',
                'Normal Weight (Kg)', 'Damaged Weight (Kg)', 'Expired Weight (Kg)', 'Missing Weight (Kg)'
            ]

            writer.writerow(headings)

            row = []
            current_sku_batch = ''
            for inv in bin_inventories:
                if current_sku_batch != str(inv.warehouse_id) + str(inv.sku.id) + str(inv.bin_id) + str(inv.batch_id):
                    if row:
                        writer.writerow(row)
                    sku = inv.sku
                    current_sku_batch = str(inv.warehouse_id) + str(inv.sku.id) + str(inv.bin_id) + str(inv.batch_id)
                    parent = inv.sku.parent_product
                    row = [inv.warehouse_id, parent.parent_id, parent.name, sku.product_sku, sku.product_name,
                           sku.status, inv.batch_id,
                           inv.bin.bin_id, sku.product_mrp, 0, 0, 0, 0]

                if inv.inventory_type.inventory_type == 'normal':
                    row[9] = inv.weight / 1000
                elif inv.inventory_type.inventory_type == 'damaged':
                    row[10] = inv.weight / 1000
                elif inv.inventory_type.inventory_type == 'expired':
                    row[11] = inv.weight / 1000
                elif inv.inventory_type.inventory_type == 'missing':
                    row[12] = inv.weight / 1000

            writer.writerow(row)

            curr_date = datetime.datetime.now()
            curr_date = curr_date.strftime('%Y-%m-%d %H:%M:%S')

            email = EmailMessage()
            email.subject = 'Packing Material SKUs below Threshold Inventory'
            email.body = 'PFA the list of Packing Material SKUs whose inventory (in Kgs) is below the set threshold of ' \
                         + str(threshold_kg_weight) + ' Kgs'
            sender = GlobalConfig.objects.get(key='sender')
            email.from_email = sender.value
            receiver = GlobalConfig.objects.get(key='packing_material_inventory_recipient')
            email.to = eval(receiver.value)
            email.attach('packing_sku__below_threshold_{}'.format(curr_date) + '.csv', f.getvalue(), 'text/csv')
            email.send()
            cron_logger.info('cron packing material inventory alert | mailed')
        else:
            cron_logger.info('cron packing material inventory alert | none below threshold')
    except Exception as e:
        cron_logger.error(e)
        cron_logger.info('cron packing material inventory alert | exception')


def update_price_discounted_product():
    """
    Update price of discounted product on the basis of remaining life
    and Move to expired when life ends
    """
    cron_logger.info('cron update price of discounted product | started')
    type_normal = InventoryType.objects.get(inventory_type='normal')
    type_expired = InventoryType.objects.get(inventory_type='expired')
    state_total_available = InventoryState.objects.get(inventory_state='total_available')
    today = datetime.datetime.today().date()
    tr_id = today.isoformat()
    inventory = BinInventory.objects.filter(sku__product_type=Product.PRODUCT_TYPE_CHOICE.DISCOUNTED,
                                            inventory_type__inventory_type='normal', quantity__gt=0) \
        .prefetch_related('sku__parent_product') \
        .prefetch_related('sku__product_ref')
    cron_logger.info("Total Inventories " + str(inventory.count()))
    for dis_prod in inventory:
        try:
            latest_in = In.objects.filter(batch_id=dis_prod.batch_id)
            expiry_date = latest_in[0].expiry_date
            manufacturing_date = latest_in[0].manufacturing_date
            product_life = expiry_date - manufacturing_date
            remaining_life = expiry_date - datetime.date.today()
            discounted_life = math.floor(product_life.days * dis_prod.sku.parent_product.discounted_life_percent / 100)
            half_life = (discounted_life - 2) / 2

            # Calculate Base Price
            product_price = dis_prod.sku.product_ref.product_pro_price.filter(seller_shop=dis_prod.warehouse,
                                                                              approval_status=ProductPrice.APPROVED).last()
            base_price_slab = product_price.price_slabs.filter(end_value=0).last()
            base_price = base_price_slab.ptr
            half_life_selling_price = base_price * int(get_config('DISCOUNTED_HALF_LIFE_PRICE_PERCENT', 50)) / 100
            selling_price = None

            # Active Discounted Product Price
            dis_prod_price = DiscountedProductPrice.objects.filter(product=dis_prod.sku, approval_status=2,
                                                                   seller_shop=dis_prod.warehouse)
            expired_life_days = get_config('EXPIRED_LIFE_DAYS')
            cron_logger.info('SKU {},  expiry_date {}, manufacturing_date {}, product_life {}, remaining life {},'
                             'discounted_life {}, half life {}, expired_life_days {}'
                             .format(dis_prod.sku_id, expiry_date, manufacturing_date, product_life, remaining_life,
                                     discounted_life, half_life, expired_life_days))
            if remaining_life.days <= expired_life_days:
                move_inventory(dis_prod.warehouse, dis_prod.sku, dis_prod.bin, dis_prod.batch_id, dis_prod.quantity,
                               state_total_available, type_normal, type_expired, tr_id, 'expired')
                cron_logger.info(
                    f'moved discounted product {dis_prod.sku} successfully to expired if remaining life is less than 2.')

            elif remaining_life.days <= half_life:
                if not dis_prod_price.last() or dis_prod_price.last().selling_price != half_life_selling_price and not dis_prod.sku.is_manual_price_update:
                    selling_price = half_life_selling_price
                    cron_logger.info(
                        f'update selling price of discounted product {dis_prod.sku} successfully if remaining life is less than or equal to half life and not updated.')
            else:
                if not dis_prod_price.last():
                    selling_price = base_price * int(get_config('DISCOUNTED_PRICE_PERCENT', 75)) / 100
                    cron_logger.info(
                        f'update selling price of discounted product {dis_prod.sku} successfully if price doesnot exist.')

            if selling_price:
                with transaction.atomic():
                    discounted_price = ProductPrice.objects.create(
                        product=dis_prod.sku,
                        mrp=dis_prod.product_mrp,
                        selling_price=selling_price,
                        seller_shop=dis_prod.warehouse,
                        start_date=datetime.datetime.today(),
                        approval_status=ProductPrice.APPROVED)
                    PriceSlab.objects.create(product_price=discounted_price, start_value=1, end_value=0,
                                             selling_price=selling_price)
                    cron_logger.info(f'Successfully created discounted price for {dis_prod.sku}')

        except Exception:
            cron_logger.error(f'update discounted product price | exception for sku {dis_prod.sku}')


def move_inventory(warehouse, discounted_product, bin, batch_id, quantity,
                   state_total_available, type_normal, type_expired, tr_id, tr_type_expired):
    discounted_batch_id = batch_id
    with transaction.atomic():
        CommonBinInventoryFunctions.update_bin_inventory_with_transaction_log(warehouse, bin, discounted_product,
                                                                              batch_id,
                                                                              type_normal, type_normal, -1 * quantity,
                                                                              True, tr_type_expired, tr_id)
        CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(warehouse, discounted_product,
                                                                                          type_normal,
                                                                                          state_total_available,
                                                                                          -1 * quantity,
                                                                                          tr_type_expired, tr_id)
        CommonBinInventoryFunctions.update_bin_inventory_with_transaction_log(warehouse, bin, discounted_product,
                                                                              discounted_batch_id, type_normal,
                                                                              type_expired,
                                                                              quantity, True, tr_type_expired,
                                                                              tr_id)
        CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(warehouse, discounted_product,
                                                                                          type_expired,
                                                                                          state_total_available,
                                                                                          quantity, tr_type_expired,
                                                                                          tr_id)
