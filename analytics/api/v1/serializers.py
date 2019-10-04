from rest_framework import serializers
from products.models import Product


class ProductSerializer(serializers.Serializer):
    class Meta:
        model = Product
        fields = ('id',)