from rest_framework import serializers
from products.models import Product, ProductPrice
from retailer_to_sp.models import Order, OrderedProduct, OrderedProductMapping
from gram_to_brand.models import Order as PurchaseOrder
from shops.models import Shop, ParentRetailerMapping


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

class PurchaseOrderSerializer(serializers.Serializer):
    class Meta:
        model=PurchaseOrder
        fields = '__all__'

class ShopSerializer(serializers.Serializer):
    class Meta:
        model = Shop
        fields = '__all__'

class ParentRetailerSerializer(serializers.Serializer):
    class Meta:
        model = ParentRetailerMapping
        fields = '__all__'