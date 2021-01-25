import logging
import datetime
import pyodbc
import sys
import os
from django.db import transaction
from decouple import config
from django.utils import timezone
import traceback

from franchise.models import FranchiseSales, ShopLocationMap, FranchiseReturns, HdposDataFetch
from products.models import Product
from wms.common_functions import (CommonWarehouseInventoryFunctions,
                                 InternalInventoryChange, franchise_inventory_in, OutCommonFunctions)
from wms.models import BinInventory, WarehouseInventory, InventoryState, InventoryType, Bin
from franchise.models import get_default_virtual_bin_id
from services.models import CronRunLog
from marketing.models import Referral, RewardPoint, MLMUser, RewardLog
from global_config.models import GlobalConfig

cron_logger = logging.getLogger('cron_log')
CONNECTION_PATH = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + config('HDPOS_DB_HOST')\
                  + ';DATABASE=' + config('HDPOS_DB_NAME')\
                  + ';UID=' + config('HDPOS_DB_USER') \
                  +';PWD=' + config('HDPOS_DB_PASSWORD')


def franchise_sales_returns_inventory():
    """
        Cron
        Fetch sales and returns data from hdpos server
        Process sales and returns data to adjust franchise inventory
    """

    cron_name = CronRunLog.CRON_CHOICE.FRANCHISE_SALES_RETURNS_CRON
    if CronRunLog.objects.filter(cron_name=cron_name, status=CronRunLog.CRON_STATUS_CHOICES.STARTED).exists():
        cron_logger.info("{} already running".format(cron_name))
        return

    cron_log_entry = CronRunLog.objects.create(cron_name=cron_name)
    cron_logger.info("{} started, cron log entry-{}"
                     .format(cron_log_entry.cron_name, cron_log_entry.id))

    try:
        # fetch sales data from hdpos
        to_date = datetime.datetime.now() - datetime.timedelta(minutes=60)
        sales_fetch_resp = fetch_franchise_data('sales', to_date)

        if 'code' in sales_fetch_resp and sales_fetch_resp['code'] == 'success':

            # process sales data to adjust franchise inventory
            franchise_inv_resp = process_sales_data()

            # fetch returns data from hdpos
            returns_fetch_resp = fetch_franchise_data('returns', to_date)

            if 'code' in returns_fetch_resp and returns_fetch_resp['code'] == 'success' \
                    and 'code' in franchise_inv_resp and franchise_inv_resp['code'] == 'success':

                # process returns data to adjust franchise inventory
                process_returns_data()
            else:
                cron_logger.info('Could not fetch returns data/sales data not processed')
        else:
            cron_logger.info('Could not fetch sales data')

        cron_log_entry.status = CronRunLog.CRON_STATUS_CHOICES.COMPLETED
        cron_log_entry.completed_at = timezone.now()
        cron_logger.info("{} completed, cron log entry-{}".format(cron_log_entry.cron_name, cron_log_entry.id))

    except Exception as e:
        cron_log_entry.status = CronRunLog.CRON_STATUS_CHOICES.ABORTED
        cron_logger.info("{} aborted, cron log entry-{}".format(cron_name, cron_log_entry.id))
        traceback.print_exc()
    cron_log_entry.save()


