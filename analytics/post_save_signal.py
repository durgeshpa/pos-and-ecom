from django.db import models
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F,Sum, Q
# from shops.models import Shop
# from gram_to_brand.models import Order as PurchaseOrder, GRNOrder
import requests
from decouple import config
from  services.models import RetailerReports, OrderReports,GRNReports, MasterReports, OrderGrnReports, OrderDetailReports, CategoryProductReports
# from products.models import Product, ProductPrice
# from retailer_to_sp.models import Order, OrderedProductMapping
# from shops.models import ParentRetailerMapping
from celery.task import task


# @task
# def call_analytic_product_update(id):
#     requests.post('http://127.0.0.1:8000/analytics/api/v1/product-category-report/', {'id':id})

def get_category_product_report1(sender, instance=None, created=False, **kwargs):
    def on_commit1():
        requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/product-category-report/', data={'id':instance.id})
    transaction.on_commit(on_commit1)

def get_category_product_report2(sender, instance=None, created=False, **kwargs):
    def on_commit2():
        requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/grn-report/', data={'order_id':instance.order.id})
    transaction.on_commit(on_commit2)

def get_category_product_report3(sender, instance=None, created=False, **kwargs):
    def on_commit3():
        requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/master-report/', data={'shop_id':instance.seller_shop.id})
    transaction.on_commit(on_commit3)

def get_category_product_report4(sender, instance=None, created=False, **kwargs):
    def on_commit4():
        requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/order-report/', data={'order_id':instance.ordered_product.order.id})
    transaction.on_commit(on_commit4)

def get_category_product_report5(sender, instance=None, created=False, **kwargs):
    def on_commit5():
        requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/retailer-report/', data={'retailer_id':instance.retailer.id})
    transaction.on_commit(on_commit5)