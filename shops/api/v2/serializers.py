import re

from django.db import transaction
from django.contrib.auth import get_user_model

from rest_framework import serializers

from retailer_backend.validators import PinCodeValidator

from shops.models import (RetailerType, ShopType, Shop, ShopPhoto,
                          ShopDocument, ShopInvoicePattern, ShopUserMapping
                          )
from addresses.models import Address, City, Pincode, State

from shops.common_validators import get_validate_approval_status, get_validate_existing_shop_photos, \
    get_validate_favourite_products, get_validate_related_users, get_validate_shop_address, get_validate_shop_documents,\
    get_validate_shop_invoice_pattern, get_validate_shop_type, get_validate_user, get_validated_parent_shop, \
    get_validated_shop, validate_shop_id, validate_shop, validate_employee_group, validate_employee, validate_manager
from shops.common_functions import ShopCls

from products.api.v1.serializers import LogSerializers
from accounts.api.v1.serializers import GroupSerializer

User = get_user_model()


class ChoiceField(serializers.ChoiceField):

    def to_representation(self, obj):
        if obj == '' and self.allow_blank:
            return obj
        return {'id': obj, 'desc': self._choices[obj]}

    # def to_internal_value(self, data):
    #     # To support inserts with the value
    #     if data == '' and self.allow_blank:
    #         return ''
    #
    #     for key, val in self._choices.items():
    #         if val == data:
    #             return key
    #     self.fail('invalid_choice', input=data)


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

    shop_document_type = ChoiceField(choices=ShopDocument.SHOP_DOCUMENTS_TYPE_CHOICES, required=True)

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
        fields = ('shop_owner_id', 'first_name', 'last_name', 'phone_number', 'email',)

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
        fields = ('id', 'first_name', 'last_name', 'phone_number', 'email', 'user_photo')


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


class ShopBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'shop_name',)


