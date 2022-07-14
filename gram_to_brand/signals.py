import datetime
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Sum

from global_config.views import get_config
from retailer_backend.common_function import brand_debit_note_pattern, grn_pattern, po_pattern
from shops.models import Shop, ParentRetailerMapping
from sp_to_gram.models import (Cart as SpPO, CartProductMapping as SpPOProducts, Order as SpOrder,
                               OrderedProduct as SpGRNOrder, OrderedProductMapping as SpGRNOrderProductMapping)
from whc.models import AutoOrderProcessing
from wms.common_functions import InCommonFunctions
from wms.models import BinInventory, InventoryType
from .models import BrandNote, GRNOrderProductMapping, GRNOrder, Cart, Order, CartProductMapping, \
    CartProductMappingTaxLog, ProductCostPriceChangeLog, ProductGRNCostPriceMapping
from .views import mail_to_vendor_on_po_approval
from django.db import transaction

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')


@receiver(post_save, sender=GRNOrder)
def create_grn_id(sender, instance=None, created=False, **kwargs):
    if created:
        instance.grn_id = grn_pattern(instance.pk)
        instance.save()
        # SP auto ordered product creation
        connected_shops = ParentRetailerMapping.objects.filter(
            parent=instance.order.ordered_cart.gf_shipping_address.shop_name, status=True)
        for shop in connected_shops:
            if shop.retailer.shop_type.shop_type == 'sp' and shop.retailer.status == True:
                SpPO.objects.create(shop=shop.retailer,
                                    po_validity_date=datetime.date.today() + datetime.timedelta(days=15)
                                    )

            source_wh_id_list = get_config('wh_consolidation_source')
            if source_wh_id_list is None:
                info_logger.info("process_GRN|wh_consolidation_source is not defined")
                return
            # source_wh_list = Shop.objects.filter(pk__in=source_wh_id_list).values_list('id', flat=True)
            if shop.retailer.id in source_wh_id_list:
                AutoOrderProcessing.objects.create(source_po=instance.order.ordered_cart,
                                                   grn=instance,
                                                   grn_warehouse_id=shop.retailer.id,
                                                   state=AutoOrderProcessing.ORDER_PROCESSING_STATUS.GRN
                                                   )
                info_logger.info("updated AutoOrderProcessing for GRN.")

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


@receiver(pre_save, sender=CartProductMapping)
def add_tax_change_log(sender, instance, update_fields=None, ** kwargs):
    old_instance = CartProductMapping.objects.filter(id=instance.id).last()
    if old_instance and (old_instance.gst != instance.gst or old_instance.cess != instance.cess):
        CartProductMappingTaxLog.objects.create(
            cart_product_mapping=instance, existing_gst=old_instance.gst, existing_cess=old_instance.cess,
            new_gst=instance.gst, new_cess=instance.cess, created_by=instance.cart.last_modified_by)


@receiver(post_save, sender=GRNOrderProductMapping)
def mark_po_item_as_closed(sender, instance=None, created=False, **kwargs):
    if instance.delivered_qty + instance.returned_qty > 0:
        cart_product = instance.grn_order.order.ordered_cart.cart_list.filter(cart_product=instance.product)
        cart_product.update(is_grn_done=True)


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
                BrandNote.objects.create(
                    brand_note_id=brand_debit_note_pattern(
                        BrandNote, 'brand_note_id', None, instance.grn_order.order.ordered_cart.gf_billing_address_id),
                    grn_order=instance.grn_order, amount=instance.returned_qty * instance.po_product_price, status=True
                )

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
                SpPOProducts.objects.create(
                    cart=sp_po,
                    cart_product=instance.product,
                    case_size=instance.product.product_case_size,
                    number_of_cases=instance.grn_order.order.ordered_cart.cart_list.filter(
                        cart_product=instance.product).last().no_of_cases,
                    qty=int(instance.delivered_qty),
                    price=instance.grn_order.order.ordered_cart.cart_list.filter(
                        cart_product=instance.product).last().price,
                    total_price=round(float(instance.delivered_qty) *
                                      instance.grn_order.order.ordered_cart.cart_list.filter(
                                          cart_product=instance.product).last().price, 2)
                )
                sp_order = SpOrder.objects.filter(ordered_cart=sp_po).last()
                sp_grn_orders = SpGRNOrder.objects.filter(order=sp_order)
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
                    weight = 0
                    if instance.product.repackaging_type == 'packing_material':
                        weight = int(instance.delivered_qty) * instance.product.weight_value
                    in_obj = InCommonFunctions.create_in(
                        shop.retailer, 'GRN', instance.grn_order.grn_id, instance.product, instance.batch_id,
                        int(instance.delivered_qty), putaway_quantity, type_normal, weight, instance.manufacture_date,
                        instance.grn_order.id)

        # ends here
        instance.available_qty = 0
        instance.save()


@receiver(post_save, sender=GRNOrderProductMapping)
def calculate_cost_price(sender, instance=None, created=False, **kwargs):
    product = instance.product
    if created:
        avail_qty = BinInventory.objects.filter(sku=product, 
                                                inventory_type__inventory_type='normal')\
                                                    .aggregate(total=Sum('quantity')).get('total')
        avail_qty = avail_qty if avail_qty else 0
        cost_price_change_log = ProductCostPriceChangeLog()
        try:
            cost_price = ProductGRNCostPriceMapping.objects.get(product=product)
            last_cp = cost_price.cost_price
            cost_price_change_log.grn = cost_price.latest_grn
            last_avail_qty = cost_price.current_inv
        except ProductGRNCostPriceMapping.DoesNotExist:
            cost_price = ProductGRNCostPriceMapping()
            grn = GRNOrderProductMapping.objects.filter(product=product).exclude(id=instance.pk).last()
            last_cp = grn.product_invoice_price if grn else 0
            cost_price_change_log.grn = grn
            cost_price.product = product
            last_avail_qty = 0
        cost_price_change_log.cost_price_grn_mapping = cost_price
        cost_price_change_log.cost_price = last_cp
        cost_price_change_log.current_inv = last_avail_qty
        current_purchase_price = instance.product_invoice_price
        current_purchase_qty = instance.product_invoice_qty
        new_cost_price = (float((avail_qty * last_cp)) + (current_purchase_qty * current_purchase_price)) / (avail_qty + current_purchase_qty)
        ### updating cost price of product 
        cost_price.cost_price = new_cost_price
        cost_price.latest_grn = instance
        cost_price.current_inv = avail_qty
        cost_price.modified_at = datetime.datetime.now()
        with transaction.atomic():
            cost_price.save()
            cost_price_change_log.cost_price_grn_mapping = cost_price
            cost_price_change_log.save()
    else:
        # cost_price = product.cost_price
        pass


@receiver(post_save, sender=Cart)
def generate_po_no(sender, instance=None, created=False, update_fields=None, **kwargs):
    """
        PO Number Generation on Cart creation
    """
    if not instance.po_status == 'DLVR':
        if created:
            instance.po_no = po_pattern(sender, 'po_no', instance.pk, instance.gf_billing_address_id)
            instance.save()
        order, created = Order.objects.get_or_create(ordered_cart=instance)
        order.order_no = instance.po_no
        order.save()


@receiver(post_save, sender=Cart)
def mail_to_vendor(sender, instance=None, created=False, update_fields=None, **kwargs):
    """
        Send mail to vendor on po approval
    """
    if instance.cart_type == Cart.CART_TYPE_CHOICE.AUTO and instance.is_approve and not instance.is_vendor_notified:
        mail_to_vendor_on_po_approval(instance)
        instance.is_vendor_notified = True
        instance.save()
