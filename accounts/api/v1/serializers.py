import re

from rest_framework import serializers
from products.models import Product
from django.contrib.auth import get_user_model
from accounts.models import UserDocument, AppVersion
from django.contrib.auth.models import Group

from django.db.models import Q

User =  get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('pk','id','first_name', 'last_name', 'phone_number', 'email', 'is_whatsapp', 'user_photo')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
            'user_photo': {'required': True},
            }
        read_only_fields = ('phone_number',)


class UserDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDocument
        fields = ('user_document_type','user_document_photo','user_document_number')
        extra_kwargs = {
            'user_document_type': {'required': True},
            }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user_document_type'].error_messages['required'] = "Please select user document type"
        self.fields['user_document_number'].error_messages['required'] = "Please enter user document no."
        self.fields['user_document_number'].error_messages['blank'] = "Please enter user document no."
        self.fields['user_document_photo'].error_messages['required'] = "Please upload document photo"

    def validate_user_document_number(self, data):
        if UserDocument.objects.filter(~Q(user_id=self.context.get('request').user.id), user_document_number=data).exists():
            raise serializers.ValidationError('Document number is already registered')
        return data

    def validate(self, data):
        if data.get('user_document_type') == 'pc':
            if not re.match("^([a-zA-Z]){5}([0-9]){4}([a-zA-Z]){1}?$", data.get('user_document_number')):
                raise serializers.ValidationError({'user_document_number': 'Please enter valid pan card no.'})
        return data


class AppVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppVersion
        fields = ('app_version', 'update_recommended','force_update_required')

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('name',)

class DeliveryAppVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppVersion
        fields = ('app_version', 'update_recommended','force_update_required')


class UserPhoneSerializer(serializers.ModelSerializer):
    """
         UserPhoneNumber Serializer
    """
    class Meta:
        model = User
        fields = ('phone_number', )


class PosUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.first_name + ' ' + obj.last_name

    class Meta:
        model = User
        fields = ('phone_number', 'name', 'email', 'is_whatsapp')
