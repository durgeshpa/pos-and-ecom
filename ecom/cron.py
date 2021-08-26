# python imports
import logging
import datetime
from os import stat

from django.db.models import Count
from django.db.models.signals import pre_delete
# app imports
from .models import Tag, TagProductMapping
from pos.models import RetailerProduct
from retailer_to_sp.models import Order, CartProductMapping, OrderedProductMapping
from shops.models import Shop
from global_config.views import get_config

# logger configuration
info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')

def update_tag(tag, tag_product, start, product, count):
    """
    update product of tag
    """
    try:
        while product.count() > start and count < 6:
            if count < (tag_product.count()):
                TagProductMapping.objects.filter(id = tag_product[count].id).update(product = product[start])
            else:
                TagProductMapping.objects.create(tag = tag, product = product[start])
            count += 1
            start += 1
        return count, tag_product
    except Exception as e:
        print(e)

def bestseller_product():
    """
    Cron to get bestseller product
    """
    try:
        cron_logger.info('Tag Product Mapping Started')
        # last 15 days
        days = get_config('ECOM_BESTSELLER_DAYS')
        from_date = datetime.datetime.today() - datetime.timedelta(days=days)
        # Get all Franchise Shop
        shops = Shop.objects.filter(shop_type__shop_type='f', status=True, approval_status=2, 
                                pos_enabled=True)
        # Get all Tags
        tag = Tag.objects.all()
        for shop in shops:
            cron_logger.info('Started Mapping Best Seller Product for shop {}'.format(shop))
            try:
                best_seller_tag = tag.get(key='best-seller')
                count = 0
                tag_product = TagProductMapping.objects.filter(product__shop = shop, tag = best_seller_tag).order_by('-created_at')
                
                # Get online order product
                online_order = Order.objects.filter(ordered_cart__cart_type='ECOM', created_at__gte = from_date, seller_shop=shop)
                online_ordered_product = CartProductMapping.objects.filter(cart__order_id__in = online_order.values_list('order_no'))
                online_product = RetailerProduct.objects.filter(rt_cart_retailer_product__in = online_ordered_product)
                product = online_product.annotate(prd_count=Count('id')).order_by('-prd_count')

                #Update Tagged Product
                if product.exists():
                    cron_logger.info('Started Adding {} online best seller product for shop {}'.format(product.count(), shop.id))
                    count, tag_product = update_tag(best_seller_tag, tag_product, 0, product, count)
                    cron_logger.info('Successfully Added {} online best seller product for shop {}'.format(product.count(), shop.id))
                else:
                    cron_logger.info('No online best seller product for shop {}'.format(product.count(), shop.id))

                # Get offline order if product is less than 6
                if count < 6:
                    offline_order = Order.objects.filter(ordered_cart__cart_type='BASIC', created_at__gte = from_date, seller_shop=shop)
                    offline_ordered_product = OrderedProductMapping.objects.filter(ordered_product__order__in = offline_order)
                    total_offline_product = RetailerProduct.objects.filter(rt_retailer_product_order_product__in = offline_ordered_product, online_enabled = True)
                    rem_offline_product = total_offline_product.annotate(prd_count=Count('id')).order_by('-prd_count')[:count]

                    #Update Tagged Product
                    if rem_offline_product.exists():
                        cron_logger.info('Started Adding {} offline best seller product for shop {}'.format(rem_offline_product.count(), shop.id))
                        count, tag_product = update_tag(best_seller_tag, tag_product, 0, rem_offline_product, count)
                        cron_logger.info('Successfully Added {} offline best seller product for shop {}'.format(rem_offline_product.count(), shop.id))
                    else:
                        cron_logger.info('No offline best seller product for shop {}'.format(product.count(), shop.id))
                    
                # add random product in case of no online and offline order
                if count < 6:
                    exclude_product_id = product.values('id') | rem_offline_product.values('id')
                    random_product = RetailerProduct.objects.exclude(id__in = exclude_product_id).filter(online_enabled = True)[:count]

                    # Update Tag product mapping
                    if random_product.exists():
                        cron_logger.info('Started Adding {} random product for shop {}'.format(random_product.count(), shop.id))
                        count, tag_product = update_tag(best_seller_tag, tag_product, 0, random_product, count)
                        cron_logger.info('Successfully Added {} random product for shop {}'.format(random_product.count(), shop.id))
                    else:
                        cron_logger.info('No random product for shop {}'.format(product.count(), shop.id))
            except Exception as e:
                cron_logger.error(e)
                cron_logger.error('Stopped Mapping Best Seller Product for shop {}'.format(shop))
    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Cron for tag product mapping stopped')