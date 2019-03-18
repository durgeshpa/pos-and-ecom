from rest_framework import serializers
from products.models import (Product,ProductPrice,ProductImage,Tax,ProductTaxMapping,ProductOption,
                             Size,Color,Fragrance,Flavor,Weight,PackageSize)
from retailer_to_sp.models import CartProductMapping,Cart,Order,OrderedProduct,Note, CustomerCare, Payment
from retailer_to_gram.models import ( Cart as GramMappedCart,CartProductMapping as GramMappedCartProductMapping,Order as GramMappedOrder,

                                      OrderedProduct as GramMappedOrderedProduct, CustomerCare as GramMappedCustomerCare, Payment as GramMappedPayment)
from addresses.models import Address,City,State,Country


from gram_to_brand.models import GRNOrderProductMapping

from sp_to_gram.models import OrderedProductMapping
from accounts.api.v1.serializers import UserSerializer
from django.urls import reverse
from django.db.models import F,Sum
from gram_to_brand.models import GRNOrderProductMapping
from addresses.api.v1.serializers import AddressSerializer
from brand.api.v1.serializers import BrandSerializer

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
    #product_pro_price = ProductPriceSerializer(many=True)
    product_pro_image = ProductImageSerializer(many=True)
    product_pro_tax = ProductTaxMappingSerializer(many=True)
    product_opt_product = ProductOptionSerializer(many=True)
    product_brand = BrandSerializer(read_only=True)
    product_price = serializers.SerializerMethodField('product_price_dt')
    product_mrp = serializers.SerializerMethodField('product_mrp_dt')
    product_case_size_picies = serializers.SerializerMethodField('product_case_size_picies_dt')

    def product_price_dt(self, obj):
        shop_id = self.context.get("parent_mapping_id",None)
        return 0 if obj.product_pro_price.filter(shop__id=shop_id).last() is None else round(obj.product_pro_price.filter(shop__id=shop_id).last().price_to_retailer,2)

    def product_mrp_dt(self, obj):
        shop_id = self.context.get("parent_mapping_id",None)
        return 0 if obj.product_pro_price.filter(shop__id=shop_id).last() is None else round(obj.product_pro_price.filter(shop__id=shop_id).last().mrp,2)

    def product_case_size_picies_dt(self,obj):
        return str(int(obj.product_inner_case_size)*int(obj.product_case_size))

    class Meta:
        model = Product
        fields = ('id','product_name','product_slug','product_short_description','product_long_description','product_sku','product_mrp',
                  'product_ean_code','product_brand','created_at','modified_at','product_pro_price','status','product_pro_image',
                  'product_pro_tax','product_opt_product','product_price','product_inner_case_size','product_case_size','product_case_size_picies')

class ProductDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model= Product
        fields = ('id','product_name',)


class GramGRNProductsSearchSerializer(serializers.Serializer):
    product_name = serializers.CharField(required=True, write_only=True)
    categories = serializers.CharField(write_only=True)
    brands = serializers.CharField(write_only=True)
    sort_by_price = serializers.CharField(write_only=True)
    shop_id = serializers.CharField(write_only=True)
    offset = serializers.CharField(write_only=True)
    pro_count = serializers.CharField(write_only=True)

class CartDataSerializer(serializers.ModelSerializer):
    last_modified_by = UserSerializer()

    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','last_modified_by','created_at','modified_at',)

class CartProductMappingSerializer(serializers.ModelSerializer):
    cart_product = ProductsSearchSerializer()
    cart = CartDataSerializer()
    is_available = serializers.SerializerMethodField('is_available_dt')
    no_of_pieces = serializers.SerializerMethodField('no_pieces_dt')
    product_sub_total = serializers.SerializerMethodField('product_sub_total_dt')

    def is_available_dt(self,obj):
        ordered_product_sum = OrderedProductMapping.objects.filter(product=obj.cart_product).aggregate(available_qty_sum=Sum('available_qty'))
        self.is_available = True if ordered_product_sum['available_qty_sum'] and int(ordered_product_sum['available_qty_sum'])>0 else False
        return self.is_available

    def no_pieces_dt(self, obj):
        return int(obj.cart_product.product_inner_case_size) * int(obj.qty)

    def product_sub_total_dt(self,obj):
        shop_id = self.context.get("parent_mapping_id", None)
        product_price = 0 if obj.cart_product.product_pro_price.filter(shop__id=shop_id).last() is None else round(obj.cart_product.product_pro_price.filter(shop__id=shop_id).last().price_to_retailer,2)
        return float(obj.cart_product.product_inner_case_size)*float(obj.qty)*float(product_price)

    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty','qty_error_msg','is_available','no_of_pieces','product_sub_total')


