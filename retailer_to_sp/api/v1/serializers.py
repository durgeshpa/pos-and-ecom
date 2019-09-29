from rest_framework import serializers

from common.common_utils import convert_date_format_ddmmmyyyy

from products.models import (Product,ProductPrice,ProductImage,Tax,ProductTaxMapping,ProductOption,
                             Size,Color,Fragrance,Flavor,Weight,PackageSize)
from retailer_to_sp.models import (CartProductMapping, Cart, Order,
                                   OrderedProduct, Note, CustomerCare,
                                   Payment, Dispatch, Feedback, OrderedProductMapping as RetailerOrderedProductMapping, Trip, PickerDashboard, ShipmentRescheduling)

from retailer_to_gram.models import ( Cart as GramMappedCart,CartProductMapping as GramMappedCartProductMapping,Order as GramMappedOrder,
    OrderedProduct as GramMappedOrderedProduct, CustomerCare as GramMappedCustomerCare, Payment as GramMappedPayment
 )
from addresses.models import Address,City,State,Country
from gram_to_brand.models import GRNOrderProductMapping

from sp_to_gram.models import OrderedProductMapping
from accounts.api.v1.serializers import UserSerializer
from django.urls import reverse
from django.db.models import F,Sum
from gram_to_brand.models import GRNOrderProductMapping
from addresses.api.v1.serializers import AddressSerializer
from brand.api.v1.serializers import BrandSerializer
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist
from shops.models import Shop

from django.contrib.auth import get_user_model
from coupon.serializers import CouponSerializer
import datetime
from coupon.models import Coupon

User = get_user_model()


class PickerDashboardSerializer(serializers.ModelSerializer):
   class Meta:
      model = PickerDashboard
      fields = '__all__'


class ProductImageSerializer(serializers.ModelSerializer):
   class Meta:
      model = ProductImage
      fields = '__all__'


class ProductPriceSerializer(serializers.ModelSerializer):
   class Meta:
      model = ProductPrice
      fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()

    def get_product_image(self, obj):
        if ProductImage.objects.filter(product=obj).exists():
            product_image = ProductImage.objects.filter(product=obj)[0].image.url
            return product_image
        else:
            return None

    class Meta:
        model = Product
        fields = ('id','product_name','product_inner_case_size',
            'product_case_size', 'product_image'
            )

class OrderedProductMappingSerializer(serializers.ModelSerializer):
    # This serializer is used to fetch the products for a shipment
    product = ProductSerializer()
    product_price = serializers.SerializerMethodField()
    product_total_price = serializers.SerializerMethodField()

    #ordered_product = ReadOrderedProductSerializer()

    def get_product_price(self, obj):
        # fetch product , order_id
        cart_product_mapping = CartProductMapping.objects.get(cart_product=obj.product, cart=obj.ordered_product.order.ordered_cart)
        self.product_price = cart_product_mapping.cart_product_price.price_to_retailer
        return round(self.product_price,2)

    def get_product_total_price(self, obj):
        cart_product_mapping = CartProductMapping.objects.get(cart_product=obj.product, cart=obj.ordered_product.order.ordered_cart)
        product_price = cart_product_mapping.cart_product_price.price_to_retailer
        self.product_total_price = product_price*obj.shipped_qty
        return round(self.product_total_price,2)

    class Meta:
        model = OrderedProductMapping
        fields = ('id', 'shipped_qty', 'product', 'product_price', 'product_total_price') #, 'ordered_product')


class ListOrderedProductSerializer(serializers.ModelSerializer):
    # created_at = serializers.SerializerMethodField()

    # def get_created_at(self, obj):
    #     if obj.created_at:
    #         created_at = convert_date_format_ddmmmyyyy(obj.created_at.__str__().split(' ')[0])
    #     return created_at

    class Meta:
        model = OrderedProduct
        fields = ('id', 'invoice_no') #, 'created_at')


