import codecs
import io
import csv
import decimal
import requests
import logging
import os
import datetime
from copy import deepcopy
from decimal import Decimal

from requests.models import Response

from dal import autocomplete
from dateutil.relativedelta import relativedelta
from django.db.models import Q, Sum

from django.http import HttpResponse, JsonResponse, response, Http404, FileResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.contrib import messages

from django.views import View
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from wkhtmltopdf.views import PDFTemplateResponse

from pos.common_functions import RetailerProductCls, PosInventoryCls, ProductChangeLogs
from pos.models import RetailerProduct, RetailerProductImage, PosCart, DiscountedRetailerProduct, \
    MeasurementCategory, RetailerOrderedReport, Payment, RetailerOrderedProduct, RetailerOrderReturn
from pos.forms import RetailerProductsCSVDownloadForm, RetailerProductsCSVUploadForm, RetailerProductMultiImageForm, \
    PosInventoryChangeCSVDownloadForm, RetailerProductsStockUpdateForm, RetailerOrderedReportForm
from pos.tasks import generate_pdf_data, update_es
from products.models import Product, ParentProductCategory
from shops.models import Shop, PosShopUserMapping
from retailer_to_sp.models import OrderReturn, OrderedProduct, CreditNote
from wms.models import PosInventory, PosInventoryState, PosInventoryChange

info_logger = logging.getLogger('file-info')


class RetailerProductAutocomplete(autocomplete.Select2QuerySetView):
    """
    Retailer Product Filter for Discounted Products
    """
    def get_queryset(self, *args, **kwargs):
        qs = RetailerProduct.objects.none()
        shop = self.forwarded.get('shop', None)
        if shop:
            qs = RetailerProduct.objects.filter(~Q(sku_type=4), shop=shop)
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs


class RetailerProductShopAutocomplete(autocomplete.Select2QuerySetView):
    """
    Shop Filter for Retailer and Franchise Shops
    """

    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['f'])
        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


def download_retailer_products_list_form_view(request):
    """
    Products Catalogue Download View
    """
    form = RetailerProductsCSVDownloadForm()
    return render(
        request,
        'admin/pos/retailerproductscsvdownload.html',
        {'form': form}
    )


def download_discounted_products_form_view(request):
    """
    Products Catalogue Download View
    """
    form = RetailerProductsCSVDownloadForm()
    return render(
        request,
        'admin/pos/discounted_product_download.html',
        {'form': form}
    )


