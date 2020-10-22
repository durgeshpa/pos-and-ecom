from django.contrib.auth.models import User

from products.models import Product, ProductPrice, ProductCategory, ProductTaxMapping, ProductImage, ChildProductImage
from django.db.models.signals import post_save
from django.dispatch import receiver
from sp_to_gram.tasks import update_shop_product_es
from analytics.post_save_signal import get_category_product_report
import logging
logger = logging.getLogger('django')

from .tasks import approve_product_price


@receiver(post_save, sender=ProductPrice)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    if instance.approval_status == sender.APPROVED:
        product_mrp = instance.mrp if instance.mrp else instance.product.product_mrp
        #approve_product_price.delay(instance.id)
        update_shop_product_es(
            instance.seller_shop.id,
            instance.product.id,
            ptr=instance.selling_price,
            mrp=product_mrp
        )


@receiver(post_save, sender=ProductCategory)
def update_category_elasticsearch(sender, instance=None, created=False, **kwargs):
    category = [str(c.category) for c in instance.product.product_pro_category.filter(status=True)]
    for prod_price in instance.product.product_pro_price.filter(status=True).values('seller_shop', 'product'):
        update_shop_product_es.delay(prod_price['seller_shop'], prod_price['product'], category=category)



@receiver(post_save, sender=ProductImage)
def update_product_image_elasticsearch(sender, instance=None, created=False, **kwargs):
    product_images = [{
                        "image_name":instance.image_name,
                        "image_alt":instance.image_alt_text,
                        "image_url":instance.image.url
                       }]
    for prod_price in instance.product.product_pro_price.filter(status=True).values('seller_shop', 'product'):
        update_shop_product_es.delay(prod_price['seller_shop'], prod_price['product'], product_images=product_images)


@receiver(post_save, sender=ChildProductImage)
def update_child_product_image_elasticsearch(sender, instance=None, created=False, **kwargs):
    product_images = [{
        "image_name": instance.image_name,
        "image_alt": instance.image_alt_text,
        "image_url": instance.image.url
    }]
    for prod_price in instance.product.product_pro_price.filter(status=True).values('seller_shop', 'product'):
        update_shop_product_es.delay(prod_price['seller_shop'], prod_price['product'], product_images=product_images)


@receiver(post_save, sender=Product)
def update_product_elasticsearch(sender, instance=None, created=False, **kwargs):
    logger.error("updating product to elastic search")
    # for prod_price in instance.product_pro_price.filter(status=True).values('seller_shop', 'product', 'product__product_name', 'product__product_inner_case_size', 'product__status'):
    product_categories = [str(c.category) for c in instance.parent_product.parent_product_pro_category.filter(status=True)]
    product_images = []
    if instance.use_parent_image:
        product_images = [
            {
                "image_name": p_i.image_name,
                "image_alt": p_i.image_alt_text,
                "image_url": p_i.image.url
            }
            for p_i in instance.parent_product.parent_product_pro_image.all()
        ]
    for prod_price in instance.product_pro_price.filter(status=True).values('seller_shop', 'product', 'product__product_name', 'product__status'):
        if not product_images:
            update_shop_product_es.delay(
                prod_price['seller_shop'],
                prod_price['product'],
                name=prod_price['product__product_name'],
                pack_size=instance.product_inner_case_size,
                status=True if (prod_price['product__status'] in ['active', True]) else False,
                category=product_categories
            )
        else:
            update_shop_product_es.delay(
                prod_price['seller_shop'],
                prod_price['product'],
                name=prod_price['product__product_name'],
                pack_size=instance.product_inner_case_size,
                status=True if (prod_price['product__status'] in ['active', True]) else False,
                category=product_categories,
                product_images=product_images
            )

post_save.connect(get_category_product_report, sender=Product)
