# python imports
import datetime
import logging
from io import StringIO
import csv

from django.core.mail import EmailMessage

# app imports
from .models import ProductCapping
from wms.models import WarehouseInventory, BinInventory
from global_config.models import GlobalConfig

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

        bin_inventories = BinInventory.objects.filter(sku_id__in=sku_ids, warehouse__id__in=warehouse_ids).\
            order_by('warehouse_id', 'sku_id', 'bin_id', 'batch_id')

        if bin_inventories.exists():
            f = StringIO()
            writer = csv.writer(f)

            headings = [
                'Warehouse ID', 'Parent ID', 'Parent Name', 'SKU ID', 'SKU Name', 'Product Status', 'Batch ID', 'Bin Id', 'MRP',
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
                    row = [inv.warehouse_id, parent.parent_id, parent.name, sku.product_sku, sku.product_name, sku.status, inv.batch_id,
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