def bulk_create_update_products(request, shop_id, form, uploaded_data_by_user_list):
    with transaction.atomic():
        for row in uploaded_data_by_user_list:
            measure_cat_id = None
            if row.get('measurement_category'):
                measure_cat_id = MeasurementCategory.objects.get(category=row.get('measurement_category')).id

            if str(row.get('available_for_online_orders').lower()) == 'yes':
                row['online_enabled'] = True
            else:
                row['online_enabled'] = False

            if row['online_order_price']:
                row['online_price'] = decimal.Decimal(row['online_order_price'])
            else:
                row['online_price'] = None

            if str(row['is_visible']).lower() == 'yes':
                row['is_deleted'] = False
            else:
                row['is_deleted'] = True

            if str(row['product_pack_type']).lower() == 'loose':
                purchase_pack_size = 1
            else:
                purchase_pack_size = int(row.get('purchase_pack_size')) if row.get('purchase_pack_size') else 1

            if row['offer_price']:
                row['offer_price'] = decimal.Decimal(row['offer_price'])
            else:
                row['offer_price'] = None

            if not row['offer_start_date']:
                row['offer_start_date'] = None

            if not row['offer_end_date']:
                row['offer_end_date'] = None

            name, ean, mrp, sp, offer_price, offer_sd, offer_ed, linked_pid, description, stock_qty, \
            online_enabled, online_price, is_visible,product_pack_type = row.get('product_name'), row.get('product_ean_code'), \
                                                       row.get('mrp'), row.get('selling_price'), row.get('offer_price', None), \
                                                       row.get('offer_start_date', None), row.get('offer_end_date', None), None, \
                                                       row.get('description'), row.get('quantity'), row['online_enabled'], \
                                                       row['online_price'], row['is_deleted'] , row.get('product_pack_type',None)

            if row.get('product_id') == '':
                # we need to create this product
                # if else condition for checking whether, Product we are creating is linked with existing product or not
                # with the help of 'linked_product_id'
                measure_cat_id = None
                if row.get('measurement_category'):
                    measure_cat_id = MeasurementCategory.objects.get(category=row.get('measurement_category')).id
                if 'linked_product_sku' in row.keys() and not row.get('linked_product_sku') == '':
                    if row.get('linked_product_sku') != '':
                        # If product is linked with existing product
                        if Product.objects.filter(product_sku=row.get('linked_product_sku')):
                            product = Product.objects.get(product_sku=row.get('linked_product_sku'))
                            r_product = RetailerProductCls.create_retailer_product(shop_id, name, mrp,
                                                                       sp, product.id, 2, description, ean,
                                                                       request.user, 'product',
                                                                       row.get('product_pack_type').lower(),
                                                                       measure_cat_id, None,
                                                                       row.get('status'), offer_price, offer_sd,
                                                                       offer_ed, None, online_enabled, online_price,
                                                                       purchase_pack_size, is_visible)
                else:
                    # If product is not linked with existing product, Create a new Product with SKU_TYPE == "Created"
                    r_product = RetailerProductCls.create_retailer_product(shop_id, name, mrp,
                                                               sp, linked_pid, 1, description, ean, request.user,
                                                               'product', row.get('product_pack_type').lower(),
                                                               measure_cat_id, None, row.get('status'),
                                                               offer_price, offer_sd, offer_ed, None,
                                                               online_enabled, online_price,
                                                               purchase_pack_size, is_visible)
                # Add Inventory
                PosInventoryCls.stock_inventory(r_product.id, PosInventoryState.NEW, PosInventoryState.AVAILABLE,
                                                round(Decimal(row.get('quantity')), 3), request.user,
                                                r_product.sku,
                                                PosInventoryChange.STOCK_ADD)

            else:
                # we need to update existing product

                if str(row.get('available_for_online_orders').lower()) == 'yes':
                    row['online_enabled'] = True
                else:
                    row['online_enabled'] = False

                if str(row.get('is_visible')).lower() == 'yes':
                    row['is_deleted'] = False
                else:
                    row['is_deleted'] = True

                if row['online_order_price']:
                    row['online_price'] = decimal.Decimal(row['online_order_price'])
                else:
                    row['online_price'] = None

                if row['purchase_pack_size']:
                    if str(row['product_pack_type']).lower() == 'loose':
                        purchase_pack_size = 1
                    else:
                        purchase_pack_size = int(row.get('purchase_pack_size'))
                try:
                    product = RetailerProduct.objects.get(id=row.get('product_id'))
                    old_product = deepcopy(product)

                    if (row.get('linked_product_sku') != '' and Product.objects.get(
                            product_sku=row.get('linked_product_sku'))):
                        linked_product = Product.objects.get(product_sku=row.get('linked_product_sku'))
                        product.linked_product_id = linked_product.id

                    if product.selling_price != row.get('selling_price'):
                        product.selling_price = row.get('selling_price')

                    if product.status != row.get('status'):
                        if row.get('status') == 'deactivated':
                            product.status = 'deactivated'
                        else:
                            product.status = "active"

                    if product.is_deleted != row['is_deleted']:
                        product.is_deleted = row['is_deleted']

                    if product.name != row.get('product_name'):
                        product.name = row.get('product_name')

                    if product.online_enabled != row['online_enabled']:
                        product.online_enabled = row['online_enabled']
                    if product.online_price != row['online_price']:
                        product.online_price = row['online_price']

                    if product.description != row.get('description'):
                        product.description = row.get('description')

                    if product.purchase_pack_size != purchase_pack_size:
                        product.purchase_pack_size = purchase_pack_size

                    if row['offer_price']:
                        product.offer_price = decimal.Decimal(row['offer_price'])

                    if row['offer_start_date']:
                        product.offer_start_date = row['offer_start_date']

                    if row['offer_end_date']:
                        product.offer_end_date = row['offer_end_date']

                    if product_pack_type:
                        product.product_pack_type = product_pack_type.lower()

                    product.measurement_category_id = measure_cat_id

                    product.save()

                    # Create discounted products while updating Products
                    if row.get('discounted_price', None):
                        discounted_price = decimal.Decimal(row['discounted_price'])
                        discounted_stock = int(row['discounted_stock'])
                        product_status = 'active' if decimal.Decimal(discounted_stock) > 0 else 'deactivated'

                        initial_state = PosInventoryState.AVAILABLE
                        tr_type = PosInventoryChange.STOCK_UPDATE

                        discounted_product = RetailerProduct.objects.filter(product_ref=product).last()
                        if not discounted_product:

                            initial_state = PosInventoryState.NEW
                            tr_type = PosInventoryChange.STOCK_ADD

                            discounted_product = RetailerProductCls.create_retailer_product(product.shop.id,
                                                                                            product.name,
                                                                                            product.mrp,
                                                                                            discounted_price,
                                                                                            product.linked_product_id,
                                                                                            4,
                                                                                            product.description,
                                                                                            product.product_ean_code,
                                                                                            request.user,
                                                                                            'product',
                                                                                            product.product_pack_type,
                                                                                            product.measurement_category_id,
                                                                                            None, product_status,
                                                                                            None, None, None, product,
                                                                                            False, None)
                        else:
                            RetailerProductCls.update_price(discounted_product.id, discounted_price, product_status,
                                                            request.user, 'product', discounted_product.sku)

                        PosInventoryCls.stock_inventory(discounted_product.id, initial_state,
                                                        PosInventoryState.AVAILABLE, discounted_stock,
                                                        request.user,
                                                        discounted_product.sku, tr_type, None)

                    # Change logs
                    ProductChangeLogs.product_update(product, old_product, request.user, 'product',
                                                     product.sku)
                except:
                    return render(request, 'admin/pos/retailerproductscsvupload.html',
                                  {'form': form,
                                   'error': "Please check for correct format"})


def upload_retailer_products_list(request):
    """
    Products Catalogue Upload View
    """
    shop_id = request.POST.get('shop')
    if request.method == 'POST':
        form = RetailerProductsCSVUploadForm(request.POST, request.FILES, shop_id=shop_id)

        if form.errors:
            return render(request, 'admin/pos/retailerproductscsvupload.html', {'form': form})

        if form.is_valid():

            # product_status = request.POST.get('catalogue_product_status')
            reader = csv.reader(codecs.iterdecode(request.FILES.get('file'), 'utf-8', errors='ignore'))
            header = next(reader, None)
            uploaded_data_by_user_list = []
            csv_dict = {}
            count = 0
            for id, row in enumerate(reader):
                for ele in row:
                    csv_dict[header[count]] = ele
                    count += 1
                uploaded_data_by_user_list.append(csv_dict)
                csv_dict = {}
                count = 0
            # if product_status == 'create_products':
            bulk_create_update_products(request, shop_id, form, uploaded_data_by_user_list)
            # else:
            #     bulk_create_update_products(request, shop_id, form, uploaded_data_by_user_list)

            return render(request, 'admin/pos/retailerproductscsvupload.html',
                          {'form': form,
                           'success': 'Products Created/Updated Successfully!', })
    else:
        form = RetailerProductsCSVUploadForm()
        return render(
            request,
            'admin/pos/retailerproductscsvupload.html',
            {'form': form}
        )


def retailer_products_list(product):
    """
        This function will return product related linked_product_sku, sku_type, category, sub_category, brand & sub_brand
    """
    linked_product_sku = ''
    sku_type = product.sku_type
    sku_type = RetailerProductCls.get_sku_type(sku_type)
    category = ''
    sub_category = ''
    brand = ''
    sub_brand = ''
    if product.linked_product:
        linked_product_sku = product.linked_product.product_sku
        prodct = Product.objects.values('parent_product__parent_brand__brand_name',
                                        'parent_product__parent_brand__brand_parent__brand_name')\
                                .filter(Q(id=product.linked_product.id))
        if prodct[0]['parent_product__parent_brand__brand_parent__brand_name']:
            brand = prodct[0]['parent_product__parent_brand__brand_parent__brand_name']
            sub_brand = prodct[0]['parent_product__parent_brand__brand_name']
        else:
            brand = prodct[0]['parent_product__parent_brand__brand_name']

        cat = ParentProductCategory.objects.values('category__category_name',
                                                   'category__category_parent__category_name').filter \
            (parent_product__id=product.linked_product.parent_product.id)
        if cat[0]['category__category_parent__category_name']:
            category = cat[0]['category__category_parent__category_name']
            sub_category = cat[0]['category__category_name']
        else:
            category = cat[0]['category__category_name']
    return linked_product_sku, sku_type, category, sub_category, brand, sub_brand


