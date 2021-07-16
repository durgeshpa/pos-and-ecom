import re
from django.contrib.postgres import fields
from django.db import transaction
from django.contrib.auth import get_user_model

from rest_framework import serializers

from retailer_backend.validators import PinCodeValidator

from shops.models import (RetailerType, ShopType, Shop, ShopPhoto,
                          ShopDocument, ShopInvoicePattern, ShopUserMapping
                          )
from addresses.models import Address, City, Pincode, State

from shops.common_validators import get_validate_images, get_validate_related_users, get_validate_shop_address, get_validate_shop_documents
from shops.common_functions import ShopCls
from products.api.v1.serializers import LogSerializers
from accounts.api.v1.serializers import GroupSerializer

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
        fields = ('id', 'shop_document_type',
                  'shop_document_number', 'shop_document_photo', )


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


class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name',
                  'phone_number', 'email', 'user_photo')


class PinCodeAddressSerializer(serializers.ModelSerializer):

    pincode_id = serializers.SerializerMethodField('get_pin_id_name')
    pincode = serializers.SerializerMethodField('get_pincode_name')

    class Meta:
        model = Address
        fields = ('pincode_id', 'pincode',)

    def get_pin_id_name(self, obj):
        return obj.pincode_link.id if obj.pincode_link else None

    def get_pincode_name(self, obj):
        return obj.pincode_link.pincode if obj.pincode_link else None


class CityAddressSerializer(serializers.ModelSerializer):

    city_id = serializers.SerializerMethodField('get_city_id_from_city')
    city_name = serializers.SerializerMethodField('get_city_name_from_city')

    class Meta:
        model = Address
        fields = ('city_id', 'city_name',)

    def get_city_id_from_city(self, obj):
        return obj.city.id

    def get_city_name_from_city(self, obj):
        return obj.city.city_name


class StateAddressSerializer(serializers.ModelSerializer):

    state_id = serializers.SerializerMethodField('get_state_id_from_state')
    state_name = serializers.SerializerMethodField('get_state_name_from_state')

    class Meta:
        model = Address
        fields = ('state_id', 'state_name',)

    def get_state_id_from_state(self, obj):
        return obj.state.id

    def get_state_name_from_state(self, obj):
        return obj.state.state_name


class PincodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pincode
        fields = '__all__'


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = '__all__'


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'


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
        response['pincode_link'] = PincodeSerializer(
            instance.pincode_link).data
        return response

# class ShopDocumentSerializer(serializers.ModelSerializer):
#     shop_document_photo = Base64ImageField(
#         max_length=None, use_url=True,required=False
#     )

#     class Meta:
#         model = ShopDocument
#         fields = '__all__'


