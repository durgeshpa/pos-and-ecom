import logging
import uuid

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from retailer_backend.common_function import po_pattern, grn_pattern, purchase_return_number_pattern
from wms.models import PosInventory
from wms.models import PosInventoryState
from .models import RetailerProduct, PosCart, PosOrder, PosGRNOrder, PosCartProductMapping, PosGRNOrderProductMapping, PosReturnGRNOrder
from .tasks import update_shop_retailer_product_es, update_shop_retailer_product_cart

logger = logging.getLogger(__name__)

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


def sku_generator(shop_id):
    return (str(shop_id) + str(uuid.uuid4().hex).upper())[0:17]


@receiver(pre_save, sender=RetailerProduct)
def create_product_sku(sender, instance=None, created=False, **kwargs):
    if not instance.sku:
        if instance.sku_type != 4:
            # Generate a unique SKU by using shop_id & uuid4 once,
            # then check the db. If exists, keep trying.
            sku_id = sku_generator(instance.shop.id)
            while RetailerProduct.objects.filter(sku=sku_id).exists():
                sku_id = sku_generator(instance.shop.id)
        else:
            sku_id = 'D'+ instance.product_ref.sku
        instance.sku = sku_id
        # In case of discounted products, use existing products SKU with an appended D at the beginning


@receiver(post_save, sender=RetailerProduct)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    """
        Update elastic data on RetailerProduct update
    """
    update_shop_retailer_product_es(instance.shop.id, instance.id)
    if instance.product_ref:
        update_shop_retailer_product_es(instance.shop.id, instance.product_ref.id)


@receiver(post_save, sender=RetailerProduct)
def update_cart(sender, instance=None, created=False, **kwargs):
    """
        Update cart data on RetailerProduct update
    """
    update_shop_retailer_product_cart(instance.shop.id, instance.id)


@receiver(post_save, sender=PosInventory)
def update_elasticsearch_inv(sender, instance=None, created=False, **kwargs):
    """
        Update elastic data on RetailerProduct update
    """
    update_shop_retailer_product_es(instance.product.shop.id, instance.product.id)
    if instance.product.sku_type == 4:
        update_shop_retailer_product_es(instance.product.shop.id, instance.product.product_ref.id)

#
# @receiver(post_save, sender=PosInventory)
# def update_product_online_disabled_status_on_inventory_update(sender, instance=None, created=False, **kwargs):
#     """
#         update product status on inventory update
#     """
#     if instance.product.online_enabled is False and instance.product.online_disabled_status and \
#             instance.inventory_state.inventory_state == PosInventoryState.AVAILABLE:
#         if instance.quantity > 0:
#             instance.product.online_enabled = True
#             instance.product.online_disabled_status = None
#             instance.product.save()


@receiver(post_save, sender=PosInventory)
def update_product_status_on_inventory_update(sender, instance=None, created=False, **kwargs):
    """
        update product status on inventory update
    """
    if instance.product.sku_type == 4 and instance.inventory_state.inventory_state == PosInventoryState.AVAILABLE:
        if instance.quantity == 0:
            instance.product.status = 'deactivated'
        else:
            instance.product.status = 'active'
        instance.product.save()


@receiver(post_save, sender=PosCart)
def generate_po_no(sender, instance=None, created=False, update_fields=None, **kwargs):
    """
        PO Number Generation on Cart creation
    """
    if created:
        instance.po_no = po_pattern(sender, 'po_no', instance.pk,
                                    instance.retailer_shop.shop_name_address_mapping.filter(
                                        address_type='billing').last().pk)
        instance.save()
        order, created = PosOrder.objects.get_or_create(ordered_cart=instance)
        order.order_no = instance.po_no
        order.save()


@receiver(post_save, sender=PosGRNOrder)
def create_grn_id(sender, instance=None, created=False, **kwargs):
    if created:
        instance.grn_id = grn_pattern(instance.pk)
        instance.save()


@receiver(post_save, sender=PosReturnGRNOrder)
def create_pr_number(sender, instance=None, created=False, **kwargs):
    if created:
        if instance.grn_ordered_id:
            instance.pr_number = purchase_return_number_pattern(instance.pk, instance.grn_ordered_id.grn_id)
        else:
            instance.pr_number = purchase_return_number_pattern(instance.pk, instance.vendor_id.pincode)
        instance.save()


@receiver(post_save, sender=PosGRNOrderProductMapping)
def mark_po_item_as_closed(sender, instance=None, created=False, **kwargs):
    product = instance.grn_order.order.ordered_cart.po_products.filter(product=instance.product)
    product.update(is_grn_done=True)
    po_grn_initial_value = PosCartProductMapping.objects.filter(
        product__id=instance.product.id, is_grn_done=True).last()
    instance.product.initial_purchase_value = po_grn_initial_value.price * po_grn_initial_value.pack_size
    instance.product.save()


@receiver(pre_save, sender=RetailerProduct)
def set_online_price(sender, instance=None, created=False, **kwargs):
    if instance.online_enabled:
        instance.online_disabled_status = None
        if instance.sku_type == 1 and not instance.online_price:
            instance.online_price = instance.selling_price
    else:
        instance.online_price = None