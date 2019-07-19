from django.contrib.auth.models import User
from products.models import Product, ProductPrice, ProductCategory, ProductTaxMapping
from django.db.models.signals import post_save
from django.dispatch import receiver
from sp_to_gram.tasks import update_shop_product_es

@receiver(post_save, sender=ProductPrice)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    update_shop_product_es.delay(instance.shop.id, instance.product.id, ptr=instance.price_to_retailer, 
    								mrp=round(instance.mrp,2), loyalty_discount=instance.loyalty_incentive,
    								cash_discount=instance.cash_discount, margin=instance.margin)

@receiver(post_save, sender=ProductCategory)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
	category = [str(c.category) for c in instance.product.product_pro_category.filter(status=True)]
	for prod_price in instance.product.product_pro_price.all():
		update_shop_product_es.delay(prod_price.shop.id, prod_price.product.id, category=category)