class CartSerializer(serializers.ModelSerializer):
    rt_cart_list = CartProductMappingSerializer(many=True)
    last_modified_by = UserSerializer()

    items_count = serializers.SerializerMethodField('items_count_id')
    total_amount = serializers.SerializerMethodField('total_amount_id')
    sub_total = serializers.SerializerMethodField('sub_total_id')
    delivery_msg = serializers.SerializerMethodField()

    def total_amount_id(self, obj):
        self.total_amount = 0
        self.items_count = 0
        for cart_pro in obj.rt_cart_list.all():
            self.items_count = self.items_count + int(cart_pro.qty)
            shop_id = self.context.get("parent_mapping_id", None)
            if ProductPrice.objects.filter(shop__id=shop_id, product=cart_pro.cart_product).exists():
                pro_price = ProductPrice.objects.filter(shop__id=shop_id, product=cart_pro.cart_product).last()
                self.total_amount = float(self.total_amount) + (float(pro_price.price_to_retailer) * float(cart_pro.qty) * float(pro_price.product.product_inner_case_size))
            else:
                self.total_amount = float(self.total_amount) + 0
        return round(self.total_amount,2)

    def sub_total_id(self, obj):
        return round(self.total_amount,2)

    def items_count_id(self, obj):
        return self.items_count

    def get_delivery_msg(self, obj):
        return self.context.get("delivery_message", None)

    class Meta:
        model = Cart
        fields = ('id', 'order_id', 'cart_status', 'last_modified_by',
                  'created_at', 'modified_at', 'rt_cart_list', 'total_amount',
                  'sub_total', 'items_count', 'delivery_msg')


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
    #rt_order_product_note = NoteSerializer(many=True)

    def invoice_link_id(self, obj):
        current_url = self.context.get("current_url", None)
        return "{0}{1}".format(current_url,reverse('download_invoice_sp', args=[obj.pk]))

    class Meta:
        model = OrderedProduct
        fields = ('order','invoice_no','invoice_link')

