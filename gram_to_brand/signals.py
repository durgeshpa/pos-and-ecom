import datetime

from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db.models import Sum
from django.db import transaction

from global_config.models import GlobalConfig
from wms.models import InventoryType, InventoryState
from shops.models import Shop
from .models import BrandNote, GRNOrderProductMapping, GRNOrder
from shops.models import Shop, ParentRetailerMapping
from sp_to_gram.models import (
    Cart as SpPO,
    CartProductMapping as SpPOProducts,
    Order as SpOrder,
    OrderedProduct as SpGRNOrder,
    OrderedProductMapping as SpGRNOrderProductMapping
)

from retailer_backend.common_function import brand_debit_note_pattern, grn_pattern
from wms.common_functions import PutawayCommonFunctions, InCommonFunctions, CommonBinInventoryFunctions, \
    updating_tables_on_putaway
from wms.views import update_putaway

import logging

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')

@receiver(post_save, sender=GRNOrder)
def create_grn_id(sender, instance=None, created=False, **kwargs):
    if created:
        instance.grn_id = grn_pattern(instance.pk)
        instance.save()
        # SP auto ordered product creation
        connected_shops = ParentRetailerMapping.objects.filter(
            parent=instance.order.ordered_cart.gf_shipping_address.shop_name,
            status=True
        )
        for shop in connected_shops:
            if shop.retailer.shop_type.shop_type == 'sp' and shop.retailer.status == True:
                sp_po = SpPO.objects.create(
                    shop=shop.retailer,
                    po_validity_date=datetime.date.today() + datetime.timedelta(days=15)
                )
        # data = {}
        # data['username'] = username
        # data['phone_number'] = instance.order_id.ordered_by
        # data['order_no'] = order_no
        # data['items_count'] = items_count
        # data['total_amount'] = total_amount
        # data['shop_name'] = shop_name

        # user_id = instance.order_id.ordered_by.id
        activity_type = "STOCK_IN"
        # from notification_center.utils import SendNotification
        # SendNotification(user_id=user_id, activity_type=activity_type, data=data).send()


@receiver(post_save, sender=GRNOrderProductMapping)
def create_debit_note(sender, instance=None, created=False, **kwargs):
    if created:
        if instance.returned_qty > 0:
            debit_note = BrandNote.objects.filter(grn_order=instance.grn_order)
            if debit_note.exists():
                debit_note = debit_note.last()
                debit_note.brand_note_id = brand_debit_note_pattern(
                    BrandNote, 'brand_note_id', debit_note, instance.grn_order.order.ordered_cart.gf_billing_address_id)
                debit_note.order = instance.grn_order.order
                debit_note.amount = debit_note.amount + (instance.returned_qty * instance.po_product_price)
                debit_note.save()
            else:
                debit_note = BrandNote.objects.create(
                    brand_note_id=brand_debit_note_pattern(
                        BrandNote, 'brand_note_id', None, instance.grn_order.order.ordered_cart.gf_billing_address_id),
                    grn_order=instance.grn_order, amount=instance.returned_qty * instance.po_product_price, status=True)

        # SP auto ordered product creation
        connected_shops = ParentRetailerMapping.objects.filter(
            parent=instance.grn_order.order.ordered_cart.gf_shipping_address.shop_name,
            status=True
        )
        for shop in connected_shops:
            if shop.retailer.shop_type.shop_type == 'sp' and shop.retailer.status == True:
                sp_po = SpPO.objects.filter(
                    shop=shop.retailer
                ).last()
                sp_cpm = SpPOProducts.objects.create(
                    cart=sp_po,
                    cart_product=instance.product,
                    case_size=instance.product.product_case_size,
                    number_of_cases=instance.grn_order.order. \
                        ordered_cart.cart_list.filter
                        (
                        cart_product=instance.product
                    ).last().no_of_cases,
                    qty=int(instance.delivered_qty),
                    # scheme=item.scheme,
                    price=instance.grn_order.order. \
                        ordered_cart.cart_list.filter
                        (
                        cart_product=instance.product
                    ).last().price,
                    total_price=round(float(instance.delivered_qty) * instance.grn_order.order. \
                                      ordered_cart.cart_list.filter
                        (
                        cart_product=instance.product
                    ).last().price, 2),
                )
                sp_order = SpOrder.objects.filter(
                    ordered_cart=sp_po
                ).last()
                sp_grn_orders = SpGRNOrder.objects.filter(
                    order=sp_order
                )
                if sp_grn_orders.exists():
                    sp_grn_order = sp_grn_orders.last()
                else:
                    sp_grn_order = SpGRNOrder.objects.create(order=sp_order)
                if instance.batch_id:
                    SpGRNOrderProductMapping.objects.create(
                        ordered_product=sp_grn_order,
                        product=instance.product,
                        manufacture_date=instance.manufacture_date,
                        expiry_date=instance.expiry_date,
                        shipped_qty=instance.delivered_qty,
                        available_qty=instance.delivered_qty,
                        ordered_qty=instance.delivered_qty,
                        delivered_qty=instance.delivered_qty,
                        returned_qty=0,
                        damaged_qty=0,
                        batch_id=instance.batch_id
                    )
                putaway_quantity = 0
                if instance.batch_id:
                    type_normal = InventoryType.objects.filter(inventory_type='normal').last()
                    in_obj = InCommonFunctions.create_in(shop.retailer, 'GRN', instance.grn_order.grn_id,
                                                         instance.product,
                                                         instance.batch_id, int(instance.delivered_qty),
                                                         putaway_quantity,
                                                         type_normal)

                    is_wh_consolidation_on = GlobalConfig.objects.get(key='is_wh_consolidation_on')
                    if is_wh_consolidation_on.value:
                        source_wh_id = GlobalConfig.objects.get(key='wh_consolidation_source')
                        if in_obj.warehouse.id == source_wh_id.value:
                            autoPutAway(in_obj.warehouse, [in_obj.batch_id], [in_obj.quantity])

        # ends here
        instance.available_qty = 0
        instance.save()


