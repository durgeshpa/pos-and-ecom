from rest_framework import serializers
from products.models import Product, ProductPrice
from retailer_to_sp.models import Order, OrderedProduct, OrderedProductMapping


class ProductSerializer(serializers.Serializer):
    class Meta:
        model = Product
        fields = ('id',)

class ProductPriceSerializer(serializers.Serializer):
    class Meta:
        model = ProductPrice
        fields = ('seller_shop_id',)

class OrderSerializer(serializers.Serializer):
    class Meta:
        model = Order
        fields = '__all__'

class OrderedProductSerializer(serializers.Serializer):
    class Meta:
        model = OrderedProduct
        fields = '__all__'

class OrderedProductMappingSerializer(serializers.Serializer):
    class Meta:
        model = OrderedProductMapping
        fields = '__all__'