#order serilizer
class OrderSerializer(serializers.ModelSerializer):
    ordered_cart = CartSerializer()
    ordered_by = UserSerializer()
    last_modified_by = UserSerializer()
    rt_order_order_product = OrderedProductSerializer(many=True)
    billing_address = AddressSerializer()
    shipping_address = AddressSerializer()
    order_status = serializers.CharField(source='get_order_status_display')

    def to_representation(self, instance):
        representation = super(OrderSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        return representation

    class Meta:
        model=Order
        fields = ('id','ordered_cart','order_no','billing_address','shipping_address','total_mrp','total_discount_amount',
                  'total_tax_amount','total_final_amount','order_status','ordered_by','received_by','last_modified_by',
                  'created_at','modified_at','rt_order_order_product')

class CartProductPrice(serializers.ModelSerializer):
    product = ProductsSearchSerializer()
    product_price = serializers.SerializerMethodField('product_price_dt')
    product_mrp = serializers.SerializerMethodField('product_mrp_dt')

    def product_price_dt(self,obj):
        return obj.price_to_retailer

    def product_mrp_dt(self,obj):
        return obj.mrp

    class Meta:
        model = ProductPrice
        fields = ('id','product','product_price','product_mrp','created_at')

class OrderedCartProductMappingSerializer(serializers.ModelSerializer):
    cart_product = ProductsSearchSerializer()
    cart = CartDataSerializer()
    cart_product_price = CartProductPrice()
    no_of_pieces = serializers.SerializerMethodField('no_pieces_dt')
    product_sub_total = serializers.SerializerMethodField('product_sub_total_dt')

    def no_pieces_dt(self, obj):
        return int(obj.no_of_pieces)

    def product_sub_total_dt(self,obj):
        shop = self.context.get("parent_mapping", None)
        return float(obj.no_of_pieces) * float(round(obj.cart_product_price.get_cart_product_price(shop).price_to_retailer),2)

    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty','qty_error_msg','no_of_pieces','product_sub_total','cart_product_price')


class OrderedCartSerializer(serializers.ModelSerializer):
    rt_cart_list = OrderedCartProductMappingSerializer(many=True)
    last_modified_by = UserSerializer()
    items_count = serializers.ReadOnlyField(source='qty_sum')
    total_amount = serializers.ReadOnlyField(source='subtotal')
    sub_total = serializers.ReadOnlyField(source='subtotal')

    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','last_modified_by','created_at','modified_at','rt_cart_list','total_amount','sub_total','items_count')

#order Details
class OrderDetailSerializer(serializers.ModelSerializer):
    ordered_cart = OrderedCartSerializer()
    ordered_by = UserSerializer()
    last_modified_by = UserSerializer()
    rt_order_order_product = OrderedProductSerializer(many=True)
    billing_address = AddressSerializer()
    shipping_address = AddressSerializer()
    order_status = serializers.CharField(source='get_order_status_display')

    def to_representation(self, instance):
        representation = super(OrderDetailSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        return representation

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
        fields=('order_id','paid_amount','payment_choice','neft_reference_number')

class PaymentNeftSerializer(serializers.ModelSerializer):

    class Meta:
        model= Payment
        fields=('order_id','neft_reference_number')


class GramPaymentCodSerializer(serializers.ModelSerializer):

    class Meta:
        model= GramMappedPayment
        fields=('order_id',)

class GramPaymentNeftSerializer(serializers.ModelSerializer):

    class Meta:
        model= GramMappedPayment
        fields=('order_id','neft_reference_number')

class GramMappedCartDataSerializer(serializers.ModelSerializer):
    last_modified_by = UserSerializer()

    class Meta:
        model = GramMappedCart
        fields = ('id','order_id','cart_status','last_modified_by','created_at','modified_at',)

class GramMappedCartProductMappingSerializer(serializers.ModelSerializer):
    cart_product = ProductsSearchSerializer()
    cart = GramMappedCartDataSerializer()
    is_available = serializers.SerializerMethodField('is_available_dt')
    no_of_pieces = serializers.SerializerMethodField('no_pieces_dt')
    product_sub_total = serializers.SerializerMethodField('product_sub_total_dt')

    def is_available_dt(self,obj):
        ordered_product_sum = GRNOrderProductMapping.objects.filter(product=obj.cart_product).aggregate(available_qty_sum=Sum('available_qty'))
        self.is_available = True if ordered_product_sum['available_qty_sum'] and int(ordered_product_sum['available_qty_sum'])>0 else False
        return self.is_available

    def no_pieces_dt(self,obj):
        return int(obj.cart_product.product_inner_case_size)*int(obj.qty)

    def product_sub_total_dt(self,obj):
        shop_id = self.context.get("parent_mapping_id", None)
        product_price = 0 if obj.cart_product.product_pro_price.filter(shop__id=shop_id).last() is None else obj.cart_product.product_pro_price.filter(shop__id=shop_id).last().price_to_retailer
        return float(obj.cart_product.product_inner_case_size)*float(obj.qty)*float(product_price)

    class Meta:
        model = GramMappedCartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty','qty_error_msg','is_available','no_of_pieces','product_sub_total')

class GramMappedCartSerializer(serializers.ModelSerializer):
    rt_cart_list = GramMappedCartProductMappingSerializer(many=True)
    last_modified_by = UserSerializer()

    items_count = serializers.SerializerMethodField('items_count_id')
    total_amount = serializers.SerializerMethodField('total_amount_id')
    sub_total = serializers.SerializerMethodField('sub_total_id')
    delivery_msg = serializers.SerializerMethodField()

    def total_amount_id(self,obj):
        self.total_amount = 0
        self.items_count = 0
        for cart_pro in obj.rt_cart_list.all():
            self.items_count = self.items_count + int(cart_pro.qty)
            shop_id = self.context.get("parent_mapping_id", None)
            pro_price = ProductPrice.objects.filter(shop__id=shop_id,product=cart_pro.cart_product).last()
            if pro_price and pro_price.price_to_retailer:
                self.total_amount = float(self.total_amount) + (float(pro_price.price_to_retailer) * float(cart_pro.qty) * float(pro_price.product.product_inner_case_size))
            else:
                self.total_amount = float(self.total_amount) + 0
        return self.total_amount

    def sub_total_id(self,obj):
        return self.total_amount

    def items_count_id(self,obj):
        return self.items_count

    def get_delivery_msg(self, obj):
        return self.context.get("delivery_message", None)

    def to_representation(self, instance):
        representation = super(GramMappedCartSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        return representation

    class Meta:
        model = GramMappedCart
        fields = ('id', 'order_id', 'cart_status', 'last_modified_by',
                  'created_at', 'modified_at', 'rt_cart_list', 'total_amount',
                  'items_count', 'sub_total', 'delivery_msg')


class GramMappedOrderedProductSerializer(serializers.ModelSerializer):
    invoice_link = serializers.SerializerMethodField('invoice_link_id')
    rtg_order_product_note = NoteSerializer(many=True)

    def invoice_link_id(self, obj):
        current_url = self.context.get("current_url", None)
        return "{0}{1}".format(current_url,reverse('download_invoice', args=[obj.pk]))

    class Meta:
        model = GramMappedOrderedProduct
        fields = ('order','invoice_no','vehicle_no','shipped_by','received_by','last_modified_by','created_at','modified_at','rtg_order_product_note','invoice_link')


class GramMappedOrderSerializer(serializers.ModelSerializer):
    ordered_cart = GramMappedCartSerializer()
    ordered_by = UserSerializer()
    last_modified_by = UserSerializer()
    rt_order_order_product = GramMappedOrderedProductSerializer(many=True)
    billing_address = AddressSerializer()
    shipping_address = AddressSerializer()
    order_status = serializers.CharField(source='get_order_status_display')

    def to_representation(self, instance):
        representation = super(GramMappedOrderSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        return representation

    class Meta:
        model = GramMappedOrder
        fields = ('id','ordered_cart','order_no','billing_address','shipping_address','total_mrp','total_discount_amount',
                  'total_tax_amount','total_final_amount','order_status','ordered_by','received_by','last_modified_by',
                  'created_at','modified_at','rt_order_order_product')
