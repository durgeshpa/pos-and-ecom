from rest_framework import serializers
from gram_to_brand.models import CartProductMapping


class CartProductMappingSerializer(serializers.ModelSerializer):

    class Meta:
        model = CartProductMapping
        fields = ('cart_product', 'qty', 'price',)
