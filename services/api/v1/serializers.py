# from rest_framework import serializers
# from services.models import (OrderDetailReports, OrderReports,GRNReports, MasterReports, OrderGrnReports, RetailerReports, CategoryProductReports)
# from django.contrib.auth import get_user_model
# from rest_framework import validators
#
# User =  get_user_model()
#
# class OrderDetailReportsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = OrderDetailReports
#         fields = '__all__'
#
# class OrderReportsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = OrderReports
#         fields = '__all__'
#
# class GRNReportsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = GRNReports
#         fields = '__all__'
#
# class MasterReportsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = MasterReports
#         fields = '__all__'
#
# class OrderGrnReportsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = OrderGrnReports
#         fields = '__all__'
#
# class RetailerReportsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = RetailerReports
#         fields = '__all__'
#
# class CategoryProductReportsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CategoryProductReports
#         fields = '__all__'