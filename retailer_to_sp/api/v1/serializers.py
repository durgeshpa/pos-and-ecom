from rest_framework import serializers
from products.models import Product,ProductPrice,ProductImage,Tax,ProductTaxMapping
from retailer_to_sp.models import CartProductMapping,Cart,Order
from accounts.api.v1.serializers import UserSerializer
from gram_to_brand.models import GRNOrderProductMapping

class ProductImageSerializer(serializers.ModelSerializer):
   class Meta:
      model = ProductImage
      fields = '__all__'

class ProductPriceSerializer(serializers.ModelSerializer):
   class Meta:
      model = ProductPrice
      fields = '__all__'

class TaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = '__all__'

class ProductTaxMappingSerializer(serializers.ModelSerializer):
    tax = TaxSerializer()
    class Meta:
        model = ProductTaxMapping
        fields = '__all__'

class ProductsSearchSerializer(serializers.ModelSerializer):
    product_pro_price = ProductPriceSerializer(many=True)
    product_pro_image = ProductImageSerializer(many=True)
    product_pro_tax = ProductTaxMappingSerializer(many=True)
    #product_pro_image = ProductImageSerializer(many=True)
    #product_pro_image = ProductImageSerializer(many=True)

    class Meta:
        model = Product
        fields = ('id','product_name','product_slug','product_short_description','product_long_description','product_sku',
                  'product_ean_code','product_brand','created_at','modified_at','status','product_pro_price','product_pro_image',
                  'product_pro_tax',)


class GramGRNProductsSearchSerializer(serializers.Serializer):
    product_name = serializers.CharField(required=True, write_only=True)

class CartProductSerializer(serializers.ModelSerializer):
    last_modified_by = UserSerializer()
    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','last_modified_by','created_at','modified_at',)

class CartProductMappingSerializer(serializers.ModelSerializer):
    cart_product = ProductsSearchSerializer()
    cart = CartProductSerializer()
    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty','qty_error_msg')


class CartSerializer(serializers.ModelSerializer):
    rt_cart_list = CartProductMappingSerializer(many=True)
    last_modified_by = UserSerializer()

    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','last_modified_by','created_at','modified_at','rt_cart_list')

class OrderSerializer(serializers.ModelSerializer):
    ordered_cart = CartSerializer()
    ordered_by = UserSerializer()
    last_modified_by = UserSerializer()

    class Meta:
        model=Order
        fields = ('id','ordered_cart','order_no','billing_address','shipping_address','total_mrp','total_discount_amount',
                  'total_tax_amount','total_final_amount','order_status','ordered_by','received_by','last_modified_by',
                  'created_at','modified_at',)
