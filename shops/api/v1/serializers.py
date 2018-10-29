from rest_framework import serializers
from shops.models import (RetailerType, ShopType, Shop, ShopPhoto, ShopDocument)
from django.contrib.auth import get_user_model
from addresses.api.v1.serializers import (CountrySerializer, StateSerializer,
        CitySerializer, AreaSerializer, AddressSerializer)
from retailer_backend.validators import NameValidator, AddressNameValidator, IDValidator
from rest_framework import validators

User =  get_user_model()

class RetailerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailerType
        fields = '__all__'

class ShopTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopType
        fields = '__all__'
        extra_kwargs = {
            'shop_sub_type': {'required': True},
        }

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_sub_type'] = RetailerTypeSerializer(instance.shop_sub_type).data
        return response

class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('shop_name','shop_type')

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

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_name'] = ShopSerializer(instance.shop_name).data
        return response

class ShopAddressMappingSerializer(serializers.Serializer):
    shop_name = serializers.CharField(max_length=255, validators = [NameValidator])
    city = serializers.IntegerField(max_value=None, min_value=None)
    area = serializers.IntegerField(max_value=None, min_value=None)
    shop_shipping_address = serializers.CharField(max_length=255, validators=[AddressNameValidator])
    shop_billing_address = serializers.CharField(max_length=255, validators=[AddressNameValidator])
    shop_type = serializers.IntegerField(max_value=None, min_value=None)
