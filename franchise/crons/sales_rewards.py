import sys
import os

from django.db import transaction

from franchise.models import FranchiseSales, ShopLocationMap
from products.models import Product
from global_config.models import GlobalConfig
from franchise.crons.cron import rewards_account


def process_rewards_on_sales():
    shops = []
    specific_shops = GlobalConfig.objects.filter(key="hdpos_users_from_shops").last()
    if specific_shops and specific_shops.value not in [None, '']:
        shops_str = specific_shops.value
        shops = shops_str.split('|')
    sales_objs = FranchiseSales.objects.filter(rewards_status=0)

    if sales_objs.exists():
        try:
            conf_obj = GlobalConfig.objects.get(key='total_reward_percent_of_order')
            total_reward_percent = conf_obj.value
        except:
            total_reward_percent = 10
        try:
            conf_obj = GlobalConfig.objects.get(key='direct_reward_percent')
            direct_reward_percent = conf_obj.value
        except:
            direct_reward_percent = 50

        for sales_obj in sales_objs:
            try:
                with transaction.atomic():
                    if shops and shops != [] and not sales_obj.shop_loc in shops:
                        update_sales_ret_obj(sales_obj, 2, 'shop not eligible for reward')
                        continue
                    if not ShopLocationMap.objects.filter(location_name=sales_obj.shop_loc).exists():
                        update_sales_ret_obj(sales_obj, 2, 'shop mapping not found')
                        continue
                    if not Product.objects.filter(product_sku=sales_obj.product_sku).exists():
                        update_sales_ret_obj(sales_obj, 2, 'product sku not matched')
                        continue
                    ret = rewards_account(sales_obj, total_reward_percent, direct_reward_percent)
                    if ret:
                        update_sales_ret_obj(sales_obj, 1)
                    else:
                        update_sales_ret_obj(sales_obj, 2, 'user not found')
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                update_sales_ret_obj(sales_obj, False, "{} {} {}".format(exc_type, fname, exc_tb.tb_lineno))


def update_sales_ret_obj(obj, rewards_status, error=''):
    obj.rewards_status = rewards_status
    if error != '':
        obj.error = error
    obj.save()