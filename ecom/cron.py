# python imports
import logging
import datetime
from django.db.models import Count, F, Case, When, IntegerField, Q

# app imports
from .models import Tag, TagProductMapping
from pos.models import RetailerProduct, InventoryChangePos
from pos.common_functions import PosInventoryCls
from wms.models import PosInventoryState
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
                TagProductMapping.objects.filter(id = tag_product[count].id).update(product = product[start], modified_at = datetime.datetime.now())
            else:
                TagProductMapping.objects.create(tag = tag, product = product[start])
            count += 1
            start += 1
        return count, tag_product
    except Exception as e:
        print(e)

def check_inventory(product):
    exclude_product_id = []
    sliced_product = product[0:min(product.count(),100)]
    for prd in sliced_product:
        available_inventory = PosInventoryCls.get_available_inventory(prd.id, PosInventoryState.AVAILABLE)
        if available_inventory < 1:
            exclude_product_id.append(prd.id)
    product = product.exclude(id__in = exclude_product_id)
    return product


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
                online_product = RetailerProduct.objects.filter(rt_cart_retailer_product__in = online_ordered_product, status = 'active', is_deleted=False, online_enabled=True)
                # Inventory Check and exclude product whose inventory is not available
                online_product = check_inventory(online_product)
                #sort by max value
                product = online_product.annotate(prd_count=Count('id')).order_by('-prd_count').distinct()
                #Update Tagged Product
                if product.exists():
                    cron_logger.info('Started Adding online best seller product')
                    count, tag_product = update_tag(best_seller_tag, tag_product, 0, product, count)
                    cron_logger.info('Successfully Added online best seller product for shop')
                else:
                    cron_logger.info('No online best seller product for shop')

                # Get offline order if product is less than 6
                if count < 6:
                    exclude_online_product = product.values('id')
                    offline_order = Order.objects.filter(ordered_cart__cart_type='BASIC', created_at__gte = from_date, seller_shop=shop)
                    offline_ordered_product = OrderedProductMapping.objects.filter(ordered_product__order__in = offline_order)
                    total_offline_product = RetailerProduct.objects.exclude(id__in = exclude_online_product, sku_type = 4).filter(rt_retailer_product_order_product__in = offline_ordered_product, online_enabled = True, status = 'active', is_deleted=False)
                    # Inventory Check and exclude product whose inventory is not available
                    total_offline_product = check_inventory(total_offline_product)
                    #Sort by max count
                    rem_offline_product = total_offline_product.annotate(prd_count=Count('id')).order_by('-prd_count').distinct()
                    #Update Tagged Product
                    if rem_offline_product.exists():
                        cron_logger.info('Started Adding offline best seller product for shop')
                        count, tag_product = update_tag(best_seller_tag, tag_product, 0, rem_offline_product, count)
                        cron_logger.info('Successfully Added offline best seller product for shop')
                    else:
                        cron_logger.info('No offline best seller product for shop')
                    
                # add random product in case of no online and offline order
                if count < 6:
                    exclude_product_id = product.values('id') | rem_offline_product.values('id')
                    random_product = RetailerProduct.objects.exclude(id__in = exclude_product_id, sku_type = 4).filter(online_enabled = True, status = 'active', shop = shop, is_deleted=False).order_by('-id')
                    # Inventory Check and exclude product whose inventory is not available
                    random_product = check_inventory(random_product)
                    # Update Tag product mapping
                    if random_product.exists():
                        cron_logger.info('Started Adding random product for shop')
                        count, tag_product = update_tag(best_seller_tag, tag_product, 0, random_product, count)
                        cron_logger.info('Successfully Added random product for shop')
                    else:
                        cron_logger.info('No random product for shop')
            except Exception as e:
                cron_logger.error(e)
                cron_logger.error('Stopped Mapping Best Seller Product for shop {}'.format(shop))
            
            #Mapping Best Deals Product
            cron_logger.info('Started Mapping Best Deal Product for shop {}'.format(shop))
            try:  
                count = 0
                best_deal_tag = tag.get(key='best-deals')
                product = RetailerProduct.objects.exclude(sku_type = 4).filter(online_enabled=True, status = 'active', shop = shop, is_deleted=False)
                tag_product = TagProductMapping.objects.filter(product__shop = shop, tag = best_deal_tag).order_by('-created_at')
                #sort product by max diff in mrp and selling price
                product = product.annotate(
                    price_diff = Case(
                        When(online_price__isnull = True, then=F('mrp')-F('selling_price')),
                        When(online_price__isnull = False, then=F('mrp')-F('online_price')),
                        output_field=IntegerField(),
                    )).order_by('-price_diff').distinct()
                # Inventory Check and exclude product whose inventory is not available
                product = check_inventory(product)
                if product.exists():
                    cron_logger.info('Started Adding best deal product for shop')
                    count, tag_product = update_tag(best_deal_tag, tag_product, 0, product, count)
                    cron_logger.info('Successfully Added best deals product for shop')
                else:
                    cron_logger.info('No Product for shop')
            except Exception as e:
                cron_logger.error(e)
                cron_logger.error('Stopped Mapping Best Deals Product for shop {}'.format(shop))

            # Mapping Freshly Arrived Product
            cron_logger.info('Started Mapping Freshly Arrived Product for shop {}'.format(shop))
            try:
                count = 0
                freshly_arrived_tag = tag.get(key='freshly-arrived')
                tag_product = TagProductMapping.objects.filter(product__shop = shop, tag = freshly_arrived_tag).order_by('-created_at')
                fresh_inventory = InventoryChangePos.objects.filter(Q(transaction_type = 'GRN Add') | Q(transaction_type = 'GRN Update'))
                fresh_product = RetailerProduct.objects.filter(id__in = fresh_inventory.values('product__id'), shop = shop, is_deleted=False, online_enabled=True)
                # Inventory Check and exclude product whose inventory is not available
                fresh_product = check_inventory(fresh_product)
                if fresh_product.exists():
                    cron_logger.info('Started Adding freshly arrived product for shop')
                    count, tag_product = update_tag(freshly_arrived_tag, tag_product, 0, fresh_product, count)
                    cron_logger.info('Successfully Added freshly arrived product for shop')
                else:
                    cron_logger.info('No Product for shop')
            except Exception as e:
                cron_logger.error(e)
                cron_logger.error('Stopped Mapping Freshly Arrived Product for shop {}'.format(shop))
    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Cron for tag product mapping stopped')