def DownloadRetailerCatalogue(request, *args):
    """
    This function will return an File in csv format which can be used for Downloading the Product Catalogue
    (It is used when user wants to update retailer products)
    """
    shop_id = request.GET['shop_id']
    filename = "retailer_products_update_sample_file.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(
        ['product_id', 'shop_id', 'shop_name', 'product_sku', 'product_name', 'mrp', 'selling_price',
         'linked_product_sku', 'product_ean_code', 'description', 'sku_type', 'category', 'sub_category',
         'brand', 'sub_brand', 'status', 'quantity', 'discounted_sku', 'discounted_stock','discounted_price', 'product_pack_type',
         'measurement_category', 'purchase_pack_size', 'available_for_online_orders', 'online_order_price',
         'is_visible','offer_price','offer_start_date','offer_end_date'])

    product_qs = RetailerProduct.objects.filter(~Q(sku_type=4), shop_id=int(shop_id), is_deleted=False)
    if product_qs.exists():
        retailer_products = product_qs \
            .prefetch_related('linked_product') \
            .prefetch_related('linked_product__parent_product__parent_brand') \
            .prefetch_related('linked_product__parent_product__parent_brand__brand_parent') \
            .prefetch_related('linked_product__parent_product__parent_product_pro_category__category') \
            .prefetch_related('linked_product__parent_product__parent_product_pro_category__category__category_parent') \
            .select_related('measurement_category')\
            .values('id', 'shop', 'shop__shop_name', 'sku', 'name', 'mrp', 'selling_price', 'product_pack_type',
                    'purchase_pack_size',
                    'measurement_category__category',
                    'linked_product__product_sku',
                    'product_ean_code', 'description', 'sku_type',
                    'linked_product__parent_product__parent_product_pro_category__category__category_name',
                    'linked_product__parent_product__parent_product_pro_category__category__category_parent__category_name',
                    'linked_product__parent_product__parent_brand__brand_name',
                    'linked_product__parent_product__parent_brand__brand_parent__brand_name',
                    'status', 'discounted_product', 'discounted_product__sku', 'online_enabled', 'online_price',
                    'is_deleted', 'offer_price', 'offer_start_date', 'offer_end_date')
        product_dict = {}
        discounted_product_ids = []
        for product in retailer_products:
            product_dict[product['id']] = product
            if product['discounted_product'] is not None:
                discounted_product_ids.append(product['discounted_product'])
        product_ids = list(product_dict.keys())
        product_ids.extend(discounted_product_ids)
        inventory = PosInventory.objects.filter(product_id__in=product_ids,
                                                inventory_state__inventory_state=PosInventoryState.AVAILABLE)
        inventory_data = {i.product_id: i.quantity for i in inventory}
        is_visible = 'False'
        for product_id, product in product_dict.items():
            category = product[
                'linked_product__parent_product__parent_product_pro_category__category__category_parent__category_name']
            sub_category = product[
                'linked_product__parent_product__parent_product_pro_category__category__category_name']
            if not category:
                category = sub_category
                sub_category = None

            brand = product[
                'linked_product__parent_product__parent_brand__brand_parent__brand_name']
            sub_brand = product[
                'linked_product__parent_product__parent_brand__brand_name']
            if not brand:
                brand = sub_brand
                sub_brand = None
            discounted_stock = None
            discounted_price = None
            if product['discounted_product']:
                discounted_stock = inventory_data.get(product['discounted_product'], 0)
                discounted_price = RetailerProduct.objects.filter(id=product['discounted_product']).last().selling_price
            measurement_category = product['measurement_category__category']
            if product['online_enabled']:
                online_enabled = 'Yes'
            else:
                online_enabled = 'No'

            if not product['is_deleted']:
                is_visible = 'Yes'

            writer.writerow(
                [product['id'], product['shop'], product['shop__shop_name'], product['sku'], product['name'],
                 product['mrp'], product['selling_price'], product['linked_product__product_sku'],
                 product['product_ean_code'], product['description'],
                 RetailerProductCls.get_sku_type(product['sku_type']),
                 category, sub_category, brand, sub_brand, product['status'], inventory_data.get(product_id, 0),
                 product['discounted_product__sku'], discounted_stock, discounted_price, product['product_pack_type'],
                 measurement_category, product['purchase_pack_size'], online_enabled,
                 product['online_price'], is_visible, product['offer_price'], product['offer_start_date'],
                 product['offer_end_date']])
    else:
        writer.writerow(["Products for selected shop doesn't exists"])
    return response


