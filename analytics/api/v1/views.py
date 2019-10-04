from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.generics import ListCreateAPIView,RetrieveUpdateDestroyAPIView
from rest_framework.decorators import api_view
from rest_framework.views import APIView
import datetime
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import permissions, authentication
from products.models import Product
from services.models import RetailerReports, OrderReports,GRNReports, MasterReports, OrderGrnReports, OrderDetailReports, CategoryProductReports
from .serializers import ProductSerializer
from rest_framework.response import Response
from rest_framework import status

class CategoryProductReport(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ProductSerializer
    authentication_classes = (authentication.TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product = Product.objects.get(id=request.data.get("id"))
            for cat in product.product_pro_category.all():
                product_id = product.id
                product_name = product.product_name
                product_short_description = product.product_short_description
                product_created_at = product.created_at
                category_id = cat.category.id
                category = cat.category
                category_name = cat.category.category_name
                print(cat)
                # CategoryProductReports.objects.using('gfanalytics').create(product_id = product_id,
                # product_name = product_name, product_short_description=product_short_description, product_created_at=product_created_at,
                # category_id=category_id, category=category, category_name=category_name)
            return Response({"message": [""], "response_data": '', "is_success": True})
        else:
            errors = []
            for field in serializer.errors:
                for error in serializer.errors[field]:
                    if 'non_field_errors' in field:
                        result = error
                    else:
                        result = ''.join('{} : {}'.format(field,error))
                    errors.append(result)
            msg = {'is_success': False,
                    'message': [error for error in errors],
                    'response_data': None }
            return Response(msg,status=status.HTTP_406_NOT_ACCEPTABLE)

