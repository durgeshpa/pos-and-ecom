from rest_framework import serializers
from products.models import Product, ProductPrice


class ProductSerializer(serializers.Serializer):
    class Meta:
        model = Product
        fields = ('id',)

class ProductPriceSerializer(serializers.Serializer):
    class Meta:
        model = ProductPrice
        fields = ('seller_shop_id',)