def download_discounted_products(request, *args):
    """
    Returns CSV of discounted products
    """
    shop_id = request.GET['shop_id']
    filename = "discounted_products_"+shop_id+".csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)

    writer.writerow(
        ['product_id', 'shop_id', 'shop_name', 'product_sku', 'product_name', 'mrp', 'selling_price',
         'linked_product_sku',
         'product_ean_code', 'description', 'sku_type', 'category', 'sub_category', 'brand', 'sub_brand', 'status',
         'quantity', 'product_pack_type', 'measurement_category', 'purchase_pack_size', 'available_for_online_orders',
         'online_order_price', 'is_visible'])
    product_qs = RetailerProduct.objects.filter(sku_type=4, shop_id=int(shop_id))
    if product_qs.exists():
        retailer_products = product_qs \
            .prefetch_related('linked_product') \
            .prefetch_related('linked_product__parent_product__parent_brand') \
            .prefetch_related('linked_product__parent_product__parent_brand__brand_parent') \
            .prefetch_related('linked_product__parent_product__parent_product_pro_category__category') \
            .prefetch_related('linked_product__parent_product__parent_product_pro_category__category__category_parent') \
            .select_related('measurement_category') \
            .values('id', 'shop', 'shop__shop_name', 'sku', 'name', 'mrp', 'selling_price', 'product_pack_type',
                    'purchase_pack_size',
                    'measurement_category__category',
                    'linked_product__product_sku',
                    'product_ean_code', 'description', 'sku_type',
                    'linked_product__parent_product__parent_product_pro_category__category__category_name',
                    'linked_product__parent_product__parent_product_pro_category__category__category_parent__category_name',
                    'linked_product__parent_product__parent_brand__brand_name',
                    'linked_product__parent_product__parent_brand__brand_parent__brand_name',
                    'status', 'discounted_product', 'discounted_product__sku')
        product_dict = {product['id']:product for product in retailer_products}
        product_ids = list(product_dict.keys())
        inventory = PosInventory.objects.filter(product_id__in=product_ids,
                                                inventory_state__inventory_state=PosInventoryState.AVAILABLE)
        inventory_data = {i.product_id: i.quantity for i in inventory}
        for product_id, product in product_dict.items():
            category = product[
                'linked_product__parent_product__parent_product_pro_category__category__category_parent__category_name']
            sub_category = product[
                'linked_product__parent_product__parent_product_pro_category__category__category_name']
            if not category:
                category = sub_category
                sub_category = None

            brand = product[
                'linked_product__parent_product__parent_brand__brand_parent__brand_name']
            sub_brand = product[
                'linked_product__parent_product__parent_brand__brand_name']
            if not brand:
                brand = sub_brand
                sub_brand = None
            measurement_category = product['measurement_category__category']
            writer.writerow(
                [product['id'], product['shop'], product['shop__shop_name'], product['sku'], product['name'],
                 product['mrp'], product['selling_price'], product['linked_product__product_sku'],
                 product['product_ean_code'], product['description'],
                 RetailerProductCls.get_sku_type(product['sku_type']),
                 category, sub_category, brand, sub_brand, product['status'], inventory_data.get(product_id, 0),
                 product['product_pack_type'], measurement_category, product['purchase_pack_size']])
    else:
        writer.writerow(["No discounted products for selected shop exists"])
    return response


def RetailerCatalogueSampleFile(request, *args):
    """
    This function will return an Sample File in csv format which can be used for Downloading RetailerCatalogue Sample File
    (It is used when user wants to create new retailer products)
    """
    filename = "retailer_products_create_sample_file.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(
        ['product_id', 'shop_id', 'shop_name', 'product_sku', 'product_name', 'mrp', 'selling_price',
         'linked_product_sku', 'product_ean_code', 'description', 'sku_type', 'category', 'sub_category',
         'brand', 'sub_brand', 'status', 'quantity', 'discounted_sku', 'discounted_stock', 'discounted_price',
         'product_pack_type', 'measurement_category', 'purchase_pack_size', 'available_for_online_orders',
         'online_order_price', 'is_visible', 'offer_price', 'offer_start_date', 'offer_end_date'])
    writer.writerow(["", 36966, "", "", 'Loose Noodles', 12, 10, 'PROPROTOY00000019', 'EAEASDF', 'XYZ', "",
                     "", "", "", "", 'active', 2, "", "", "", 'loose', 'weight', 1, 'Yes', 11, 'Yes', 9, "2021-11-21",
                     "2021-11-23"])
    writer.writerow(["", 36966, "", "", 'Packed Noodles', 12, 10, 'PROPROTOY00000019', 'EAEASDF', 'XYZ', "",
                     "", "", "", "", 'active', 2, "", "", "", 'packet', 'weight', 1, 'Yes', 11, 'Yes', 9, "2021-11-21",
                     "2021-11-23"])

    return response


class RetailerProductMultiImageUpload(View):
    """
    Bulk images upload with RetailerProduct SKU as image name
    """
    def get(self, request):
        images_list = RetailerProductImage.objects.all()
        return render(
            self.request,
            'admin/pos/retailerproductmultiimageupload.html',
            {'images': images_list}
        )

    def post(self, request):
        form = RetailerProductMultiImageForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            file_name = (
                os.path.splitext(form.cleaned_data['image'].name)[0])
            product_sku = file_name.split("_")[0]
            try:
                product = RetailerProduct.objects.filter(sku=product_sku)
            except:
                data = {
                    'is_valid': False,
                    'error': True,
                    'name': 'No RetailerProduct found with SKU ID <b>{}</b>'.format(product_sku),
                    'url': '#'
                }
            else:
                form_instance = form.save(commit=False)
                form_instance.product = product[0]
                form_instance.image_name = file_name
                form_instance.save()
                # es refresh for particular product and shop id
                update_es(product, product[0].shop_id)

                data = {
                    'is_valid': True,
                    'name': form_instance.image.name,
                    'url': form_instance.image.url,
                    'product_sku': product[0].sku,
                    'product_name': product[0].name
                }
        else:
            data = {'is_valid': False}
        return JsonResponse(data)


def get_retailer_product(request):
    product_id = request.GET.get('product')
    data = {
        'found': False
    }
    if not product_id:
        return JsonResponse(data)
    product = RetailerProduct.objects.filter(pk=product_id).last()
    if product:
        data = {
            'found': True,
            'product_ean_code':product.product_ean_code,
            'mrp': product.mrp,
            'selling_price' : product.selling_price
        }

    return JsonResponse(data)


class DownloadPurchaseOrder(APIView):
    permission_classes = (AllowAny,)
    filename = 'purchase_order.pdf'
    template_name = 'admin/purchase_order/retailer_purchase_order.html'

    def get(self, request, *args, **kwargs):
        po_obj = get_object_or_404(PosCart, pk=self.kwargs.get('pk'))
        data = generate_pdf_data(po_obj)
        cmd_option = {
            'encoding': 'utf8',
            'margin-top': 3
        }
        return PDFTemplateResponse(
            request=request, template=self.template_name,
            filename=self.filename, context=data,
            show_content_in_browser=False, cmd_options=cmd_option
        )

