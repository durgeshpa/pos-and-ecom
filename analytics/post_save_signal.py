from django.db import models
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django.db.models import F, Sum, Q
from shops.models import Shop, ParentRetailerMapping
from gram_to_brand.models import Order as PurchaseOrder, GRNOrder
import requests
from decouple import config
from products.models import Product, ProductPrice
from retailer_to_sp.models import Order, OrderedProduct, Trip, Shipment
# from shops.models import ParentRetailerMapping
from .api.v1.views import category_product_report, grn_report, master_report, order_report, retailer_report, \
    shipment_report, trip_report, getStock
from celery.task import task
from celery import shared_task

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Product)
def get_category_product_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: category_product_report.delay(instance.id))


@receiver(post_save, sender=PurchaseOrder)
def get_grn_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: grn_report.delay(instance.id))


@receiver(post_save, sender=ProductPrice)
def get_master_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: master_report.delay(instance.seller_shop_id))


@receiver(post_save, sender=Order)
def get_order_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: order_report.delay(instance.id))


@receiver(post_save, sender=ParentRetailerMapping)
def get_retailer_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: retailer_report.delay(instance.id))


@receiver(post_save, sender=Shipment)
def get_shipment_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: shipment_report.delay(instance.id))


@receiver(post_save, sender=Trip)
def get_tripshipment_report(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: trip_report.delay(instance.id))


if __name__ == '__main__':
    getStock()