def fetch_franchise_data(fetch_name, to_date):
    """
        Fetch Sales/Returns Data From Hdpos Server For Franchise Shops

        fetch_name: "sales" or "returns"
    """

    try:
        # proceed from last successful time till now
        fetch_type = 0 if fetch_name == 'sales' else 1

        if HdposDataFetch.objects.filter(type=int(fetch_type), status__in=[0, 1]).exists():
            hdpos_obj_last = HdposDataFetch.objects.filter(type=int(fetch_type), status__in=[0, 1]).last()
            from_date = hdpos_obj_last.to_date
        else:
            from_date = datetime.datetime(int(config('HDPOS_START_YEAR')), int(config('HDPOS_START_MONTH')),
                                          int(config('HDPOS_START_DATE')), 0, 0, 0)

        cron_logger.info('franchise {} fetch | started {}'.format(fetch_name, from_date))

        if from_date <= datetime.datetime.now():
            # create log for this run
            hdpos_obj = HdposDataFetch.objects.create(type=int(fetch_type), from_date=from_date,
                                                      to_date=to_date)

            try:
                cnxn = pyodbc.connect(CONNECTION_PATH)
                cron_logger.info('connected to hdpos | {} {}'.format(fetch_name, from_date))
                cursor = cnxn.cursor()

                module_dir = os.path.dirname(__file__)
                file_path = os.path.join(module_dir, 'sql/' + fetch_name + '.sql')
                fd = open(file_path, 'r')
                sqlfile = fd.read()
                fd.close()

                cron_logger.info('file read | {} {}'.format(fetch_name, from_date))
                sqlfile = sqlfile.format(str(from_date.strftime('%Y-%m-%d %H:%M:%S')), str(to_date.strftime('%Y-%m-%d %H:%M:%S')))
                cursor.execute(sqlfile)

                cron_logger.info('writing {} data {}'.format(fetch_name, from_date))

                if fetch_type == 1:
                    with transaction.atomic():
                        for row in cursor:
                            row[11] = '' if not row[11] else row[11].strip()
                            row[12] = '' if not row[12] else row[12].strip()
                            row[13] = '' if not row[13] else row[13].replace(' ', '')
                            row[13] = '' if len(row[13]) != 10 else row[13]

                            FranchiseReturns.objects.create(shop_loc=row[8], barcode=row[6], quantity=row[3], amount=row[4],
                                                            sr_date=row[0], sr_number=row[1], invoice_number=row[10],
                                                            product_sku=row[11], customer_name=row[12], phone_number=row[13])
                else:
                    with transaction.atomic():
                        for row in cursor:
                            row[9] = '' if not row[9] else row[9].strip()
                            row[10] = '' if not row[10] else row[10].strip()
                            row[11] = '' if not row[11] else row[11].replace(' ', '')
                            row[11] = '' if len(row[11]) != 10 else row[11]

                            FranchiseSales.objects.create(shop_loc=row[1], barcode=row[8], quantity=row[5], amount=row[6],
                                                          invoice_date=row[2], invoice_number=row[3],
                                                          product_sku=row[9], customer_name=row[10],
                                                          phone_number=row[11], discount_amount=row[12])

                hdpos_obj.status = 1
                hdpos_obj.save()

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                hdpos_obj.status = 2
                hdpos_obj.process_text = "{} {} {}".format(exc_type, fname, exc_tb.tb_lineno)
                hdpos_obj.save()
                return {'code': 'failed'}

        return {'code': 'success'}

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        cron_logger.info('Franchise {} fetch exception {} {} {}'.format(fetch_name, exc_type, fname, exc_tb.tb_lineno))
        return {'code': 'failed'}


def process_sales_data(id=''):
    """
        Proceed Inventory Adjustment Accounting for Sales of Franchise Shops
    """
    try:
        if id != '':
            sales_objs = FranchiseSales.objects.filter(pk=id)
        else:
            sales_objs = FranchiseSales.objects.filter(process_status__in=[0, 2])
        if sales_objs.exists():
            type_normal = InventoryType.objects.filter(inventory_type='normal').last(),
            state_available = InventoryState.objects.filter(inventory_state='total_available').last(),
            state_shipped = InventoryState.objects.filter(inventory_state='shipped').last(),

            for sales_obj in sales_objs:
                if not ShopLocationMap.objects.filter(location_name=sales_obj.shop_loc).exists():
                    update_sales_ret_obj(sales_obj, 2, 'shop mapping not found')
                    continue

                try:
                    sku = Product.objects.get(product_sku=sales_obj.product_sku)
                except:
                    update_sales_ret_obj(sales_obj, 2, 'product sku not matched')
                    continue

                shop_map = ShopLocationMap.objects.filter(location_name=sales_obj.shop_loc).last()
                warehouse = shop_map.shop
                if warehouse.approval_status != 2:
                    update_sales_ret_obj(sales_obj, 2, 'warehouse is not approved')
                    continue

                bin_obj = Bin.objects.filter(warehouse=warehouse, bin_id=get_default_virtual_bin_id()).last()
                sales_inventory_update_franchise(warehouse, bin_obj, sales_obj.quantity, type_normal, state_shipped,
                                                 state_available, sku, sales_obj)
        return {'code': 'success'}
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        cron_logger.info('Franchise sales inv exception {} {} {}'.format(exc_type, fname, exc_tb.tb_lineno))
        return {'code': 'failed'}


