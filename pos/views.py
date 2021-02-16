import decimal
import uuid

from rest_framework import status, authentication, permissions
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from pos.models import RetailerProduct, RetailerProductImage
from pos.serializers import RetailerProductCreateSerializer, RetailerProductUpdateSerializer, \
    RetailerProductResponseSerializer
from products.models import Product
from shops.models import Shop

POS_SERIALIZERS_MAP = {
    '0' : RetailerProductCreateSerializer,
    '1' : RetailerProductUpdateSerializer
}




class CatalogueProductCreation(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)


    def get_shop_id(self, request):
        if request.data.get('shop_id'):
            return request.data.get('shop_id')
        else:
            shop = Shop.objects.filter(shop_owner_id=request.user.id)
            return shop.values()[0].get('id')

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
        shop_id = self.get_shop_id(request)
        serializer = self.get_serializer_class(0)(data=request.data, partial=True)
        if serializer.is_valid():
            product_sku = str(uuid.uuid4()).split('-')[-1][:6].upper() # Generate a unique SKU by using uuid4
            # if else condition for checking whether, Product we are creating is linked with existing product or not
            # with the help of 'linked_product_id'
            if request.data.get('linked_product_id'):
                # If product is linked with existing product
                if Product.objects.filter(id=request.data.get('linked_product_id')).exists():
                    product = Product.objects.filter(id=request.data.get('linked_product_id'))
                    if str(product.values()[0].get('product_mrp')) == format(decimal.Decimal(request.data.get('mrp')), ".2f"):
                        # If Linked_Product_MRP == Input_MRP , create a Product with [SKU TYPE : LINKED]
                        RetailerProduct.objects.create(shop_id=shop_id,
                                                       sku=product_sku, name=request.data.get('product_name'),
                                                       linked_product_id=request.data.get('linked_product_id'),
                                                       mrp=request.data.get('mrp'), sku_type=2,
                                                       selling_price=request.data.get('selling_price'),
                                                       description=request.data.get('description') if request.data.get('description') else '')
                    else:
                        # If Linked_Product_MRP != Input_MRP, Create a new Product with SKU_TYPE == "LINKED_EDITED"
                        RetailerProduct.objects.create(shop_id=shop_id,
                                                       sku=product_sku, name=request.data.get('product_name'),
                                                       linked_product_id=request.data.get('linked_product_id'),
                                                       mrp=request.data.get('mrp'),
                                                       sku_type=3, selling_price=request.data.get('selling_price'),
                                                       description=request.data.get('description') if request.data.get('description') else '')
            else:
                # If product is not linked with existing product, Create a new Product with SKU_TYPE == "Created"
                RetailerProduct.objects.create(shop_id=shop_id,
                                               sku=product_sku, name=request.data.get('product_name'),
                                               mrp=request.data.get('mrp'),
                                               selling_price=request.data.get('selling_price'),
                                               description=request.data.get('description') if request.data.get('description') else '')
            product = RetailerProduct.objects.all().last()
            # Fetching the data of created product
            data = RetailerProduct.objects.values('id', 'shop__shop_name', 'name', 'sku', 'mrp', 'selling_price', 'description', 'sku_type',
                                               'linked_product__product_name', 'created_at', 'modified_at').filter(id=product.id)
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
                   'error_message': errors[0] if len(errors)==1  else [error for error in errors],
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    def put(self, request, *args, **kwargs):
        """
        PUT API for Product Update.
        Using RetailerProductUpdateSerializer for request and RetailerProductResponseSerializer for response.
        """

        # RetailerProductUpdateSerializer is used
        shop_id = self.get_shop_id(request)
        serializer = self.get_serializer_class(1)(data=request.data, partial=True)
        product_status = "UPDATED"
        if serializer.is_valid():
            if RetailerProduct.objects.filter(id=request.data.get('product_id'), shop_id=shop_id).exists():
                expected_input_data_list = ['product_name', 'product_id', 'mrp', 'selling_price', 'description']
                actual_input_data_list = [] # List of keys that user wants to update(If user wants to update product_name, this list wil only have product_name)
                for key in expected_input_data_list:
                    if key in request.data.keys():
                        actual_input_data_list.append(key)
                product = RetailerProduct.objects.filter(id=request.data.get('product_id'))
                if product.values()[0].get('linked_product_id'):
                    # Checking whether the product is Linked or not!
                    if 'mrp' in actual_input_data_list:
                        # If MRP in actual_input_data_list
                        if format(decimal.Decimal(request.data.get('mrp')), ".2f") == str(product.values()[0].get('mrp')):
                            # If Input_MRP == Product_MRP
                            if 'selling_price' in actual_input_data_list:
                                # If selling price in actual_input_data_list
                                RetailerProduct.objects.filter(id=request.data.get('product_id')).update(selling_price=request.data.get('selling_price'))
                            if 'product_name' in actual_input_data_list:
                                # Update Product Name
                                RetailerProduct.objects.filter(id=request.data.get('product_id')).update(name=request.data.get('product_name'))
                            if 'description' in actual_input_data_list:
                                # Update Description
                                RetailerProduct.objects.filter(id=request.data.get('product_id')).update(description=request.data.get('description'))
                        else:
                            # If Input_MRP != Product_MRP, Create a new product with [SKU Type : Created]
                            product_status = "CREATED"
                            product_sku = str(uuid.uuid4()).split('-')[-1][:6].upper()
                            RetailerProduct.objects.create(shop_id=product.values()[0].get('shop_id'),
                                                           sku=product_sku, name=request.data.get('product_name'),
                                                           mrp=request.data.get('mrp'), sku_type=3,
                                                           selling_price=request.data.get('selling_price'),
                                                           description=request.data.get('description') if request.data.get(
                                                               'description') else '')
                    else:
                        # If MRP not in actual_input_data_list
                        if 'selling_price' in actual_input_data_list:
                            # If selling price in actual_input_data_list
                            RetailerProduct.objects.filter(id=request.data.get('product_id')).update(
                                selling_price=request.data.get('selling_price'), sku_type=3)
                        if 'product_name' in actual_input_data_list:
                            # Update Product Name
                            RetailerProduct.objects.filter(id=request.data.get('product_id')).update(
                                name=request.data.get('product_name'))
                        if 'description' in actual_input_data_list:
                            # Update Description
                            RetailerProduct.objects.filter(id=request.data.get('product_id')).update(
                                description=request.data.get('description'))
                else:
                    # If not Linked with any product
                    if 'mrp' in actual_input_data_list:
                        # If MRP in actual_input_data_list
                        if format(decimal.Decimal(request.data.get('mrp')), ".2f") == str(product.values()[0].get('mrp')):
                            # If Input_MRP == Product_MRP
                            if 'selling_price' in actual_input_data_list:
                                # Update selling price
                                RetailerProduct.objects.filter(id=request.data.get('product_id')).update(
                                    selling_price=request.data.get('selling_price'))
                            if 'product_name' in actual_input_data_list:
                                # Update product name
                                RetailerProduct.objects.filter(id=request.data.get('product_id')).update(
                                    name=request.data.get('product_name'))
                            if 'description' in actual_input_data_list:
                                # Update description
                                RetailerProduct.objects.filter(id=request.data.get('product_id')).update(
                                    description=request.data.get('description'))
                        else:
                            # If Input_MRP != Product_MRP, Create a new Product with [SKU Type : Created]
                            product_status = "CREATED"
                            product_sku = str(uuid.uuid4()).split('-')[-1][:6].upper()
                            RetailerProduct.objects.create(shop_id=product.values()[0].get('shop_id'),
                                                           sku=product_sku, name=request.data.get('product_name'),
                                                           mrp=request.data.get('mrp'),
                                                           selling_price=request.data.get('selling_price'),
                                                           description=request.data.get('description') if request.data.get(
                                                               'description') else '')
                    else:
                        # If MRP not in actual_input_data_list
                        if 'selling_price' in actual_input_data_list:
                            # Update selling price
                            RetailerProduct.objects.filter(id=request.data.get('product_id')).update(
                                selling_price=request.data.get('selling_price'))
                        if 'product_name' in actual_input_data_list:
                            # Update product name
                            RetailerProduct.objects.filter(id=request.data.get('product_id')).update(
                                name=request.data.get('product_name'))
                        if 'description' in actual_input_data_list:
                            # Update description
                            RetailerProduct.objects.filter(id=request.data.get('product_id')).update(
                                description=request.data.get('description'))

                if product_status == "UPDATED":
                    data = RetailerProduct.objects.values('id', 'shop__shop_name', 'name', 'sku', 'mrp', 'selling_price','description', 'sku_type',
                                                          'linked_product__product_name', 'created_at', 'modified_at').filter(id=request.data.get('product_id'))
                else:
                    product = RetailerProduct.objects.all().last()
                    data = RetailerProduct.objects.values('id', 'shop__shop_name', 'name', 'sku', 'mrp', 'selling_price',
                                                          'description', 'sku_type',
                                                          'linked_product__product_name', 'created_at',
                                                          'modified_at').filter(id=product.id)
                response_serializer = RetailerProductResponseSerializer(instance=data[0])
                message = {"is_success": True, "message": f"Product has been successfully {product_status}!",
                           "response_data": response_serializer.data}
                if product_status == "UPDATED":
                    return Response(message, status=status.HTTP_202_ACCEPTED)
                else:
                    return Response(message, status=status.HTTP_201_CREATED)
            else:
                msg = {'is_success': False,
                       'message': f"There is no product available with product id -> {request.data.get('product_id')} "
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
                   'message': errors[0] if len(errors) == 1 else [error for error in errors],
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)


