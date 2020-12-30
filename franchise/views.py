from django.db.models import Q
from django.views import View
from django.contrib import messages
from django.shortcuts import render, redirect
import csv
import codecs
from django.http import HttpResponse
from io import StringIO

from shops.models import Shop
from franchise.forms import FranchiseStockForm
from franchise.models import get_default_virtual_bin_id
from products.models import Product
from wms.models import Bin


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
            first_row = next(reader)

            # download file
            filename = 'franchise_stock_correction' + ".csv"
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            writer = csv.writer(response)
            writer.writerow(
                ['Status', 'Error', 'Barcode', 'Shop Id', 'Stock Qty', 'Warehouse ID', 'Product Name', 'SKU',
                 'Expiry Date', 'Bin ID',
                 'Normal Quantity', 'Damaged Quantity', 'Expired Quantity', 'Missing Quantity'])

            for row in reader:
                product_ean_match_count = Product.objects.filter(product_ean_code=row[0]).count()
                if product_ean_match_count <= 0:
                    writer.writerow(["Error", "Product doesn't exist", row[0], row[1], row[2]])
                    continue
                if product_ean_match_count > 1:
                    writer.writerow(["Error", "Multiple products exist", row[0], row[1], row[2]])
                    continue
                try:
                    shop_obj = Shop.objects.get(pk=int(row[1]), shop_type__shop_type='f', approval_status=2)
                except Exception as e:
                    writer.writerow(["Error", "No approved franchise shop", row[0], row[1], row[2]])
                    continue
                try:
                    bin_obj = Bin.objects.get(warehouse_id=int(row[1]),
                                              bin_id=get_default_virtual_bin_id())
                except Exception as e:
                    writer.writerow(["Error", "Bin doesn't exist", row[0], row[1], row[2]])
                    continue

                sku = Product.objects.get(product_ean_code=row[0])

                row[2] = row[2] if int(row[2]) > 0 else 0
                writer.writerow(
                    ['Processed', '', row[0], row[1], row[2], row[1], sku.product_name, sku.product_sku, '01/01/2024',
                     bin_obj.bin_id, row[2], '0', '0', '0'])

            return response

    def get(self, request, *args, **kwargs):
        form_path = 'admin/franchise/stockcsvconvert.html'
        form = FranchiseStockForm()
        return render(request, form_path, {'form': form})


class DownloadFranchiseStockCSV(View):

    def get(self, request, *args, **kwargs):
        filename = 'sample_franchise_stock' + ".csv"
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(['Barcode', 'Shop Id', 'Stock Qty'])
        writer.writerow(['8901233035567_100', '35040', '500'])
        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response
