import codecs
import csv
import decimal
import os

from dal import autocomplete
from django.db.models import Q

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from wkhtmltopdf.views import PDFTemplateResponse

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from django.views import View
from pos.common_functions import RetailerProductCls
from pos.models import RetailerProduct, RetailerProductImage, PosCart
from pos.forms import RetailerProductsCSVDownloadForm, RetailerProductsCSVUploadForm, RetailerProductMultiImageForm
from products.models import Product, ParentProductCategory
from shops.models import Shop
from .tasks import generate_pdf_data


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


def bulk_create_products(shop_id, uploaded_data_by_user_list):
    """
        This Function will create Product by uploaded_data_by_user_list
    """
    for row in uploaded_data_by_user_list:
        # if else condition for checking whether, Product we are creating is linked with existing product or not
        # with the help of 'linked_product_id'
        if 'linked_product_sku' in row.keys():
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


def bulk_update_products(request, form ,shop_id, uploaded_data_by_user_list):
    """
       This Function will update Product by uploaded_data_by_user_list
    """
    for row in uploaded_data_by_user_list:
        product_id = row.get('product_id')
        product_mrp = row.get('mrp')
        if RetailerProduct.objects.filter(id=product_id, shop_id=shop_id).exists():
            expected_input_data_list = ['product_name', 'product_id', 'mrp', 'selling_price', 'product_ean_code', 'description', 'status']
            actual_input_data_list = []  # List of keys that user wants to update(If user wants to update product_name, this list wil have product_name with product_id)
            for key in expected_input_data_list:
                if key in row.keys():
                    actual_input_data_list.append(key)
            product = RetailerProduct.objects.get(id=product_id)
            linked_product_id = product.linked_product_id
            if linked_product_id:
                product.sku_type = 2
                # if 'mrp' in actual_input_data_list:
                #     # If MRP in actual_input_data_list
                #     linked_product = Product.objects.filter(id=linked_product_id)
                #     if format(decimal.Decimal(product_mrp), ".2f") == str(
                #             linked_product.values()[0].get('mrp')):
                #         # If Input_MRP == Product_MRP, Update the product with [SKU Type : Linked]
                #         product.sku_type = 2
                #     else:
                #         # If Input_MRP != Product_MRP, Update the product with [SKU Type : Linked Edited]
                #         product.sku_type = 3
            if 'mrp' in actual_input_data_list:
                # If MRP in actual_input_data_list
                product.mrp = product_mrp
            if 'selling_price' in actual_input_data_list:
                # If selling price in actual_input_data_list
                product.selling_price = row.get('selling_price')
            if 'product_name' in actual_input_data_list:
                # Update Product Name
                product.name = row.get('product_name')
            if 'product_ean_code' in actual_input_data_list:
                # Update product_ean_code
                product.product_ean_code = row.get('product_ean_code')
            if 'description' in actual_input_data_list:
                # Update Description
                product.description = row.get('description')
            if 'status' in actual_input_data_list:
                # Update product_ean_code
                product.status = row.get('status')
            product.save()

        else:
            return render(request, 'admin/pos/retailerproductscsvupload.html',
                          {'form': form,
                           'error': f"There is no product available with (product id : {product_id}) "
                                    f"for the (shop_id: {shop_id})", })


def upload_retailer_products_list(request):
    """
    Products Catalogue Upload View
    """
    if request.method == 'POST':
        form = RetailerProductsCSVUploadForm(request.POST, request.FILES)

        if form.errors:
            return render(request, 'admin/pos/retailerproductscsvupload.html', {'form': form})

        if form.is_valid():
            shop_id = request.POST.get('shop')
            product_status = request.POST.get('catalogue_product_status')
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
            if product_status == 'create_products':
                bulk_create_products(shop_id, uploaded_data_by_user_list)
            else:
                bulk_update_products(request, form, shop_id, uploaded_data_by_user_list)

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
        ['product_id', 'shop', 'product_sku', 'product_name', 'mrp', 'selling_price', 'linked_product_sku',
         'product_ean_code', 'description', 'sku_type', 'category', 'sub_category', 'brand', 'sub_brand', 'status'])
    if RetailerProduct.objects.filter(shop_id=int(shop_id)).exists():
        retailer_products = RetailerProduct.objects.filter(shop_id=int(shop_id))
        for product in retailer_products:
            product_data = retailer_products_list(product)
            writer.writerow([product.id, product.shop, product.sku, product.name,
                            product.mrp, product.selling_price, product_data[0], product.product_ean_code,
                            product.description, product_data[1], product_data[2], product_data[3],
                            product_data[4], product_data[5], product.status])
    else:
        writer.writerow(["Products for selected shop doesn't exists"])
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
    writer.writerow(['product_name', 'mrp', 'linked_product_sku', 'product_ean_code', 'selling_price', 'description', 'status'])
    writer.writerow(['Noodles', 12, 'PROPROTOY00000019', 'EAEASDF', 10, 'XYZ', 'active'])
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