class InventoryRetailerProductAutocomplete(autocomplete.Select2QuerySetView):
    """
    Retailer Product Filter for Discounted Products
    """
    def get_queryset(self, *args, **kwargs):
        qs = RetailerProduct.objects.filter(~Q(sku_type=4))
        if self.q:
            qs = qs.filter(Q(name__icontains=self.q) | Q(sku__icontains = self.q))
        return qs

def download_posinventorychange_products_form_view(request):
    """
    PosInventory Change Form
    """
    form = PosInventoryChangeCSVDownloadForm()
    return render(
        request,
        'admin/pos/posinventorychange_download_list.html',
        {'form': form}
    )

def download_posinventorychange_products(request,sku=None, *args):
    """
    Download PosInventory Change Product for last 2 month
    """
    if sku:
        prod_sku = sku
    else:
        prod_sku = request.GET['prod_sku']

    try:
        prod = RetailerProduct.objects.get(id = prod_sku)
        filename = "posinventory_products_sku_"+prod.sku+".csv"
        pos_inventory = PosInventoryChange.objects.filter(product = prod).order_by('-modified_at')
        discount_prod = DiscountedRetailerProduct.objects.filter(product_ref = prod)
        if len(discount_prod) > 0:
            discount_pros_inventory = PosInventoryChange.objects.filter(product = discount_prod[0]).order_by('-modified_at')
            pos_inventory = pos_inventory.union(discount_pros_inventory).order_by('-modified_at')
    except Exception:
        filename = "posinventory_products_last2month.csv"
        today = datetime.date.today()
        two_month_back = today - relativedelta(months=2)
        pos_inventory = PosInventoryChange.objects.filter(modified_at__gte = two_month_back).order_by('-modified_at')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(
            ['Product Name', 'Product SKU', 'Quantity', 'Transaction Type', 'Transaction Id', 'Initial State', 'Final State', 'Changed By', 'Created at', 'Modfied at',
            ])
    for prod in pos_inventory:
        writer.writerow([prod.product.name, prod.product.sku, prod.quantity, prod.transaction_type, prod.transaction_id,
        prod.initial_state, prod.final_state, prod.changed_by, prod.created_at, prod.modified_at,
        ])
    return response

def get_pos_posinventorychange(prod_sku=None):
    try:
        prod = RetailerProduct.objects.get(id = prod_sku)
        pos_inventory = PosInventoryChange.objects.filter(product = prod).order_by('-modified_at')
        discount_prod = DiscountedRetailerProduct.objects.filter(product_ref = prod)
        if len(discount_prod) > 0:
            discount_pros_inventory = PosInventoryChange.objects.filter(product = discount_prod[0]).order_by('-modified_at')
            pos_inventory = pos_inventory.union(discount_pros_inventory).order_by('-modified_at')
    except Exception:
        today = datetime.date.today()
        two_month_back = today - relativedelta(months=2)
        pos_inventory = PosInventoryChange.objects.filter(modified_at__gte = two_month_back).order_by('-modified_at')

    return pos_inventory


def posinventorychange_data_excel(request,queryset):


    filename = "posinventorychange_data_excel.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(
            ['shop_id', 'shop_name', 'Product Name', 'Product SKU', 'Quantity', 'Transaction Type', 'Transaction Id', 'Initial State',
             'Final State', 'Changed By', 'Created at', 'Modfied at'])
    for obj in queryset:
        pos_inventory = get_pos_posinventorychange(obj.product.id)
        for prod in pos_inventory:
            writer.writerow([prod.product.shop.id, prod.product.shop.shop_name, prod.product.name, prod.product.sku, prod.quantity, prod.transaction_type, prod.transaction_id,
            prod.initial_state, prod.final_state, prod.changed_by, prod.created_at, prod.modified_at,
            ])
    return response


def get_product_details(product):
    parent_id, category, sub_category, brand, sub_brand = None, None, None, None, None
    if product.linked_product:
        parent_id = product.linked_product.parent_product.parent_id
        brand_details = Product.objects.values('parent_product__parent_brand__brand_name',
                                        'parent_product__parent_brand__brand_parent__brand_name') \
            .filter(Q(id=product.linked_product.id))
        if brand_details[0]['parent_product__parent_brand__brand_parent__brand_name']:
            brand = brand_details[0]['parent_product__parent_brand__brand_parent__brand_name']
            sub_brand = brand_details[0]['parent_product__parent_brand__brand_name']
        else:
            brand = brand_details[0]['parent_product__parent_brand__brand_name']

        cat = ParentProductCategory.objects.values('category__category_name',
                                                   'category__category_parent__category_name').filter \
            (parent_product__id=product.linked_product.parent_product.id)
        if cat[0]['category__category_parent__category_name']:
            category = cat[0]['category__category_parent__category_name']
            sub_category = cat[0]['category__category_name']
        else:
            category = cat[0]['category__category_name']
    return parent_id, category, sub_category, brand, sub_brand


def get_tax_details(product):
    gst_amount, cess_amount, surcharge_amount, tcs_amount = 0, 0, 0, 0
    if product.linked_product:
        tax_details = product.linked_product.product_pro_tax
        if tax_details.filter(tax__tax_type='gst').last():
            gst_amount = tax_details.filter(tax__tax_type='gst').last().tax.tax_percentage
        if tax_details.filter(tax__tax_type='cess').last():
            cess_amount = tax_details.filter(tax__tax_type='cess').last().tax.tax_percentage
        if tax_details.filter(tax__tax_type='surcharge').last():
            surcharge_amount = tax_details.filter(tax__tax_type='surcharge').last().tax.tax_percentage
        if tax_details.filter(tax__tax_type='tcs').last():
            tcs_amount = tax_details.filter(tax__tax_type='tcs').last().tax.tax_percentage
    return gst_amount, cess_amount, surcharge_amount, tcs_amount


