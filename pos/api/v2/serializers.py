from shops.models import Shop, RetailerType, ShopType
from pos.models import (PosStoreRewardMapping, ShopRewardConfig, ShopRewardConfigration,
                        ShopConfigKey, ShopConfigKey)
from rest_framework import serializers
from django.db import transaction

"""
@Durgesh patel
"""

class ShopOwnerNameListSerializer(serializers.ModelSerializer):
    shop_owner_id = serializers.SerializerMethodField('get_user_id')
    first_name = serializers.SerializerMethodField('get_user_first_name')
    last_name = serializers.SerializerMethodField('get_user_last_name')
    phone_number = serializers.SerializerMethodField('get_user_phone_number')
    email = serializers.SerializerMethodField('get_user_email')

    class Meta:
        model = Shop
        fields = ('shop_owner_id', 'first_name',
                  'last_name', 'phone_number', 'email',)
        ref_name = "Shop Owner Name List Serializer v1"

    def get_user_id(self, obj):
        return obj.shop_owner.id if obj.shop_owner else None

    def get_user_first_name(self, obj):
        return obj.shop_owner.first_name if obj.shop_owner else None

    def get_user_last_name(self, obj):
        return obj.shop_owner.last_name if obj.shop_owner else None

    def get_user_phone_number(self, obj):
        return obj.shop_owner.phone_number if obj.shop_owner else None

    def get_user_email(self, obj):
        return obj.shop_owner.email if obj.shop_owner else None


class ShopNameListSerializer(serializers.ModelSerializer):
    shop_id = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField('get_user_first_name')
    last_name = serializers.SerializerMethodField('get_user_last_name')
    phone_number = serializers.SerializerMethodField('get_user_phone_number')
    shop_type = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = ('shop_id', 'shop_name', 'first_name', 'last_name', 'phone_number', 'shop_type')

    def get_shop_id(self, obj):
        return obj.id

    def get_user_first_name(self, obj):
        return obj.shop_owner.first_name if obj.shop_owner else None

    def get_user_last_name(self, obj):
        return obj.shop_owner.last_name if obj.shop_owner else None

    def get_user_phone_number(self, obj):
        return obj.shop_owner.phone_number if obj.shop_owner else None

    def get_shop_type(self, obj):
        return obj.shop_type.shop_sub_type.retailer_type_name if obj.shop_type else None

class RetailerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailerType
        fields = ('id', 'retailer_type_name')
        ref_name = "RetailerTypeSerializer v1"

class ShopTypeListSerializers(serializers.ModelSerializer):
    shop_sub_type = RetailerTypeSerializer(read_only=True)

    class Meta:
        model = ShopType
        ref_name = "ShopTypeListSerializers v1"
        fields = ('id', 'shop_type', 'shop_sub_type')

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_type'] = instance.get_shop_type_display()
        response['shop_type_value'] = instance.shop_type
        return response

class RewardConfigListShopSerializers(serializers.ModelSerializer):
    pin_code = serializers.SerializerMethodField()
    shop_name = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    class Meta:
        model = ShopRewardConfig
        fields = ('id','shop', 'shop_name', 'city', 'pin_code', 'status')

    def get_pin_code(self, obj):
        return obj.shop.get_shop_pin_code

    def get_shop_name(self, obj):
        return obj.shop.shop_name

    def get_city(self, obj):
        return obj.shop.city_name


class ShopConfigSerializers(serializers.ModelSerializer):
    key_id = serializers.SerializerMethodField()
    key_name = serializers.SerializerMethodField()
    class Meta:
        model = ShopRewardConfigration
        fields = ('key_id','key_name','value')

    def get_key_id(self, obj):
        return obj.key.id

    def get_key_name(self, obj):
        return obj.key.key






class RewardConfigShopSerializers(serializers.ModelSerializer):
    shop_config = serializers.SerializerMethodField()#ShopConfigSerializers(many=True)
    class Meta:
        model = ShopRewardConfig
        fields = ('id', 'shop','status', 'shop_config')
        """('id','shop', 'status', 'min_order_value',
            'is_point_add_pos_order', 'point_add_pos_order', 'is_point_add_ecom_order',
            'point_add_ecom_order', 'is_point_add_ecom_order',
            'is_max_redeem_point_ecom', 'max_redeem_point_ecom', 'is_max_redeem_point_pos', 'max_redeem_point_pos',
            'value_of_each_point', 'first_order_redeem_point', 'second_order_redeem_point',
            'max_monthly_points_added', 'max_monthly_points_redeemed')"""
    def get_shop_config(self,obj):
        query = ShopRewardConfigration.objects.filter(shop_config=obj.id)
        return ShopConfigSerializers(query, many=True).data

    def validate(self, data):

        return data

    #@transaction.atomic
    def create(self, validated_data):
        """create a new RewardConfigShop"""
        try:
            shop_instance = ShopRewardConfig.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return shop_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Shop's attribute. """
            # call super to save modified instance along with the validated data
        try:
            shop_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return shop_instance

class ShopRewardConfigKeySerilizer(serializers.ModelSerializer):
    """ShopRewardConfigKeySerilizer"""
    class Meta:
        model = ShopConfigKey
        fields = ('id' ,'key')
