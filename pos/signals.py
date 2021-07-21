import uuid

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver

from .tasks import update_shop_retailer_product_es
from .models import RetailerProduct, RetailerProductImage
from wms.models import PosInventory


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


@receiver(post_save, sender=PosInventory)
def update_elasticsearch_inv(sender, instance=None, created=False, **kwargs):
    """
        Update elastic data on RetailerProduct update
    """
    update_shop_retailer_product_es(instance.product.shop.id, instance.product.id)


# @receiver(post_save, sender=RetailerProductImage)
# def update_elasticsearch_image(sender, instance=None, created=False, **kwargs):
#     """
#         Update elastic data on RetailerProduct update
#     """
#     update_shop_retailer_product_es(instance.product.shop.id, instance.product.id)
#
#
# @receiver(post_delete, sender=RetailerProductImage)
# def update_elasticsearch_image(sender, instance=None, created=False, **kwargs):
#     """
#         Update elastic data on RetailerProduct update
#     """
#     update_shop_retailer_product_es(instance.product.shop.id, instance.product.id)
