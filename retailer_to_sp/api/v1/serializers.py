from rest_framework import serializers
from products.models import Product
from retailer_to_sp.models import CartProductMapping,Cart,Order
from gram_to_brand.models import GRNOrderProductMapping

class ProductsSearchSerializer(serializers.ModelSerializer):
   class Meta:
      model = Product
      fields = '__all__'

class GramGRNProductsSearchSerializer(serializers.Serializer):
    product_name = serializers.CharField(required=True, write_only=True)

class CartProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Cart
        fields = 'id'

class CartProductMappingSerializer(serializers.ModelSerializer):

    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty','qty_error_msg')


class CartSerializer(serializers.ModelSerializer):
    #rt_cart_list = serializers.RelatedField(many=True,read_only=True)
    rt_cart_list = CartProductMappingSerializer(many=True)

    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','last_modified_by','created_at','modified_at','rt_cart_list')


class OrderSerializer(serializers.ModelSerializer):

    class Meta:
        model=Order
        fields = '__all__'