class ShopCrudSerializers(serializers.ModelSerializer):

    related_users = UserSerializers(read_only=True, many=True)
    shop_log = LogSerializers(many=True, read_only=True)

    approval_status = serializers.SerializerMethodField('shop_approval_status')
    shop_type = serializers.SerializerMethodField('get_shop_type_name')
    address = serializers.SerializerMethodField('get_addresses')
    pincode = serializers.SerializerMethodField('get_pin_code')
    city = serializers.SerializerMethodField('get_city_name')
    shop_photo = serializers.SerializerMethodField('get_shop_photos')
    shop_docs = serializers.SerializerMethodField('get_shop_documents')
    shop_invoice_pattern = serializers.SerializerMethodField(
        'get_shop_invoices')

    class Meta:
        model = Shop
        fields = ('id', 'shop_name', 'shop_code', 'shop_code_bulk', 'shop_code_discounted', 'warehouse_code',
                  'owner', 'parent_shop', 'address', 'pincode', 'city',
                  'approval_status', 'status', 'shop_type', 'related_users', 'shipping_address',
                  'created_at', 'imei_no', 'shop_photo', 'shop_docs', 'shop_invoice_pattern', 'shop_log')

    def shop_approval_status(self, obj):
        return obj.get_approval_status_display()

    def get_shop_type_name(self, obj):
        return obj.shop_type.get_shop_type_display()

    def get_addresses(self, obj):
        return AddressSerializer(obj.shop_name_address_mapping.all(), read_only=True, many=True).data

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

    def validate(self, data):

        if 'related_users' in self.initial_data and self.initial_data['related_users']:
            related_users = get_validate_related_users(
                self.initial_data['related_users'])
            if 'error' in related_users:
                raise serializers.ValidationError((related_users["error"]))
            data['related_users'] = related_users['related_users']

        if 'shop_docs' in self.initial_data and self.initial_data['shop_docs']:
            shop_docs = get_validate_shop_documents(
                self.initial_data['id'], self.initial_data['shop_docs'])
            if 'error' in shop_docs:
                raise serializers.ValidationError((shop_docs["error"]))
            data['shop_docs'] = shop_docs

        if 'address' in self.initial_data and self.initial_data['address']:
            addresses = get_validate_shop_address(
                self.initial_data['address'])
            if 'error' in addresses:
                raise serializers.ValidationError((addresses["error"]))
            data['address'] = addresses['addresses']

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new Shop with image category & tax"""

        try:
            shop_instance = Shop.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.create_upadte_shop_address_photos_docs_invoices(shop_instance)
        ShopCls.create_shop_log(shop_instance)
        return shop_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Shop's attribute. """

        try:
            # call super to save modified instance along with the validated data
            shop_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.create_upadte_shop_address_photos_docs_invoices(shop_instance)
        ShopCls.create_shop_log(shop_instance)
        return shop_instance

    def create_upadte_shop_address_photos_docs_invoices(self, shop):
        ''' Create Shop Address, Photos, Docs, Invoice Pattern'''
        shop_address = None
        shop_photo = None
        shop_docs = None
        shop_invoice_pattern = None

        if 'address' in self.initial_data and self.initial_data['address']:
            shop_address = self.initial_data['address']
        if 'shop_photos' in self.initial_data and self.initial_data['shop_photos']:
            shop_photo = self.initial_data['shop_photos']
        if 'shop_docs' in self.initial_data and self.initial_data['shop_docs']:
            shop_docs = self.initial_data['shop_docs']
        if 'shop_invoice_pattern' in self.initial_data and self.initial_data['shop_invoice_pattern']:
            shop_invoice_pattern = self.initial_data['shop_invoice_pattern']

        ShopCls.create_update_shop_address(shop, shop_address)
        ShopCls.upload_shop_photos(shop, shop_photo)
        # print(shop_docs)
        # ShopCls.create_shop_docs(shop, shop_docs)
        # ShopCls.create_shop_invoice_pattern(shop, shop_invoice_pattern)


class ServicePartnerShopsSerializer(serializers.ModelSerializer):
    shop = serializers.SerializerMethodField('get_shop_repr')

    class Meta:
        model = Shop
        fields = ('id', 'shop')

    def get_shop_repr(self, obj):
        if obj.shop_owner.first_name and obj.shop_owner.last_name:
            return "%s - %s - %s %s - %s - %s" % (obj.shop_name, str(
                obj.shop_owner.phone_number), obj.shop_owner.first_name,
                obj.shop_owner.last_name, str(obj.shop_type), str(obj.id))

        elif obj.shop_owner.first_name:
            return "%s - %s - %s - %s - %s" % (obj.shop_name, str(
                obj.shop_owner.phone_number), obj.shop_owner.first_name,
                str(obj.shop_type), str(obj.id))

        return "%s - %s - %s - %s" % (obj.shop_name, str(
            obj.shop_owner.phone_number), str(obj.shop_type), str(obj.id))


class ManagerSerializers(serializers.ModelSerializer):

    manager_name = serializers.SerializerMethodField('get_manager_repr')

    class Meta:
        model = ShopUserMapping
        fields = ('id', 'manager_name')

    def get_manager_repr(self, obj):
        if obj.employee:
            return str(obj.employee)


class ShopUserMappingCrudSerializers(serializers.ModelSerializer):
    shop = ServicePartnerShopsSerializer()
    employee = UserSerializers()
    manager = ManagerSerializers()
    employee_group = GroupSerializer()

    class Meta:
        model = ShopUserMapping
        fields = '__all__'
