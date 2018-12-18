from rest_framework import serializers
from products.models import (Product,ProductPrice,ProductImage,Tax,ProductTaxMapping,ProductOption,
                             Size,Color,Fragrance,Flavor,Weight,PackageSize)
from retailer_to_sp.models import CartProductMapping,Cart,Order,OrderedProduct,Note
from retailer_to_gram.models import ( Cart as GramMappedCart,CartProductMapping as GramMappedCartProductMapping,Order as GramMappedOrder,

                                      OrderedProduct as GramMappedOrderedProduct, CustomerCare, Payment)
from addresses.models import Address,City,State,Country


from gram_to_brand.models import GRNOrderProductMapping

from sp_to_gram.models import OrderedProductMapping
from accounts.api.v1.serializers import UserSerializer
from django.urls import reverse
from django.db.models import F,Sum
from gram_to_brand.models import GRNOrderProductMapping
from addresses.api.v1.serializers import AddressSerializer

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

class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = '__all__'

class PackageSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageSize
        fields = '__all__'

class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = '__all__'

class FragranceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fragrance
        fields = '__all__'

class FlavorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flavor
        fields = '__all__'

class WeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Weight
        fields = '__all__'

class ProductOptionSerializer(serializers.ModelSerializer):
    size = SizeSerializer()
    package_size = PackageSizeSerializer()
    color = ColorSerializer()
    fragrance = FragranceSerializer()
    flavor = FlavorSerializer()
    weight = WeightSerializer()
    class Meta:
        model = ProductOption
        fields = ('size','package_size','color','fragrance','flavor','weight')


class ProductsSearchSerializer(serializers.ModelSerializer):
    product_pro_price = ProductPriceSerializer(many=True)
    product_pro_image = ProductImageSerializer(many=True)
    product_pro_tax = ProductTaxMappingSerializer(many=True)
    product_opt_product = ProductOptionSerializer(many=True)

    class Meta:
        model = Product
        fields = ('id','product_name','product_slug','product_short_description','product_long_description','product_sku',
                  'product_ean_code','product_brand','created_at','modified_at','status','product_pro_price','product_pro_image',
                  'product_pro_tax','product_opt_product')


class GramGRNProductsSearchSerializer(serializers.Serializer):
    product_name = serializers.CharField(required=True, write_only=True)
    categories = serializers.CharField(write_only=True)
    brands = serializers.CharField(write_only=True)
    sort_by_price = serializers.CharField(write_only=True)
    shop_id = serializers.CharField(write_only=True)

class CartDataSerializer(serializers.ModelSerializer):
    last_modified_by = UserSerializer()

    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','last_modified_by','created_at','modified_at',)

class CartProductMappingSerializer(serializers.ModelSerializer):
    cart_product = ProductsSearchSerializer()
    cart = CartDataSerializer()
    is_available = serializers.SerializerMethodField('is_available_id')

    def is_available_id(self,obj):
        ordered_product_sum = OrderedProductMapping.objects.filter(product=obj.cart_product).aggregate(available_qty_sum=Sum('available_qty'))
        self.is_available = True if ordered_product_sum['available_qty_sum'] and int(ordered_product_sum['available_qty_sum'])>0 else False
        return self.is_available

    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty','qty_error_msg','is_available')


class CartSerializer(serializers.ModelSerializer):
    rt_cart_list = CartProductMappingSerializer(many=True)
    last_modified_by = UserSerializer()

    items_count = serializers.SerializerMethodField('items_count_id')
    total_tax = serializers.SerializerMethodField('total_tax_id')
    total_amount = serializers.SerializerMethodField('total_amount_id')
    sub_total = serializers.SerializerMethodField('sub_total_id')

    def total_amount_id(self,obj):
        self.total_amount = 0
        self.items_count = 0
        for cart_pro in obj.rt_cart_list.all():
            self.items_count = self.items_count + int(cart_pro.qty)
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

    def items_count_id(self,obj):
        return self.items_count

    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','last_modified_by','created_at','modified_at','rt_cart_list','total_amount','total_tax','sub_total','items_count')

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
    billing_address = AddressSerializer()
    shipping_address = AddressSerializer()

    class Meta:
        model=Order
        fields = ('id','ordered_cart','order_no','billing_address','shipping_address','total_mrp','total_discount_amount',
                  'total_tax_amount','total_final_amount','order_status','ordered_by','received_by','last_modified_by',
                  'created_at','modified_at','rt_order_order_product')


