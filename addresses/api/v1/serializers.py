from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from addresses.common_validators import get_validate_city_routes, get_validate_routes_mandatory_fields
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
        ref_name = "Address v1"
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


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ('id', 'name')


class StateBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ('id', 'state_name', 'state_code')


class CityBasicSerializer(serializers.ModelSerializer):
    state = StateBasicSerializer(read_only=True)
    city_routes = RouteSerializer(many=True, read_only=True)

    class Meta:
        model = City
        fields = ('id', 'city_name', 'state', 'city_routes')

    def validate(self, data):

        city_id = self.instance.id if self.instance else None
        if 'state' in self.initial_data and self.initial_data['state']:
            try:
                state_instance = State.objects.get(id=self.initial_data['state'])
                data['state'] = state_instance
            except:
                raise serializers.ValidationError("Invalid state")
        else:
            raise serializers.ValidationError("'state' | This is mandatory")

        if 'city_name' in self.initial_data and self.initial_data['city_name']:
            data['city_name'] = str(self.initial_data['city_name']).strip()
        else:
            raise serializers.ValidationError("'city_name' | This is mandatory")

        city_instance = None
        if 'id' in self.initial_data and self.initial_data['id']:
            city_instance = City.objects.filter(id=self.initial_data['id'], state=state_instance).last()
            if not city_instance:
                raise serializers.ValidationError("'id' | Invalid city.")

        if City.objects.filter(
                city_name__iexact=str(self.initial_data['city_name']).strip().lower(), state=state_instance).\
                exclude(id=city_id).exists():
            raise serializers.ValidationError(f"City already exists with this name in state {state_instance}.")

        if 'city_routes' in self.initial_data and self.initial_data['city_routes']:
            if city_instance:
                city_routes = get_validate_city_routes(self.initial_data['city_routes'], city_instance)
            else:
                city_routes = get_validate_routes_mandatory_fields(self.initial_data['city_routes'])
            if 'error' in city_routes:
                raise serializers.ValidationError(city_routes['error'])
            data['routes'] = city_routes['data']['routes']
            data['route_update_ids'] = city_routes['data'].get('route_update_ids', [])

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new City"""
        routes = validated_data.pop("routes", [])
        route_update_ids = validated_data.pop("route_update_ids", [])
        try:
            city_instance = City.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.post_city_save(routes, route_update_ids, city_instance)

        return city_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update City"""
        routes = validated_data.pop("routes", [])
        route_update_ids = validated_data.pop("route_update_ids", [])
        try:
            city_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.post_city_save(routes, route_update_ids, city_instance)

        return city_instance

    def post_city_save(self, routes, route_update_ids, city_instance):
        self.remove_non_exist_city_routes(route_update_ids, city_instance)
        if routes:
            self.create_update_city_routes(routes, city_instance)

    def remove_non_exist_city_routes(self, route_ids, city_instance):
        routes_to_be_deleted = Route.objects.filter(~Q(id__in=route_ids), city=city_instance)
        for route in routes_to_be_deleted:
            if route.route_shops.exists():
                route.route_shops.all().delete()
        routes_to_be_deleted.delete()

    def create_update_city_routes(self, data_list, city_instance):
        for data in data_list:
            if 'id' in data and data['id']:
                Route.objects.filter(id=data['id'], city=city_instance).\
                    update(name=data['name'], updated_by=self.context['user'])
            else:
                Route.objects.create(city=city_instance, name=data['name'], created_by=self.context['user'])


class CityRouteSerializer(serializers.Serializer):
    city = serializers.SerializerMethodField()
    routes = serializers.SerializerMethodField()

    @staticmethod
    def get_city(obj):
        return CityBasicSerializer(City.objects.filter(id=obj['city_id']).last(), read_only=True).data

    @staticmethod
    def get_routes(obj):
        return RouteSerializer(Route.objects.filter(city=obj['city_id']), read_only=True, many=True).data