class ReadOrderedProductSerializer(serializers.ModelSerializer):
    shop_owner_name = serializers.SerializerMethodField()
    shop_owner_number = serializers.SerializerMethodField()
    order_created_date = serializers.SerializerMethodField()
    rt_order_product_order_product_mapping = OrderedProductMappingSerializer(many=True)

    def get_shop_owner_number(self, obj):
        shop_owner_number = obj.order.buyer_shop.shop_owner.phone_number
        return shop_owner_number

    def get_shop_owner_name(self, obj):
        shop_owner_name = obj.order.buyer_shop.shop_owner.first_name + obj.order.buyer_shop.shop_owner.last_name
        return shop_owner_name

    def get_order_created_date(self, obj):
        order_created_date = obj.order.created_at
        return order_created_date.strftime("%d/%b/%Y")

    class Meta:
        model = OrderedProduct
        #fields = '__all__'
        fields = ('id','invoice_no','shipment_status','invoice_amount',
            'payment_mode', 'shipment_address', 'shop_owner_name', 'shop_owner_number',
            'order_created_date', 'rt_order_product_order_product_mapping')
        #depth = 1


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
    #product_pro_tax = ProductTaxMappingSerializer(many=True)
    product_opt_product = ProductOptionSerializer(many=True)
    #product_brand = BrandSerializer(read_only=True)
    product_price = serializers.SerializerMethodField('product_price_dt')
    product_mrp = serializers.SerializerMethodField('product_mrp_dt')
    product_case_size_picies = serializers.SerializerMethodField('product_case_size_picies_dt')
    margin = serializers.SerializerMethodField('margin_dt')
    loyalty_discount = serializers.SerializerMethodField('loyalty_discount_dt')
    cash_discount = serializers.SerializerMethodField('cash_discount_dt')

    def product_price_dt(self, obj):
        self.product_price = obj.getRetailerPrice(self.context.get("parent_mapping_id"))
        return self.product_price

    def product_mrp_dt(self, obj):
        self.product_mrp = obj.getMRP(self.context.get("parent_mapping_id"))
        return self.product_mrp

    def product_case_size_picies_dt(self,obj):
        return str(int(obj.product_inner_case_size)*int(obj.product_case_size))

    def loyalty_discount_dt(self,obj):
        self.loyalty_discount = obj.getLoyaltyIncentive(self.context.get("parent_mapping_id"))
        return self.loyalty_discount

    def cash_discount_dt(self,obj):
        self.cash_discount = obj.getCashDiscount(self.context.get("parent_mapping_id"))
        return self.cash_discount

    def margin_dt(self,obj):
        return round(100 - (float(self.product_price) * 1000000 / (float(self.product_mrp) * (100 - float(obj.getCashDiscount(self.context.get("parent_mapping_id")))) * (100 -  float(obj.getLoyaltyIncentive(self.context.get("parent_mapping_id")))))),2) if self.product_mrp and self.product_mrp > 0 else 0



    class Meta:
        model = Product
        fields = ('id','product_name','product_slug','product_short_description','product_long_description','product_sku','product_mrp',
                  'product_ean_code','created_at','modified_at','status','product_pro_image',
                  'product_opt_product','product_price','product_inner_case_size','product_case_size','product_case_size_picies',
                  'margin', 'loyalty_discount', 'cash_discount')

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
    product_coupons = serializers.SerializerMethodField('product_coupons_dt')

    def is_available_dt(self,obj):
        ordered_product_sum = OrderedProductMapping.objects.filter(product=obj.cart_product).aggregate(available_qty_sum=Sum('available_qty'))
        self.is_available = True if ordered_product_sum['available_qty_sum'] and int(ordered_product_sum['available_qty_sum'])>0 else False
        return self.is_available

    def no_pieces_dt(self, obj):
        return int(obj.cart_product.product_inner_case_size) * int(obj.qty)

    def product_sub_total_dt(self,obj):
        shop_id = self.context.get("parent_mapping_id", None)
        product_price = 0 if obj.cart_product.product_pro_price.filter(shop__id=shop_id).last() is None else round(obj.cart_product.product_pro_price.filter(shop__id=shop_id).last().price_to_retailer,2)
        return round(float(obj.cart_product.product_inner_case_size)*float(obj.qty)*float(product_price),2)

    def product_coupons_dt(self, obj):
        product_coupons = []
        date = datetime.datetime.now()
        sku_no_of_pieces = int(obj.cart_product.product_inner_case_size) * int(obj.qty)
        for rules in obj.cart_product.purchased_product_coupon.filter(rule__is_active = True, rule__expiry_date__gte = date):
            for rule in rules.rule.coupon_ruleset.filter(is_active=True, expiry_date__gte = date):
                product_coupons.append(rule.coupon_code)
        if product_coupons:
            coupons_queryset = Coupon.objects.filter(coupon_code__in = product_coupons)
            coupons = CouponSerializer(coupons_queryset, many=True).data
            for coupon in coupons_queryset:
                for product_coupon in coupon.rule.product_ruleset.filter(purchased_product = obj.cart_product):
                    if product_coupon.max_qty_per_use > 0:
                        max_qty = product_coupon.max_qty_per_use
                        for i in coupons: i['max_qty'] = max_qty
            keyValList3 = ['catalog']
            exampleSet3 = obj.cart.offers
            array3 = list(filter(lambda d: d['coupon_type'] in keyValList3, exampleSet3))
            for i in array3:
                if i['item_sku']== obj.cart_product.product_sku:
                    for i in coupons: i['is_applied'] = True
            return coupons

    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty','qty_error_msg', 'is_available','no_of_pieces','product_sub_total', 'product_coupons')


