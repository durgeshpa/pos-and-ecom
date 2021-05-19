from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import status, authentication
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser

from products.models import ParentProduct as ParentProducts, ProductHSN, ProductCapping as ProductCappings
from products.utils import MultipartJsonParser
from retailer_backend.utils import SmallOffsetPagination
from .serializers import ParentProductSerializers, ParentProductBulkUploadSerializers, \
    ParentProductExportAsCSVSerializers, ActiveDeactivateSelectedProductSerializers, \
    ProductCappingSerializers, ProductVendorMappingSerializers
from .common_function import validate_id, get_response


class ParentProduct(GenericAPIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    parser_classes = [MultipartJsonParser, JSONParser]
    queryset = ParentProducts.objects.prefetch_related('parent_brand', 'product_hsn', 'parent_product_pro_image',
                                                       'parent_product_pro_category', 'parent_product_pro_tax',
                                                       'parent_product_pro_category__category',
                                                       'parent_product_pro_tax__tax')
    serializer_class = ParentProductSerializers

    def get(self, request):
        """ Get Parent Product when product_id is given in params """

        if request.GET.get('id'):
            """ Get Parent Product when id is given in params """
            # validations for input id
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            parent_product = id_validation['data']
        else:
            """ GET API to get Parent Product List """
            self.queryset = self.get_parent_product_list()
            parent_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(parent_product, many=True)
        msg = {'is_success': True, 'message': ['Parent Product List'], 'response_data': {'results': serializer.data}}
        return Response(msg, status=status.HTTP_200_OK)

    def post(self, request):

        """ POST API for Parent Product Creation with Image Category & Tax """

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return get_response('Parent Product created successfully!', serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):

        """ PUT API for Parent Product Updation with Image Category & Tax """

        if not request.POST.get('id'):
            msg = {'is_success': False,
                   'message': 'Please Provide a id to update parent product',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.POST.get('id')))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        parent_product_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=parent_product_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return get_response('Parent Product Updated', serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):

        """ Delete Parent Product with image """

        if not request.data.get('parent_product_id'):
            return get_response('Please Provide a parent_product_id', False)
        try:
            for id in request.data.get('parent_product_id'):
                parent_product_id = self.queryset.get(id=int(id))
                parent_product_id.delete()
        except ObjectDoesNotExist:
            return get_response(f'Please Provide a Valid parent_product_id {id}', False)
        return get_response('Parent Product were deleted successfully!', [], True)

    def get_parent_product_list(self):

        category = self.request.GET.get('category')
        brand = self.request.GET.get('brand')
        product_status = self.request.GET.get('status')
        search_text = self.request.GET.get('search_text')

        # search using parent_id, name & category_name based on criteria that matches
        if search_text:
            self.queryset = self.queryset.filter(Q(name__icontains=search_text)
                                 | Q(parent_product_pro_category__category__category_name__icontains=search_text)
                                 | Q(parent_id__icontains=search_text))

        # filter using brand_name, category & product_status exact match
        if brand is not None:
            self.queryset = self.queryset.filter(parent_brand__brand_name=brand)
        if product_status is not None:
            self.queryset = self.queryset.filter(status=product_status)
        if category is not None:
            self.queryset = self.queryset.filter(
                parent_product_pro_category__category__category_name=category)

        return self.queryset


class ParentProductBulkUpload(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ParentProductBulkUploadSerializers

    def post(self, request, *args, **kwargs):

        """ POST API for Bulk Upload Parent Product CSV with Category & Tax """

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True, 'message': ['Parent Product CSV uploaded successfully !'],
                   'response_data': {'results': None}}
            return Response(msg, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ParentProductExportAsCSV(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request):

        """ POST API for Download Selected Parent Product CSV with Image Category & Tax """

        serializer = ParentProductExportAsCSVSerializers(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActiveDeactivateSelectedProduct(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    parent_product_list = ParentProducts.objects.all()

    def put(self, request):

        """ PUT API for Activate or Deactivate Selected Parent Product """

        serializer = ActiveDeactivateSelectedProductSerializers(instance=
                            self.parent_product_list.filter(id__in=request.data['parent_product_id_list']),
                            data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True, 'message': ['Parent Product Updated'],
                   'response_data': {'results': serializer.data}}
            return Response(msg, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductCapping(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ProductCappings.objects.select_related('product', 'seller_shop', 'buyer_shop')
    serializer_class = ProductCappingSerializers

    def get(self, request):

        if request.GET.get('id'):
            """ Get Parent Product when id is given in params """
            # validations for input id
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_capping = id_validation['data']

        else:
            """ GET API to get Parent Product List """
            self.queryset = self.get_product_capping()
            product_capping = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(product_capping, many=True)
        msg = {'is_success': True, 'message': ['Product Capping List'], 'response_data': {'results': serializer.data}}
        return Response(msg, status=status.HTTP_200_OK)

    def post(self, request):

        """ Post API for Product Capping Creation """

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True, 'message': ['Product Capping Created'],
                   'response_data': {'results': [serializer.data]}}
            return Response(msg, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):

        """ Put API for Product Capping Updation """

        if not request.data.get('id'):
            msg = {'is_success': False,
                   'message': 'Please Provide id to update product capping',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        cap_product_id = int(request.data.get('id'))
        try:
            id_instance = self.product_capping_list.get(id=cap_product_id)
        except ObjectDoesNotExist:
            msg = {'is_success': False,
                   'message': f'product capping id "{cap_product_id}" not found, Please Provide a Valid id',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        serializer = self.serializer_class(instance=id_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True, 'message': ['Product Capping Updated'],
                   'response_data': {'results': [serializer.data]}}
            return Response(msg, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):

        """ Delete Product Capping """

        if not request.data.get('product_capping_id'):
            msg = {'is_success': False,
                   'message': 'Please Provide a product_capping_id',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            for cap_product_id in request.data.get('product_capping_id'):
                product_capping_id = self.product_capping_list.get(id=int(cap_product_id))
                product_capping_id.delete()
        except ObjectDoesNotExist:
            msg = {'is_success': False,
                   'message': f'id {cap_product_id} not found',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        msg = {'is_success': True, 'message': ['Product Capping were deleted successfully!'],
               'response_data': {'results': None}}
        return Response(msg, status=status.HTTP_200_OK)

    def get_product_capping(self):
        product_sku = self.request.GET.get('product_sku')
        product_name = self.request.GET.get('product_name')
        product_capping_status = self.request.GET.get('status')
        seller_shop = self.request.GET.get('seller_shop')

        # filter using product_sku, seller_shop, product_capping_status & product_name
        if product_sku is not None:
            self.queryset = self.queryset.filter(product__product_sku__icontains=product_sku)
        if seller_shop is not None:
            self.queryset = self.queryset.filter(seller_shop_id=seller_shop)
        if product_capping_status is not None:
            self.queryset = self.queryset.filter(status=product_capping_status)
        if product_name is not None:
            self.queryset = self.queryset.filter(
                product_id=product_name)

        return self.queryset
