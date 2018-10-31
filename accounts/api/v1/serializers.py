from rest_framework import serializers
from products.models import Product
from django.contrib.auth import get_user_model
from accounts.models import UserDocument

User =  get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('pk','id','first_name', 'last_name', 'phone_number', 'email', 'user_photo')
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
