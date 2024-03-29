# python imports
import logging

from ecom.models import UserPastPurchases
from global_config.views import get_config
from products.models import Product
from retailer_to_sp.views import generate_e_invoice
from sp_to_gram.tasks import upload_all_products_in_es
from retailer_to_sp.models import Order, OrderReturn, OrderedProduct
from global_config.models import GlobalConfig
from pos.tasks import order_loyalty_points_credit
from marketing.models import ReferralCode
import datetime
info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')


def all_products_es_refresh():
    cron_logger.info('RefreshEs| Started for index named all_products')
    try:
        upload_all_products_in_es()
        cron_logger.info_logger('RefreshEs has been done for index named all_products')
    except Exception as e:
        cron_logger.error('Exception during ES refresh .........', e)


def generate_e_invoice_cron():
    generate_e_invoice()


def get_back_date(day=0):
    """return back date accourding to given date"""
    return datetime.datetime.today() - datetime.timedelta(days=day)

def order_point_credit(order):
    try:
        returns = OrderReturn.objects.filter(order=order)
        return_amount = 0
        ordered_product = OrderedProduct.objects.get(order=order)
        for ret in returns:
            return_amount += ret.refund_amount
        new_paid_amount = ordered_product.invoice_amount_final - return_amount

        if ReferralCode.is_marketing_user(order.buyer):
            points_added = order_loyalty_points_credit(new_paid_amount, order.buyer.id, order.order_no,
                                                            'order_credit', 'order_indirect_credit',
                                                            order.buyer.id, order.seller_shop, app_type="SUPERSTORE")
        ordered_product.points_added = True
        ordered_product.save()
    except Exception as e:
        info_logger.error(e)


def get_super_store_order():
    info_logger.info("cron super_store_order add redeem point Started...")
    day = GlobalConfig.objects.get(key='return_window_day').value
    end_date = get_back_date(day)
    start_date = get_back_date(day+1)
    orders = OrderedProduct.objects.prefetch_related().\
             filter(order__order_app_type='pos_superstore', modified_at__gte=start_date,
                  modified_at__lte=end_date, shipment_status="DELIVERED", points_added=False)

    for order in orders:
        order_point_credit(order.order)
    info_logger.info("cron super_store_order add redeem point finished...")




def past_purchases_retail():
    try:
        cron_logger.info('past_purchases Started')
        # last 15 days
        days = get_config('RetailerBestSeller')
        from_date = datetime.datetime.today() - datetime.timedelta(days=days)
        try:
            # Get order product
            past_orders = Order.objects.filter(ordered_cart__cart_type__in=['RETAIL'], created_at__gte=from_date,
                                                seller_shop__status=True,
                                               )
            cron_logger.info(f"Order Count {past_orders.count()}")
            for order in past_orders:
                past_ordered_product = order.ordered_cart.rt_cart_list.all()
                cron_logger.info(f"Order{order.order_no} |  Product Count {past_ordered_product.count()}")

                products_purchased = Product.objects.filter(rt_cart_product_mapping__in=past_ordered_product,
                                                                    status='active',)
                # Update Tagged Product
                if products_purchased.exists():
                    for p in products_purchased:
                        UserPastPurchases.objects.update_or_create(buyer_shop=order.buyer_shop, shop=order.seller_shop, retail_Product=p,
                                                                   defaults={'last_purchased_at':order.created_at})
        except Exception as e:
            cron_logger.info("past_purchases | Failed")
            cron_logger.error(e)
        cron_logger.info("past_purchases | Completed")

    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Cron for past purchases stopped')


