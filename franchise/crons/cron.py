import logging
import datetime
import pyodbc
import sys
import os
from django.db import transaction
from decouple import config

from franchise.models import FranchiseSales, ShopLocationMap, FranchiseReturns, HdposDataFetch
from products.models import Product
from wms.common_functions import (CommonWarehouseInventoryFunctions, WareHouseInternalInventoryChange,
                                 InternalInventoryChange, franchise_inventory_in, OutCommonFunctions)
from wms.models import BinInventory, WarehouseInventory, InventoryState, InventoryType, Bin
from franchise.models import get_default_virtual_bin_id

cron_logger = logging.getLogger('cron_log')
CONNECTION_PATH = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + config('HDPOS_DB_HOST')\
                  + ';DATABASE=' + config('HDPOS_DB_NAME')\
                  + ';UID=' + config('HDPOS_DB_USER') \
                  +';PWD=' + config('HDPOS_DB_PASSWORD')


def franchise_sales_returns_inventory():
    cron_logger.info('Franchise Cron Started')
    sales_fetch_resp = fetch_franchise_sales()
    if 'code' in sales_fetch_resp and sales_fetch_resp['code'] == 'success':
        franchise_inv_resp = franchise_inventory_sales_cron()
        returns_fetch_resp = fetch_franchise_returns()
        if 'code' in returns_fetch_resp and returns_fetch_resp['code'] == 'success' \
                and 'code' in franchise_inv_resp and franchise_inv_resp['code'] == 'success':
            franchise_inventory_returns_cron()
        else:
            cron_logger.info('Counld not fetch returns data/sales data not processed')
    else:
        cron_logger.info('Counld not fetch sales data')


def fetch_franchise_sales():
    #testing
    return {'code': 'success'}
    #testing
    try:
        if HdposDataFetch.objects.filter(type=0, status__in=[0, 1]).exists():
            hdpos_obj_last = HdposDataFetch.objects.filter(type=0, status__in=[0, 1]).last()
            next_date = hdpos_obj_last.to_date
        else:
            next_date = datetime.datetime(int(config('HDPOS_START_YEAR')), int(config('HDPOS_START_MONTH')),
                                          int(config('HDPOS_START_DATE')), 0, 0, 0)

        cron_logger.info('franchise sales fetch | started {}'.format(next_date))
        if next_date <= datetime.datetime.now():
            hdpos_obj = HdposDataFetch.objects.create(type=0, from_date=next_date, to_date=datetime.datetime.now())

            try:
                cnxn = pyodbc.connect(CONNECTION_PATH)
                cron_logger.info('connected to hdpos | sales {}'.format(next_date))
                cursor = cnxn.cursor()

                fd = open('franchise/crons/sql/sales.sql', 'r')
                sqlfile = fd.read()
                fd.close()

                cron_logger.info('file read | sales {}'.format(next_date))
                sqlfile = sqlfile + "'" + str(next_date) + "'"
                cursor.execute(sqlfile)

                cron_logger.info('writing sales data {}'.format(next_date))

                with transaction.atomic():
                    for row in cursor:
                        FranchiseSales.objects.create(shop_loc=row[1], barcode=row[8], quantity=row[5], amount=row[6],
                                                      invoice_date=row[2], invoice_number=row[3])

                hdpos_obj.status = 1
                hdpos_obj.save()
                return {'code' : 'success'}

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                hdpos_obj.status = 2
                hdpos_obj.process_text = "{} {} {}".format(exc_type, fname, exc_tb.tb_lineno)
                hdpos_obj.save()
                return {'code': 'failed'}

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        cron_logger.info('Franchise sales fetch exception {} {} {}'.format(exc_type, fname, exc_tb.tb_lineno))
        return {'code': 'failed'}