def RetailerProductStockDownload(request, *args):
    """
    This function will return an Sample File in csv format which can be used for
    Downloading Retailer Products current stock and update the stock
    """

    shop_id = request.GET['shop_id']
    filename = "retailer_product_stock.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(
        ['product_id', 'shop_id', 'shop', 'product_sku', 'product_name', 'product_ean_code', 'mrp', 'selling_price',
         'current_inventory', 'discounted_sku', 'discounted_inventory', 'discounted_price', 'updated_inventory', 'reason_for_update'])
    product_qs = RetailerProduct.objects.filter(~Q(sku_type=4), shop_id=int(shop_id))
    if product_qs.exists():
        retailer_products = product_qs \
            .prefetch_related('shop') \
            .values('id', 'shop_id', 'shop__shop_name', 'sku', 'name', 'product_ean_code', 'mrp', 'selling_price',
                    'discounted_product')
        product_dict = {}
        discounted_product_ids = []
        for product in retailer_products:
            product_dict[product['id']] = product
            if product['discounted_product'] is not None:
                discounted_product_ids.append(product['discounted_product'])
        product_ids = list(product_dict.keys())
        product_ids.extend(discounted_product_ids)
        inventory = PosInventory.objects.filter(product_id__in=product_ids,
                                                inventory_state__inventory_state=PosInventoryState.AVAILABLE)
        inventory_data = {i.product_id: i.quantity for i in inventory}
        for product_id, product in product_dict.items():
            discounted_stock, discounted_sku, discounted_price = None, None, None
            if product['discounted_product']:
                discounted_stock = inventory_data.get(product['discounted_product'], 0)
                discounted_product = RetailerProduct.objects.filter(id=product['discounted_product']).last()
                discounted_sku = discounted_product.sku
                discounted_price = discounted_product.selling_price
            writer.writerow(
                [product['id'], product['shop_id'], product['shop__shop_name'], product['sku'], product['name'],
                 product['product_ean_code'], product['mrp'], product['selling_price'],
                 inventory_data.get(product_id, 0), discounted_sku, discounted_stock, discounted_price, '', ''])
    else:
        writer.writerow(["Products for selected shop doesn't exists"])
    return response


def update_retailer_product_stock(request):
    """
    Products Catalogue Upload View
    """
    shop_id = request.POST.get('shop')
    if request.method == 'POST':
        form = RetailerProductsStockUpdateForm(request.POST, request.FILES, shop_id=shop_id)

        if form.errors:
            return render(request, 'admin/pos/retailer_product_stock_update.html', {'form': form})

        if form.is_valid():

            # product_status = request.POST.get('catalogue_product_status')
            reader = csv.reader(codecs.iterdecode(request.FILES.get('file'), 'utf-8', errors='ignore'))
            header = next(reader, None)
            uploaded_data_list = []
            csv_dict = {}
            count = 0
            for id, row in enumerate(reader):
                for ele in row:
                    csv_dict[header[count]] = ele
                    count += 1
                uploaded_data_list.append(csv_dict)
                csv_dict = {}
                count = 0
            stock_update(request, uploaded_data_list)
            return render(request, 'admin/pos/retailer_product_stock_update.html',
                          {'form': form,
                           'success': 'Stock updated successfully!', })
    else:
        form = RetailerProductsStockUpdateForm()
        return render(
            request,
            'admin/pos/retailer_product_stock_update.html',
            {'form': form}
        )


def stock_update(request, data):
    for row in data:
        with transaction.atomic():
            stock_qty = row.get('updated_inventory')

            try:
                product = RetailerProduct.objects.get(id=row.get('product_id'))
                old_product = deepcopy(product)
                # Update Inventory
                PosInventoryCls.app_stock_inventory(product.id, PosInventoryState.AVAILABLE,
                                                PosInventoryState.AVAILABLE, stock_qty,
                                                request.user, product.sku, PosInventoryChange.STOCK_UPDATE,
                                                row.get('reason_for_update'))
                # Create discounted products while updating Products
                try:
                    if row.get('discounted_price', None):
                        discounted_price = decimal.Decimal(row['discounted_price'])
                        discounted_stock = int(row['discounted_inventory'])
                        product_status = 'active' if decimal.Decimal(discounted_stock) > 0 else 'deactivated'

                        initial_state = PosInventoryState.AVAILABLE
                        tr_type = PosInventoryChange.STOCK_UPDATE

                        discounted_product = RetailerProduct.objects.filter(product_ref=product).last()
                        if not discounted_product:

                            initial_state = PosInventoryState.NEW
                            tr_type = PosInventoryChange.STOCK_ADD

                            discounted_product = RetailerProductCls.create_retailer_product(product.shop.id,
                                                                                            product.name,
                                                                                            product.mrp,
                                                                                            discounted_price,
                                                                                            product.linked_product_id,
                                                                                            4,
                                                                                            product.description,
                                                                                            product.product_ean_code,
                                                                                            request.user,
                                                                                            'product',
                                                                                            product.product_pack_type,
                                                                                            product.measurement_category_id,
                                                                                            None, product_status,
                                                                                            None, None, None, product,
                                                                                            False, None)
                        else:
                            RetailerProductCls.update_price(discounted_product.id, discounted_price, product_status,
                                                            request.user, 'product', discounted_product.sku)

                        PosInventoryCls.app_stock_inventory(discounted_product.id, initial_state,
                                                        PosInventoryState.AVAILABLE, discounted_stock,
                                                        request.user,
                                                        discounted_product.sku, tr_type, None)

                    # Change logs
                    ProductChangeLogs.product_update(product, old_product, request.user, 'product',
                                                     product.sku)
                except Exception as e:
                    info_logger.info(f"Exception|POS|add discounted product|product id {row.get('product_id')}, e {e}")
            except Exception as e:
                info_logger.info(f"Exception|POS|stock_update|product id {row.get('product_id')}, e {e}")


