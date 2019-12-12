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

@task
def product_category_report_task(id):
    requests.post(config('REDSHIFT_URL') + '/analytics/api/v1/product-category-report/', data={'id': id})


@task
def get_grn_report_task(order_id):
    requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/grn-report/', data={'order_id': order_id})


@task
def master_report_task(seller_shop_id):
    requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/master-report/', data={'seller_shop_id': seller_shop_id})


@task
def order_report_task(order_id):
    requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/order-report/', data={'order_id': order_id})


@task
def retailer_report_task(retailer_id):
    requests.post(config('REDSHIFT_URL') + '/analytics/api/v1/retailer-report/',
                  data={'retailer_id': retailer_id})


def get_category_product_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: product_category_report_task.delay(instance.id))


def get_grn_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: get_grn_report_task.delay(instance.order.id))


def get_master_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: master_report_task.delay(instance.seller_shop_id))


def get_order_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: order_report_task.delay(instance.id))


def get_retailer_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: retailer_report_task.delay(instance.retailer.id))
