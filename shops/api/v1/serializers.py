from rest_framework import serializers
from shops.models import (RetailerType, ShopType, Shop, ShopPhoto, 
    ShopRequestBrand, ShopDocument, ShopUserMapping, SalesAppVersion)
from django.contrib.auth import get_user_model
from accounts.api.v1.serializers import UserSerializer,GroupSerializer
from retailer_backend.validators import MobileNumberValidator
from rest_framework import validators

User =  get_user_model()

class RetailerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailerType
        fields = '__all__'

class ShopTypeSerializer(serializers.ModelSerializer):
    shop_type = serializers.SerializerMethodField()

    def get_shop_type(self, obj):
        return obj.get_shop_type_display()

    class Meta:
        model = ShopType
        fields = '__all__'
        #extra_kwargs = {
        #    'shop_sub_type': {'required': True},
        #}

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_sub_type'] = RetailerTypeSerializer(instance.shop_sub_type).data
        return response



class ShopSerializer(serializers.ModelSerializer):
    shop_id = serializers.SerializerMethodField('my_shop_id')

    def my_shop_id(self, obj):
        return obj.id

    class Meta:
        model = Shop
        fields = ('id','shop_name','shop_type','imei_no','shop_id')

class ShopPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopPhoto
        fields = ('__all__')
        extra_kwargs = {
            'shop_name': {'required': True},
            'shop_photo': {'required': True},
            }

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_name'] = ShopSerializer(instance.shop_name).data
        return response

class ShopDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopDocument
        fields = ('__all__')
        extra_kwargs = {
            'shop_name': {'required': True},
            }

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_name'] = ShopSerializer(instance.shop_name).data
        return response

class ShopRequestBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopRequestBrand
        fields = '__all__'

class ShopUserMappingSerializer(serializers.ModelSerializer):
    shop = ShopSerializer()
    employee = UserSerializer()
    employee_group = GroupSerializer()

    class Meta:
        model = ShopUserMapping
        fields = ('shop','manager','employee','employee_group','created_at','status')


class SellerShopSerializer(serializers.ModelSerializer):
    shop_owner = serializers.CharField(max_length=10, allow_blank=False, trim_whitespace=True, validators=[MobileNumberValidator])

    class Meta:
        model = Shop
        fields = ('id', 'shop_owner', 'shop_name', 'shop_type', 'imei_no')
        extra_kwargs = {
            'shop_owner': {'required': True},
        }

class AppVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesAppVersion
        fields = ('app_version', 'update_recommended','force_update_required')

class ShopUserMappingUserSerializer(serializers.ModelSerializer):
    employee = UserSerializer()

    class Meta:
        model = ShopUserMapping
        fields = ('shop','manager','employee','employee_group','created_at','status')

