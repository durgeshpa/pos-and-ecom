from shops.models import Shop, RetailerType, ShopType, FOFOConfigurations, FOFOConfigSubCategory
from pos.models import (PosStoreRewardMappings)
from rest_framework import serializers
from django.db import transaction

"""
@Durgesh patel
"""
class ChoiceField(serializers.ChoiceField):

    def to_representation(self, obj):
        if obj == '' and self.allow_blank:
            return obj
        return {'id': obj, 'desc': self._choices[obj]}


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
    shop_owner = serializers.SerializerMethodField()
    shop_type = ShopTypeListSerializers()
    approval_status = ChoiceField(choices=Shop.APPROVAL_STATUS_CHOICES, required=False)
    class Meta:
        model = PosStoreRewardMappings
        fields = ('id', 'shop_name', 'city', 'pin_code', 'approval_status',
            'enable_loyalty_points', 'status', 'shop_owner', 'shop_type')

    def get_pin_code(self, obj):
        return obj.get_shop_pin_code

    def get_shop_name(self, obj):
        return obj.shop_name

    def get_city(self, obj):
        return obj.city_name

    def get_shop_owner(self, obj):
        return obj.shop_owner.first_name


class ShopConfigSerializers(serializers.ModelSerializer):
    key_id = serializers.SerializerMethodField()
    key_name = serializers.SerializerMethodField()
    class Meta:
        model = FOFOConfigurations
        fields = ('id','key_id','key_name','value')

    def get_key_id(self, obj):
        return obj.key.id

    def get_key_name(self, obj):
        return obj.key.name






class RewardConfigShopSerializers(serializers.ModelSerializer):
    shop_config = serializers.SerializerMethodField()#ShopConfigSerializers(many=True)
    class Meta:
        model = PosStoreRewardMappings
        fields = ('id', 'shop_name','enable_loyalty_points', 'shop_config')
        """('id','shop', 'status', 'min_order_value',
            'is_point_add_pos_order', 'point_add_pos_order', 'is_point_add_ecom_order',
            'point_add_ecom_order', 'is_point_add_ecom_order',
            'is_max_redeem_point_ecom', 'max_redeem_point_ecom', 'is_max_redeem_point_pos', 'max_redeem_point_pos',
            'value_of_each_point', 'first_order_redeem_point', 'second_order_redeem_point',
            'max_monthly_points_added', 'max_monthly_points_redeemed')"""
    def get_shop_config(self,obj):
        objects = obj.fofo_shop.all()
        shop_keys = {}
        for obj in objects:
            shop_keys[obj.key.name] = obj.value
        return shop_keys

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
    key_id = serializers.SerializerMethodField()
    class Meta:
        model = FOFOConfigSubCategory
        fields = ('key_id' ,'name')

    def get_key_id(self,obj):
        return obj.id

