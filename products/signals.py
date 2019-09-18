from django.contrib.auth.models import User

from products.models import Product, ProductPrice, ProductCategory, ProductTaxMapping, ProductImage
from django.db.models.signals import post_save
from django.dispatch import receiver
from sp_to_gram.tasks import update_shop_product_es

from .tasks import approve_product_price


@receiver(post_save, sender=ProductPrice)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    if instance.approval_status == sender.APPROVED:
        approve_product_price.delay(instance.id)
        update_shop_product_es.delay(
            instance.seller_shop.id, instance.product.id,
            ptr=instance.selling_price, mrp=instance.mrp)


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


@receiver(post_save, sender=Product)
def update_product_elasticsearch(sender, instance=None, created=False, **kwargs):
    for prod_price in instance.product_pro_price.filter(status=True).values('seller_shop', 'product'):
	    update_shop_product_es.delay(prod_price['seller_shop'], prod_price['product'], name=instance.product_name)
	    update_shop_product_es.delay(prod_price['seller_shop'], prod_price['product'], pack_size=instance.product_inner_case_size)
	    update_shop_product_es.delay(prod_price['seller_shop'], prod_price['product'], product_status=instance.status)
