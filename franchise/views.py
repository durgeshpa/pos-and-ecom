import datetime
import sys
import os
import csv
import codecs
from io import StringIO

import pyodbc
from django.db.models import Q
from django.views import View
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse
from decouple import config
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from shops.models import Shop
from franchise.forms import FranchiseStockForm
from franchise.models import get_default_virtual_bin_id, ShopLocationMap, FranchiseSales
from products.models import Product
from wms.models import Bin
from franchise.crons.cron import process_sales_data

CONNECTION_PATH = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + config('HDPOS_DB_HOST') \
                              + ';DATABASE=' + config('HDPOS_DB_NAME') \
                              + ';UID=' + config('HDPOS_DB_USER') \
                              + ';PWD=' + config('HDPOS_DB_PASSWORD')

# Create your views here.


class ProductList(View):
    """
        Product List to display on admin site under B2C Franchise Management
        To link to products mapped with the particular Franchise shop mapped with the logged in user
    """

    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.is_superuser:
            franchise_shop = Shop.objects.filter(shop_type__shop_type__in=['f'])
            franchise_shop = franchise_shop.filter(Q(related_users=user) | Q(shop_owner=user)).last()
            if franchise_shop:
                return redirect('/admin/shops/shop-mapped/' + str(franchise_shop.id) + '/product/')
            messages.add_message(request, messages.ERROR, 'No Franchise Shop Mapping Exists To Show Product List For')
        return redirect('/admin/')


class StockCsvConvert(View):

    def post(self, request, *args, **kwargs):
        form_path = 'admin/franchise/stockcsvconvert.html'
        form = FranchiseStockForm(request.POST, request.FILES)
        if form.errors:
            return render(request, form_path, {'form': form})

        if form.is_valid():
            file = form.cleaned_data['file']
            reader = csv.reader(codecs.iterdecode(file, 'utf-8', errors='ignore'))

            # download file
            filename = 'franchise_stock_correction' + ".csv"
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            writer = csv.writer(response)
            process_stock_data(reader, writer)

            return response

    def get(self, request, *args, **kwargs):
        form_path = 'admin/franchise/stockcsvconvert.html'
        form = FranchiseStockForm()
        return render(request, form_path, {'form': form})


def process_stock_data(reader, writer):
    cnxn = pyodbc.connect(CONNECTION_PATH)
    fd = open('franchise/management/sku_query.sql', 'r')
    sqlfile = fd.read()
    fd.close()

    first_row = next(reader)
    writer.writerow(first_row + ['Status', 'Error', 'Warehouse ID',
                                 'Product Name', 'SKU', 'Expiry Date', 'Bin ID', 'Normal Quantity',
                                 'Damaged Quantity', 'Expired Quantity', 'Missing Quantity'])

    for row in reader:
        row = [i.strip() for i in row]
        row[5] = int(float(row[5]))
        row[4] = int(float(row[4]))

        pro_check = check_product(row[0], cnxn, sqlfile)

        if not pro_check['status']:
            writer.writerow(row + ["Error", pro_check['error']])
            continue
        try:
            shop_loc = ShopLocationMap.objects.get(location_name=row[2])
        except Exception as e:
            writer.writerow(row + ["Error", "No shop location map exists"])
            continue
        try:
            shop_obj = Shop.objects.get(pk=shop_loc.shop.id, shop_type__shop_type='f', approval_status=2)
        except Exception as e:
            writer.writerow(row + ["Error", "Shop not approved"])
            continue
        try:
            bin_obj = Bin.objects.get(warehouse=shop_obj,
                                      bin_id=get_default_virtual_bin_id())
        except Exception as e:
            writer.writerow(row + ["Error", "Bin doesn't exist"])
            continue

        sku = pro_check['sku']

        qty = row[5] if row[5] > 0 else 0
        writer.writerow(row + ['Processed', '', shop_obj.id, sku.product_name, sku.product_sku, '01/01/2024',
                               bin_obj.bin_id, qty, '0', '0', '0'])


def check_product(ean, cnxn, sqlfile):
    cursor = cnxn.cursor()
    sqlfile = sqlfile + "'" + ean + "'"
    cursor.execute(sqlfile)
    sku = []
    for row in cursor:
        sku += [row[0]]
    if len(sku) < 1:
        return {'status': False, 'error': 'No Sku found'}
    elif len(sku) == 1:
        if not sku[0]:
            return {'status': False, 'error': 'No Sku found'}
        try:
            product = Product.objects.get(product_sku=row[0])
            return {'status': True, 'sku': product}
        except:
            return {'status': False, 'error': 'Could not fetch product {}'.format(row[0])}
    else:
        return {'status': False, 'error': 'Multiple Sku found'}


class DownloadFranchiseStockCSV(View):

    def get(self, request, *args, **kwargs):
        filename = 'sample_franchise_stock' + ".csv"
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(['ITEMCODE (required)', 'ITEMNAME', 'WAREHOUSENAME (required)', 'CATEGORYNAME',
                         'MRP (required)', 'CURRENTSTOCK (required)', 'STOCKVALUEONMRP'])
        writer.writerow(['8901233035567_100', '', 'Pepper Tape (K Mart Grocery Store)', '', '50', '500', ''])
        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response


class AddSales(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        try:
            shop_id = request.GET.get('shop_id')
            if not shop_id:
                return Response({"error": "provide shop_id"}, status=status.HTTP_200_OK)
            product_sku = request.GET.get('product_sku')
            if not product_sku:
                return Response({"error": "provide product_sku"}, status=status.HTTP_200_OK)
            phone_number = request.GET.get('phone_number')
            if not phone_number:
                return Response({"error": "provide phone_number"}, status=status.HTTP_200_OK)
            quantity = request.GET.get('quantity')
            if not quantity:
                return Response({"error": "provide quantity"}, status=status.HTTP_200_OK)
            amount = request.GET.get('amount')
            if not amount:
                return Response({"error": "provide amount"}, status=status.HTTP_200_OK)
            try:
                shop = ShopLocationMap.objects.get(shop_id=shop_id)
            except:
                return Response({"error": "shop not found"}, status=status.HTTP_200_OK)

            try:
                product = Product.objects.get(product_sku=product_sku)
            except:
                return Response({"error": "product not found"}, status=status.HTTP_200_OK)

            sales_obj = FranchiseSales.objects.create(shop_loc=shop.location_name, barcode='9999', quantity=quantity,
                                                      amount=amount, invoice_date=datetime.date.today(),
                                                      invoice_number='ABCD',
                                                      product_sku=product.product_sku, customer_name='monali',
                                                      phone_number=phone_number, discount_amount=10)
            resp = process_sales_data(sales_obj.id)
            return Response(resp, status=status.HTTP_200_OK)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error = "{} {} {} {}".format(exc_type, fname, exc_tb.tb_lineno, e)
            return Response({"error": error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
