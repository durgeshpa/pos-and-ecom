import codecs
import csv
import os
import datetime

from dal import autocomplete
from dateutil.relativedelta import relativedelta
from django.db.models import Q

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db import transaction

from django.views import View
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from wkhtmltopdf.views import PDFTemplateResponse

from pos.common_functions import RetailerProductCls
from pos.models import RetailerProduct, RetailerProductImage, PosCart, DiscountedRetailerProduct, MeasurementCategory
from pos.forms import RetailerProductsCSVDownloadForm, RetailerProductsCSVUploadForm, RetailerProductMultiImageForm, \
    PosInventoryChangeCSVDownloadForm
from pos.tasks import generate_pdf_data
from products.models import Product, ParentProductCategory
from shops.models import Shop
from wms.models import PosInventory, PosInventoryState, PosInventoryChange


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
            if row.get('product_id') == '':
                # we need to create this product
                # if else condition for checking whether, Product we are creating is linked with existing product or not
                # with the help of 'linked_product_id'
                if 'linked_product_sku' in row.keys() and not row.get('linked_product_sku') == '':
                    if row.get('linked_product_sku') != '':
                        # If product is linked with existing product
                        if Product.objects.filter(product_sku=row.get('linked_product_sku')):
                            product = Product.objects.get(product_sku=row.get('linked_product_sku'))
                            measure_cat_id = MeasurementCategory.objects.get(category=row.get('measurement_category')).id
                            RetailerProductCls.create_retailer_product(shop_id, row.get('product_name'), row.get('mrp'),
                                                                       row.get('selling_price'), product.id,
                                                                       2, row.get('description'),
                                                                       row.get('product_ean_code'),
                                                                       request.user, 'product', row.get('product_pack_type'),
                                                                       measure_cat_id, None,
                                                                       row.get('status'))
                else:
                    # If product is not linked with existing product, Create a new Product with SKU_TYPE == "Created"
                    RetailerProductCls.create_retailer_product(shop_id, row.get('product_name'), row.get('mrp'),
                                                               row.get('selling_price'), None,
                                                               1, row.get('description'), row.get('product_ean_code'),
                                                               request.user, 'product', row.get('product_pack_type'),
                                                               measure_cat_id, None,
                                                               row.get('status'))

            else:
                # we need to update existing product
                try:

                    product = RetailerProduct.objects.get(id=row.get('product_id'))

                    if (row.get('linked_product_sku') != '' and Product.objects.get(
                            product_sku=row.get('linked_product_sku'))):
                        linked_product = Product.objects.get(product_sku=row.get('linked_product_sku'))
                        product.linked_product_id = linked_product.id
                    if (product.selling_price != row.get('selling_price')):
                        product.selling_price = row.get('selling_price')
                    if (product.status != row.get('status')):
                        if row.get('status') == 'deactivated':
                            product.status = 'deactivated'
                        else:
                            product.status = "active"
                    product.save()
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
         'linked_product_sku',
         'product_ean_code', 'description', 'sku_type', 'category', 'sub_category', 'brand', 'sub_brand', 'status',
         'quantity', 'discounted_sku', 'discounted_stock', 'product_pack_type', 'measurement_category'])
    product_qs = RetailerProduct.objects.filter(~Q(sku_type=4), shop_id=int(shop_id))
    if product_qs.exists():
        retailer_products = product_qs \
            .prefetch_related('linked_product') \
            .prefetch_related('linked_product__parent_product__parent_brand') \
            .prefetch_related('linked_product__parent_product__parent_brand__brand_parent') \
            .prefetch_related('linked_product__parent_product__parent_product_pro_category__category') \
            .prefetch_related('linked_product__parent_product__parent_product_pro_category__category__category_parent') \
            .select_related('measurement_category')\
            .values('id', 'shop', 'shop__shop_name', 'sku', 'name', 'mrp', 'selling_price', 'product_pack_type',
                    'measurement_category__category'
                    'linked_product__product_sku',
                    'product_ean_code', 'description', 'sku_type',
                    'linked_product__parent_product__parent_product_pro_category__category__category_name',
                    'linked_product__parent_product__parent_product_pro_category__category__category_parent__category_name',
                    'linked_product__parent_product__parent_brand__brand_name',
                    'linked_product__parent_product__parent_brand__brand_parent__brand_name',
                    'status', 'discounted_product', 'discounted_product__sku')
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
            if product['discounted_product']:
                discounted_stock = inventory_data.get(product['discounted_product'], 0)
            measurement_category = product['measurement_category__category']
            writer.writerow(
                [product['id'], product['shop'], product['shop__shop_name'], product['sku'], product['name'],
                 product['mrp'], product['selling_price'], product['linked_product__product_sku'],
                 product['product_ean_code'], product['description'],
                 RetailerProductCls.get_sku_type(product['sku_type']),
                 category, sub_category, brand, sub_brand, product['status'], inventory_data.get(product_id, 0),
                 product['discounted_product__sku'], discounted_stock, product['product_pack_type'],
                 measurement_category])
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
         'quantity', 'product_pack_type', 'measurement_category'])
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
                 product['product_pack_type'], measurement_category])
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
        ['product_id', 'shop_id', 'shop', 'product_sku', 'product_name', 'mrp', 'selling_price', 'linked_product_sku',
         'product_ean_code', 'description', 'sku_type', 'category', 'sub_category', 'brand', 'sub_brand', 'status', 'quantity',
         'product_pack_type', 'measurement_category'])
    writer.writerow(['', 36966, '', '', 'Noodles', 12, 10, 'PROPROTOY00000019', 'EAEASDF',  'XYZ', '','', '','','', 'active', 'loose', 'weight'])

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
                product = RetailerProduct.objects.get(sku=product_sku)
            except:
                data = {
                    'is_valid': False,
                    'error': True,
                    'name': 'No RetailerProduct found with SKU ID <b>{}</b>'.format(product_sku),
                    'url': '#'
                }
            else:
                form_instance = form.save(commit=False)
                form_instance.product = product
                form_instance.image_name = file_name
                form_instance.save()

                data = {
                    'is_valid': True,
                    'name': form_instance.image.name,
                    'url': form_instance.image.url,
                    'product_sku': product.sku,
                    'product_name': product.name
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

def download_posinventorychange_products(request, *args):
    """
    Download PosInventory Change Product for last 2 month
    """
    try:
        prod_sku = request.GET['prod_sku']
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

