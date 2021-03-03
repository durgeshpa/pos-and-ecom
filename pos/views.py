import codecs
import csv
import decimal
import uuid

from dal import autocomplete
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from rest_framework import status, authentication, permissions
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from pos.common_functions import RetailerProductCls
from pos.forms import RetailerProductsCSVDownloadForm, RetailerProductsCSVUploadForm
from pos.models import RetailerProduct, RetailerProductImage
from pos.serializers import RetailerProductCreateSerializer, RetailerProductUpdateSerializer, \
    RetailerProductResponseSerializer
from products.models import Product, ParentProductCategory
from shops.models import Shop

POS_SERIALIZERS_MAP = {
    '0': RetailerProductCreateSerializer,
    '1': RetailerProductUpdateSerializer
}


class CatalogueProductCreation(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get_shop_id_or_error_message(self, request):
        # If Token and shop_id, check whether Token is valid for shop_id or not
        shopID = request.data.get('shop_id')
        if request.user.id and shopID:
            if Shop.objects.filter(shop_owner_id=request.user.id).exists():
                shop_id_from_token = Shop.objects.filter(shop_owner_id=request.user.id)
            else:
                if Shop.objects.filter(related_users=request.user.id).exists():
                    shop_id_from_token = Shop.objects.filter(related_users=request.user.id)
                else:
                    return "Please Provide a Valid TOKEN"
            shop_id = Shop.objects.filter(id=shopID)
            if not shop_id.values()[0].get('id') == shop_id_from_token.values()[0].get('id'):
                return "INCORRECT TOKEN for given SHOP_ID"

        if shopID:
            return int(shopID)
        else:
            if request.user.id:
                if Shop.objects.filter(shop_owner_id=request.user.id).exists():
                    shop = Shop.objects.filter(shop_owner_id=request.user.id)
                else:
                    if Shop.objects.filter(related_users=request.user.id).exists():
                        shop = Shop.objects.filter(related_users=request.user.id)
                    else:
                        return "Please Provide a Valid TOKEN"
                return int(shop.values()[0].get('id'))
            return "Please provide SHOP_ID or Token"

    def get_serializer_class(self, data):
        """
        We are getting different serializer_class for post and put API's.
        0 refers to POST and 1 refers to PUT .
        """
        if data == 0:
            return POS_SERIALIZERS_MAP['0']
        if data == 1:
            return POS_SERIALIZERS_MAP['1']

    def post(self, request, *args, **kwargs):
        """
        POST API for Product Creation.
        Using RetailerProductCreateSerializer for request and RetailerProductResponseSerializer for response.
        """
        shop_id_or_error_message = self.get_shop_id_or_error_message(request)
        if type(shop_id_or_error_message) == int:
            serializer = self.get_serializer_class(0)(data=request.data)
            if serializer.is_valid():
                product_name = request.data.get('product_name')
                mrp = request.data.get('mrp')
                selling_price = request.data.get('selling_price')
                linked_product_id = request.data.get('linked_product_id')
                description = request.data.get('description') if request.data.get('description') else ''
                # if else condition for checking whether, Product we are creating is linked with existing product or not
                # with the help of 'linked_product_id'
                if request.data.get('linked_product_id'):
                    # If product is linked with existing product
                    if Product.objects.filter(id=request.data.get('linked_product_id')).exists():
                        product = Product.objects.filter(id=request.data.get('linked_product_id'))
                        if str(product.values()[0].get('product_mrp')) == format(
                                decimal.Decimal(request.data.get('mrp')), ".2f"):
                            # If Linked_Product_MRP == Input_MRP , create a Product with [SKU TYPE : LINKED]
                            RetailerProductCls.create_retailer_product(shop_id_or_error_message,
                                                                       product_name, mrp, selling_price,
                                                                       linked_product_id, 2, description)
                        else:
                            # If Linked_Product_MRP != Input_MRP, Create a new Product with SKU_TYPE == "LINKED_EDITED"
                            RetailerProductCls.create_retailer_product(shop_id_or_error_message,
                                                                       product_name, mrp, selling_price,
                                                                       linked_product_id, 3, description)
                else:
                    # If product is not linked with existing product, Create a new Product with SKU_TYPE == "Created"
                    RetailerProductCls.create_retailer_product(shop_id_or_error_message, product_name, mrp,
                                                               selling_price, None, 1, description)
                product = RetailerProduct.objects.all().last()
                # Fetching the data of created product
                data = RetailerProduct.objects.values('id', 'shop__shop_name', 'name', 'sku', 'mrp', 'selling_price',
                                                      'description', 'sku_type',
                                                      'linked_product__product_name', 'created_at',
                                                      'modified_at').filter(id=product.id)
                response_serializer = RetailerProductResponseSerializer(instance=data[0])
                message = {"is_success": True, "message": "Product has been successfully created!",
                           "response_data": response_serializer.data}
                return Response(message, status=status.HTTP_201_CREATED)
            else:
                errors = []
                for field in serializer.errors:
                    for error in serializer.errors[field]:
                        if 'non_field_errors' in field:
                            result = error
                        else:
                            result = ''.join('{} : {}'.format(field, error))
                        errors.append(result)
                msg = {'is_success': False,
                       'error_message': errors[0] if len(errors) == 1 else [error for error in errors],
                       'response_data': None}
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            msg = {'is_success': False,
                   'error_message': shop_id_or_error_message,
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    def put(self, request, *args, **kwargs):
        """
        PUT API for Product Update.
        Using RetailerProductUpdateSerializer for request and RetailerProductResponseSerializer for response.
        """
        # RetailerProductUpdateSerializer is used
        shop_id_or_error_message = self.get_shop_id_or_error_message(request)
        if type(shop_id_or_error_message) == int:
            serializer = self.get_serializer_class(1)(data=request.data)
            if serializer.is_valid():
                product_id = request.data.get('product_id')
                mrp = request.data.get('mrp')
                if RetailerProduct.objects.filter(id=product_id,
                                                  shop_id=shop_id_or_error_message).exists():
                    expected_input_data_list = ['product_name', 'product_id', 'mrp', 'selling_price', 'description']
                    actual_input_data_list = []  # List of keys that user wants to update(If user wants to update product_name, this list wil only have product_name)
                    for key in expected_input_data_list:
                        if key in request.data.keys():
                            actual_input_data_list.append(key)
                    product = RetailerProduct.objects.get(id=product_id)
                    linked_product_id = product.linked_product_id
                    if linked_product_id:
                        if 'mrp' in actual_input_data_list:
                            # If MRP in actual_input_data_list
                            linked_product = Product.objects.filter(id=linked_product_id)
                            if format(decimal.Decimal(mrp), ".2f") == str(
                                    linked_product.values()[0].get('product_mrp')):
                                # If Input_MRP == Product_MRP, Update the product with [SKU Type : Linked]
                                product.sku_type = 2
                            else:
                                # If Input_MRP != Product_MRP, Update the product with [SKU Type : Linked Edited]
                                product.sku_type = 3
                    if 'mrp' in actual_input_data_list:
                        # If MRP in actual_input_data_list
                        product.mrp = mrp
                    if 'selling_price' in actual_input_data_list:
                        # If selling price in actual_input_data_list
                        product.selling_price = request.data.get('selling_price')
                    if 'product_name' in actual_input_data_list:
                        # Update Product Name
                        product.name = request.data.get('product_name')
                    if 'description' in actual_input_data_list:
                        # Update Description
                        product.description = request.data.get('description')
                    product.save()

                    data = RetailerProduct.objects.values('id', 'shop__shop_name', 'name', 'sku', 'mrp',
                                                          'selling_price', 'description', 'sku_type',
                                                          'linked_product__product_name', 'created_at',
                                                          'modified_at').filter(id=request.data.get('product_id'))
                    response_serializer = RetailerProductResponseSerializer(instance=data[0])
                    message = {"is_success": True, "message": f"Product has been successfully UPDATED!",
                               "response_data": response_serializer.data}
                    return Response(message, status=status.HTTP_202_ACCEPTED)
                else:
                    msg = {'is_success': False,
                           'error_message': f"There is no product available with (product id : {product_id}) "
                                            f"for the shop_id provided",
                           'response_data': None}
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                errors = []
                for field in serializer.errors:
                    for error in serializer.errors[field]:
                        if 'non_field_errors' in field:
                            result = error
                        else:
                            result = ''.join('{} : {}'.format(field, error))
                        errors.append(result)
                msg = {'is_success': False,
                       'error_message': errors[0] if len(errors) == 1 else [error for error in errors],
                       'response_data': None}
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            msg = {'is_success': False,
                   'error_message': shop_id_or_error_message,
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)


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
                                                                               2, row.get('description'))
                                else:
                                    # If Linked_Product_MRP != Input_MRP, Create a new Product with SKU_TYPE == "LINKED_EDITED"
                                    RetailerProductCls.create_retailer_product(shop_id, row.get('product_name'), row.get('mrp'),
                                                                               row.get('selling_price'), product.id,
                                                                               3, row.get('description'))
                    else:
                        # If product is not linked with existing product, Create a new Product with SKU_TYPE == "Created"
                        RetailerProductCls.create_retailer_product(shop_id, row.get('product_name'), row.get('mrp'),
                                                                   row.get('selling_price'), None,
                                                                   1, row.get('description'))
                return render(request, 'admin/pos/retailerproductscsvupload.html',
                              {'form': form,
                               'success': 'Products Created Successfully!', })

            else:
                for row in uploaded_data_by_user_list:
                    product_id = row.get('product_id')
                    product_mrp = row.get('mrp')
                    if RetailerProduct.objects.filter(id=product_id, shop_id=shop_id).exists():
                        expected_input_data_list = ['product_name', 'product_id', 'mrp', 'selling_price', 'description']
                        actual_input_data_list = []  # List of keys that user wants to update(If user wants to update product_name, this list wil have product_name with product_id)
                        for key in expected_input_data_list:
                            if key in row.keys():
                                actual_input_data_list.append(key)
                        product = RetailerProduct.objects.get(id=product_id)
                        linked_product_id = product.linked_product_id
                        if linked_product_id:
                            if 'mrp' in actual_input_data_list:
                                # If MRP in actual_input_data_list
                                linked_product = Product.objects.filter(id=linked_product_id)
                                if format(decimal.Decimal(product_mrp), ".2f") == str(
                                        linked_product.values()[0].get('mrp')):
                                    # If Input_MRP == Product_MRP, Update the product with [SKU Type : Linked]
                                    product.sku_type = 2
                                else:
                                    # If Input_MRP != Product_MRP, Update the product with [SKU Type : Linked Edited]
                                    product.sku_type = 3
                        if 'mrp' in actual_input_data_list:
                            # If MRP in actual_input_data_list
                            product.mrp = product_mrp
                        if 'selling_price' in actual_input_data_list:
                            # If selling price in actual_input_data_list
                            product.selling_price = row.get('selling_price')
                        if 'product_name' in actual_input_data_list:
                            # Update Product Name
                            product.name = row.get('product_name')
                        if 'description' in actual_input_data_list:
                            # Update Description
                            product.description = row.get('description')
                        product.save()
                return render(request, 'admin/pos/retailerproductscsvupload.html',
                              {'form': form,
                               'success': 'Products Updated Successfully!', })

    else:
        form = RetailerProductsCSVUploadForm()
        return render(
            request,
            'admin/pos/retailerproductscsvupload.html',
            {'form': form}
        )


def DownloadRetailerCatalogue(request, *args):
    """
    This function will return an File in csv format which can be used for Downloading the Product Catalogue
    """
    shop_id = request.GET['shop_id']
    filename = "retailer_products_update_sample_file.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(
        ['product_id', 'shop', 'product_sku', 'product_name', 'mrp', 'selling_price', 'linked_product_sku', 'description',
         'sku_type', 'category', 'sub_category', 'brand', 'sub_brand', 'status'])
    if RetailerProduct.objects.filter(shop_id=int(shop_id)).exists():
        retailer_products = RetailerProduct.objects.filter(shop_id=int(shop_id))

        for product in retailer_products:
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
            writer.writerow(
                [product.id, product.shop, product.sku, product.name,
                 product.mrp, product.selling_price, linked_product_sku, product.description,
                 sku_type, category, sub_category, brand, sub_brand, product.status])
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
    writer.writerow(['product_name', 'mrp', 'linked_product_sku', 'selling_price', 'description'])
    writer.writerow(['Noodles', '12', 'ORCPCRTOY000000020820', '10', 'XYZ'])
    return response
