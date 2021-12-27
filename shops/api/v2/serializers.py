import codecs
import csv
from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import manager
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.http import HttpResponse

from rest_framework import serializers

from retailer_backend.validators import PinCodeValidator

from shops.models import (BeatPlanning, RetailerType, ShopType, Shop, ShopPhoto,
                          ShopDocument, ShopInvoicePattern, ShopUserMapping, SHOP_TYPE_CHOICES, ParentRetailerMapping,
                          DayBeatPlanning, ShopStatusLog)
from addresses.models import Address, City, Pincode, State, address_type_choices

from shops.common_validators import get_validate_approval_status, get_validate_existing_shop_photos, \
    get_validate_favourite_products, get_validate_related_users, get_validate_shop_address, get_validate_shop_documents, \
    get_validate_shop_invoice_pattern, get_validate_shop_type, get_validate_user, get_validated_parent_shop, \
    get_validated_shop, read_beat_planning_file, validate__existing_shop_with_name_owner, validate_shop_id, \
    validate_shop, validate_employee_group, validate_employee, validate_manager, \
    validate_shop_sub_type, validate_shop_and_sub_shop_type, validate_shop_name, read_file
from shops.common_functions import ShopCls

from products.api.v1.serializers import LogSerializers
from accounts.api.v1.serializers import GroupSerializer

User = get_user_model()


class ChoiceField(serializers.ChoiceField):

    def to_representation(self, obj):
        if obj == '' and self.allow_blank:
            return obj
        return {'id': obj, 'desc': self._choices[obj]}


'''
For Shop Type List
'''


class RetailerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailerType
        fields = ('id', 'retailer_type_name')


