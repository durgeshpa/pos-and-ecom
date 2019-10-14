from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F,Sum, Q
from shops.models import Shop
from gram_to_brand.models import Order as PurchaseOrder, GRNOrder
import requests
from decouple import config
from  services.models import RetailerReports, OrderReports,GRNReports, MasterReports, OrderGrnReports, OrderDetailReports, CategoryProductReports
from products.models import Product, ProductPrice
from retailer_to_sp.models import Order, OrderedProductMapping
from shops.models import ParentRetailerMapping

@receiver(post_save, sender=Product)
def get_category_product_report(sender, instance=None, created=False, **kwargs):
    requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/product-category-report/', data={'id':instance.id})

@receiver(post_save, sender=GRNOrder)
def get_category_product_report(sender, instance=None, created=False, **kwargs):
    requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/grn-report/', data={'order_id':instance.order.id})

@receiver(post_save, sender=ProductPrice)
def get_category_product_report(sender, instance=None, created=False, **kwargs):
    requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/master-report/', data={'shop_id':instance.seller_shop.id})

@receiver(post_save, sender=OrderedProductMapping)
def get_category_product_report(sender, instance=None, created=False, **kwargs):
    requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/order-report/', data={'order_id':instance.ordered_product.order.id})

@receiver(post_save, sender=ParentRetailerMapping)
def get_category_product_report(sender, instance=None, created=False, **kwargs):
    requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/retailer-report/', data={'retailer_id':instance.retailer.id})