class ShopCrudSerializers(serializers.ModelSerializer):

    related_users = UserSerializers(read_only=True, many=True)
    shop_log = LogSerializers(many=True, read_only=True)
    parent_shop = serializers.SerializerMethodField('get_parent_shop_obj')
    owner = serializers.SerializerMethodField('get_shop_owner_obj')
    approval_status = ChoiceField(choices=Shop.APPROVAL_STATUS_CHOICES, required=True)
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

    def get_shop_type_name(self, obj):
        return ShopTypeListSerializers(obj.shop_type, read_only=True).data

    def get_parent_shop_obj(self, obj):
        if obj.retiler_mapping.exists():
            return ShopBasicSerializer(obj.retiler_mapping.filter(status=True).last().parent).data
        else:
            return None
    
    def get_shop_owner_obj(self, obj):
        return UserSerializers(obj.shop_owner, read_only=True).data

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

        if 'approval_status' in self.initial_data and self.initial_data['approval_status']:
            approval_status = get_validate_approval_status(
                self.initial_data['approval_status'])
            if 'error' in approval_status:
                raise serializers.ValidationError((approval_status["error"]))
            data['approval_status'] = approval_status['data']

        if 'shop_owner' in self.initial_data and self.initial_data['shop_owner']:
            shop_owner = get_validate_user(self.initial_data['shop_owner'])
            if 'error' in shop_owner:
                raise serializers.ValidationError((shop_owner["error"]))
            data['shop_owner'] = shop_owner['data']

        if 'shop_type' in self.initial_data and self.initial_data['shop_type']:
            shop_type = get_validate_shop_type(self.initial_data['shop_type'])
            if 'error' in shop_type:
                raise serializers.ValidationError((shop_type["error"]))
            data['shop_type'] = shop_type['data']

        if 'shop_photo' in self.initial_data and self.initial_data['shop_photo']:
            photos = get_validate_existing_shop_photos(
                self.initial_data['shop_photo'])
            if 'error' in photos:
                raise serializers.ValidationError((photos["error"]))
            data['shop_photo'] = photos['photos']

        if 'related_users' in self.initial_data and self.initial_data['related_users']:
            related_users = get_validate_related_users(
                self.initial_data['related_users'])
            if 'error' in related_users:
                raise serializers.ValidationError((related_users["error"]))
            data['related_users'] = related_users['related_users']

        if 'favourite_products' in self.initial_data and self.initial_data['favourite_products']:
            favourite_products = get_validate_favourite_products(
                self.initial_data['favourite_products'])
            if 'error' in favourite_products:
                raise serializers.ValidationError(
                    (favourite_products["error"]))
            data['favourite_products'] = favourite_products['favourite_products']

        if 'shop_docs' in self.initial_data and self.initial_data['shop_docs']:
            shop_documents = get_validate_shop_documents(
                self.initial_data['shop_docs'])
            if 'error' in shop_documents:
                raise serializers.ValidationError((shop_documents["error"]))
            data['shop_docs'] = shop_documents['data']

        if 'address' in self.initial_data and self.initial_data['address']:
            addresses = get_validate_shop_address(
                self.initial_data['address'])
            if 'error' in addresses:
                raise serializers.ValidationError((addresses["error"]))
            data['address'] = addresses['addresses']

        if 'shop_invoice_pattern' in self.initial_data and self.initial_data['shop_invoice_pattern']:
            shop_invoice_patterns = get_validate_shop_invoice_pattern(
                self.initial_data['shop_invoice_pattern'])
            if 'error' in shop_invoice_patterns:
                raise serializers.ValidationError(
                    (shop_invoice_patterns["error"]))

        if 'parent_shop' in self.initial_data and self.initial_data['parent_shop']:
            parent_shop = get_validated_parent_shop(
                self.initial_data['parent_shop'])
            if 'error' in parent_shop:
                raise serializers.ValidationError(parent_shop['error'])
            # data['parent_shop'] = parent_shop['data']

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new Shop with Address, Photos, Docs & Invoice Pattern"""
        validated_data.pop('related_users', None)
        validated_data.pop('favourite_products', None)
        validated_data.pop('address', None)
        validated_data.pop('shop_docs', None)
        validated_data.pop('shop_photo', None)
        validated_data.pop('shop_invoice_pattern', None)
        validated_data.pop('parent_shop', None)

        try:
            shop_instance = Shop.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.cr_up_addrs_imgs_docs_invoices_parentshop_relateduser_favouriteprd(
            shop_instance, "created")
        ShopCls.create_shop_log(shop_instance, "created")
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

        self.cr_up_addrs_imgs_docs_invoices_parentshop_relateduser_favouriteprd(
            shop_instance, "updated")
        ShopCls.create_shop_log(shop_instance, "updated")
        return shop_instance

    def cr_up_addrs_imgs_docs_invoices_parentshop_relateduser_favouriteprd(self, shop, action):
        ''' 
            Create Shop Address, Photos, Docs, 
            Invoice Pattern, Related users & Favourite Products
        '''
        shop_address = None
        shop_photo = None
        shop_new_photos = None
        shop_docs = None
        shop_invoice_pattern = None
        shop_parent_shop = None
        related_usrs = None
        favourite_prd = None

        if 'address' in self.validated_data and self.validated_data['address']:
            shop_address = self.validated_data['address']

        if 'shop_docs' in self.validated_data and self.validated_data['shop_docs']:
            shop_docs = self.validated_data['shop_docs']

        if 'shop_photo' in self.validated_data and self.validated_data['shop_photo']:
            shop_photo = self.validated_data['shop_photo']

        if 'shop_images' in self.initial_data and self.initial_data['shop_images']:
            shop_new_photos = self.initial_data['shop_images']

        if 'shop_invoice_pattern' in self.initial_data and self.initial_data['shop_invoice_pattern']:
            shop_invoice_pattern = self.initial_data['shop_invoice_pattern']

        if 'parent_shop' in self.initial_data and self.initial_data['parent_shop']:
            shop_parent_shop = get_validated_shop(
                self.initial_data['parent_shop'])
            if 'error' in shop_parent_shop:
                raise serializers.ValidationError(shop_parent_shop['error'])

        if 'related_users' in self.validated_data and self.validated_data['related_users']:
            related_usrs = self.validated_data['related_users']

        if 'favourite_products' in self.validated_data and self.validated_data['favourite_products']:
            favourite_prd = self.validated_data['favourite_products']

        ShopCls.create_update_shop_address(shop, shop_address)
        ShopCls.create_upadte_shop_photos(shop, shop_photo, shop_new_photos)
        ShopCls.create_upadte_shop_docs(shop, shop_docs)
        ShopCls.create_upadte_shop_invoice_pattern(shop, shop_invoice_pattern)
        ShopCls.update_related_users_and_favourite_products(
            shop, related_usrs, favourite_prd)
        if action == "updated":
            ShopCls.update_parent_shop(shop, shop_parent_shop['data'])
        elif action == "created":
            obj = ShopCls.create_parent_shop(shop, shop_parent_shop['data'])
        # ShopCls.update_parent_shop(shop, shop_parent_shop['data'])


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


class ParentShopsListSerializer(serializers.ModelSerializer):
    parent_id = serializers.SerializerMethodField('get_parent_shop_id')
    parent = serializers.SerializerMethodField('get_parent_shop')

    class Meta:
        model = Shop
        fields = ('parent_id', 'parent', )

    def get_parent_shop_id(self, obj):
        return obj.parent.id

    def get_parent_shop(self, obj):

        return obj.parent.__str__()


class ManagerSerializers(serializers.ModelSerializer):

    manager_name = serializers.SerializerMethodField('get_manager_repr')

    class Meta:
        model = ShopUserMapping
        fields = ('id', 'manager_name')

    def get_manager_repr(self, obj):
        if obj.employee:
            return str(obj.employee)


class ShopEmployeeSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'phone_number', 'first_name', 'last_name')


class ShopManagerSerializers(serializers.ModelSerializer):
    employee = ShopEmployeeSerializers()

    class Meta:

        model = ShopUserMapping
        fields = ('id', 'employee')


class ShopUserMappingCrudSerializers(serializers.ModelSerializer):
    shop = ServicePartnerShopsSerializer(read_only=True)
    employee = UserSerializers(read_only=True)
    manager = ManagerSerializers(read_only=True)
    employee_group = GroupSerializer(read_only=True)

    class Meta:
        model = ShopUserMapping
        fields = '__all__'

    def validate(self, data):

        if 'shop' not in self.initial_data or self.initial_data['shop'] is None:
            raise serializers.ValidationError("shop is required")
        if 'employee' not in self.initial_data or self.initial_data['employee'] is None:
            raise serializers.ValidationError("employee is required")
        if 'employee_group' not in self.initial_data or self.initial_data['employee_group'] is None:
            raise serializers.ValidationError("employee_group is required")

        if 'shop' in self.initial_data and self.initial_data['shop']:
            shop_id = validate_shop(self.initial_data['shop'])
            if 'error' in shop_id:
                raise serializers.ValidationError((shop_id["error"]))
            data['shop'] = shop_id['data']

        if 'employee' in self.initial_data and self.initial_data['employee']:
            employee_id = validate_employee(self.initial_data['shop'])
            if 'error' in employee_id:
                raise serializers.ValidationError((employee_id["error"]))
            data['employee'] = employee_id['data']

        if 'manager' in self.initial_data and self.initial_data['manager']:
            manager_id = validate_manager(self.initial_data['manager'])
            if 'error' in manager_id:
                raise serializers.ValidationError((manager_id["error"]))
            data['manager'] = manager_id['data']
            if data['manager'].employee == data['employee']:
                raise serializers.ValidationError('Manager and Employee cannot be same')

        if 'employee_group' in self.initial_data and self.initial_data['employee_group']:
            employee_group_id = validate_employee_group(self.initial_data['employee_group'])
            if 'error' in employee_group_id:
                raise serializers.ValidationError((employee_group_id["error"]))
            data['employee_group'] = employee_group_id['data']

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create shop user mapping"""
        # manager_obj = validated_data.pop('manager', None)
        try:
            shop_user_map = ShopUserMapping.objects.create(**validated_data)
            ShopCls.create_shop_user_map_log(shop_user_map, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return shop_user_map

    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Shop User Mapping attribute. """

        try:
            # call super to save modified instance along with the validated data
            shop_instance = super().update(instance, validated_data)
            ShopCls.create_shop_user_map_log(shop_instance, "updated")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return shop_instance