class ShopTypeSerializers(serializers.ModelSerializer):
    # shop_type = serializers.SerializerMethodField()
    shop_type = ChoiceField(choices=SHOP_TYPE_CHOICES, required=True)
    shop_min_amount = serializers.FloatField(required=True)
    shop_sub_type = RetailerTypeSerializer(read_only=True)
    shop_type_log = LogSerializers(many=True, read_only=True)

    # def get_shop_type(self, obj):
    #     return obj.get_shop_type_display()

    def validate(self, data):

        if 'shop_sub_type' in self.initial_data and self.initial_data['shop_sub_type']:
            shop_id = validate_shop_sub_type(self.initial_data['shop_sub_type'])
            if 'error' in shop_id:
                raise serializers.ValidationError((shop_id["error"]))
            data['shop_sub_type'] = shop_id['data']

        shop_type_id = self.instance.id if self.instance else None
        if 'shop_sub_type' in self.initial_data and self.initial_data['shop_sub_type'] and \
                'shop_type' in self.initial_data and self.initial_data['shop_type']:
            shop_type_obj = validate_shop_and_sub_shop_type(self.initial_data['shop_type'], data['shop_sub_type'],
                                                            shop_type_id)
            if shop_type_obj is not None and 'error' in shop_type_obj:
                raise serializers.ValidationError(shop_type_obj['error'])
        return data

    class Meta:
        model = ShopType
        fields = ('id', 'shop_type', 'shop_sub_type',
                  'shop_min_amount', 'status', 'shop_type_log')

    @transaction.atomic
    def create(self, validated_data):
        """create shop type """
        try:
            shop_type = ShopType.objects.create(**validated_data)
            ShopCls.create_shop_type_log(shop_type, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return shop_type

    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Shop User Mapping attribute. """

        try:
            # call super to save modified instance along with the validated data
            shop_instance = super().update(instance, validated_data)
            ShopCls.create_shop_type_log(shop_instance, "updated")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return shop_instance

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_type'] = {
            "shop_type": instance.shop_type,
            "shop_type_name": instance.get_shop_type_display()
        }
        # response['shop_type'] = instance.shop_type
        # response['shop_type_name'] = instance.get_shop_type_display()
        return response


'''
For Shop Type List
'''


class ShopTypeListSerializers(serializers.ModelSerializer):
    shop_sub_type = RetailerTypeSerializer(read_only=True)

    class Meta:
        model = ShopType
        fields = ('id', 'shop_type', 'shop_sub_type')

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_type'] = instance.get_shop_type_display()
        response['shop_type_value'] = instance.shop_type
        return response


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
        fields = ('id', 'pattern', 'status', 'start_date', 'end_date',)


class ShopDocSerializer(serializers.ModelSerializer):
    shop_document_type = ChoiceField(
        choices=ShopDocument.SHOP_DOCUMENTS_TYPE_CHOICES, required=True)

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     representation['update_at'] = instance.update_at.strftime("%b %d %Y %I:%M%p")
    #     return representation

    class Meta:
        model = ShopDocument
        fields = ('id', 'shop_document_type', 'shop_document_number', 'shop_document_photo',)


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
        ref_name = 'Pin Code Serializer v2'
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
    address_type = ChoiceField(choices=address_type_choices)

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

class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        ref_name = 'User Serializer v2'
        fields = ('id', 'first_name', 'last_name', 'phone_number',)


class ShopBasicSerializer(serializers.ModelSerializer):
    shop_name = serializers.SerializerMethodField('get_shop_repr')

    class Meta:
        model = Shop
        ref_name = 'Shop Basic Serializer v2'
        fields = ('id', 'shop_name', 'shop_owner')

    def get_shop_repr(self, obj):
        if obj.shop_owner.first_name and obj.shop_owner.last_name:
            return "%s - %s - %s %s - %s - %s" % (obj.shop_name, str(
                obj.shop_owner.phone_number), obj.shop_owner.first_name, obj.shop_owner.last_name,
                                                  str(obj.shop_type), str(obj.id))

        elif obj.shop_owner.first_name:
            return "%s - %s - %s - %s - %s" % (obj.shop_name, str(
                obj.shop_owner.phone_number), obj.shop_owner.first_name, str(obj.shop_type), str(obj.id))

        return "%s - %s - %s - %s" % (obj.shop_name, str(
            obj.shop_owner.phone_number), str(obj.shop_type), str(obj.id))

    class Meta:
        model = Shop
        fields = ('id', 'shop_name',)


class ParentRetailerMappingSerializers(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'shop_name',)


class RetailerMappingDataSerializers(serializers.ModelSerializer):
    parent = ParentRetailerMappingSerializers(read_only=True)

    class Meta:
        model = ParentRetailerMapping
        fields = ('id', 'parent')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return representation['parent'] if 'parent' in representation else representation


class StateDataSerializers(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ('id', 'state_name',)


class CityDataSerializers(serializers.ModelSerializer):

    class Meta:
        model = City
        fields = ('id', 'city_name')


class PincodeDataSerializers(serializers.ModelSerializer):
    class Meta:
        model = Pincode
        fields = ('id', 'pincode',)


class ShopDocumentDataSerializers(serializers.ModelSerializer):
    shop_document_type = ChoiceField(choices=ShopDocument.SHOP_DOCUMENTS_TYPE_CHOICES)
    class Meta:
        model = ShopDocument
        fields = ('id', 'shop_document_type', 'shop_document_number', 'shop_document_photo')


class ShopPhotoDataSerializers(serializers.ModelSerializer):
    class Meta:
        model = ShopPhoto
        fields = ('id', 'shop_name', 'shop_photo',)


class AddressDataSerializers(serializers.ModelSerializer):
    pincode_link = PincodeDataSerializers(read_only=True)
    state = StateDataSerializers(read_only=True)
    city = CityDataSerializers(read_only=True)
    address_type = ChoiceField(choices=address_type_choices, required=True)

    class Meta:
        model = Address
        fields = ('id', 'nick_name', 'address_line1', 'address_contact_name', 'address_contact_number',
                  'pincode_link', 'state', 'city', 'address_type')


class ShopCrudSerializers(serializers.ModelSerializer):
    related_users = UserSerializers(read_only=True, many=True)
    shop_log = LogSerializers(many=True, read_only=True)
    shop_type = ShopTypeListSerializers(read_only=True)
    retiler_mapping = RetailerMappingDataSerializers(read_only=True, many=True)
    shop_owner = UserSerializers(read_only=True)
    approval_status = ChoiceField(choices=Shop.APPROVAL_STATUS_CHOICES, required=True)
    shop_name_address_mapping = AddressDataSerializers(read_only=True, many=True)
    shop_name_photos = ShopPhotoDataSerializers(read_only=True, many=True)
    shop_name_documents = ShopDocumentDataSerializers(read_only=True, many=True)

    class Meta:
        model = Shop
        fields = ('id', 'shop_name', 'shop_code', 'shop_code_bulk', 'shop_code_discounted', 'warehouse_code',
                  'shop_owner', 'retiler_mapping', 'shop_name_address_mapping', 'approval_status', 'status',
                  'shop_type', 'related_users', 'shipping_address', 'created_at', 'imei_no', 'shop_name_photos',
                  'shop_name_documents', 'shop_log', 'pos_enabled')

    def validate(self, data):

        shop_id = self.instance.id if self.instance else None
        if not 'shop_name_photos' in self.initial_data or not self.initial_data['shop_name_photos']:
            if not 'shop_images' in self.initial_data or not self.initial_data['shop_images']:
                raise serializers.ValidationError(_('shop photo is required'))

        if 'approval_status' in self.initial_data and self.initial_data['approval_status']:
            approval_status = get_validate_approval_status(self.initial_data['approval_status'])
            if 'error' in approval_status:
                raise serializers.ValidationError((approval_status["error"]))
            data['approval_status'] = approval_status['data']

        if 'shop_owner' in self.initial_data and self.initial_data['shop_owner']:
            shop_owner = get_validate_user(self.initial_data['shop_owner'])
            if 'error' in shop_owner:
                raise serializers.ValidationError((shop_owner["error"]))
            data['shop_owner'] = shop_owner['data']
            # Validate existing shop with shop name and shop owner
            shop_obj = validate__existing_shop_with_name_owner(
                self.initial_data['shop_name'], shop_owner['data'], shop_id)
            if shop_obj is not None and 'error' in shop_obj:
                raise serializers.ValidationError(shop_obj['error'])
        else:
            raise serializers.ValidationError("'shop_owner': This field is required.")

        if 'shop_type' in self.initial_data and self.initial_data['shop_type']:
            shop_type = get_validate_shop_type(self.initial_data['shop_type'])
            if 'error' in shop_type:
                raise serializers.ValidationError((shop_type["error"]))
            if shop_type['data'].shop_type in ['gf', 'sp']:
                if 'shop_code' not in self.initial_data or not self.initial_data['shop_code'] or \
                        'shop_code_bulk' not in self.initial_data or not self.initial_data['shop_code_bulk'] or \
                        'shop_code_discounted' not in self.initial_data or not self.initial_data[
                    'shop_code_discounted'] or \
                        'warehouse_code' not in self.initial_data or not self.initial_data['warehouse_code']:
                    raise serializers.ValidationError(
                        "Key 'shop_code', 'shop_code_bulk', 'shop_code_discounted', 'warehouse_code' are mandatory "
                        "for selected type.")
                try:
                    if int(self.initial_data['warehouse_code']) < 0:
                        raise serializers.ValidationError("'warehouse_code' | can not ne negative")
                except ValueError:
                    raise serializers.ValidationError("'warehouse_code' | can only be positive integer value.")
            data['shop_type'] = shop_type['data']

        if 'shop_name_photos' in self.initial_data and self.initial_data['shop_name_photos']:
            photos = get_validate_existing_shop_photos(
                self.initial_data['shop_name_photos'])
            if 'error' in photos:
                raise serializers.ValidationError((photos["error"]))
            data['shop_name_photos'] = photos['photos']

        if 'related_users' in self.initial_data and self.initial_data['related_users']:
            related_users = get_validate_related_users(self.initial_data['related_users'])
            if 'error' in related_users:
                raise serializers.ValidationError((related_users["error"]))
            data['related_users'] = related_users['related_users']

        if 'shop_name_documents' in self.initial_data and self.initial_data['shop_name_documents']:
            shop_documents = get_validate_shop_documents(
                self.initial_data['shop_name_documents'])
            if 'error' in shop_documents:
                raise serializers.ValidationError((shop_documents["error"]))
            data['shop_name_documents'] = shop_documents['data']
        else:
            raise serializers.ValidationError("atleast one shop document is required")

        if 'shop_name_address_mapping' in self.initial_data and self.initial_data['shop_name_address_mapping']:
            addresses = get_validate_shop_address(self.initial_data['shop_name_address_mapping'])
            if 'error' in addresses:
                raise serializers.ValidationError((addresses["error"]))
            data['shop_name_address_mapping'] = addresses['addresses']
        else:
            raise serializers.ValidationError("'address': This field is required.")

        if 'retiler_mapping' in self.initial_data and self.initial_data['retiler_mapping']:
            parent_shop = get_validated_parent_shop(
                self.initial_data['retiler_mapping'])
            if 'error' in parent_shop:
                raise serializers.ValidationError(parent_shop['error'])
            # data['parent_shop'] = parent_shop['data']

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new Shop with Address, Photos, Docs & Invoice Pattern"""
        validated_data.pop('related_users', None)
        validated_data.pop('shop_name_address_mapping', None)
        validated_data.pop('shop_name_documents', None)
        validated_data.pop('shop_name_photos', None)
        validated_data.pop('shop_invoice_pattern', None)
        validated_data.pop('retiler_mapping', None)

        try:
            shop_instance = Shop.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.cr_up_addrs_imgs_docs_parentshop_relateduser(shop_instance, "created")
        ShopCls.create_shop_log(shop_instance, "created")
        return shop_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Shop's attribute. """
        validated_data.pop('related_users', None)
        validated_data.pop('shop_name_address_mapping', None)
        validated_data.pop('shop_name_documents', None)
        validated_data.pop('shop_name_photos', None)
        validated_data.pop('retiler_mapping', None)
        new_approval_status = validated_data.get('approval_status', None)
        old_approval_status = getattr(instance, 'approval_status')
        request = self.context.get('request', None)
        try:
            # call super to save modified instance along with the validated data
            shop_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.cr_up_addrs_imgs_docs_parentshop_relateduser(shop_instance, "updated")
        ShopCls.create_shop_log(shop_instance, "updated")

        if old_approval_status != new_approval_status:
            if new_approval_status == 0:
                reason = 'Disapproved'
            elif new_approval_status == 1:
                reason = 'Awaiting Approval'
            else:
                reason = 'Approved'
            ShopStatusLog.objects.create(reason=reason, user=request.user, shop=instance)
        return shop_instance

    def cr_up_addrs_imgs_docs_parentshop_relateduser(self, shop, action):
        '''
            Create Shop Address, Photos, Docs,
            Invoice Pattern, Related users & Favourite Products
        '''
        shop_address = None
        shop_photo = None
        shop_new_photos = None
        shop_docs = None
        shop_parent_shop = None
        related_usrs = None

        if 'shop_name_address_mapping' in self.validated_data and self.validated_data['shop_name_address_mapping']:
            shop_address = self.validated_data['shop_name_address_mapping']

        if 'shop_name_documents' in self.validated_data and self.validated_data['shop_name_documents']:
            shop_docs = self.validated_data['shop_name_documents']

        if 'shop_name_photos' in self.validated_data and self.validated_data['shop_name_photos']:
            shop_photo = self.validated_data['shop_name_photos']

        if 'shop_images' in self.initial_data and self.initial_data['shop_images']:
            shop_new_photos = self.initial_data['shop_images']

        if 'related_users' in self.validated_data and self.validated_data['related_users']:
            related_usrs = self.validated_data['related_users']

        if 'retiler_mapping' in self.initial_data:
            if self.initial_data['retiler_mapping']:
                validated_parent_shop = get_validated_shop(
                    self.initial_data['retiler_mapping'])
                if 'error' in validated_parent_shop:
                    raise serializers.ValidationError(validated_parent_shop['error'])
            shop_parent_shop = validated_parent_shop['data']

        ShopCls.create_update_shop_address(shop, shop_address)
        ShopCls.create_upadte_shop_photos(shop, shop_photo, shop_new_photos)
        ShopCls.create_upadte_shop_docs(shop, shop_docs)
        ShopCls.update_related_users(shop, related_usrs)
        ShopCls.update_parent_shop(shop, shop_parent_shop)


class ServicePartnerShopsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shop
        fields = ('id', '__str__')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['service_partner'] = {
            'id': representation['id'],
            'shop': representation['__str__']
        }
        return representation['service_partner']


class ParentShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', '__str__')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['parent'] = {
            'parent_id': representation['id'],
            'parent': representation['__str__']
        }
        return representation['parent']


