from django.db.models.signals import post_save
from django.dispatch import receiver

from .tasks import update_shop_retailer_product_es
from .models import RetailerProduct, RetailerProductImage


@receiver(post_save, sender=RetailerProduct)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    """
        Update elastic data on RetailerProduct update
    """
    update_shop_retailer_product_es(instance.shop.id, instance.id)


@receiver(post_save, sender=RetailerProductImage)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    """
        Update elastic data on RetailerProduct update
    """
    update_shop_retailer_product_es(instance.product.shop.id, instance.product.id)