class OrderNumberSerializer(serializers.ModelSerializer):

    class Meta:
        model=GramMappedOrder
        fields=('id','order_no',)


class CustomerCareSerializer(serializers.ModelSerializer):
    #order_id=OrderNumberSerializer(read_only=True)
    class Meta:
        model=CustomerCare
        fields=('name','email_us','contact_us','order_id', 'order_status', 'select_issue','complaint_detail')
        read_only_fields=('name','email_us','contact_us','order_status')

class PaymentCodSerializer(serializers.ModelSerializer):

    class Meta:
        model= Payment
        fields=('order_id',)

class PaymentNeftSerializer(serializers.ModelSerializer):

    class Meta:
        model= Payment
        fields=('order_id','neft_reference_number')

class GramMappedCartDataSerializer(serializers.ModelSerializer):
    last_modified_by = UserSerializer()

    class Meta:
        model = GramMappedCart
        fields = ('id','order_id','cart_status','last_modified_by','created_at','modified_at',)

class GramMappedCartProductMappingSerializer(serializers.ModelSerializer):
    cart_product = ProductsSearchSerializer()
    cart = GramMappedCartDataSerializer()
    is_available = serializers.SerializerMethodField('is_available_id')

    def is_available_id(self,obj):
        ordered_product_sum = GRNOrderProductMapping.objects.filter(product=obj.cart_product).aggregate(available_qty_sum=Sum('available_qty'))
        self.is_available = True if ordered_product_sum['available_qty_sum'] and int(ordered_product_sum['available_qty_sum'])>0 else False
        return self.is_available

    class Meta:
        model = GramMappedCartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty','qty_error_msg','is_available')

class GramMappedCartSerializer(serializers.ModelSerializer):
    rt_cart_list = GramMappedCartProductMappingSerializer(many=True)
    last_modified_by = UserSerializer()

    items_count = serializers.SerializerMethodField('items_count_id')
    total_tax = serializers.SerializerMethodField('total_tax_id')
    total_amount = serializers.SerializerMethodField('total_amount_id')
    sub_total = serializers.SerializerMethodField('sub_total_id')

    def total_amount_id(self,obj):
        self.total_amount = 0
        self.items_count = 0
        for cart_pro in obj.rt_cart_list.all():
            self.items_count = self.items_count + int(cart_pro.qty)
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

    def items_count_id(self,obj):
        return self.items_count

    class Meta:
        model = GramMappedCart
        fields = ('id','order_id','cart_status','last_modified_by','created_at','modified_at','rt_cart_list','total_amount','total_tax','sub_total','items_count')

class GramMappedOrderedProductSerializer(serializers.ModelSerializer):
    invoice_link = serializers.SerializerMethodField('invoice_link_id')
    rt_order_product_note = NoteSerializer(many=True)

    def invoice_link_id(self, obj):
        request = self.context.get("request")
        return "{0}{1}".format(request.get_host(),reverse('download_invoice', args=[obj.pk]))

    class Meta:
        model = GramMappedOrderedProduct
        fields = ('order','invoice_no','vehicle_no','shipped_by','received_by','last_modified_by','created_at','modified_at','invoice_link','rt_order_product_note')


class GramMappedOrderSerializer(serializers.ModelSerializer):
    ordered_cart = GramMappedCartSerializer()
    ordered_by = UserSerializer()
    last_modified_by = UserSerializer()
    rt_order_order_product = GramMappedOrderedProductSerializer(many=True)
    billing_address = AddressSerializer()
    shipping_address = AddressSerializer()

    class Meta:
        model = GramMappedOrder
        fields = ('id','ordered_cart','order_no','billing_address','shipping_address','total_mrp','total_discount_amount',
                  'total_tax_amount','total_final_amount','order_status','ordered_by','received_by','last_modified_by',
                  'created_at','modified_at','rt_order_order_product')
