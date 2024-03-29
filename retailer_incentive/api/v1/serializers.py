import datetime

from django.db import transaction
from decimal import Decimal
import logging
import io
import xlsxwriter
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.urls import reverse
from rest_framework import serializers

from retailer_incentive.common_validators import bulk_incentive_data_validation
from retailer_incentive.models import SchemeShopMapping, SchemeSlab, Scheme, Incentive, BulkIncentive
from retailer_incentive.utils import pos_save_file
from shops.models import ShopUserMapping, Shop
from accounts.models import User


info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


class SchemeSlabSerializer(serializers.ModelSerializer):

    discount_type = serializers.SerializerMethodField('m_discount_type')

    def m_discount_type(self, obj):
        return SchemeSlab.DISCOUNT_TYPE_CHOICE[obj.discount_type]

    class Meta:
        model = SchemeSlab
        fields = ('min_value', 'max_value', 'discount_value', 'discount_type')


class SchemeSerializer(object):
    class Meta:
        model = Scheme
        fields = ('id', 'name', 'start_date', 'end_date')


class SchemeShopMappingSerializer(serializers.ModelSerializer):
    scheme_name = serializers.SerializerMethodField('m_scheme_name')
    start_date = serializers.SerializerMethodField('m_start_date')
    end_date = serializers.SerializerMethodField('m_end_date')
    slabs = serializers.SerializerMethodField('scheme_slab')

    def scheme_slab(self, obj):
        slabs = SchemeSlab.objects.filter(scheme=obj.scheme)
        serializer = SchemeSlabSerializer(slabs, many=True)
        return serializer.data

    def m_scheme_name(self, obj):
        return obj.scheme.name

    def m_start_date(self, obj):
        return obj.scheme.start_date

    def m_end_date(self, obj):
        return obj.scheme.end_date

    class Meta:
        model = SchemeShopMapping
        fields = ('scheme', 'scheme_name', 'start_date', 'end_date', 'shop', 'slabs')


class EmployeeDetails(serializers.ModelSerializer):
    class Meta:
        """ Meta class """
        model = User
        fields = ['id', 'first_name', 'last_name']


class SalesExecutiveListSerializer(serializers.ModelSerializer):
    employee = EmployeeDetails(read_only=True)

    class Meta:
        """ Meta class """
        model = ShopUserMapping
        fields = ['employee', ]


class SchemeDetailSerializer(serializers.ModelSerializer):
    scheme = serializers.SerializerMethodField('scheme_slab')

    def scheme_slab(self, obj):
        slabs = SchemeSlab.objects.filter(scheme=obj.scheme)
        serializer = SchemeSlabSerializer(slabs, many=True)
        return serializer.data

    class Meta:
        """ Meta class """
        model = SchemeSlab
        fields = ['id', 'scheme', ]


class IncentiveSerializer(serializers.ModelSerializer):
    uploaded_file = serializers.FileField(label='Upload Incentive')

    class Meta:
        """ Meta class """
        model = BulkIncentive
        fields = ('uploaded_file',)

    def validate(self, data):
        if not data['uploaded_file'].name[-5:] in ('.xlsx'):
            raise serializers.ValidationError('Sorry! Only xlsx file accepted.')

        return data

    @transaction.atomic
    def create(self, validated_data):
        """ create incentive """
        try:
            bulk_incentive_obj = BulkIncentive.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        data = pos_save_file(bulk_incentive_obj)
        return data if data else bulk_incentive_obj


class GetListIncentiveSerializer(serializers.ModelSerializer):
    shop_name = serializers.SerializerMethodField()

    class Meta:
        """ Meta class """
        model = Incentive
        fields = ('shop', 'shop_name', 'capping_applicable', 'capping_value', 'date_of_calculation',
                  'total_ex_tax_delivered_value', 'incentive')

    def get_shop_name(self, obj):
        return obj.shop.shop_name
