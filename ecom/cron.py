# python imports
import logging
import datetime
from os import stat

from django.db.models import Count
from django.db.models.signals import pre_delete
# app imports
from .models import Tag, TagProductMapping
from pos.models import RetailerProduct
from retailer_to_sp.models import Order, OrderedProductMapping
from shops.models import Product, Shop

# logger configuration
info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')

def update_tag(tag, tag_product, start, product, count):
    """
    update product of tag
    """
    while product.count() > start and count < 6:
        if count < tag_product.count():
            TagProductMapping.objects.filter(id = tag_product[count].id).update(product = product[start])
        else:
            TagProductMapping.objects.create(tag = tag, product = product[start])
        count += 1
        start += 1
    return count, tag_product

def bestseller_product():
    """
    Cron to get bestseller product
    """

    # last 15 days
    from_date = datetime.datetime.today() - datetime.timedelta(days=15)
    # Get all Franchise Shop
    shops = Shop.objects.filter(shop_type__shop_type='f')
    # Get Tag
    tag = Tag.objects.filter(name='BestSeller').last()
    for shop in shops:
        count = 0
        tag_product = TagProductMapping.objects.filter(product__shop = shop, tag = tag).order_by('-created_at')
        
        # Get online order product
        online_order = Order.objects.filter(ordered_cart__cart_type='ECOM', created_at__gte = from_date, seller_shop=shop)
        online_ordered_product = OrderedProductMapping.objects.filter(ordered_product__order__in = online_order)
        online_product = RetailerProduct.objects.filter(rt_retailer_product_order_product__in = online_ordered_product)
        #Sort by max count
        product = online_product.annotate(prd_count=Count('id')).order_by('-prd_count')
        #Update Tagged Product
        count, tag_product = update_tag(tag, tag_product, 0, product, count)

        # Get offline order if product is less than 6
        if count < 6:
            offline_order = Order.objects.filter(ordered_cart__cart_type='BASIC', created_at__gte = from_date, seller_shop=shop)
            offline_ordered_product = OrderedProductMapping.objects.filter(ordered_product__order__in = offline_order)
            total_offline_product = RetailerProduct.objects.filter(rt_retailer_product_order_product__in = offline_ordered_product, online_enabled = True)
            rem_offline_product = total_offline_product.annotate(prd_count=Count('id')).order_by('-prd_count')[:count]

            #Update Tagged Product
            count, tag_product = update_tag(tag, tag_product, 0, rem_offline_product, count)

        # add random product in case of no online and offline order
        if count < 6:
            exclude_product_id = product.values('id')
            random_product = RetailerProduct.objects.exclude(id__in = exclude_product_id).filter(online_enabled = True)[:count]

            # Update Tag product mapping
            count, tag_product = update_tag(tag, tag_product, 0, random_product, count)