def sales_inventory_update_franchise(warehouse, bin_obj, quantity, type_normal, state_shipped,
                                             state_available, sku, sales_obj):
    """
        Inventory Adjustment (available to shipped) Accounting for Sales of single Franchise Shop.

        warehouse: Franchise shop
        bin_obj: default virtual bin for warehouse
        quantity: sold sku quantity
        type_normal: Tuple containing Inventory Type (normal) object
        state_shipped: Tuple containing Inventory State (shipped) object
        sku: Product sold
        sales_obj: Collected sales record from hdpos
    """

    try:
        with transaction.atomic():
            if quantity > 0:
                transaction_type = 'franchise_sales'
                transaction_id = sales_obj.id

                # check if inventory exists to be sold
                ware_house_inventory_obj = WarehouseInventory.objects.filter(warehouse=warehouse, sku=sku, inventory_state=state_available[0],
                                                                             inventory_type=type_normal[0], in_stock=True).last()
                if not ware_house_inventory_obj:
                    update_sales_ret_obj(sales_obj, 2, 'warehouse object does not exist')
                elif ware_house_inventory_obj.quantity < quantity:
                    update_sales_ret_obj(sales_obj, 2, 'quantity not present in warehouse')
                else:
                    # out quantity from warehouse available
                    CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                        warehouse, sku, type_normal[0], state_available[0], quantity * -1, transaction_type, transaction_id)
                    # in quantity to warehouse shipped
                    CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                        warehouse, sku, type_normal[0], state_shipped[0], quantity, transaction_type, transaction_id)
                    # get all warehouse bins where sku quantity is present
                    bin_inv_objs = BinInventory.objects.filter(warehouse=warehouse, bin=bin_obj, sku=sku, quantity__gt=0,
                                                               inventory_type=type_normal[0],
                                                               in_stock=True).order_by('-batch_id', 'quantity')
                    # first expiry first out logic
                    bin_inv_dict = get_bin_inv_dict(bin_inv_objs)

                    # adjust full quantity in bin inventory according to first expiry first out
                    qty = quantity
                    for bin_inv in bin_inv_dict.keys():
                        if qty == 0:
                            break
                        already_picked = 0
                        batch_id = bin_inv.batch_id if bin_inv else None
                        qty_in_bin = bin_inv.quantity if bin_inv else 0
                        if qty - already_picked <= qty_in_bin:
                            already_picked += qty
                            remaining_qty = qty_in_bin - already_picked
                            bin_inv.quantity = remaining_qty
                            bin_inv.save()
                            qty = 0
                            OutCommonFunctions.create_out(warehouse, transaction_type, transaction_id, sku, batch_id,
                                                          already_picked, type_normal[0])
                            InternalInventoryChange.create_bin_internal_inventory_change(warehouse, sku, batch_id, bin_obj,
                                                                                         type_normal[0], type_normal[0],
                                                                                         transaction_type, transaction_id,
                                                                                         already_picked)
                        else:
                            already_picked = qty_in_bin
                            remaining_qty = qty - already_picked
                            bin_inv.quantity = qty_in_bin - already_picked
                            bin_inv.save()
                            qty = remaining_qty
                            OutCommonFunctions.create_out(warehouse, transaction_type, transaction_id, sku, batch_id,
                                                          already_picked, type_normal[0])
                            InternalInventoryChange.create_bin_internal_inventory_change(warehouse, sku, batch_id, bin_obj,
                                                                                         type_normal[0], type_normal[0],
                                                                                         transaction_type, transaction_id,
                                                                                         already_picked)
                    update_sales_ret_obj(sales_obj, 1)
                    rewards_account(sales_obj)
            else:
                update_sales_ret_obj(sales_obj, 2, 'sales quantity not positive')

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        update_sales_ret_obj(sales_obj, 2, "{} {} {}".format(exc_type, fname, exc_tb.tb_lineno))