class CartSerializer(serializers.ModelSerializer):
    rt_cart_list = CartProductMappingSerializer(many=True)
    last_modified_by = UserSerializer()

    items_count = serializers.SerializerMethodField('items_count_id')
    total_amount = serializers.SerializerMethodField('total_amount_id')
    total_discount = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField('sub_total_id')
    delivery_msg = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('id', 'order_id', 'cart_status', 'last_modified_by',
                  'created_at', 'modified_at', 'rt_cart_list', 'total_amount',
                  'total_discount', 'sub_total', 'items_count', 'delivery_msg', 'offers')

    def get_total_discount(self, obj):
        sum = 0
        keyValList1 = ['discount']
        exampleSet1 = obj.offers
        array1 = list(filter(lambda d: d['type'] in keyValList1, exampleSet1))
        for i in array1:
            sum = sum + i['discount_value']
        return round(sum, 2)

    def total_amount_id(self, obj):
        self.total_amount = 0
        self.items_count = 0
        total_discount = self.get_total_discount(obj)
        for cart_pro in obj.rt_cart_list.all():
            self.items_count = self.items_count + int(cart_pro.qty)
            shop_id = self.context.get("parent_mapping_id", None)
            shop = Shop.objects.get(pk=shop_id)
            pro_price = cart_pro.cart_product.get_current_shop_price(shop)
            self.total_amount += float(pro_price.price_to_retailer) * float(cart_pro.qty) * float(pro_price.product.product_inner_case_size)
        return round(self.total_amount, 2)

    def sub_total_id(self, obj):
        sub_total = self.total_amount_id(obj) - self.get_total_discount(obj)
        return round(sub_total, 2)

    def items_count_id(self, obj):
        return obj.rt_cart_list.count()

    def get_delivery_msg(self, obj):
        return self.context.get("delivery_message", None)


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
    total_final_amount = serializers.ReadOnlyField()#source='total_final_amount')
    total_mrp_amount = serializers.ReadOnlyField()#source='total_mrp_amount')

    def to_representation(self, instance):
        representation = super(OrderSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        return representation

    class Meta:
        model=Order
        fields = ('id','ordered_cart','order_no','billing_address','shipping_address','total_mrp','total_discount_amount',
                  'total_tax_amount','total_final_amount','order_status','ordered_by','received_by','last_modified_by',
                  'created_at','modified_at','rt_order_order_product', 'total_mrp_amount')

class CartProductPrice(serializers.ModelSerializer):
    product_price = serializers.SerializerMethodField('product_price_dt')
    product_mrp = serializers.SerializerMethodField('product_mrp_dt')

    def product_price_dt(self,obj):
        return round(obj.price_to_retailer,2)

    def product_mrp_dt(self,obj):
        return round(obj.mrp,2)

    class Meta:
        model = ProductPrice
        fields = ('id','product_price','product_mrp','created_at')

class OrderedCartProductMappingSerializer(serializers.ModelSerializer):
    cart_product = ProductsSearchSerializer()
    #cart = CartDataSerializer()
    cart_product_price = CartProductPrice()
    no_of_pieces = serializers.SerializerMethodField('no_pieces_dt')
    product_sub_total = serializers.SerializerMethodField('product_sub_total_dt')
    product_inner_case_size = serializers.SerializerMethodField('product_inner_case_size_dt')

    def no_pieces_dt(self, obj):
        return int(obj.no_of_pieces)

    def product_sub_total_dt(self,obj):
        shop = self.context.get("parent_mapping", None)
        return float(obj.no_of_pieces) * float(round(obj.get_cart_product_price(shop).price_to_retailer,2))

    def product_inner_case_size_dt(self,obj):
        return int(int(obj.no_of_pieces) // int(obj.qty))


    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty','qty_error_msg','no_of_pieces','product_sub_total','cart_product_price','product_inner_case_size')


class OrderedCartSerializer(serializers.ModelSerializer):
    rt_cart_list = OrderedCartProductMappingSerializer(many=True)
    items_count = serializers.ReadOnlyField(source='qty_sum')
    total_amount = serializers.ReadOnlyField(source='subtotal')
    sub_total = serializers.ReadOnlyField(source='subtotal')

    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','created_at','modified_at','rt_cart_list','total_amount','sub_total','items_count', 'offers')

#order Details
class OrderDetailSerializer(serializers.ModelSerializer):
    ordered_cart = OrderedCartSerializer()
    rt_order_order_product = OrderedProductSerializer(many=True)
    shipping_address = AddressSerializer()
    order_status = serializers.CharField(source='get_order_status_display')

    def to_representation(self, instance):
        representation = super(OrderDetailSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        return representation

    class Meta:
        model=Order
        fields = ('id','ordered_cart','order_no','shipping_address','total_mrp','total_discount_amount',
                  'total_tax_amount','total_final_amount','order_status','received_by',
                  'created_at','modified_at','rt_order_order_product')

# Order List Realted Serilizer Start

class ProductsSearchListSerializer(serializers.ModelSerializer):
    product_price = serializers.SerializerMethodField('product_price_dt')
    product_mrp = serializers.SerializerMethodField('product_mrp_dt')
    product_case_size_picies = serializers.SerializerMethodField('product_case_size_picies_dt')

    def product_price_dt(self, obj):
        shop_id = self.context.get("parent_mapping_id",None)
        return obj.getRetailerPrice(shop_id)

    def product_mrp_dt(self, obj):
        shop_id = self.context.get("parent_mapping_id",None)
        return obj.getMRP(shop_id)

    def product_case_size_picies_dt(self,obj):
        return str(int(obj.product_inner_case_size)*int(obj.product_case_size))

    class Meta:
        model = Product
        fields = ('id','product_name','product_sku','product_mrp',
                  'product_price','product_inner_case_size','product_case_size','product_case_size_picies')


class CartProductListPrice(serializers.ModelSerializer):
    product_price = serializers.SerializerMethodField('product_price_dt')
    product_mrp = serializers.SerializerMethodField('product_mrp_dt')

    def product_price_dt(self,obj):
        return obj.price_to_retailer

    def product_mrp_dt(self,obj):
        return obj.mrp

    class Meta:
        model = ProductPrice
        fields = ('id','product_price','product_mrp','created_at')

class OrderedCartProductMappingListSerializer(serializers.ModelSerializer):
    cart_product = ProductsSearchListSerializer()
    no_of_pieces = serializers.SerializerMethodField('no_pieces_dt')
    product_sub_total = serializers.SerializerMethodField('product_sub_total_dt')
    product_inner_case_size = serializers.SerializerMethodField('product_inner_case_size_dt')
    cart_product_price = CartProductListPrice()

    def no_pieces_dt(self, obj):
        return int(obj.no_of_pieces)

    def product_sub_total_dt(self,obj):
        shop = self.context.get("parent_mapping", None)
        return float(obj.no_of_pieces) * float(round(obj.get_cart_product_price(shop).price_to_retailer,2))

    def product_inner_case_size_dt(self,obj):
        return int(int(obj.no_of_pieces) // int(obj.qty))

    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product','qty','qty_error_msg','no_of_pieces','product_sub_total','cart_product_price','product_inner_case_size')


class OrderedCartListSerializer(serializers.ModelSerializer):
    rt_cart_list = OrderedCartProductMappingListSerializer(many=True)
    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','rt_cart_list', 'offers')


#order List
class OrderListSerializer(serializers.ModelSerializer):
    ordered_cart = OrderedCartListSerializer()
    #Todo remove
    shipping_address = AddressSerializer()
    order_status = serializers.CharField(source='get_order_status_display')
    #rt_order_order_product = ListOrderedProductSerializer(many=True)
    rt_order_order_product = serializers.SerializerMethodField()

    def get_rt_order_order_product(self, obj):
        qs = OrderedProduct.objects.filter(order_id=obj.id).exclude(shipment_status='SHIPMENT_CREATED')
        serializer = ListOrderedProductSerializer(instance=qs, many=True)
        return serializer.data

    def to_representation(self, instance):
        representation = super(OrderListSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        return representation

    class Meta:
        model=Order
        fields = ('id','ordered_cart','order_no','total_final_amount','order_status','shipping_address',
                  'created_at','modified_at','rt_order_order_product')

# Order List Related Serializer End


class OrderNumberSerializer(serializers.ModelSerializer):

    class Meta:
        model=Order
        fields=('id','order_no',)

class CustomerCareSerializer(serializers.ModelSerializer):
    #order_id=OrderNumberSerializer(read_only=True)

    #phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$')
    #phone_number = serializers.CharField(validators=[phone_regex])
    class Meta:
        model=CustomerCare
        fields=('phone_number', 'complaint_id','email_us', 'order_id', 'issue_status', 'select_issue','complaint_detail')
        read_only_fields=('complaint_id','email_us','issue_status')

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
    rt_order_order_product = ListOrderedProductSerializer(many=True)

    def to_representation(self, instance):
        representation = super(GramMappedOrderSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        return representation

    class Meta:
        model = GramMappedOrder
        fields = ('id','ordered_cart','order_no','billing_address','shipping_address','total_mrp','total_discount_amount',
                  'total_tax_amount','total_final_amount','order_status','ordered_by','received_by','last_modified_by',
                  'created_at','modified_at','rt_order_order_product')


class DispatchSerializer(serializers.ModelSerializer):
    shipment_status = serializers.CharField(
                                        source='get_shipment_status_display')
    order = serializers.SlugRelatedField(read_only=True, slug_field='order_no')
    created_at = serializers.DateTimeField()

    class Meta:
        model = Dispatch
        fields = ('pk', 'trip', 'order', 'shipment_status', 'invoice_no',
                  'shipment_address', 'invoice_city', 'invoice_amount',
                  'created_at')
        read_only_fields = ('shipment_address', 'invoice_city', 'invoice_amount')


class CommercialShipmentSerializer(serializers.ModelSerializer):
    shipment_status = serializers.CharField(
                                        source='get_shipment_status_display')
    order = serializers.SlugRelatedField(read_only=True, slug_field='order_no')
    cash_to_be_collected = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_cash_to_be_collected(self, obj):
        return obj.cash_to_be_collected()

    class Meta:
        model = OrderedProduct
        fields = ('pk', 'trip', 'order', 'shipment_status', 'invoice_no',
                  'shipment_address', 'invoice_city', 'invoice_amount',
                  'created_at', 'cash_to_be_collected')
        read_only_fields = ('shipment_address', 'invoice_city', 'invoice_amount', 'cash_to_be_collected')

class FeedBackSerializer(serializers.ModelSerializer):

    class Meta:
        model = Feedback
        fields = ('user', 'shipment', 'delivery_experience', 'overall_product_packaging', 'comment', 'status')
        extra_kwargs = {'status': {'required': True}, 'user':{'required':False}}


class CancelOrderSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(required=True)
    order_status = serializers.HiddenField(default='CANCELLED')

    class Meta:
        model = Order
        fields = ('order_id', 'order_status')

    def validate(self, data):
        order = self.context.get('order')
        if order.order_status == 'CANCELLED':
            raise serializers.ValidationError(_('This order is already cancelled!'),)
        shipments_data = list(order.rt_order_order_product.values(
            'id', 'shipment_status', 'trip__trip_status'))
        if len(shipments_data) == 1:
            # last shipment
            s = shipments_data[-1]
            if (s['shipment_status'] not in [i[0] for i in OrderedProduct.SHIPMENT_STATUS[:3]]):
                raise serializers.ValidationError(
                    _('Sorry! This order cannot be cancelled'),)
            elif (s['trip__trip_status'] and s['trip__trip_status'] != 'READY'):
                raise serializers.ValidationError(
                    _('Sorry! This order cannot be cancelled'),)
        elif len(shipments_data) > 1:
            status = [x[0] for x in OrderedProduct.SHIPMENT_STATUS[1:]
                      if x[0] in [x['shipment_status'] for x in shipments_data]]
            if status:
                raise serializers.ValidationError(
                    _('Sorry! This order cannot be cancelled'),)
        return data

class ShipmentOrderSerializer(serializers.ModelSerializer):
    ordered_by = UserSerializer()
    shipping_address = AddressSerializer()

    class Meta:
        model=Order
        fields = ('buyer_shop', 'shipping_address', 'ordered_by')


class ShipmentSerializer(serializers.ModelSerializer):
    shipment_id = serializers.ReadOnlyField()
    order = ShipmentOrderSerializer()
    class Meta:
        model = OrderedProduct
        fields = ('shipment_id', 'invoice_no', 'shipment_status', 'payment_mode', 'invoice_amount', 'order')


class ShipmentStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderedProduct
        fields = ('shipment_status',)


class ShipmentDetailSerializer(serializers.ModelSerializer):
    ordered_product_status = serializers.ReadOnlyField()
    product_short_description = serializers.ReadOnlyField()
    mrp = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    price_to_retailer = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    #cash_discount = serializers.ReadOnlyField()
    #loyalty_incentive = serializers.ReadOnlyField()
    #margin = serializers.ReadOnlyField()
    product_image = serializers.SerializerMethodField()

    def get_product_image(self, obj):
        return obj.product.product_pro_image.last().image.url if obj.product.product_pro_image.last() else ''

    class Meta:
        model = RetailerOrderedProductMapping
        fields = ('ordered_product', 'ordered_product_status', 'product', 'product_short_description', 'mrp','price_to_retailer',
                  #'cash_discount', 'loyalty_incentive', 'margin',
                  'shipped_qty',  'returned_qty','damaged_qty', 'product_image')

class TripSerializer(serializers.ModelSerializer):
    trip_id = serializers.ReadOnlyField()
    total_trip_amount = serializers.SerializerMethodField()
    trip_return_amount = serializers.SerializerMethodField()
    cash_to_be_collected = serializers.SerializerMethodField()
    no_of_shipments = serializers.ReadOnlyField()
    trip_status = serializers.CharField(
                                        source='get_trip_status_display')

    def get_total_trip_amount(self, obj):
        return obj.total_trip_amount()

    def get_cash_to_be_collected(self, obj):
        return obj.cash_collected_by_delivery_boy()

    def get_trip_return_amount(self, obj):
        return round(float(obj.total_trip_amount()) - float(obj.cash_to_be_collected()),2)

    class Meta:
        model = Trip
        fields = ('trip_id','dispatch_no', 'trip_status', 'no_of_shipments', 'total_trip_amount', 'cash_to_be_collected','trip_return_amount')


class RetailerShopSerializer(serializers.ModelSerializer):
    shop_owner = UserSerializer()
    shipping_address = AddressSerializer()
    class Meta:
        model = Shop
        fields = ('shop_name', 'shipping_address', 'shop_owner', 'shop_type', 'related_users', 'status')


"""
Seller Order List Start
Created Date : 22/07/2019
By : Mukesh Kumar
"""

class SellerProductsSearchListSerializer(serializers.ModelSerializer):
    product_case_size_picies = serializers.SerializerMethodField('product_case_size_picies_dt')

    def product_case_size_picies_dt(self,obj):
        return str(int(obj.product_inner_case_size)*int(obj.product_case_size))

    class Meta:
        model = Product
        fields = ('id','product_name','product_sku','product_inner_case_size','product_case_size', 'product_case_size_picies')

class SellerCartProductMappingListSerializer(serializers.ModelSerializer):
    cart_product = SellerProductsSearchListSerializer()
    no_of_pieces = serializers.SerializerMethodField('no_pieces_dt')
    product_sub_total = serializers.SerializerMethodField('product_sub_total_dt')
    product_inner_case_size = serializers.SerializerMethodField('product_inner_case_size_dt')
    cart_product_price = CartProductListPrice()

    def no_pieces_dt(self, obj):
        return int(obj.no_of_pieces)

    def product_sub_total_dt(self,obj):
        return float(obj.no_of_pieces) * float(obj.cart_product_price.price_to_retailer)

    def product_inner_case_size_dt(self,obj):
        return int(int(obj.no_of_pieces) // int(obj.qty))

    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product','qty','qty_error_msg','no_of_pieces','product_sub_total', 'cart_product_price', 'product_inner_case_size')

class SellerOrderedCartListSerializer(serializers.ModelSerializer):
    rt_cart_list = SellerCartProductMappingListSerializer(many=True)
    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','rt_cart_list')

class SellerOrderListSerializer(serializers.ModelSerializer):
    ordered_cart = SellerOrderedCartListSerializer()
    order_status = serializers.CharField(source='get_order_status_display')
    rt_order_order_product = serializers.SerializerMethodField()
    is_ordered_by_sales = serializers.SerializerMethodField('is_ordered_by_sales_dt')
    shop_name = serializers.SerializerMethodField('shop_name_dt')
    shop_id = serializers.SerializerMethodField('shop_id_dt')

    def get_rt_order_order_product(self, obj):
        qs = OrderedProduct.objects.filter(order_id=obj.id).exclude(shipment_status='SHIPMENT_CREATED')
        serializer = ListOrderedProductSerializer(instance=qs, many=True)
        return serializer.data

    def to_representation(self, instance):
        representation = super(SellerOrderListSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        return representation

    def is_ordered_by_sales_dt(self, obj):
        qs = self.context.get('sales_person_list')
        return obj.ordered_by.id in qs

    def shop_name_dt(self, obj):
        return obj.buyer_shop.shop_name

    def shop_id_dt(self, obj):
        return obj.buyer_shop.id

    class Meta:
        model= Order
        fields = ('id', 'ordered_cart', 'order_no', 'total_final_amount', 'order_status',
                  'created_at', 'modified_at', 'rt_order_order_product', 'is_ordered_by_sales', 'shop_name','shop_id')

class ShipmentReschedulingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentRescheduling
        fields = ('shipment', 'rescheduling_reason', 'rescheduling_date')

class ShipmentReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderedProduct
        fields = ('id', 'return_reason')
