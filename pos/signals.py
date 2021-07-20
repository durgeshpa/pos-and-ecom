import uuid

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from retailer_backend.common_function import po_pattern
from wms.models import PosInventory

from .tasks import update_shop_retailer_product_es
from .models import RetailerProduct, PosCart, PosOrder


def sku_generator(shop_id):
    return (str(shop_id) + str(uuid.uuid4().hex).upper())[0:17]


@receiver(pre_save, sender=RetailerProduct)
def create_product_sku(sender, instance=None, created=False, **kwargs):
    if not instance.sku:
        # Generate a unique SKU by using shop_id & uuid4 once,
        # then check the db. If exists, keep trying.
        sku_id = sku_generator(instance.shop.id)
        while RetailerProduct.objects.filter(sku=sku_id).exists():
            sku_id = sku_generator(instance.shop.id)
        instance.sku = sku_id


@receiver(post_save, sender=RetailerProduct)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    """
        Update elastic data on RetailerProduct update
    """
    update_shop_retailer_product_es(instance.shop.id, instance.id)


@receiver(post_save, sender=PosInventory)
def update_elasticsearch_inv(sender, instance=None, created=False, **kwargs):
    """
        Update elastic data on RetailerProduct update
    """
    update_shop_retailer_product_es(instance.product.shop.id, instance.product.id)


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