def process_returns_data():
    """
        Proceed Inventory Adjustment Accounting for Returns of Franchise Shops
    """
    try:
        returns_objs = FranchiseReturns.objects.filter(process_status__in=[0, 2])
        if returns_objs.exists():
            initial_type = InventoryType.objects.filter(inventory_type='normal').last(),
            final_type = InventoryType.objects.filter(inventory_type='normal').last(),
            initial_stage = InventoryState.objects.filter(inventory_state='shipped').last(),
            final_stage = InventoryState.objects.filter(inventory_state='total_available').last(),
            initial_type1 = InventoryType.objects.filter(inventory_type='new').last(),
            initial_stage1 = InventoryState.objects.filter(inventory_state='new').last(),

            for return_obj in returns_objs:
                if not ShopLocationMap.objects.filter(location_name=return_obj.shop_loc).exists():
                    update_sales_ret_obj(return_obj, 2, 'shop mapping not found')
                    continue

                try:
                    sku = Product.objects.get(product_sku=return_obj.product_sku)
                except:
                    update_sales_ret_obj(return_obj, 2, 'product sku not matched')
                    continue

                if return_obj.quantity >=0:
                    update_sales_ret_obj(return_obj, 2, 'return quantity is positive')
                    continue

                shop_map = ShopLocationMap.objects.filter(location_name=return_obj.shop_loc).last()
                warehouse = shop_map.shop
                if warehouse.approval_status != 2:
                    update_sales_ret_obj(return_obj, 2, 'warehouse is not approved')
                    continue
                bin_obj = Bin.objects.filter(warehouse=warehouse, bin_id=get_default_virtual_bin_id()).last()
                try:
                    with transaction.atomic():
                        default_expiry = datetime.date(int(config('FRANCHISE_IN_DEFAULT_EXPIRY_YEAR')), 1, 1)
                        batch_id = '{}{}'.format(sku.product_sku, default_expiry.strftime('%d%m%y'))

                        if return_obj.invoice_date and return_obj.invoice_date != '' and return_obj.invoice_date < datetime.datetime(2020, 12, 29, 0, 0, 0):
                            franchise_inventory_in(warehouse, sku, batch_id, return_obj.quantity * -1, 'franchise_returns', return_obj.id,
                                                   final_type, initial_type1, initial_stage1, final_stage, bin_obj, False)
                            update_sales_ret_obj(return_obj, 1)
                        else:
                            ware_house_inventory_obj = WarehouseInventory.objects.filter(warehouse=warehouse, sku=sku,
                                                                                         inventory_state=initial_stage[0],
                                                                                         inventory_type=initial_type[0],
                                                                                         in_stock=True).last()
                            if not ware_house_inventory_obj:
                                update_sales_ret_obj(return_obj, 2, 'shipping warehouse object does not exist')
                            elif ware_house_inventory_obj.quantity < return_obj.quantity * -1:
                                update_sales_ret_obj(return_obj, 2, 'quantity not present in shipped warehouse entry')
                            else:
                                franchise_inventory_in(warehouse, sku, batch_id, return_obj.quantity * -1, 'franchise_returns', return_obj.id,
                                                       final_type, initial_type, initial_stage, final_stage, bin_obj, True)
                                update_sales_ret_obj(return_obj, 1)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    update_sales_ret_obj(return_obj, 2, "{} {} {}".format(exc_type, fname, exc_tb.tb_lineno))

        return {'code': 'success'}
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        cron_logger.info('Franchise sales inv exception {} {} {}'.format(exc_type, fname, exc_tb.tb_lineno))
        return {'code': 'failed'}