class ParentRetailerMappingListSerializer(serializers.ModelSerializer):
    parent = ParentShopSerializer(read_only=True)

    class Meta:
        model = ParentRetailerMapping
        fields = ('parent',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return representation['parent']


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


class ShopNameOwnerSerializers(serializers.ModelSerializer):
    shop_owner = UserSerializers()

    class Meta:
        model = Shop
        fields = ('id', 'shop_name', 'shop_owner',)


class ShopManagerListSerializers(serializers.ModelSerializer):
    employee = ShopEmployeeSerializers()

    class Meta:
        model = ShopUserMapping
        fields = ('id', 'employee',)


class ShopManagerListDistSerializers(serializers.ModelSerializer):
    employee = ShopEmployeeSerializers()

    class Meta:
        model = ShopUserMapping
        fields = ('employee',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return representation['employee']


class ShopManagerSerializers(serializers.ModelSerializer):
    employee = ShopEmployeeSerializers()
    employee_group = GroupSerializer()

    class Meta:
        model = ShopUserMapping
        fields = ('id', 'employee', 'employee_group')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['managers'] = {
            "id": representation['id'],
            "manager": representation['employee'],
            "employee_group": representation['employee_group'],
        }
        return representation['managers']


class BeatPlanningExecutivesListSerializers(serializers.ModelSerializer):
    employee = ShopEmployeeSerializers()

    class Meta:
        model = ShopUserMapping
        fields = ('id', 'employee',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return representation['employee']


class ShopTypeSerializer(serializers.ModelSerializer):
    shop_type = ChoiceField(choices=SHOP_TYPE_CHOICES, required=True)

    class Meta:
        model = ShopType
        fields = ('id', 'shop_type',)


class ServicePartnerShopsSerializers(serializers.ModelSerializer):
    shop_owner = UserSerializers(read_only=True)
    shop_type = ShopTypeSerializer(read_only=True)

    class Meta:
        model = Shop
        fields = ('id', 'shop_name', 'shop_type', 'shop_owner')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation[
            'shop_name'] = f"{representation['shop_name']} - {representation['shop_owner']['phone_number']} - " \
                           f"{representation['shop_owner']['first_name']} {representation['shop_owner']['last_name']}" \
                           f" - {representation['shop_type']['shop_type']['desc']} - {representation['id']}"
        representation['shop'] = {
            "id": representation['id'],
            "shop_name": representation['shop_name'],
        }
        return representation['shop']


class ShopUserMappingCrudSerializers(serializers.ModelSerializer):
    shop = ServicePartnerShopsSerializers(read_only=True)
    employee = UserSerializers(read_only=True)
    manager = ShopManagerSerializers(read_only=True)
    employee_group = GroupSerializer(read_only=True)
    shop_user_map_log = LogSerializers(many=True, read_only=True)

    class Meta:
        model = ShopUserMapping
        fields = ('id', 'shop', 'manager', 'employee', 'employee_group',
                  'status', 'created_at', 'shop_user_map_log',)

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
            employee_id = validate_employee(self.initial_data['employee'])
            if 'error' in employee_id:
                raise serializers.ValidationError((employee_id["error"]))
            data['employee'] = employee_id['data']

        if 'manager' in self.initial_data and self.initial_data['manager']:
            manager_id = validate_manager(self.initial_data['manager'])
            if 'error' in manager_id:
                raise serializers.ValidationError((manager_id["error"]))
            data['manager'] = manager_id['data']
            if data['manager'].employee == data['employee']:
                raise serializers.ValidationError(
                    'Manager and Employee cannot be same')

        if 'employee_group' in self.initial_data and self.initial_data['employee_group']:
            employee_group_id = validate_employee_group(self.initial_data['employee_group'])
            if 'error' in employee_group_id:
                raise serializers.ValidationError((employee_group_id["error"]))
            data['employee_group'] = employee_group_id['data']

        # if data['employee'] and data['employee_group']:
        if data['employee_group'].name == "Sales Manager":
            # not data['employee'].groups.filter(name="Sales Manager")
            if not data['employee'].user_type == 7:
                raise serializers.ValidationError(f"User Type is not Sales Manager "
                                                  f"'{data['employee'].phone_number} - {data['employee'].first_name}"
                                                  f" {data['employee'].last_name}'")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create shop user mapping"""
        try:
            shop_user_map = ShopUserMapping.objects.create(**validated_data)
            ShopCls.create_shop_user_map_log(shop_user_map, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return shop_user_map

    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Shop User Mapping attribute. """
        try:
            # call super to save modified instance along with the validated data
            shop_instance = super().update(instance, validated_data)
            ShopCls.create_shop_user_map_log(shop_instance, "updated")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return shop_instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['created_at'] = instance.created_at.strftime(
            "%b %d %Y %I:%M%p")
        return representation


class DisapproveSelectedShopSerializers(serializers.ModelSerializer):
    approval_status = serializers.BooleanField(required=True)
    shop_id_list = serializers.ListField(
        child=serializers.IntegerField(min_value=1))

    class Meta:
        model = Shop
        fields = ('approval_status', 'shop_id_list',)

    def validate(self, data):

        if data.get('approval_status') is None:
            raise serializers.ValidationError(
                'approval_status field is required')

        if not int(data.get('approval_status')) == 0:
            raise serializers.ValidationError('invalid approval_status')

        if not 'shop_id_list' in data or not data['shop_id_list']:
            raise serializers.ValidationError(
                _('atleast one shop id must be selected '))

        for p_id in data.get('shop_id_list'):
            try:
                Shop.objects.get(id=p_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    f'shop not found for id {p_id}')

        return data

    @transaction.atomic
    def update(self, instance, validated_data):

        try:
            request = self.context.get('request', None)
            parent_products = Shop.objects.filter(
                id__in=validated_data['shop_id_list'])
            parent_products.update(approval_status=int(validated_data['approval_status']),
                                   updated_by=validated_data['updated_by'], updated_at=timezone.now())
            for shop in parent_products:
                ShopStatusLog.objects.create(reason='Disapproved', user=request.user, shop=shop)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return validated_data


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ('id', 'state_name',)


class CitySerializer(serializers.ModelSerializer):
    ref_name = 'Shop City v2'
    state = StateSerializer()

    class Meta:
        model = City
        fields = ('id', 'city_name', 'state')


class PinCodeSerializer(serializers.ModelSerializer):
    city = CitySerializer()

    class Meta:
        model = Pincode
        fields = ('id', 'pincode', 'city')


class BulkUpdateShopSampleCSVSerializer(serializers.ModelSerializer):
    shop_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = Shop
        fields = ('shop_id_list',)

    def validate(self, data):

        if len(data.get('shop_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one shop id must be selected '))

        for s_id in data.get('shop_id_list'):
            try:
                Shop.objects.get(id=s_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    f'shop not found for id {s_id}')

        return data

    def create(self, validated_data):
        data = Address.objects.values_list(
            'shop_name__id', 'shop_name__shop_name', 'shop_name__shop_type__shop_type',
            'shop_name__shop_owner__phone_number', 'shop_name__status', 'id', 'nick_name',
            'address_line1', 'address_contact_name', 'address_contact_number',
            'pincode_link__pincode', 'state__state_name', 'city__city_name', 'address_type',
            'shop_name__imei_no', 'shop_name__retiler_mapping__parent__shop_name', 'shop_name__created_at') \
            .filter(shop_name__id__in=validated_data['shop_id_list'])

        meta = Shop._meta
        field_names = ['shop_id', 'shop_name', 'shop_type', 'shop_owner', 'shop_activated', 'address_id',
                       'nick_name', 'address', 'contact_person', 'contact_number', 'pincode', 'state',
                       'city', 'address_type', 'imei_no', 'parent_shop_name', 'shop_created_at']

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(
            meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in data:
            writer.writerow(list(obj))
        return response


class BulkUpdateShopUserMappingSampleCSVSerializer(serializers.ModelSerializer):
    shop_user_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = ShopUserMapping
        fields = ('shop_user_id_list',)

    def validate(self, data):

        if len(data.get('shop_user_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one shop user mapping id must be selected '))

        for s_id in data.get('shop_user_id_list'):
            try:
                Shop.objects.get(id=s_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'shop user mapping not found for id {s_id}')

        return data


class BulkCreateShopUserMappingSerializer(serializers.ModelSerializer):
    file = serializers.FileField(
        label='Upload Shop User Mapping', required=True, write_only=True)

    class Meta:
        model = ShopUserMapping
        fields = ('file',)

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError(_('Sorry! Only csv file accepted.'))

        csv_file_data = csv.reader(codecs.iterdecode(
            data['file'], 'utf-8', errors='ignore'))
        # Checking, whether csv file is empty or not!
        if csv_file_data:
            read_file(csv_file_data, "shop_user_map")
        else:
            raise serializers.ValidationError("CSV File cannot be empty.Please add some data to upload it!")

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            ShopCls.create_shop_user_mapping(validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return validated_data


class BulkUpdateShopSerializer(serializers.ModelSerializer):
    file = serializers.FileField(
        label='Update Shop Data', required=True, write_only=True)

    class Meta:
        model = Shop
        fields = ('file',)

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError(_('Sorry! Only csv file accepted.'))

        csv_file_data = csv.reader(codecs.iterdecode(
            data['file'], 'utf-8', errors='ignore'))
        # Checking, whether csv file is empty or not!
        if csv_file_data:
            read_file(csv_file_data, "shop_update")
        else:
            raise serializers.ValidationError("CSV File cannot be empty.Please add some data to upload it!")

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            ShopCls.update_shop(validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return validated_data


class BeatPlanningSampleCSVSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id',)

    def validate(self, data):
        if 'id' not in self.initial_data or not self.initial_data['id']:
            raise serializers.ValidationError(_('User must be selected '))
        u_id = self.initial_data['id']
        try:
            User.objects.get(id=u_id)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(f'user not found for id {u_id}')
        data['id'] = u_id
        return data

    def get_manager(self, user):
        return ShopUserMapping.objects.filter(employee=user, status=True)

    def create(self, validated_data):
        query_set = ShopUserMapping.objects.filter(
            employee=validated_data['id']).values_list('employee').last()

        # get the shop queryset assigned with executive
        if validated_data['created_by'].is_superuser:
            data = ShopUserMapping.objects.values_list(
                'employee__phone_number', 'employee__first_name', 'shop__shop_name', 'shop__pk',
                'shop__shop_name_address_mapping__address_contact_number',
                'shop__shop_name_address_mapping__address_line1', 'shop__shop_name_address_mapping__pincode') \
                .filter(employee=query_set, status=True, shop__shop_user__shop__approval_status=2).distinct('shop')
        else:
            if not query_set:
                raise serializers.ValidationError({"error": "Shop user mapping does not exist."})
            data = ShopUserMapping.objects.values_list(
                'employee__phone_number', 'employee__first_name', 'shop__shop_name', 'shop__pk',
                'shop__shop_name_address_mapping__address_contact_number',
                'shop__shop_name_address_mapping__address_line1', 'shop__shop_name_address_mapping__pincode') \
                .filter(employee=query_set[0], manager__in=self.get_manager(user=validated_data['created_by']),
                        status=True, shop__shop_user__shop__approval_status=2).distinct('shop')

        meta = ShopUserMapping._meta
        field_names = ['employee_phone_number', 'employee_first_name', 'shop_name', 'shop_id', 'address_contact_number',
                       'address_line1', 'pincode', 'priority', 'date (dd/mm/yyyy)']

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in data:
            writer.writerow(list(obj))
        return response


class BeatPlanningExportAsCSVSerializers(serializers.ModelSerializer):
    beat_planning_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = BeatPlanning
        fields = ('beat_planning_id_list',)

    def validate(self, data):

        if len(data.get('beat_planning_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one beat planning id must be selected '))

        for c_id in data.get('beat_planning_id_list'):
            try:
                BeatPlanning.objects.get(id=c_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'beat planning not found for id {c_id}')
        return data

    def create(self, validated_data):
        meta = BeatPlanning._meta
        field_names = ["Sales Executive (Number - Name)", "Sales Manager (Number - Name)", "Shop ID ",
                       "Contact Number", "Address", "Pin Code", "Priority", "Date (dd/mm/yyyy)", "Status"]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)

        queryset = BeatPlanning.objects.filter(id__in=validated_data['beat_planning_id_list'])
        for query in queryset:
            day_beat_plan_query_set = query.beat_plan.select_related('shop')
            for plan_obj in day_beat_plan_query_set:
                address_contact_number, address_line1, pincode = None, None, None
                if plan_obj.shop.shop_name_address_mapping.exists():
                    address = plan_obj.shop.shop_name_address_mapping.select_related('pincode_link'). \
                        only('pincode_link__pincode', 'address_contact_number', 'address_line1').last()
                    address_contact_number = address.address_contact_number
                    address_line1 = address.address_line1
                    pincode = address.pincode_link.pincode

                writer.writerow([plan_obj.beat_plan.executive, plan_obj.beat_plan.manager, plan_obj.shop_id,
                                 address_contact_number, address_line1, pincode, plan_obj.shop_category,
                                 plan_obj.beat_plan_date.strftime("%d/%m/%y"),
                                 'Active' if plan_obj.beat_plan.status is True else 'Inactive'])
        return response


class BeatPlanningListSerializer(serializers.ModelSerializer):
    manager = UserSerializers(read_only=True)
    executive = UserSerializers(read_only=True)

    class Meta:
        model = BeatPlanning
        fields = ('id', 'manager', 'executive',
                  'status', 'created_at', 'modified_at')


class BeatPlanningSerializer(serializers.ModelSerializer):
    executive_id = serializers.IntegerField(required=True)
    file = serializers.FileField(
        label='Upload Beat Planning', required=True, write_only=True)

    def __init__(self, *args, **kwargs):
        super(BeatPlanningSerializer, self).__init__(*args, **kwargs)  # call the super()
        self.fields['executive_id'].error_messages['required'] = 'Please select an executive.'

    class Meta:
        model = BeatPlanning
        fields = ('executive_id', 'file',)

    def validate(self, data):
        if not User.objects.filter(id=data['executive_id']).exists():
            raise serializers.ValidationError(_('Please select a valid executive.'))
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError(
                _('Sorry! Only csv file accepted.'))
        executive = User.objects.filter(id=data['executive_id']).last()
        csv_file_data = csv.reader(codecs.iterdecode(
            data['file'], 'utf-8', errors='ignore'))
        # Checking, whether csv file is empty or not!
        if csv_file_data:
            read_beat_planning_file(executive, csv_file_data, "beat_planning")
        else:
            raise serializers.ValidationError("CSV File cannot be empty.Please add some data to upload it!")

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            ShopCls.create_beat_planning(validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return validated_data


class DownloadShopStatusCSVSerializer(serializers.ModelSerializer):
    shop_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = Shop
        fields = ('shop_id_list',)

    def validate(self, data):

        if len(data.get('shop_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one shop id must be selected '))

        for s_id in data.get('shop_id_list'):
            try:
                Shop.objects.get(id=s_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    f'shop not found for id {s_id}')

        return data

    def create(self, validated_data):
        meta = Shop._meta
        field_names = ['shop_id', 'shop_name', 'reason', 'changed at', 'user_id', 'user_name']

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        for s_id in validated_data['shop_id_list']:
            data = ShopStatusLog.objects.values_list(
                'shop__id', 'shop__shop_name', 'reason', 'changed_at', 'user__id', 'user__first_name') \
                .filter(shop__id=s_id)
            for obj in data:
                writer.writerow(list(obj))
        return response