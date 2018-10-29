from rest_framework import serializers
from addresses.models import (Country, State, City, Area, Address)

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = '__all__'

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'

class AreaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Area
        fields = '__all__'
        extra_kwargs = {
            'city': {'required': True},
        }

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['city'] = CitySerializer(instance.city).data
        return response

from shops.api.v1.serializers import ShopSerializer

class AddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = Address
        fields = '__all__'
        extra_kwargs = {
            'city': {'required': True},
            'state': {'required': True},
            'shop_name': {'required': True},
            'address_line1': {'required': True},
            'pincode': {'required': True},
            'address_contact_number': {'required': True},
            'address_contact_name': {'required': True},
        }

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['city'] = CitySerializer(instance.city).data
        response['state'] = StateSerializer(instance.state).data
        response['shop_name'] = ShopSerializer(instance.shop_name).data
        return response
