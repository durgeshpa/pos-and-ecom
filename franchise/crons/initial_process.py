import datetime
import pyodbc
import os
from io import StringIO
import sys
import csv
import logging
from decouple import config
import math
from django.core.files import File
from django.core.mail import EmailMessage
from django.db import transaction

from global_config.models import GlobalConfig
from franchise.models import ShopLocationMap
from products.models import Product
from wms.forms import validation_stock_correction
from wms.common_functions import StockMovementCSV
from wms.views import stock_correction_data
from accounts.models import User
from franchise.models import HdposInventoryHistory, WmsInventoryHistory

cron_logger = logging.getLogger('cron_log')
CONNECTION_PATH = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + config('HDPOS_DB_HOST') \
                  + ';DATABASE=' + config('HDPOS_DB_NAME') \
                  + ';UID=' + config('HDPOS_DB_USER') \
                  + ';PWD=' + config('HDPOS_DB_PASSWORD')


def initial_inventory_franchise():
    try:
        curr_date = datetime.datetime.now()
        curr_date = curr_date.strftime('%Y-%m-%d %H:%M:%S')

        # connectiong to hdpos database
        cnxn = pyodbc.connect(CONNECTION_PATH)
        cron_logger.info('Franchise initial | connected to hdpos inventory fetch')
        cursor = cnxn.cursor()

        # execute query to get realtime inventory from hdpos
        module_dir = os.path.dirname(__file__)
        file_path = os.path.join(module_dir, 'sql/inventory.sql')
        fd = open(file_path, 'r')
        sqlfile = fd.read()
        fd.close()
        cursor.execute(sqlfile)
        cron_logger.info('Franchise initial | hdpos inventory query executed')

        # store exact inventory data from hdpos
        raw_f = StringIO()
        raw_writer = csv.writer(raw_f)

        # store hdpos inventory data in wms stock correction format for 'PepperTap (Gram Mart, Chipyana)' and 'PepperTap (Anshika Store)'
        stock_file_path = os.path.join(module_dir, 'initial_stock.csv')

        prepare_files(raw_writer, stock_file_path, cursor)
        cron_logger.info('Franchise initial | files prepared')
        add_to_wms(stock_file_path)
        cron_logger.info('Franchise initial | stock added wms')
        enable_trip_close_inventory()
        cron_logger.info('Franchise initial | grn enabled')
        email_report(curr_date, raw_f)
        cron_logger.info('Franchise initial | mailed, completed')

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        cron_logger.info('Franchise initial | exception {} {} {} {}'.format(exc_type, fname, exc_tb.tb_lineno, e))


def add_to_wms(stock_file_path):
    with transaction.atomic():
        user = User.objects.get(phone_number='7763886418')
        stock_file = open(stock_file_path, 'rb')
        data = validation_stock_correction(stock_file, user, 'f')
        stock_movement_obj = StockMovementCSV.create_stock_movement_csv(user, File(file=stock_file,
                                                                                   name='franchise_stock_add_34016_34037.csv'), 3)
        stock_correction_data(data, stock_movement_obj)


def enable_trip_close_inventory():
    trip_inv_add_config = GlobalConfig.objects.filter(key='franchise_inv_add_trip_block').last()
    trip_inv_add_config.value = 0
    trip_inv_add_config.save()


def email_report(curr_date, file):
    email = EmailMessage()
    email.subject = 'HDPOS Inventory'
    sender = GlobalConfig.objects.get(key='hdpos_sender')
    email.from_email = sender.value
    receiver = GlobalConfig.objects.get(key='hdpos_recipient')
    email.to = eval(receiver.value)
    email.attach('hdpos_initial_inventory_{}'.format(curr_date) + '.csv', file.getvalue(), 'text/csv')
    email.send()


def prepare_files(raw_writer, stock_file_path, cursor):
    with open(stock_file_path, 'w') as sf:
        stock_writer = csv.writer(sf)
        headings = ['Shop_name', 'warehouse_id', 'Barcode', 'item_id', 'product_sku', 'product_name', 'category', 'hsn',
                    'Tax_structure', 'GST_flag', 'MRP', 'PTC', 'Realtime_available_qty', 'Last90daysaleqty', 'error']
        stock_headings = ['Warehouse ID', 'Product Name', 'SKU', 'Expiry Date', 'Bin ID',
                          'Normal Quantity', 'Damaged Quantity', 'Expired Quantity', 'Missing Quantity']

        raw_writer.writerow(headings)
        stock_writer.writerow(stock_headings)
        count = 0

        for row in cursor:
            if row[0] not in ['PepperTap (Gram Mart, Chipyana)', 'PepperTap (Anshika Store)']:
                continue
            count += 1
            if not row[0]:
                HdposInventoryHistory.objects.create(shop_name=row[0], product_sku=row[4], product_name=row[5],
                                                     quantity=row[12], error='shop_name')
                raw_writer.writerow(list(row) + ['shop_name'])
                continue
            row[0] = row[0].strip()
            if not ShopLocationMap.objects.filter(location_name=row[0]).exists():
                HdposInventoryHistory.objects.create(shop_name=row[0], product_sku=row[4], product_name=row[5],
                                                     quantity=row[12], error='shop_mapping')
                raw_writer.writerow(list(row) + ['shop_mapping'])
                continue
            if row[4] is None or row[4] == '':
                HdposInventoryHistory.objects.create(shop_name=row[0], product_sku=row[4], product_name=row[5],
                                                     quantity=row[12], error='product_sku')
                raw_writer.writerow(list(row) + ['product_sku'])
                continue
            row[4] = row[4].strip()
            if not Product.objects.filter(product_sku=row[4]).exists():
                HdposInventoryHistory.objects.create(shop_name=row[0], product_sku=row[4], product_name=row[5],
                                                     quantity=row[12], error='product')
                raw_writer.writerow(list(row) + ['product'])
                continue
            try:
                row[12] = int(row[12])
                raw_writer.writerow(list(row))
                HdposInventoryHistory.objects.create(shop_name=row[0], product_sku=row[4], product_name=row[5],
                                                     quantity=row[12], error='')
            except ValueError:
                row[12] = float(row[12])
                raw_writer.writerow(list(row) + ['float_quantity'])
                HdposInventoryHistory.objects.create(shop_name=row[0], product_sku=row[4], product_name=row[5],
                                                     quantity=row[12], error='float_quantity')
            # add to warehouse for Anshika store and Chipyana store only
            row[12] = math.ceil(row[12])
            if row[0] == 'PepperTap (Gram Mart, Chipyana)':
                WmsInventoryHistory.objects.create(warehouse_id=34016, sku_id=row[4], quantity=row[12])
                stock_writer.writerow(
                    [34016, row[5], row[4], '01/01/2024', 'V2VZ01SR001-0001', row[12], 0, 0, 0])
            elif row[0] == 'PepperTap (Anshika Store)':
                WmsInventoryHistory.objects.create(warehouse_id=34037, sku_id=row[4], quantity=row[12])
                stock_writer.writerow(
                    [34037, row[5], row[4], '01/01/2024', 'V2VZ01SR001-0001', row[12], 0, 0, 0])