def get_bin_inv_dict(bin_inv_objs):
    # for first expiry first out logic

    bin_inv_dict = {}
    for k in bin_inv_objs:
        if len(k.batch_id) == 23:
            bin_inv_dict[k] = str(datetime.datetime.strptime(
                k.batch_id[17:19] + '-' + k.batch_id[19:21] + '-' + '20' + k.batch_id[21:23],
                "%d-%m-%Y"))
        else:
            bin_inv_dict[k] = str(
                datetime.datetime.strptime('30-' + k.batch_id[17:19] + '-20' + k.batch_id[19:21],
                                           "%d-%m-%Y"))

    bin_inv_list = list(bin_inv_dict.items())
    bin_inv_dict = dict(sorted(dict(bin_inv_list).items(), key=lambda x: x[1]))

    return  bin_inv_dict


def update_sales_ret_obj(obj, status, error=''):
    obj.process_status = status
    if error != '':
        obj.error = error
    obj.save()


def rewards_account(sales_obj):
    """
        Account for used rewards by user w.r.t sales order
        Account for rewards to referrer (direct and indirect) w.r.t sales order
    """

    if sales_obj.phone_number and sales_obj.phone_number != '':
        sales_user = MLMUser.objects.filter(phone_number=sales_obj.phone_number).last()
        if sales_user:
            referrer_reward(sales_user, sales_obj.id)


def referrer_reward(sales_user, transaction_id):
    """
        Account for reward (direct and indirect) w.r.t sales order
    """

    # Check if some user referred sales_user from referral_obj

    referral_obj = Referral.objects.filter(referral_to=sales_user).last()
    if referral_obj:
        referred_by = referral_obj.referral_by
        try:
            conf_obj = GlobalConfig.objects.get(key='direct_reward_factor')
            direct_reward_factor = int(conf_obj.value)
        except:
            direct_reward_factor = 4

        # account for direct reward to user who referred sales_user
        reward_obj = RewardPoint.objects.filter(user=referred_by).last()
        if reward_obj:
            reward_obj.direct_users += 1
            reward_obj.direct_earned += direct_reward_factor
            reward_obj.save()
        else:
            RewardPoint.objects.create(user=referred_by, direct_users=1, direct_earned=direct_reward_factor)

        RewardLog.objects.create(user=referred_by, transaction_type='direct_reward',
                                 transaction_id=transaction_id, points=direct_reward_factor)

        # account for indirect reward to user who referred user who referred sales_user
        referral_obj_indirect = Referral.objects.filter(referral_to=referred_by).last()
        if referral_obj_indirect:
            referral_by_indirect = referral_obj_indirect.referral_by
            try:
                conf_obj = GlobalConfig.objects.get(key='indirect_reward_factor')
                indirect_reward_factor = int(conf_obj.value)
            except:
                indirect_reward_factor = 3

            reward_obj = RewardPoint.objects.filter(user=referral_by_indirect).last()
            if reward_obj:
                reward_obj.indirect_users += 1
                reward_obj.indirect_earned += indirect_reward_factor
                reward_obj.save()
            else:
                RewardPoint.objects.create(user=referral_by_indirect, indirect_users=1, indirect_earned=indirect_reward_factor)

            RewardLog.objects.create(user=referral_by_indirect, transaction_type='indirect_reward',
                                     transaction_id=transaction_id, points=indirect_reward_factor)

        referral_obj.reward_status = 1
        referral_obj.save()