def franchise_inventory_sales_cron():
    try:
        sales_objs = FranchiseSales.objects.filter(process_status=0)
        if sales_objs.exists():
            type_normal = InventoryType.objects.filter(inventory_type='normal').last(),
            state_available = InventoryState.objects.filter(inventory_state='available').last(),
            state_shipped = InventoryState.objects.filter(inventory_state='shipped').last(),

            for sales_obj in sales_objs:
                if not ShopLocationMap.objects.filter(location_name=sales_obj.shop_loc).exists():
                    sales_obj.process_status = 2
                    sales_obj.error = 'shop mapping not found'
                    sales_obj.save()
                    continue

                product_ean_match_count = Product.objects.filter(product_ean_code=sales_obj.barcode).count()

                if product_ean_match_count <= 0:
                    sales_obj.process_status = 2
                    sales_obj.error = 'product barcode not found'
                    sales_obj.save()
                    continue

                if product_ean_match_count > 1:
                    sales_obj.process_status = 2
                    sales_obj.error = 'multiple products found'
                    sales_obj.save()
                    continue

                shop_map = ShopLocationMap.objects.filter(location_name=sales_obj.shop_loc).last()
                warehouse = shop_map.shop
                bin_obj = Bin.objects.filter(warehouse=warehouse, bin_id=get_default_virtual_bin_id()).last()
                sku = Product.objects.filter(product_ean_code=sales_obj.barcode).last()
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

    try:
        with transaction.atomic():
            if quantity > 0:
                transaction_type = 'franchise_sales'
                transaction_id = sales_obj.id
                ware_house_inventory_obj = WarehouseInventory.objects.filter(warehouse=warehouse, sku=sku, inventory_state=state_available[0],
                                                                             inventory_type=type_normal[0], in_stock=True).last()
                if not ware_house_inventory_obj:
                    sales_obj.process_status = 2
                    sales_obj.error = 'warehouse object does not exist'
                    sales_obj.save()
                elif ware_house_inventory_obj.quantity < quantity:
                    sales_obj.process_status = 2
                    sales_obj.error = 'quantity not present in warehouse'
                    sales_obj.save()
                else:
                    CommonWarehouseInventoryFunctions.create_warehouse_inventory(warehouse, sku, type_normal[0], state_available[0],
                                                                                 quantity * -1, True)
                    CommonWarehouseInventoryFunctions.create_warehouse_inventory(warehouse, sku, type_normal[0], state_shipped[0],
                                                                                 quantity, True)
                    WareHouseInternalInventoryChange.create_warehouse_inventory_change(warehouse, sku, transaction_type, transaction_id,
                                                                                       type_normal[0], state_available[0], type_normal[0],
                                                                                       state_shipped[0], quantity)

                    bin_inv_objs = BinInventory.objects.filter(warehouse=warehouse, bin=bin_obj, sku=sku, quantity__gt=0,
                                                              inventory_type=type_normal[0], in_stock=True).order_by(
                        '-batch_id',
                        'quantity')
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
                                                          quantity,
                                                          type_normal[0])
                            InternalInventoryChange.create_bin_internal_inventory_change(warehouse, sku, batch_id,
                                                                                         bin_obj, type_normal[0],
                                                                                         type_normal[0], transaction_type,
                                                                                         transaction_id,
                                                                                         already_picked)
                        else:
                            already_picked = qty_in_bin
                            remaining_qty = qty - already_picked
                            bin_inv.quantity = qty_in_bin - already_picked
                            bin_inv.save()
                            qty = remaining_qty
                            OutCommonFunctions.create_out(warehouse, transaction_type, transaction_id, sku, batch_id,
                                                          quantity,
                                                          type_normal[0])
                            InternalInventoryChange.create_bin_internal_inventory_change(warehouse, sku, batch_id,
                                                                                         bin_obj,
                                                                                         type_normal[0], type_normal[0],
                                                                                         transaction_type,
                                                                                         transaction_id,
                                                                                         already_picked)
                    sales_obj.process_status = 1
                    sales_obj.save()
            else:
                sales_obj.process_status = 2
                sales_obj.error = 'sales quantity not positive'
                sales_obj.save()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        sales_obj.process_status = 2
        sales_obj.error = "{} {} {}".format(exc_type, fname, exc_tb.tb_lineno)
        sales_obj.save()


