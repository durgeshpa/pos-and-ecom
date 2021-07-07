from addresses.models import Address
from django.db import transaction
from rest_framework import serializers

from shops.models import (RetailerType, ShopType, Shop, ShopPhoto,
                          ShopDocument, ShopInvoicePattern
                          )
from django.contrib.auth import get_user_model
from accounts.api.v1.serializers import UserSerializer


User = get_user_model()

'''
For Shop Type List
'''


class RetailerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailerType
        fields = '__all__'


class ShopTypeSerializers(serializers.ModelSerializer):
    shop_type = serializers.SerializerMethodField()

    def get_shop_type(self, obj):
        return obj.get_shop_type_display()

    class Meta:
        model = ShopType
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_sub_type'] = RetailerTypeSerializer(
            instance.shop_sub_type).data
        return response


'''
For Shop Type List
'''


class ShopTypeListSerializers(serializers.ModelSerializer):
    shop_type = serializers.SerializerMethodField()

    def get_shop_type(self, obj):
        return obj.get_shop_type_display()

    class Meta:
        model = ShopType
        fields = ('id', 'shop_type')


'''
For Shops Listing
'''


class RelatedUsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name',  'phone_number',  'email', )


class ShopPhotoSerializers(serializers.ModelSerializer):

    class Meta:
        model = ShopPhoto
        fields = ('id', 'shop_photo',)


class ShopInvoicePatternSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShopInvoicePattern
        fields = ('id', 'pattern', 'status', 'start_date', 'end_date', )


class ShopDocSerializer(serializers.ModelSerializer):

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     representation['update_at'] = instance.update_at.strftime("%b %d %Y %I:%M%p")
    #     return representation

    class Meta:
        model = ShopDocument
        fields = ('id', 'shop_document_type', 'shop_document_number', )


class ShopOwnerNameListSerializer(serializers.ModelSerializer):
    shop_owner = UserSerializer()

    class Meta:
        model = Shop
        fields = ('shop_owner',)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('pk', 'id', 'first_name', 'last_name', 'phone_number', 'email', 'user_photo')


class PinCodeSerializer(serializers.ModelSerializer):
    
    pincode_id = serializers.SerializerMethodField('get_pin_id_name')
    pincode = serializers.SerializerMethodField('get_pincode_name')
    
    class Meta:
        model = Address
        fields = ('pincode_id', 'pincode',)
    
    def get_pin_id_name(self, obj):
        return obj.pincode_link.id if obj.pincode_link else None
    
    def get_pincode_name(self, obj):
        return obj.pincode_link.pincode if obj.pincode_link else None


class CitySerializer(serializers.ModelSerializer):
    
    city_id = serializers.SerializerMethodField('get_city_id_from_city')
    city_name = serializers.SerializerMethodField('get_city_name_from_city')
    
    class Meta:
        model = Address
        fields = ('city_id', 'city_name',)

    def get_city_id_from_city(self, obj):
        return obj.city.id

    def get_city_name_from_city(self, obj):
        return obj.city.city_name    

class StateSerializer(serializers.ModelSerializer):
    
    state_id = serializers.SerializerMethodField('get_state_id_from_state')
    state_name = serializers.SerializerMethodField('get_state_name_from_state')
    
    class Meta:
        model = Address
        fields = ('state_id', 'state_name',)

    def get_state_id_from_state(self, obj):
        return obj.state.id

    def get_state_name_from_state(self, obj):
        return obj.state.state_name    

class ShopCrudSerializers(serializers.ModelSerializer):

    related_users = RelatedUsersSerializer(read_only=True, many=True)

    approval_status = serializers.SerializerMethodField('shop_approval_status')
    shop_type = serializers.SerializerMethodField('get_shop_type_name')
    pincode = serializers.SerializerMethodField('get_pin_code')
    city = serializers.SerializerMethodField('get_city_name')
    shop_photo = serializers.SerializerMethodField('get_shop_photos')
    shop_docs = serializers.SerializerMethodField('get_shop_documents')
    shop_invoice_pattern = serializers.SerializerMethodField(
        'get_shop_invoices')

    class Meta:
        model = Shop
        fields = ('shop_name', 'owner', 'parent_shop', 'pincode', 'city',
                  'approval_status', 'status', 'shop_type', 'related_users', 'shipping_address',
                  'created_at', 'imei_no', 'shop_photo', 'shop_docs', 'shop_invoice_pattern')

    def shop_approval_status(self, obj):
        return obj.get_approval_status_display()

    def get_shop_type_name(self, obj):
        return obj.shop_type.get_shop_type_display()

    def get_pin_code(self, obj):
        return obj.pin_code

    def get_city_name(self, obj):
        return obj.city_name

    def get_shop_photos(self, obj):
        return ShopPhotoSerializers(obj.shop_name_photos.all(), read_only=True, many=True).data

    def get_shop_documents(self, obj):
        return ShopDocSerializer(obj.shop_name_documents.all(), read_only=True, many=True).data

    def get_shop_invoices(self, obj):
        return ShopInvoicePatternSerializer(obj.invoice_pattern.all(), read_only=True, many=True).data

    # def validate(self, data):
    #     if 'shop_start_at' in self.initial_data and 'shop_end_at' in self.initial_data:
    #         if data['shop_start_at'] and data['shop_end_at']:
    #             if data['shop_end_at'] < data['shop_start_at']:
    #                 raise serializers.ValidationError("End date should be greater than start date.")

    #     # if data['shop_name'] and data['shop_type'] and data['shop_percentage']:
    #     #     if Shop.objects.filter(shop_name=data['shop_name'], shop_type=data['shop_type'],
    #     #                           shop_percentage=data['shop_percentage']):
    #     #         raise serializers.ValidationError("Shop already exists .")
    #     return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new shop"""
        return Shop.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """update shop"""
        instance = super().update(instance, validated_data)
        return instance
