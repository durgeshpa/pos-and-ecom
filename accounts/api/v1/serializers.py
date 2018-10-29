from rest_framework import serializers
from products.models import Product
from django.contrib.auth import get_user_model

User =  get_user_model()

class UserIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('pk')
        read_only_fields = ('pk',)
