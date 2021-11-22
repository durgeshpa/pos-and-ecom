# from django.shortcuts import render
# from rest_framework.views import APIView
# from rest_framework import permissions, authentication
# from rest_framework.response import Response
# from .serializers import (OrderDetailReportsSerializer, OrderReportsSerializer, GRNReportsSerializer,
#                           MasterReportsSerializer, OrderGrnReportsSerializer, RetailerReportsSerializer,CategoryProductReportsSerializer)
# from services.models import (OrderDetailReports, OrderReports,GRNReports, MasterReports, OrderGrnReports, RetailerReports, CategoryProductReports)
#
# from rest_framework import generics
# from rest_framework import status
# from django.http import Http404
# from rest_framework.decorators import api_view
# from django.contrib.auth import get_user_model
# from django.contrib.auth.models import User
# from django.contrib.auth import authenticate, login
#
# from retailer_backend.messages import SUCCESS_MESSAGES, VALIDATION_ERROR_MESSAGES
# from rest_framework.parsers import FormParser, MultiPartParser
#
# User = get_user_model()
#
# class OrderDetailView(generics.ListAPIView):
#     queryset = OrderDetailReports.objects.all()
#     serializer_class = OrderDetailReportsSerializer
#     permission_classes = (permissions.AllowAny,)
#
#     def list(self, request):
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)
#         msg = {'is_success': True,
#                 'message': None,
#                 'response_data': serializer.data}
#         return Response(msg,
#                         status=status.HTTP_200_OK)
#
#
# class OrderReportsView(generics.ListAPIView):
#     queryset = OrderReports.objects.all()
#     serializer_class = OrderReportsSerializer
#     permission_classes = (permissions.AllowAny,)
#
#     def list(self, request):
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)
#         msg = {'is_success': True,
#                 'message': None,
#                 'response_data': serializer.data}
#         return Response(msg,
#                         status=status.HTTP_200_OK)
#
# class OrderReportView(generics.RetrieveAPIView):
#     queryset = OrderReports.objects.all()
#     serializer_class = OrderReportsSerializer
#     permission_classes = (permissions.AllowAny,)
#
#     def get(self, request, *args, **kwargs):
#         try:
#             a_orderreport = self.queryset.get(pk=kwargs["pk"])
#             return Response(OrderReportsSerializer(a_orderreport).data)
#         except OrderReports.DoesNotExist:
#             return Response(
#                 data={
#                     "message": "Order with id: {} does not exist".format(kwargs["pk"])
#                 },
#                 status=status.HTTP_404_NOT_FOUND
#             )
#
# class GRNReportsView(generics.ListAPIView):
#     queryset = GRNReports.objects.all()
#     serializer_class = GRNReportsSerializer
#     permission_classes = (permissions.AllowAny,)
#
#     def list(self, request):
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)
#         msg = {'is_success': True,
#                 'message': None,
#                 'response_data': serializer.data}
#         return Response(msg,
#                         status=status.HTTP_200_OK)
#
# class GRNReportView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = GRNReports.objects.all()
#     serializer_class = GRNReportsSerializer
#     permission_classes = (permissions.AllowAny,)
#
#     def get(self, request, *args, **kwargs):
#         try:
#             a_orderreport = self.queryset.get(pk=kwargs["pk"])
#             return Response(GRNReportsSerializer(a_orderreport).data)
#         except GRNReports.DoesNotExist:
#             return Response(
#                 data={
#                     "message": "Order with id: {} does not exist".format(kwargs["pk"])
#                 },
#                 status=status.HTTP_404_NOT_FOUND
#             )
#
# class MasterReportsView(generics.ListAPIView):
#     queryset = MasterReports.objects.all()
#     serializer_class = MasterReportsSerializer
#     permission_classes = (permissions.AllowAny,)
#
#     def list(self, request):
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)
#         msg = {'is_success': True,
#                 'message': None,
#                 'response_data': serializer.data}
#         return Response(msg,
#                         status=status.HTTP_200_OK)
#
# class MasterReportView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = MasterReports.objects.all()
#     serializer_class = MasterReportsSerializer
#     permission_classes = (permissions.AllowAny,)
#
#     def get(self, request, *args, **kwargs):
#         try:
#             a_orderreport = self.queryset.get(pk=kwargs["pk"])
#             return Response(MasterReportsSerializer(a_orderreport).data)
#         except MasterReports.DoesNotExist:
#             return Response(
#                 data={
#                     "message": "Order with id: {} does not exist".format(kwargs["pk"])
#                 },
#                 status=status.HTTP_404_NOT_FOUND
#             )
#
# class OrderGrnReportsView(generics.ListAPIView):
#     queryset = OrderGrnReports.objects.all()
#     serializer_class = OrderGrnReportsSerializer
#     permission_classes = (permissions.AllowAny,)
#
#     def list(self, request):
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)
#         msg = {'is_success': True,
#                 'message': None,
#                 'response_data': serializer.data}
#         return Response(msg,
#                         status=status.HTTP_200_OK)
#
# class OrderGrnReportView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = OrderGrnReports.objects.all()
#     serializer_class = OrderGrnReportsSerializer
#     permission_classes = (permissions.AllowAny,)
#
#     def get(self, request, *args, **kwargs):
#         try:
#             a_orderreport = self.queryset.get(pk=kwargs["pk"])
#             return Response(OrderGrnReportsSerializer(a_orderreport).data)
#         except OrderGrnReports.DoesNotExist:
#             return Response(
#                 data={
#                     "message": "Order with id: {} does not exist".format(kwargs["pk"])
#                 },
#                 status=status.HTTP_404_NOT_FOUND
#             )
#
# class RetailerReportsView(generics.ListAPIView):
#     queryset = RetailerReports.objects.all()
#     serializer_class = RetailerReportsSerializer
#     permission_classes = (permissions.AllowAny,)
#
#     def list(self, request):
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)
#         msg = {'is_success': True,
#                 'message': None,
#                 'response_data': serializer.data}
#         return Response(msg,
#                         status=status.HTTP_200_OK)
#
# class CategoryProductReportsView(generics.ListAPIView):
#     queryset = CategoryProductReports.objects.all()
#     serializer_class = CategoryProductReportsSerializer
#     permission_classes = (permissions.AllowAny,)
#
#     def list(self, request):
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)
#         msg = {'is_success': True,
#                 'message': None,
#                 'response_data': serializer.data}
#         return Response(msg,
#                         status=status.HTTP_200_OK)
#
#
#
#



