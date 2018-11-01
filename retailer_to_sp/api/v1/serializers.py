from rest_framework import serializers
from products.models import Product,ProductPrice,ProductImage,Tax,ProductTaxMapping
from retailer_to_sp.models import CartProductMapping,Cart,Order,OrderedProduct,Note
from accounts.api.v1.serializers import UserSerializer
from django.urls import reverse
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

    total_tax = serializers.SerializerMethodField('total_tax_id')
    total_amount = serializers.SerializerMethodField('total_amount_id')
    sub_total = serializers.SerializerMethodField('sub_total_id')

    def total_amount_id(self,obj):
        self.total_amount = 0
        for cart_pro in obj.rt_cart_list.all():
            pro_price = ProductPrice.objects.filter(product=cart_pro.cart_product)[0]
            self.total_amount = float(self.total_amount) + (float(pro_price.price_to_retailer) * float(cart_pro.qty))
        return self.total_amount

    def total_tax_id(self,obj):
        self.total_tax = 0
        for cart_pro in obj.rt_cart_list.all():
            pro_price = ProductPrice.objects.filter(product=cart_pro.cart_product)[0]
            for product_tax in ProductTaxMapping.objects.filter(product=cart_pro.cart_product):
                self.total_tax = float(self.total_tax) + (float(pro_price.price_to_retailer) * float(product_tax.tax.tax_percentage)/100)
        return self.total_tax

    def sub_total_id(self,obj):
        return self.total_amount + self.total_tax

    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','last_modified_by','created_at','modified_at','rt_cart_list','total_amount','total_tax','sub_total')


class NoteSerializer(serializers.ModelSerializer):
    note_link = serializers.SerializerMethodField('note_link_id')
    note_type = serializers.SerializerMethodField()
    last_modified_by = UserSerializer()

    def note_link_id(self, obj):
        request = self.context.get("request")
        return "{0}{1}".format(request.get_host(),reverse('download_note', args=[obj.pk]))

    def get_note_type(self, obj):
        return obj.get_note_type_display()

    class Meta:
        model = Note
        fields = ('id','amount','note_type','last_modified_by','created_at','modified_at','note_link')

class OrderedProductSerializer(serializers.ModelSerializer):
    invoice_link = serializers.SerializerMethodField('invoice_link_id')
    rt_order_product_note = NoteSerializer(many=True)

    def invoice_link_id(self, obj):
        request = self.context.get("request")
        return "{0}{1}".format(request.get_host(),reverse('download_invoice', args=[obj.pk]))

    class Meta:
        model = OrderedProduct
        fields = ('order','invoice_no','vehicle_no','shipped_by','received_by','last_modified_by','created_at','modified_at','invoice_link','rt_order_product_note')

class OrderSerializer(serializers.ModelSerializer):
    ordered_cart = CartSerializer()
    ordered_by = UserSerializer()
    last_modified_by = UserSerializer()
    rt_order_order_product = OrderedProductSerializer(many=True)

    class Meta:
        model=Order
        fields = ('id','ordered_cart','order_no','billing_address','shipping_address','total_mrp','total_discount_amount',
                  'total_tax_amount','total_final_amount','order_status','ordered_by','received_by','last_modified_by',
                  'created_at','modified_at','rt_order_order_product')
