import csv
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework import status, authentication
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

from products.models import  ParentProduct, ProductHSN
from .serializers import ParentProductSerializers, ParentProductBulkUploadSerializers, ParentProductExportAsCSVSerializers
from products.utils import MultipartJsonParser
from retailer_backend.utils import SmallOffsetPagination


class ParentProduct(GenericAPIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    parser_classes = [MultipartJsonParser, JSONParser]
    parent_product_list = ParentProduct.objects.all()

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
        return Response(serializer.data)

    def post(self, request):

        """ POST API for Parent Product Creation with Image Category & Tax """

        serializer = ParentProductSerializers(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):

        """ PUT API for Parent Product Updation with Image Category & Tax """

        if not request.POST.get('id'):
            msg = {'is_success': False,
                   'message': ['Please Provide a id to update parent product'],
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        id = int(request.POST.get('id'))
        id_instance = self.parent_product_list.filter(id=id).last()
        if id_instance is None:
            msg = {'is_success': False,
                   'message': ['Please Provide a Valid id to update parent product'],
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        serializer = ParentProductSerializers(instance=id_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
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

        msg = {'is_success': True,
               'message': 'Parent Product were deleted successfully!',
               'data': None
               }
        return Response(msg, status=status.HTTP_204_NO_CONTENT)


class ParentProductBulkUpload(CreateAPIView):
    serializer_class = ParentProductBulkUploadSerializers

    def post(self, request, *args, **kwargs):

        """ POST API for Bulk Upload Parent Product CSV with Category & Tax """

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response('Parent Product CSV uploaded successfully !',
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ParentProductExportAsCSV(GenericAPIView):

    def post(self, request):

        """ POST API for Download Selected Parent Product CSV with Image Category & Tax """

        serializer = ParentProductExportAsCSVSerializers(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


