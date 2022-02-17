from rest_framework import serializers
from addresses.models import (Country, State, City, Area, Address, Pincode, Route)
from retailer_backend.validators import PinCodeValidator

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        ref_name = 'Address State v1'
        fields = '__all__'

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        ref_name = "AddressCity"
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

    pincode = serializers.CharField(max_length=6, min_length=6,
                                    validators=[PinCodeValidator])

    class Meta:
        model = Address
        fields = '__all__'
        extra_kwargs = {
            'city': {'required': True},
            'state': {'required': True},
            'shop_name': {'required': True},
            'pincode': {'required': True},
            'address_line1': {'required': True},
            'address_contact_number': {'required': True},
            'address_contact_name': {'required': True},
        }

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['city'] = CitySerializer(instance.city).data
        response['state'] = StateSerializer(instance.state).data
        response['shop_name'] = ShopSerializer(instance.shop_name).data
        return response


class PinCityStateSerializer(serializers.ModelSerializer):
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()

    @staticmethod
    def get_city(obj):
        return obj.city.city_name

    @staticmethod
    def get_state(obj):
        return obj.city.state.state_name

    class Meta:
        model = Pincode
        fields = ('pincode', 'city', 'state')


class StateBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ('id', 'state_name', 'state_code')


class CityBasicSerializer(serializers.ModelSerializer):
    state = StateBasicSerializer(read_only=True)

    class Meta:
        model = City
        fields = ('id', 'city_name', 'state')


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ('id', 'name')


class CityRouteSerializer(serializers.Serializer):
    city = serializers.SerializerMethodField()
    routes = serializers.SerializerMethodField()

    @staticmethod
    def get_city(obj):
        return CityBasicSerializer(City.objects.filter(id=obj['city_id']).last(), read_only=True).data

    @staticmethod
    def get_routes(obj):
        return RouteSerializer(Route.objects.filter(city=obj['city_id']), read_only=True, many=True).data