def autoPutAway(warehouse, batch_id, quantity):
    virtual_bin_ids = GlobalConfig.objects.get(key='virtual_bins')
    bin_ids = eval(virtual_bin_ids.value)

    glob_user = GlobalConfig.objects.get(key='user')
    user = glob_user.value
    data, key = {}, 0
    inventory_type = 'normal'

    type_normal = InventoryType.objects.filter(inventory_type=inventory_type).last()
    diction = {i[0]: i[1] for i in zip(batch_id, quantity)}
    for i, value in diction.items():
        key += 1
        val = value
        put_away = PutawayCommonFunctions.get_filtered_putaways(batch_id=i, warehouse=warehouse,
                                                                inventory_type=type_normal).order_by('created_at')
        ids = [i.id for i in put_away]

        sh = Shop.objects.filter(id=int(warehouse.id)).last()
        state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()

        if sh.shop_type.shop_type == 'sp':

            # Get the Bin Inventory for concerned SKU and Bin excluding the current batch id
            for bin_id in bin_ids:
                bin_inventory = CommonBinInventoryFunctions.get_filtered_bin_inventory(sku=i[:17], bin__bin_id=bin_id).exclude(
                                                                                                    batch_id=i)
                if bin_inventory.exists():
                    qs = bin_inventory.filter(inventory_type=type_normal) \
                        .aggregate(available=Sum('quantity'), to_be_picked=Sum('to_be_picked_qty'))
                    total = qs['available'] + qs['to_be_picked']

                    # if inventory is more than zero, putaway won't be allowed,check for another bin_id

                    if total > 0:
                        break
                else:
                    break

            with transaction.atomic():

                pu = PutawayCommonFunctions.get_filtered_putaways(id=ids[0], batch_id=i, warehouse=warehouse)
                put_away_status = False

                while len(ids):
                    put_away_done = update_putaway(ids[0], i, warehouse, int(value), user)
                    value = put_away_done
                    put_away_status = True
                    ids.remove(ids[0])

                    updating_tables_on_putaway(sh, bin_id, put_away, i, type_normal, state_total_available, 't', val,
                                               put_away_status, pu)
                    break
            info_logger.info("quantity has been updated in put away.")