def fetch_franchise_returns():
    # testing
    return {'code': 'success'}
    # testing

    try:
        if HdposDataFetch.objects.filter(type=1, status__in=[0, 1]).exists():
            hdpos_obj_last = HdposDataFetch.objects.filter(type=1, status__in=[0, 1]).last()
            next_date = hdpos_obj_last.to_date
        else:
            next_date = datetime.datetime(int(config('HDPOS_START_YEAR')), int(config('HDPOS_START_MONTH')),
                                          int(config('HDPOS_START_DATE')), 0, 0, 0)

        cron_logger.info('franchise returns fetch | started {}'.format(next_date))

        if next_date <= datetime.datetime.now():
            hdpos_obj = HdposDataFetch.objects.create(type=1, from_date=next_date, to_date=datetime.datetime.now())

            try:
                cnxn = pyodbc.connect(CONNECTION_PATH)
                cron_logger.info('connected to hdpos | returns {}'.format(next_date))
                cursor = cnxn.cursor()

                fd = open('franchise/crons/sql/returns.sql', 'r')
                sqlfile = fd.read()
                fd.close()

                cron_logger.info('file read | returns {}'.format(next_date))
                sqlfile = sqlfile + "'" + str(next_date) + "'"
                cursor.execute(sqlfile)

                cron_logger.info('writing returns data {}'.format(next_date))

                with transaction.atomic():
                    for row in cursor:
                        FranchiseReturns.objects.create(shop_loc=row[8], barcode=row[6], quantity=row[3], amount=row[4],
                                                        sr_date=row[0], sr_number=row[1], invoice_number=row[10])

                hdpos_obj.status = 1
                hdpos_obj.save()

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                hdpos_obj.status = 2
                hdpos_obj.process_text = "{} {} {}".format(exc_type, fname, exc_tb.tb_lineno)
                hdpos_obj.save()

        return {'code': 'success'}
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        cron_logger.info('Franchise returns fetch exception {} {} {}'.format(exc_type, fname, exc_tb.tb_lineno))
        return {'code': 'failed'}


def franchise_inventory_returns_cron():
    try:
        returns_objs = FranchiseReturns.objects.filter(process_status=0)
        if returns_objs.exists():
            initial_type = InventoryType.objects.filter(inventory_type='normal').last(),
            final_type = InventoryType.objects.filter(inventory_type='normal').last(),
            initial_stage = InventoryState.objects.filter(inventory_state='shipped').last(),
            final_stage = InventoryState.objects.filter(inventory_state='available').last(),

            for return_obj in returns_objs:
                if not ShopLocationMap.objects.filter(location_name=return_obj.shop_loc).exists():
                    return_obj.process_status = 2
                    return_obj.error = 'shop mapping not found'
                    return_obj.save()
                    continue

                product_ean_match_count = Product.objects.filter(product_ean_code=return_obj.barcode).count()

                if product_ean_match_count <= 0:
                    return_obj.process_status = 2
                    return_obj.error = 'product barcode not found'
                    return_obj.save()
                    continue

                if product_ean_match_count > 1:
                    return_obj.process_status = 2
                    return_obj.error = 'multiple products found'
                    return_obj.save()
                    continue

                if return_obj.quantity >=0:
                    return_obj.process_status = 2
                    return_obj.error = 'return quantity is positive'
                    return_obj.save()
                    continue

                shop_map = ShopLocationMap.objects.filter(location_name=return_obj.shop_loc).last()
                warehouse = shop_map.shop
                bin_obj = Bin.objects.filter(warehouse=warehouse, bin_id=get_default_virtual_bin_id()).last()
                sku = Product.objects.filter(product_ean_code=return_obj.barcode).last()
                try:
                    with transaction.atomic():
                        default_expiry = datetime.date(int(config('FRANCHISE_IN_DEFAULT_EXPIRY_YEAR')), 1, 1)
                        batch_id = '{}{}'.format(sku.product_sku, default_expiry.strftime('%d%m%y'))
                        ware_house_inventory_obj = WarehouseInventory.objects.filter(warehouse=warehouse, sku=sku,
                                                                                     inventory_state=initial_stage[0],
                                                                                     inventory_type=initial_type[0],
                                                                                     in_stock=True).last()
                        if not ware_house_inventory_obj:
                            return_obj.process_status = 2
                            return_obj.error = 'shipping warehouse object does not exist'
                            return_obj.save()
                        elif ware_house_inventory_obj.quantity < return_obj.quantity * -1:
                            return_obj.process_status = 2
                            return_obj.error = 'quantity not present in shipped warehouse entry'
                            return_obj.save()
                        else:
                            franchise_inventory_in(warehouse, sku, batch_id, return_obj.quantity * -1, 'franchise_returns', return_obj.id,
                                                   final_type, initial_type, initial_stage, final_stage, bin_obj)
                            return_obj.process_status = 1
                            return_obj.save()

                except Exception as e:

                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    return_obj.process_status = 2
                    return_obj.error = "{} {} {}".format(exc_type, fname, exc_tb.tb_lineno)
                    return_obj.save()

        return {'code': 'success'}
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        cron_logger.info('Franchise sales inv exception {} {} {}'.format(exc_type, fname, exc_tb.tb_lineno))
        return {'code': 'failed'}