class RetailerOrderedReportView(APIView):
    permission_classes = (AllowAny,)

    def total_order_calculation(self, user, start_date, end_date, shop):
        pos_cash_order_qs = OrderedProduct.objects.filter(invoice__created_at__date__gte=start_date,
                                                          invoice__created_at__date__lte=end_date,
                                                          order__ordered_cart__cart_type='BASIC',
                                                          order__seller_shop__id=shop,
                                                          order__rt_payment_retailer_order__payment_type__type__in=
                                                          ['cash', 'Cash On Delivery', 'cash on delivery'],
                                                          order__ordered_by__id=user,
                                                          order__order_status__in=
                                                          [RetailerOrderedReport.ORDERED,
                                                           RetailerOrderedReport.PARTIALLY_RETURNED,
                                                           RetailerOrderedReport.FULLY_RETURNED]).\
            aggregate(amt=Sum('order__rt_payment_retailer_order__amount'))

        pos_online_order_qs = OrderedProduct.objects.filter(invoice__created_at__date__gte=start_date,
                                                            invoice__created_at__date__lte=end_date,
                                                            order__ordered_cart__cart_type='BASIC',
                                                            order__seller_shop__id=shop,
                                                            order__rt_payment_retailer_order__payment_type__type__in=
                                                            ['PayU', 'credit', 'online', 'payu'],
                                                            order__ordered_by__id=user,
                                                            order__order_status__in=[
                                                                RetailerOrderedReport.ORDERED,
                                                                RetailerOrderedReport.PARTIALLY_RETURNED,
                                                                RetailerOrderedReport.FULLY_RETURNED]). \
            aggregate(amt=Sum('order__rt_payment_retailer_order__amount'))

        ecom_total_order_qs = OrderedProduct.objects.filter(order__created_at__date__gte=start_date,
                                                            order__created_at__date__lte=end_date,
                                                            order__ordered_cart__cart_type='ECOM',
                                                            order__seller_shop__id=shop,
                                                            order__ordered_by__id=user,
                                                            order__order_status=
                                                            RetailerOrderedReport.PICKUP_CREATED). \
            aggregate(amt=Sum('order__rt_payment_retailer_order__amount'))

        ecom_cash_order_qs = OrderedProduct.objects.filter(invoice__created_at__date__gte=start_date,
                                                           invoice__created_at__date__lte=end_date,
                                                           order__ordered_cart__cart_type='ECOM',
                                                           order__seller_shop__id=shop,
                                                           order__rt_payment_retailer_order__payment_type__type__in=
                                                           ['cash', 'Cash On Delivery', 'cash on delivery'],
                                                           order__ordered_by__id=user,
                                                           order__order_status__in=[RetailerOrderedReport.DELIVERED,
                                                                                    RetailerOrderedReport.PARTIALLY_RETURNED,
                                                                                    RetailerOrderedReport.FULLY_RETURNED]).\
            aggregate(amt=Sum('order__rt_payment_retailer_order__amount'))

        ecom_online_order_qs = OrderedProduct.objects.filter(invoice__created_at__date__gte=start_date,
                                                             invoice__created_at__date__lte=end_date,
                                                             order__ordered_cart__cart_type='ECOM',
                                                             order__seller_shop__id=shop,
                                                             order__rt_payment_retailer_order__payment_type__type__in=
                                                             ['PayU', 'credit', 'online', 'payu'],
                                                             order__ordered_by__id=user,
                                                             order__order_status__in=[
                                                                 RetailerOrderedReport.OUT_FOR_DELIVERY,
                                                                 RetailerOrderedReport.PARTIALLY_RETURNED,
                                                                 RetailerOrderedReport.DELIVERED,
                                                                 RetailerOrderedReport.FULLY_RETURNED],
                                                             ). \
            aggregate(amt=Sum('order__rt_payment_retailer_order__amount'))

        pos_cash_order_amt = pos_cash_order_qs['amt'] if 'amt' in pos_cash_order_qs and pos_cash_order_qs['amt'] else 0
        pos_online_order_amt = pos_online_order_qs['amt'] if 'amt' in pos_online_order_qs and pos_online_order_qs['amt'] else 0
        ecom_cash_order_amt = ecom_cash_order_qs['amt'] if 'amt' in ecom_cash_order_qs and ecom_cash_order_qs['amt'] else 0
        ecom_online_order_amt = ecom_online_order_qs['amt'] if 'amt' in ecom_online_order_qs and ecom_online_order_qs['amt'] else 0
        ecom_total_order_amt = ecom_total_order_qs['amt'] if 'amt' in ecom_total_order_qs and ecom_total_order_qs['amt'] else 0

        pos_cash_return_order_qs = CreditNote.objects.filter(order_return__order__ordered_cart__cart_type='BASIC',
                                                             order_return__order__seller_shop__id=shop,
                                                             created_at__date__gte=start_date,
                                                             created_at__date__lte=end_date,
                                                             order_return__processed_by__id=user,
                                                             order_return__refund_mode='cash').\
            aggregate(amt=Sum('order_return__refund_amount'))

        pos_online_return_order_qs = CreditNote.objects.filter(order_return__order__ordered_cart__cart_type='BASIC',
                                                               order_return__order__seller_shop__id=shop,
                                                               created_at__date__gte=start_date,
                                                               created_at__date__lte=end_date,
                                                               order_return__processed_by__id=user,
                                                               order_return__refund_mode__in=['online', 'credit']).\
            aggregate(amt=Sum('order_return__refund_amount'))

        ecom_cash_return_order_qs = CreditNote.objects.filter(order_return__order__ordered_cart__cart_type='ECOM',
                                                              order_return__order__seller_shop__id=shop,
                                                              created_at__date__gte=start_date,
                                                              created_at__date__lte=end_date,
                                                              order_return__processed_by__id=user,
                                                              order_return__refund_mode='cash').\
            aggregate(amt=Sum('order_return__refund_amount'))

        ecom_online_return_order_qs = CreditNote.objects.filter(order_return__order__ordered_cart__cart_type='ECOM',
                                                                order_return__order__seller_shop__id=shop,
                                                                created_at__date__gte=start_date,
                                                                created_at__date__lte=end_date,
                                                                order_return__processed_by__id=user,
                                                                order_return__refund_mode__in=['online', 'credit']).\
            aggregate(amt=Sum('order_return__refund_amount'))

        pos_cash_return_amt = pos_cash_return_order_qs['amt'] if 'amt' in pos_cash_return_order_qs and \
                                                                 pos_cash_return_order_qs['amt'] else 0
        pos_online_return_amt = pos_online_return_order_qs['amt'] if 'amt' in pos_online_return_order_qs and \
                                                                     pos_online_return_order_qs['amt'] else 0
        ecom_cash_return_amt = ecom_cash_return_order_qs['amt'] if 'amt' in ecom_cash_return_order_qs and \
                                                                   ecom_cash_return_order_qs['amt'] else 0
        ecom_online_return_amt = ecom_online_return_order_qs['amt'] if 'amt' in ecom_online_return_order_qs and \
                                                                       ecom_online_return_order_qs['amt'] else 0

        # can_order_qs = RetailerOrderedReport.objects.filter(ordered_cart__cart_type='BASIC', seller_shop__id=shop,
        #                                                     created_at__gte=start_date, created_at__lte=end_date,
        #                                                     order_status=RetailerOrderedReport.CANCELLED,
        #                                                     ordered_by__id=user)\
        #     .aggregate(amt=Sum('order_amount'))
        #
        # can_order_amt = can_order_qs['amt'] if 'amt' in can_order_qs and can_order_qs['amt'] else 0

        pos_cash_amt = float(pos_cash_order_amt) - float(pos_cash_return_amt)
        pos_online_amt = float(pos_online_order_amt) - float(pos_online_return_amt)
        ecomm_online_amt = float(ecom_online_order_amt) - float(ecom_online_return_amt)
        ecomm_cash_amt = float(ecom_cash_order_amt) - float(ecom_cash_return_amt)
        return pos_cash_amt, pos_online_amt, ecom_total_order_amt, ecomm_cash_amt, ecomm_online_amt

    def get(self, *args, **kwargs):

        start_date = self.request.GET.get('start_date', None)
        end_date = self.request.GET.get('end_date', None)
        shop = self.request.GET.get('shop', None)
        error = False
        if not shop:
            messages.error(self.request, 'shop is mandatory')
            error = True
        if not Shop.objects.filter(id=shop, shop_type__shop_type='f', status=True, approval_status=2,
                                   pos_enabled=True, pos_shop__status=True):
            messages.error(self.request, "Franchise Shop Id Not Approved / Invalid!")
            error = True
        if not start_date and not end_date:
            messages.error(self.request, 'Start and End dates are mandatory')
            error = True
        elif not start_date:
            messages.error(self.request, 'Start date is mandatory')
            error = True
        elif not end_date:
            messages.error(self.request, 'End date is mandatory')
            error = True
        elif end_date < start_date:
            messages.error(self.request, 'End date cannot be less than the start date')
            error = True
        if error:
            return render(
                self.request,
                'admin/services/retailer-order-report.html',
                {'form': RetailerOrderedReportForm(initial=self.request.GET)}
            )

        users_list = PosShopUserMapping.objects.filter(shop=shop).values('user__id', 'user__first_name',
                                                                         'user__phone_number', 'user__last_name',
                                                                         'user_type')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="order-report.csv"'
        writer = csv.writer(response)
        shop_obj = Shop.objects.filter(id=shop, shop_type__shop_type='f', status=True, approval_status=2,
                                        pos_enabled=True, pos_shop__status=True).last()
        writer.writerow(['Shop Name:', shop_obj.shop_name])
        writer.writerow(['Start Date:', start_date])
        writer.writerow(['End Date:', end_date])
        writer.writerow([])
        writer.writerow(['User Name', 'Walkin Cash', 'Walkin Online', 'Ecomm PG', 'Ecomm Cash', 'Total Cash',
                         'Total Online', 'Total PG'])
        for user in users_list:
            pos_cash_amt, pos_online_amt, ecom_total_order_amt, ecomm_cash_amt, ecomm_online_amt = \
                self.total_order_calculation(user['user__id'], start_date, end_date, shop)
            writer.writerow([str(str(user['user__phone_number']) + " - " + user['user__first_name'] + " " +
                                 user['user__last_name'] + " - " + str(user['user_type'])),
                             pos_cash_amt, pos_online_amt, ecomm_online_amt,  ecomm_cash_amt,
                             (pos_cash_amt+ecomm_cash_amt),
                             pos_online_amt, ecomm_online_amt],)
        return response


