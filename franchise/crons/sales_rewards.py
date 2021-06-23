import sys
import os

from django.db import transaction

from franchise.models import FranchiseSales, ShopLocationMap
from products.models import Product
from global_config.models import GlobalConfig
from pos.tasks import order_loyalty_points_credit
from accounts.models import User
from marketing.models import ReferralCode


def process_rewards_on_sales():

    hdpos_shops_str = GlobalConfig.objects.filter(key="hdpos_loyalty_shop_ids").last()
    pos_shops_str = GlobalConfig.objects.get(key='order_loyalty_active_shops').value
    sales_objs = FranchiseSales.objects.filter(rewards_status=0)

    if sales_objs.exists():

        for sales_obj in sales_objs:
            try:
                with transaction.atomic():
                    shop_map = ShopLocationMap.objects.filter(location_name=sales_obj.shop_loc).last()
                    if not shop_map:
                        update_sales_ret_obj(sales_obj, 2, 'shop mapping not found')
                        continue
                    if pos_shops_str == 'all' or (pos_shops_str and shop_map.shop.id in pos_shops_str.split(',')):
                        update_sales_ret_obj(sales_obj, 2, 'shop not eligible for reward')
                        continue
                    if not hdpos_shops_str or (hdpos_shops_str and shop_map.shop.id not in hdpos_shops_str.split(',')):
                        update_sales_ret_obj(sales_obj, 2, 'shop not eligible for reward')
                        continue
                    if not Product.objects.filter(product_sku=sales_obj.product_sku).exists():
                        update_sales_ret_obj(sales_obj, 2, 'product sku not matched')
                        continue
                    ret = rewards_account(sales_obj, shop_map)
                    if ret:
                        update_sales_ret_obj(sales_obj, 1)
                    else:
                        update_sales_ret_obj(sales_obj, 2, 'user not found')
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                update_sales_ret_obj(sales_obj, False, "{} {} {}".format(exc_type, fname, exc_tb.tb_lineno))


def rewards_account(sales_obj, shop_map):
    """
        Account for used rewards by user w.r.t sales order
        Account for rewards to referrer (direct and indirect) w.r.t sales order
    """
    if sales_obj.phone_number and sales_obj.phone_number != '':
        sales_user = User.objects.filter(phone_number=sales_obj.phone_number).last()
        if sales_user and ReferralCode.is_marketing_user(sales_user):
            order_loyalty_points_credit(sales_obj.amount, sales_user.id, sales_obj.id, 'purchase_reward',
                                        'indirect_reward', None, shop_map.shop.id)
            return True
    return False


def update_sales_ret_obj(obj, rewards_status, error=''):
    obj.rewards_status = rewards_status
    if error != '':
        obj.error = error
    obj.save()