from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import status, authentication
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser

from products.models import ParentProduct as ParentProducts, ProductHSN, ProductCapping
from products.utils import MultipartJsonParser
from retailer_backend.utils import SmallOffsetPagination
from .serializers import ParentProductSerializers, ParentProductBulkUploadSerializers, \
    ParentProductExportAsCSVSerializers, ActiveDeactivateSelectedProductSerializers, \
    ProductCappingSerializers


class ParentProduct(GenericAPIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    parser_classes = [MultipartJsonParser, JSONParser]
    parent_product_list = ParentProducts.objects.all()

    def get(self, request):

        """ GET API to get Parent Product List """

        category = request.GET.get('category')
        brand = request.GET.get('brand')
        product_status = request.GET.get('status')
        search_text = request.GET.get('search_text')

        if request.GET.get('parent_product_id'):

            """ Get Parent Product when product_id is given in params """

            parent_pro_id = int(request.GET.get('parent_product_id'))
            if self.parent_product_list.filter(id=parent_pro_id).last() is None:
                msg = {'is_success': False,
                       'message': ['Please Provide a Valid parent_product_id'],
                       'data': None}
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

            self.parent_product_list = self.parent_product_list.filter(id=parent_pro_id)

        # search using parent_id, category_name & name based on criteria that matches
        if search_text is not None:
            self.parent_product_list = self.parent_product_list.filter(Q(name__icontains=search_text)
                                                                       | Q(parent_id__icontains=search_text)
                                                                       | Q(parent_product_pro_category__category__category_name__icontains=search_text))
            
        # filter using brand_name, category & product_status exact match
        if brand is not None:
            self.parent_product_list = self.parent_product_list.filter(parent_brand__brand_name=brand)
        if product_status is not None:
            self.parent_product_list = self.parent_product_list.filter(status=product_status)
        if category is not None:
            self.parent_product_list = self.parent_product_list.filter(parent_product_pro_category__category__category_name=category)
        parent_product = SmallOffsetPagination().paginate_queryset(self.parent_product_list, request)
        serializer = ParentProductSerializers(parent_product, many=True)
        msg = {'is_success': True, 'message': ['Parent Product List'], 'response_data': {'results': [serializer.data]}}
        return Response(msg, status=status.HTTP_200_OK)

    def post(self, request):

        """ POST API for Parent Product Creation with Image Category & Tax """

        serializer = ParentProductSerializers(data=request.data)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True, 'message': ['Parent Product created successfully!'],
                   'response_data': {'results': serializer.data}}
            return Response(msg, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):

        """ PUT API for Parent Product Updation with Image Category & Tax """

        if not request.POST.get('id'):
            msg = {'is_success': False,
                   'message': 'Please Provide a id to update parent product',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        id_instance = self.parent_product_list.filter(id=int(request.POST.get('id'))).last()
        if id_instance is None:
            msg = {'is_success': False,
                   'message': 'Please Provide a Valid id to update parent product',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        serializer = ParentProductSerializers(instance=id_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True, 'message': ['Parent Product Updated'],
                   'response_data': {'results': [serializer.data]}}
            return Response(msg, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):

        """ Delete Parent Product with image """

        if not request.data.get('parent_product_id'):
            msg = {'is_success': False,
                   'message': 'Please Provide a parent_product_id',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            for id in request.data.get('parent_product_id'):
                parent_product_id = self.parent_product_list.get(id=int(id))
                parent_product_id.delete()
        except ObjectDoesNotExist:
            msg = {'is_success': False,
                   'message': f'Please Provide a Valid parent_product_id {id}',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        msg = {'is_success': True, 'message': ['Parent Product were deleted successfully!'],
               'response_data': {'results': None}}
        return Response(msg, status=status.HTTP_200_OK)


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
                   'response_data': {'results': [serializer.data]}}
            return Response(msg, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductCapping(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    product_capping_list = ProductCapping.objects.all()

    def get(self, request):

        """ GET API to get Parent Product List """

        product_sku = request.GET.get('product_sku')
        product_name = request.GET.get('product_name')
        product_capping_status = request.GET.get('status')
        seller_shop = request.GET.get('seller_shop')

        if request.GET.get('id'):

            """ Get Parent Product when id is given in params """
            product_capping_id = int(request.GET.get('id'))
            if self.product_capping_list.filter(id=product_capping_id).last() is None:
                msg = {'is_success': False,
                       'message': ['Please Provide a Valid id'],
                       'data': None}
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

            self.product_capping_list = self.product_capping_list.filter(id=product_capping_id)

        # filter using product_sku, seller_shop, product_capping_status & product_name
        if product_sku is not None:
            self.product_capping_list = self.product_capping_list.filter(product__product_sku__icontains=product_sku)
        if seller_shop is not None:
            self.product_capping_list = self.product_capping_list.filter(seller_shop_id=seller_shop)
        if product_capping_status is not None:
            self.product_capping_list = self.product_capping_list.filter(status=product_capping_status)
        if product_name is not None:
            self.product_capping_list = self.product_capping_list.filter(
                product_id=product_name)
        parent_product = SmallOffsetPagination().paginate_queryset(self.product_capping_list, request)
        serializer = ProductCappingSerializers(parent_product, many=True)
        msg = {'is_success': True, 'message': ['Product Capping List'], 'response_data': {'results': [serializer.data]}}
        return Response(msg, status=status.HTTP_200_OK)


    def post(self, request):

        """ Post API for Product Capping Creation """

        serializer = ProductCappingSerializers(data=request.data)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True, 'message': ['Product Capping Created'],
                   'response_data': {'results': [serializer.data]}}
            return Response(msg, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):

        """ Post API for Product Capping Updation """

        if not request.data.get('id'):
            msg = {'is_success': False,
                   'message': 'Please Provide a id to update product capping',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        id = int(request.data.get('id'))
        try:
            id_instance = self.product_capping_list.get(id=id)
        except ObjectDoesNotExist:
            msg = {'is_success': False,
                   'message': f'product capping id "{id}" not found, Please Provide a Valid id',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        serializer = ProductCappingSerializers(instance=id_instance, data=request.data, partial=True)
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
            for id in request.data.get('product_capping_id'):
                product_capping_id = self.product_capping_list.get(id=int(id))
                product_capping_id.delete()
        except ObjectDoesNotExist:
            msg = {'is_success': False,
                   'message': f'id {id} not found',
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        msg = {'is_success': True, 'message': ['Product Capping were deleted successfully!'],
               'response_data': {'results': None}}
        return Response(msg, status=status.HTTP_200_OK)