class RetailerOrderedReportFormView(View):
    def get(self, request):
        form = RetailerOrderedReportForm()
        return render(
            self.request,
            'admin/services/retailer-order-report.html',
            {'form': form}
        )

class RetailerOrderProductInvoiceView(View):

    def get(self, request, pk):
        try:
            order = get_object_or_404(RetailerOrderedProduct, pk=pk)
            if order.invoice.invoice_pdf.url:
                with requests.Session() as s:
                    try:
                        response = s.get(order.invoice.invoice_pdf.url)
                        response = FileResponse(io.BytesIO(response.content), content_type='application/pdf')
                        response['Content-Length'] = response['Content-Length']
                        response['Content-Disposition'] = 'attachment; filename="%s"' % order.invoice.pdf_name
                        return response
                    except Exception as err:
                        return HttpResponseBadRequest(err)
            else:
                return HttpResponseBadRequest("Invoice not generated")
        except RetailerOrderedProduct.DoesNotExist:
            raise Http404("Resource not found on server")
        except Exception as err:
            logging.exception("Invoice download failed due to %s" % err)
            return HttpResponseBadRequest("Invoice download failed due to %s" % err)


class RetailerOrderReturnCreditNoteView(View):

    def get(self, request, pk):
        try:
            order_return = get_object_or_404(RetailerOrderReturn, pk=pk)
            if order_return.credit_note_order_return_mapping.last() \
                and order_return.credit_note_order_return_mapping.last().credit_note_pdf:
                with requests.Session() as s:
                    try:
                        response = s.get(order_return.credit_note_order_return_mapping.last().credit_note_pdf.url)
                        response = FileResponse(io.BytesIO(response.content), content_type='application/pdf')
                        response['Content-Length'] = response['Content-Length']
                        response['Content-Disposition'] = 'attachment; filename="%s"' % order_return.credit_note_order_return_mapping.last().pdf_name
                        return response
                    except Exception as err:
                        return HttpResponseBadRequest(err)
            else:
                return HttpResponseBadRequest("CreditNote not generated")
        except RetailerOrderedProduct.DoesNotExist:
            raise Http404("Resource not found on server")
        except Exception as err:
            logging.exception("CreditNote download failed due to %s" % err)
            return HttpResponseBadRequest("CreditNote download failed due to %s" % err)