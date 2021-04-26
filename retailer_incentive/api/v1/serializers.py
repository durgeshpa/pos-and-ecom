from rest_framework import serializers

from retailer_incentive.models import SchemeShopMapping, SchemeSlab, Scheme
from shops.models import ShopUserMapping, Shop
from accounts.models import User


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
