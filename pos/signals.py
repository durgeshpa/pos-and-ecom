import uuid

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .tasks import update_shop_retailer_product_es
from .models import RetailerProduct, RetailerProductImage


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


@receiver(post_save, sender=RetailerProductImage)
def update_elasticsearch_image(sender, instance=None, created=False, **kwargs):
    """
        Update elastic data on RetailerProduct update
    """
    update_shop_retailer_product_es(instance.product.shop.id, instance.product.id)
