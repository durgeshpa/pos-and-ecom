import codecs
import csv
import decimal
from itertools import product
import os
import re
import datetime
from dateutil.relativedelta import relativedelta

from dal import autocomplete
from django.core.exceptions import ValidationError
from django.db.models import Q

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from wkhtmltopdf.views import PDFTemplateResponse

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from django.views import View
from pos.common_functions import PosInventoryCls, RetailerProductCls
from pos.models import RetailerProduct, RetailerProductImage, PosCart, DiscountedRetailerProduct
from pos.forms import RetailerProductsCSVDownloadForm, RetailerProductsCSVUploadForm, RetailerProductMultiImageForm, PosInventoryChangeCSVDownloadForm
from products.models import Product, ParentProductCategory
from shops.models import Shop
from wms.models import PosInventory, PosInventoryState
from .tasks import generate_pdf_data
from wms.models import PosInventoryChange


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
        qs = Shop.objects.filter(shop_type__shop_type__in=['r', 'f'])
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


# def bulk_create_products(shop_id, uploaded_data_by_user_list):
def bulk_create_update_products(request, shop_id, form, uploaded_data_by_user_list):

    """
        This Function will create Product by uploaded_data_by_user_list
    """
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
                        if str(product.product_mrp) == format(
                                decimal.Decimal(row.get('mrp')), ".2f"):
                            # If Linked_Product_MRP == Input_MRP , create a Product with [SKU TYPE : LINKED]
                            RetailerProductCls.create_retailer_product(shop_id, row.get('product_name'), row.get('mrp'),
                                                                    row.get('selling_price'), product.id,
                                                                    2, row.get('description'), row.get('product_ean_code'),
                                                                    row.get('status'))
                        else:
                            # If Linked_Product_MRP != Input_MRP, Create a new Product with SKU_TYPE == "LINKED_EDITED"
                            RetailerProductCls.create_retailer_product(shop_id, row.get('product_name'), row.get('mrp'),
                                                                    row.get('selling_price'), product.id,
                                                                    3, row.get('description'), row.get('product_ean_code'),
                                                                    row.get('status'))
            else:
                # If product is not linked with existing product, Create a new Product with SKU_TYPE == "Created"
                RetailerProductCls.create_retailer_product(shop_id, row.get('product_name'), row.get('mrp'),
                                                        row.get('selling_price'), None,
                                                        1, row.get('description'), row.get('product_ean_code'),
                                                        row.get('status'))

        else:
            # we need to update existing product
            try:

                product = RetailerProduct.objects.get(id = row.get('product_id'))
            
                if (row.get('linked_product_sku') != '' and Product.objects.get(product_sku=row.get('linked_product_sku'))):
                    linked_product=Product.objects.get(product_sku=row.get('linked_product_sku'))
                    product.linked_product_id = linked_product.id
                if(product.selling_price != row.get('selling_price')):
                    product.selling_price=row.get('selling_price')
                if(product.status != row.get('status')):
                    if row.get('status') == 'deactivated':
                        product.status='deactivated'
                    else:
                        product.status="active"
                product.save()
            except:
                return render(request, 'admin/pos/retailerproductscsvupload.html',
                    {'form': form,
                    'error': "Please check for correct format" })




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
                                        'parent_product__parent_brand__brand_parent__brand_name').filter(
                                        Q(id=product.linked_product.id))
        if prodct[0]['parent_product__parent_brand__brand_parent__brand_name']:
           brand = prodct[0]['parent_product__parent_brand__brand_parent__brand_name']
           sub_brand = prodct[0]['parent_product__parent_brand__brand_name']
        else:
            brand = prodct[0]['parent_product__parent_brand__brand_name']

        cat = ParentProductCategory.objects.values('category__category_name',
                                                   'category__category_parent__category_name').filter\
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
        ['product_id', 'shop_id', 'shop', 'product_sku', 'product_name', 'mrp', 'selling_price', 'linked_product_sku',
         'product_ean_code', 'description', 'sku_type', 'category', 'sub_category', 'brand', 'sub_brand', 'status', 'quantity'])
    if RetailerProduct.objects.filter(shop_id=int(shop_id)).exists():
        retailer_products = RetailerProduct.objects.filter(shop_id=int(shop_id))

        for product in retailer_products:
            product_data = retailer_products_list(product)
            try:
                quantity = PosInventory.objects.get(product=product, inventory_state__inventory_state=PosInventoryState.AVAILABLE).quantity
            except:
                quantity = 0


            writer.writerow([product.id, shop_id, product.shop, product.sku, product.name,
                            product.mrp, product.selling_price, product_data[0], product.product_ean_code,
                            product.description, product_data[1], product_data[2], product_data[3],
                            product_data[4], product_data[5], product.status, quantity])
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
        ['product_id', 'shop', 'product_sku', 'product_ref', 'product_name', 'mrp', 'selling_price', 'linked_product_sku',
         'product_ean_code', 'description', 'sku_type', 'category', 'sub_category', 'brand', 'sub_brand', 'status'])
    if RetailerProduct.objects.filter(shop_id=int(shop_id), sku_type=4).exists():
        retailer_products = RetailerProduct.objects.filter(shop_id=int(shop_id), sku_type=4)
        for product in retailer_products:
            product_data = retailer_products_list(product)
            writer.writerow([product.id, product.shop, product.sku, product.product_ref.sku, product.name,
                            product.mrp, product.selling_price, product_data[0], product.product_ean_code,
                            product.description, product_data[1], product_data[2], product_data[3],
                            product_data[4], product_data[5], product.status])
    else:
        writer.writerow(["No doscounted products for selected shop exists"])
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
         'product_ean_code', 'description', 'sku_type', 'category', 'sub_category', 'brand', 'sub_brand', 'status', 'quantity'])
    writer.writerow(['', 36966, '', '', 'Noodles', 12, 10, 'PROPROTOY00000019', 'EAEASDF',  'XYZ', '','', '','','', 'active', ''])

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
