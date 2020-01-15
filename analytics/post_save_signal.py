from django.db import models
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django.db.models import F,Sum, Q
from shops.models import Shop, ParentRetailerMapping
from gram_to_brand.models import Order as PurchaseOrder, GRNOrder
import requests
from decouple import config
from products.models import Product, ProductPrice
from retailer_to_sp.models import Order, OrderedProduct, Trip
# from shops.models import ParentRetailerMapping
from .api.v1.views import category_product_report, grn_report, master_report, order_report, retailer_report, shipment_report, trip_shipment_report,trip_report
from celery.task import task
from celery import shared_task

import logging

logger = logging.getLogger(__name__)



# @task
# def call_analytic_product_update(id):
#     requests.post('http://127.0.0.1:8000/analytics/api/v1/product-category-report/', {'id':id})
#
# @task(queue='analytics_tasks', routing_key='analytics')
# def product_category_report_task(id):
#     logger.exception('adding product description in analytics')
#     requests.post(config('REDSHIFT_URL') + '/analytics/api/v1/product-category-report/', data={'id': id})
#
#
# @task(queue='analytics_tasks', routing_key='analytics')
# def get_grn_report_task(order_id):
#     requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/grn-report/', data={'order_id': order_id})
#
#
# @task(queue='analytics_tasks', routing_key='analytics')
# def master_report_task(seller_shop_id):
#     requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/master-report/', data={'seller_shop_id': seller_shop_id})
#
#
# @task(queue='analytics_tasks', routing_key='analytics')
# def order_report_task(order_id):
#     requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/order-report/', data={'order_id': order_id})
#
#
# @task(queue='analytics_tasks', routing_key='analytics')
# def retailer_report_task(retailer_id):
#     requests.post(config('REDSHIFT_URL') + '/analytics/api/v1/retailer-report/',
#                   data={'retailer_id': retailer_id})


def get_category_product_report(sender, instance=None, created=False, **kwargs):
    category_product_report.delay(instance.id)
    # transaction.on_commit(lambda: product_category_report_task.delay(instance.id))

@receiver(post_save, sender=PurchaseOrder)
def get_grn_report(sender, instance=None, created=False, **kwargs):
    grn_report.delay(instance.order.id)
    # transaction.on_commit(lambda: get_grn_report_task.delay(instance.order.id))

@receiver(post_save, sender=ProductPrice)
def get_master_report(sender, instance=None, created=False, **kwargs):
    master_report.delay(instance.seller_shop_id)
    # transaction.on_commit(lambda: master_report_task.delay(instance.seller_shop_id))

@receiver(post_save, sender=Order)
def get_order_report(sender, instance=None, created=False, **kwargs):
    order_report.delay(instance.id)
    # transaction.on_commit(lambda: order_report_task.delay(instance.id))

# def get_order_report(sender, instance=None, created=False, **kwargs):
#     def on_commit4():
#         requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/order-report/', data={'order_id':instance.id})
#     transaction.on_commit(on_commit4)

@receiver(post_save, sender=ParentRetailerMapping)
def get_retailer_report(sender, instance=None, created=False, **kwargs):
    retailer_report.delay(instance.id)
    # transaction.on_commit(lambda: retailer_report_task.delay(instance.retailer.id))

@receiver(post_save, sender=OrderedProduct)
def get_shipment_report(sender, instance=None, created=False, **kwargs):
    shipment_report.delay(instance.id)



@receiver(post_save, sender=Trip)
def get_tripshipment_report(sender, instance=None, created=False, **kwargs):
    # trip_shipment_report.delay(instance.id)
    trip_report.delay(instance.id)

# def get_category_product_report(sender, instance=None, created=False, **kwargs):
#     transaction.on_commit(lambda: requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/product-category-report/',
#                                                 data={'id': instance.id}))
#
# def get_grn_report(sender, instance=None, created=False, **kwargs):
#     transaction.on_commit(lambda: requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/grn-report/',
#                                                 data={'order_id': instance.order.id}))
#
# def get_master_report(sender, instance=None, created=False, **kwargs):
#     transaction.on_commit(lambda: requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/master-report/',
#                                                 data={'seller_shop_id': instance.seller_shop_id}))
#
# def get_order_report(sender, instance=None, created=False, **kwargs):
#     transaction.on_commit(lambda: requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/order-report/',
#                                                 data={'order_id': instance.id}))
#
# def get_retailer_report(sender, instance=None, created=False, **kwargs):
#     transaction.on_commit(lambda: requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/retailer-report/',
#                                                 data={'retailer_id': instance.retailer.id}))


