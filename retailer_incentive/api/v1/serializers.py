
from rest_framework import serializers

from accounts.api.v1.serializers import UserSerializer
from retailer_backend.messages import SUCCESS_MESSAGES
from retailer_incentive.models import SchemeShopMapping, SchemeSlab, Scheme
from shops.api.v1.serializers import ShopSerializer
from shops.models import ShopUserMapping


class SchemeSlabSerializer(serializers.ModelSerializer):

    def validate(self, data):
        if data['min_value'] > data['max_value']:
            raise serializers.ValidationError("min_value must be less than max value")
        return data

    class Meta:
        model = SchemeSlab
        fields = ('min_value', 'max_value', 'discount_value', 'discount_type')


class SchemeSerializer(object):
    class Meta:
        model = Scheme
        fields = ('id', 'name')


class SchemeShopMappingSerializer(serializers.ModelSerializer):
    scheme = SchemeSerializer()
    slabs = serializers.SerializerMethodField('scheme_slab')

    def scheme_slab(self, obj):
        slabs = SchemeSlab.objects.filter(scheme=obj.scheme)
        serializer = SchemeSlabSerializer(slabs, many=True)
        return serializer.data

    def to_representation(self, obj):
        representation = super(SchemeShopMappingSerializer, self).to_representation(obj)
        representation['scheme_name'] = obj.scheme.name
        return representation

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("start_date must be earlier than end_date")
        return data

    class Meta:
        model = SchemeShopMapping
        fields = ('scheme', 'shop', 'start_date', 'end_date', 'slabs')

#
# class ShopSalesMatrixSerializer(serializers.ModelSerializer):
#     purchase_value = serializers.SerializerMethodField('m_total_sales')
#     discount_percentage = serializers.SerializerMethodField('m_discount_percentage')
#     discount_value = serializers.SerializerMethodField('m_discount_value')
#     # add_on_amount = serializers.SerializerMethodField('m_add_on_amount')
#     # add_on_discount = serializers.SerializerMethodField('m_add_on_discount')
#     # add_on_discount_percentage = serializers.SerializerMethodField('m_add_on_discount_percentage_m')
#     message = serializers.SerializerMethodField('m_get_message')
#
#     def m_total_sales(self):
#         shop_id = self.context.get('shop_id', None)
#         return 15000
#
#     def m_discount_percentage(self):
#         shop_id = self.context.get('shop_id', None)
#         if SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True).exists():
#             scheme = SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True).last().scheme
#             scheme_slab = SchemeSlab.objects.filter(scheme=scheme,
#                                                      min_value__lte=self.get_total_sales(),
#                                                      max_value__gt=self.get_total_sales())
#             if scheme_slab.exists():
#                 return scheme_slab.discount_value
#         return 0
#
#     def m_discount_value(self):
#         return self.get_total_sales()*self.discount_percentage/100
#     #
#     # def get_add_on_amount(self):
#     #     shop_id = self.context.get('shop_id', None)
#     #     scheme_slab = self.get_next_slab(shop_id)
#     #     if scheme_slab is not None:
#     #         return (scheme_slab.min_value - self.get_total_sales())
#     #
#     # def get_add_on_discount(self):
#     #     shop_id = self.context.get('shop_id', None)
#     #     scheme_slab = self.get_next_slab(shop_id)
#     #     if scheme_slab is not None:
#     #         return (scheme_slab.min_value * scheme_slab.discount_value/100)
#     #
#     # def get_add_on_discount(self):
#     #     shop_id = self.context.get('shop_id', None)
#     #     scheme_slab = self.get_next_slab(shop_id)
#     #     if scheme_slab is not None:
#     #         return  scheme_slab.discount_value
#
#     def m_message(self):
#         shop_id = self.context.get('shop_id', None)
#         scheme_slab = self.get_next_slab(shop_id)
#         if scheme_slab is not None:
#             return SUCCESS_MESSAGES['SCHEME_SLAB_ADD_MORE']\
#                 .format((scheme_slab.min_value - self.get_total_sales()),
#                         (scheme_slab.min_value * scheme_slab.discount_value/100),
#                         scheme_slab.discount_value)
#         return SUCCESS_MESSAGES['SCHEME_SLAB_HIGHEST']
#
#
#     class Meta:
#         model = SchemeShopMapping
#         fields = ('purchase_value', 'discount_percentage', 'discount_value', 'message' )
