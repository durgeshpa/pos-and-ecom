import logging
import math
import datetime

from django.db import transaction
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.db.models import Sum, Q, F
from decimal import Decimal
from rest_framework import serializers

from accounts.models import UserWithName
from pos.models import PaymentType
from addresses.models import Address, Pincode, City
from products.models import (Product, ProductPrice, ProductImage, Tax, ProductTaxMapping, ProductOption, Size, Color,
                             Fragrance, Flavor, Weight, PackageSize, ParentProductImage, SlabProductPrice, PriceSlab)
from retailer_to_sp.common_validators import validate_shipment_crates_list, validate_shipment_package_list
from retailer_to_sp.models import (CartProductMapping, Cart, Order, OrderedProduct, Note, CustomerCare, Payment,
                                   Dispatch, Feedback, OrderedProductMapping as RetailerOrderedProductMapping,
                                   Trip, PickerDashboard, ShipmentRescheduling, OrderedProductBatch, ShipmentPackaging,
                                   ShipmentPackagingMapping, ShipmentNotAttempt)

from retailer_to_gram.models import (Cart as GramMappedCart, CartProductMapping as GramMappedCartProductMapping,
                                     Order as GramMappedOrder, OrderedProduct as GramMappedOrderedProduct,
                                     Payment as GramMappedPayment)
from pos.models import Payment as PosPayment
from coupon.models import Coupon
from sp_to_gram.models import OrderedProductMapping
from gram_to_brand.models import GRNOrderProductMapping
from shops.models import Shop, ShopTiming
from accounts.api.v1.serializers import UserSerializer
from addresses.api.v1.serializers import AddressSerializer
from coupon.serializers import CouponSerializer
from wms.api.v2.serializers import QCDeskSerializer, QCAreaSerializer
from wms.common_functions import release_picking_crates, send_update_to_qcdesk
from wms.models import Crate

User = get_user_model()

info_logger = logging.getLogger('file-info')


class PickerDashboardSerializer(serializers.ModelSerializer):
   class Meta:
      model = PickerDashboard
      fields = '__all__'


class ProductImageSerializer(serializers.ModelSerializer):
   class Meta:
      model = ProductImage
      fields = '__all__'


class ParentProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentProductImage
        fields = '__all__'


class ProductPriceSerializer(serializers.ModelSerializer):
   class Meta:
      model = ProductPrice
      fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()
    product_brand = serializers.SerializerMethodField()

    def get_product_image(self, obj):
        if ProductImage.objects.filter(product=obj).exists():
            product_image = ProductImage.objects.filter(product=obj)[0].image.url
            return product_image
        else:
            return None

    def get_product_brand(self, obj):
        return obj.product_brand.brand_name

    class Meta:
        model = Product
        ref_name = "Product v1"
        fields = ('id', 'product_sku', 'product_name', 'product_brand', 'product_inner_case_size', 'product_case_size',
                  'product_image', 'product_mrp', 'product_ean_code')

class OrderedProductMappingSerializer(serializers.ModelSerializer):
    # This serializer is used to fetch the products for a shipment
    product = ProductSerializer()
    product_price = serializers.SerializerMethodField()
    product_total_price = serializers.SerializerMethodField()

    #ordered_product = ReadOrderedProductSerializer()

    def get_product_price(self, obj):
        """
        Get effective product price per piece from OrderedProductMapping instance if available,
        else get the price instance from CartProductMapping and calculate effective price applicable per piece based on shipped quantity
        """

        if obj.effective_price:
            return obj.effective_price

        cart_product_mapping = CartProductMapping.objects.filter(cart_product=obj.product, cart=obj.ordered_product.order.ordered_cart).last()
        if cart_product_mapping and cart_product_mapping.cart_product_price:
            cart_product_price = cart_product_mapping.cart_product_price
            cart_product_case_size = cart_product_mapping.no_of_pieces/cart_product_mapping.qty
            shipped_qty_in_pack = math.ceil(obj.shipped_qty / cart_product_case_size)
            self.product_price = round(cart_product_price.get_per_piece_price(shipped_qty_in_pack), 2)
            return self.product_price
        else :
            return 0

    def get_product_total_price(self, obj):
        self.product_total_price = obj.effective_price * obj.shipped_qty
        return round(self.product_total_price,2)

    class Meta:
        model = RetailerOrderedProductMapping
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
    shipment_status = serializers.SerializerMethodField()
    order_status = serializers.SerializerMethodField()

    def get_shipment_status(self, obj):
        return obj.get_shipment_status_display()

    def get_order_status(self, obj):
        return obj.order.get_order_status_display()

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
        fields = ('id','invoice_no','shipment_status','invoice_amount', 'order_status',
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


class PriceSlabSerializer(serializers.ModelSerializer):

    ptr = serializers.SerializerMethodField('m_ptr')
    margin = serializers.SerializerMethodField('m_margin')

    def m_ptr(self, obj):
        return obj.ptr

    def m_margin(self, obj):
        return round(100 * ((float(obj.product_price.mrp) - obj.ptr)/float(obj.product_price.mrp)), 2)

    class Meta:
        model = PriceSlab
        fields = ('start_value', 'end_value', 'ptr', 'margin')

class SlabProductPriceSerializer(serializers.ModelSerializer):
    mrp = serializers.SerializerMethodField()
    product_price = serializers.SerializerMethodField()
    price_slabs = PriceSlabSerializer(many=True)

    def get_mrp(self, obj):
        return obj.mrp if obj.mrp else obj.product.product_mrp

    def get_product_price(self, obj):
        return obj.get_per_piece_price(self.context.get('qty', 1))

    class Meta:
        model = SlabProductPrice
        fields = ('mrp', 'product_price', 'price_slabs',)


class ProductsSearchSerializer(serializers.ModelSerializer):
    #product_pro_price = ProductPriceSerializer(many=True)
    product_pro_image = ProductImageSerializer(many=True)
    #product_pro_tax = ProductTaxMappingSerializer(many=True)
    product_opt_product = ProductOptionSerializer(many=True)
    #product_brand = BrandSerializer(read_only=True)
    product_price = serializers.SerializerMethodField('product_price_dt')
    per_piece_price = serializers.SerializerMethodField('m_per_piece_price')
    price_details = serializers.SerializerMethodField('m_slab_price')
    product_mrp = serializers.SerializerMethodField('product_mrp_dt')
    product_case_size_picies = serializers.SerializerMethodField('product_case_size_picies_dt')
    margin = serializers.SerializerMethodField('margin_dt')
    loyalty_discount = serializers.SerializerMethodField('loyalty_discount_dt')
    cash_discount = serializers.SerializerMethodField('cash_discount_dt')

    def m_slab_price(self, obj):
        product_price = obj.get_current_shop_price(self.context.get('parent_mapping_id'),
                                                   self.context.get('buyer_shop_id'))
        serializer = SlabProductPriceSerializer(product_price, context=self.context)
        return serializer.data

    def product_price_dt(self, obj):
        current_price = obj.get_current_shop_price(self.context.get('parent_mapping_id'), self.context.get('buyer_shop_id'))
        if current_price:
            self.product_price = current_price.get_applicable_slab_price_per_pack(self.context.get('qty', 1),
                                                                                  obj.product_inner_case_size)
            return ("%.2f" % round(self.product_price, 2))

    def m_per_piece_price(self, obj):
        return round(self.product_price/obj.product_inner_case_size, 2)

    def product_mrp_dt(self, obj):
        self.product_mrp = obj.getMRP(
            self.context.get('parent_mapping_id'),
            self.context.get('buyer_shop_id'))
        return self.product_mrp

    def product_case_size_picies_dt(self, obj):
        return str(int(obj.product_inner_case_size)*int(obj.product_case_size))

    def loyalty_discount_dt(self, obj):
        self.loyalty_discount = obj.getLoyaltyIncentive(
            self.context.get('parent_mapping_id'),
            self.context.get('buyer_shop_id'))
        return self.loyalty_discount

    def cash_discount_dt(self, obj):
        self.cash_discount = obj.getCashDiscount(
            self.context.get('parent_mapping_id'),
            self.context.get('buyer_shop_id'))
        return self.cash_discount

    def margin_dt(self, obj):
        if self.product_mrp:
            return round((((float(self.product_mrp) - float(self.product_price)/int(obj.product_inner_case_size)) / float(self.product_mrp)) * 100), 2)
        return False



    class Meta:
        model = Product
        fields = ('id','product_name','product_slug','product_short_description','product_long_description',
                  'product_sku','product_mrp', 'price_details', 'product_price', 'per_piece_price',
                  'product_ean_code','created_at','updated_at','status','product_pro_image', 'product_opt_product',
                  'product_inner_case_size', 'product_case_size','product_case_size_picies', 'margin',
                  'loyalty_discount', 'cash_discount')

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
    # cart_product = ProductsSearchSerializer()
    cart_product = serializers.SerializerMethodField('m_cart_product')
    cart = CartDataSerializer()
    is_available = serializers.SerializerMethodField('is_available_dt')
    no_of_pieces = serializers.SerializerMethodField('no_pieces_dt')
    product_sub_total = serializers.SerializerMethodField('product_sub_total_dt')
    product_coupons = serializers.SerializerMethodField('product_coupons_dt')
    margin = serializers.SerializerMethodField('margin_dt')
    qty = serializers.SerializerMethodField('qty_dt')

    def m_cart_product(self, obj):
        self.context['qty'] = abs(obj.qty)
        serializer = ProductsSearchSerializer(obj.cart_product, context=self.context)
        return serializer.data

    def is_available_dt(self,obj):
        """
            Check is quantity of product is available
        """
        ordered_product_sum = OrderedProductMapping.objects.filter(product=obj.cart_product).aggregate(available_qty_sum=Sum('available_qty'))
        self.is_available = True if ordered_product_sum['available_qty_sum'] and int(ordered_product_sum['available_qty_sum'])>0 else False
        return self.is_available

    def no_pieces_dt(self, obj):
        """
            No of pieces of Product
        """
        return int(obj.cart_product.product_inner_case_size) * int(obj.qty)

    def product_sub_total_dt(self, obj):
        product_price = obj.cart_product.get_current_shop_price(self.context.get('parent_mapping_id'), self.context.get('buyer_shop_id'))
        price_per_piece = product_price.get_per_piece_price(obj.qty)
        return round(Decimal(Decimal(price_per_piece) * Decimal(obj.no_of_pieces)), 2)

    def product_coupons_dt(self, obj):
        """
            Coupons for a product
        """
        product_coupons = []
        date = datetime.datetime.now()
        for rules in obj.cart_product.purchased_product_coupon.filter(rule__is_active = True, rule__expiry_date__gte = date).\
                exclude(rule__coupon_ruleset__shop__shop_type__shop_type='f'):
            for rule in rules.rule.coupon_ruleset.filter(is_active=True, expiry_date__gte = date).exclude(shop__shop_type__shop_type='f'):
                product_coupons.append(rule.coupon_code)
        parent_product_brand = obj.cart_product.parent_product.parent_brand if obj.cart_product.parent_product else None
        if parent_product_brand:
            parent_brand = parent_product_brand.brand_parent.id if parent_product_brand.brand_parent else None
        else:
            parent_brand = None
        product_brand_id = obj.cart_product.parent_product.parent_brand.id if obj.cart_product.parent_product else None
        brand_coupons = Coupon.objects.filter(coupon_type = 'brand', is_active = True, expiry_date__gte = date).filter(Q(rule__brand_ruleset__brand = product_brand_id)| Q(rule__brand_ruleset__brand = parent_brand)).order_by('rule__cart_qualifying_min_sku_value')
        for x in brand_coupons:
            product_coupons.append(x.coupon_code)
        if product_coupons:
            coupons_queryset1 = Coupon.objects.filter(coupon_code__in = product_coupons, coupon_type='catalog')
            coupons_queryset2 = Coupon.objects.filter(coupon_code__in = product_coupons, coupon_type='brand').order_by('rule__cart_qualifying_min_sku_value')
            coupons_queryset = coupons_queryset1 | coupons_queryset2
            coupons = CouponSerializer(coupons_queryset, many=True).data
            for coupon in coupons_queryset:
                for product_coupon in coupon.rule.product_ruleset.filter(purchased_product = obj.cart_product):
                    if product_coupon.max_qty_per_use > 0:
                        max_qty = product_coupon.max_qty_per_use
                        for i in coupons:
                            if i['coupon_type'] == 'catalog':
                                i['max_qty'] = max_qty
            product_offers = list(filter(lambda d: d['sub_type'] in ['discount_on_product'], obj.cart.offers))
            brand_offers = list(filter(lambda d: d['sub_type'] in ['discount_on_brand'], obj.cart.offers))
            for j in coupons:
                for i in (product_offers + brand_offers):
                    if j['coupon_code'] == i['coupon_code']:
                        j['is_applied'] = True
            return coupons

    def margin_dt(self, obj):
        """
            Mrp, selling price margin
        """
        product_price = obj.cart_product.\
            get_current_shop_price(self.context.get('parent_mapping_id'),
                             self.context.get('buyer_shop_id'))
        if product_price:
            product_mrp = product_price.mrp if product_price.mrp else obj.cart_product.product_mrp
            margin = (((float(product_mrp) - product_price.get_per_piece_price(obj.qty)) / float(product_mrp)) * 100)
            if obj.cart.offers:
                margin = (((float(product_mrp) - obj.item_effective_prices) / float(product_mrp)) * 100)
            return round(margin, 2)
        return False

    def qty_dt(self, obj):
        return abs(obj.qty)

    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty','qty_error_msg', 'capping_error_msg', 'is_available',
                  'no_of_pieces','product_sub_total', 'product_coupons', 'margin')


class CartSerializer(serializers.ModelSerializer):
    rt_cart_list = serializers.SerializerMethodField('rt_cart_list_dt')
    last_modified_by = UserSerializer()
    items_count = serializers.SerializerMethodField('items_count_id')
    total_amount = serializers.SerializerMethodField('total_amount_id')
    total_discount = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField('sub_total_id')
    delivery_msg = serializers.SerializerMethodField()
    discounted_prices_sum = serializers.SerializerMethodField()
    shop_min_amount = serializers.SerializerMethodField('shop_min_amount_id')

    class Meta:
        model = Cart
        fields = ('id', 'order_id', 'cart_status', 'last_modified_by',
                  'created_at', 'modified_at', 'rt_cart_list', 'total_amount', 'shop_min_amount',
                  'total_discount', 'sub_total', 'discounted_prices_sum', 'items_count', 'delivery_msg', 'offers',)

    def rt_cart_list_dt(self, obj):
        """
         Search and pagination on cart
        """
        qs = CartProductMapping.objects.filter(cart=obj)
        search_text = self.context.get('search_text')
        # Search on name, ean and sku
        if search_text:
            qs = qs.filter(Q(cart_product__product_sku__icontains=search_text)
                              | Q(cart_product__product_name__icontains=search_text)
                              | Q(cart_product__product_ean_code__icontains=search_text))
        # Pagination
        # if qs.exists() and self.context.get('request'):
        #     qs = SmallOffsetPagination().paginate_queryset(qs, self.context.get('request'))

        return CartProductMappingSerializer(qs, many=True, context=self.context).data

    def get_discounted_prices_sum(self, obj):
        sum = 0

        keyValList1 = ['catalog']
        if obj.offers:
            exampleSet1 = obj.offers
            array1 = list(filter(lambda d: d['coupon_type'] in keyValList1, exampleSet1))
            for i in array1:
                sum = sum + round(i['discounted_product_subtotal'], 2)
        return round(sum, 2)

    def get_total_discount(self, obj):
        sum = 0
        keyValList1 = ['discount']
        if obj.offers:
            exampleSet1 = obj.offers
            array1 = list(filter(lambda d: d['type'] in keyValList1, exampleSet1))
            for i in array1:
                sum = sum + i['discount_value']
        return round(sum, 2)

    def total_amount_id(self, obj):
        self.total_amount = 0
        self.items_count = 0
        for cart_pro in obj.rt_cart_list.all():
            self.items_count = self.items_count + int(cart_pro.qty)
            pro_price = cart_pro.cart_product.get_current_shop_price(self.context.get('parent_mapping_id'),
                                                                     self.context.get('buyer_shop_id'))
            if pro_price:
                self.total_amount += Decimal(pro_price.get_per_piece_price(cart_pro.qty)) * Decimal(cart_pro.no_of_pieces)
        return self.total_amount

    def shop_min_amount_id(self, obj):
        return round(obj.seller_shop.shop_type.shop_min_amount,2)

    def sub_total_id(self, obj):
        sub_total = float(self.total_amount_id(obj)) - self.get_total_discount(obj)
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
    shipment_status = serializers.SerializerMethodField()

    def get_shipment_status(self, obj):
        return obj.get_shipment_status_display()

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
        return obj.selling_price

    def product_mrp_dt(self,obj):
        return obj.product.product_mrp

    class Meta:
        model = ProductPrice
        fields = ('id','product_price','product_mrp','created_at')

# Order Details Related Serializer Start
class ProductsSerializer(serializers.ModelSerializer):
    product_pro_image = ProductImageSerializer(many=True)
    product_opt_product = ProductOptionSerializer(many=True)
    product_case_size_picies = serializers.SerializerMethodField('product_case_size_picies_dt')

    def product_case_size_picies_dt(self, obj):
        return str(int(obj.product_inner_case_size)*int(obj.product_case_size))

    class Meta:
        model = Product
        fields = ('id','product_name','product_slug','product_short_description','product_long_description','product_sku',
                  'product_ean_code','created_at','updated_at','status','product_pro_image',
                  'product_opt_product', 'product_case_size_picies',
                  #'product_price','product_inner_case_size','product_case_size','margin', 'loyalty_discount', 'cash_discount'
         )


class OrderedCartProductMappingSerializer(serializers.ModelSerializer):
    cart_product = ProductsSerializer()
    # cart_product_price = SlabProductPriceSerializer()
    cart_product_price = serializers.SerializerMethodField()
    no_of_pieces = serializers.SerializerMethodField('no_pieces_dt')
    qty = serializers.SerializerMethodField('qty_dt')
    product_sub_total = serializers.SerializerMethodField('product_sub_total_dt')
    product_inner_case_size = serializers.SerializerMethodField('product_inner_case_size_dt')
    product_price = serializers.SerializerMethodField()

    def get_cart_product_price(self, obj):
        product_price = obj.get_cart_product_price(self.context.get('parent_mapping_id'),
                                                   self.context.get('buyer_shop_id'))
        self.context['qty'] = obj.qty
        serializer = SlabProductPriceSerializer(product_price, context=self.context)
        return serializer.data

    def no_pieces_dt(self, obj):
        return int(obj.no_of_pieces)

    def qty_dt(self, obj):
        return int(obj.qty)

    def get_product_price(self,obj):
        return obj.get_cart_product_price(self.context.get('parent_mapping_id'), self.context.get('buyer_shop_id'))\
                  .get_per_piece_price(obj.qty)

    def product_sub_total_dt(self,obj):
        product_price = obj.get_cart_product_price(self.context.get('parent_mapping_id'), self.context.get('buyer_shop_id'))
        price_per_piece = product_price.get_per_piece_price(obj.qty)
        return round((Decimal(price_per_piece) * Decimal(obj.no_of_pieces)), 2)

    def product_inner_case_size_dt(self,obj):
        return int(int(obj.no_of_pieces) // int(obj.qty))


    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty','qty_error_msg','no_of_pieces','product_sub_total',
                  'cart_product_price','product_inner_case_size', 'product_price')


class OrderedCartSerializer(serializers.ModelSerializer):
    rt_cart_list = OrderedCartProductMappingSerializer(many=True)
    items_count = serializers.SerializerMethodField('items_count_id')
    total_amount = serializers.SerializerMethodField('total_amount_id')
    total_discount = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField('sub_total_id')

    def get_total_discount(self, obj):
        sum = 0
        keyValList1 = ['discount']
        if obj.offers:
            exampleSet1 = obj.offers
            array1 = list(filter(lambda d: d['type'] in keyValList1, exampleSet1))
            for i in array1:
                sum = sum + i['discount_value']
        return round(sum, 2)

    def total_amount_id(self, obj):
        try:
            self.total_amount = 0
            self.items_count = 0
            total_discount = self.get_total_discount(obj)
            for cart_pro in obj.rt_cart_list.all():
                self.items_count = self.items_count + int(cart_pro.qty)
                pro_price = cart_pro.get_cart_product_price(self.context.get('parent_mapping_id'),
                                                            self.context.get('buyer_shop_id'))
                self.total_amount += pro_price.get_per_piece_price(cart_pro.qty) * cart_pro.no_of_pieces
            return self.total_amount
        except:
            return obj.subtotal

    def sub_total_id(self, obj):
        if self.total_amount_id(obj) is None:
            sub_total = 0 - self.get_total_discount(obj)
        else:
            sub_total = float(self.total_amount_id(obj)) - self.get_total_discount(obj)
        return round(sub_total, 2)

    def items_count_id(self, obj):
        return obj.rt_cart_list.count()

    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','created_at','modified_at','rt_cart_list','total_amount','sub_total','items_count', 'offers', 'total_discount')


#Order Details
class OrderDetailSerializer(serializers.ModelSerializer):
    ordered_cart = OrderedCartSerializer()
    rt_order_order_product = OrderedProductSerializer(many=True)
    shipping_address = AddressSerializer()
    order_status = serializers.CharField(source='get_order_status_display')

    def to_representation(self, instance):
        representation = super(OrderDetailSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        shipment = instance.rt_order_order_product.last()
        if shipment:
            representation['shipment_status'] = shipment.shipment_status
        return representation

    class Meta:
        model=Order
        fields = ('id','ordered_cart','order_no','shipping_address','total_mrp','total_discount_amount',
                  'total_tax_amount','total_final_amount','order_status','received_by',
                  'created_at','modified_at','rt_order_order_product')

# Order Details Related Serializer End

# Order List Related Serializer Start

class ProductsSearchListSerializer(serializers.ModelSerializer):
    product_case_size_picies = serializers.SerializerMethodField('product_case_size_picies_dt')

    def product_case_size_picies_dt(self,obj):
        return str(int(obj.product_inner_case_size)*int(obj.product_case_size))

    class Meta:
        model = Product
        fields = ('id', 'product_name', 'product_sku', 'product_inner_case_size', 'product_case_size', 'product_case_size_picies')


class CartProductListPrice(serializers.ModelSerializer):
    product_price = serializers.SerializerMethodField('product_price_dt')
    product_mrp = serializers.SerializerMethodField('product_mrp_dt')

    def product_price_dt(self,obj):
        return obj.selling_price

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

    def product_sub_total_dt(self, obj):
        product_price = obj.get_cart_product_price(self.context.get('parent_mapping_id'),
                                                   self.context.get('buyer_shop_id'))
        price_per_piece = Decimal(product_price.get_per_piece_price(obj.qty))
        return round((price_per_piece * obj.no_of_pieces), 2)

    def product_inner_case_size_dt(self, obj):
        try:
            return int(int(obj.no_of_pieces) // int(obj.qty))
        except:
            return int(obj.no_of_pieces)

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
    shipment_status = serializers.SerializerMethodField()

    def get_shipment_status(self, obj):
        shipment_status_obj = OrderedProduct.objects.filter(order__id=obj.id)
        if shipment_status_obj:
            return shipment_status_obj.last().get_shipment_status_display()
        return ""

    def get_rt_order_order_product(self, obj):
        qs = OrderedProduct.objects.filter(order_id=obj.id).exclude(shipment_status='SHIPMENT_CREATED')
        serializer = ListOrderedProductSerializer(instance=qs, many=True)
        return serializer.data

    def to_representation(self, instance):
        representation = super(OrderListSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        shipment = instance.rt_order_order_product.last()
        if shipment:
            representation['shipment_status'] = shipment.shipment_status
        return representation

    class Meta:
        model=Order
        fields = ('id','ordered_cart','order_no','total_final_amount','order_status', 'shipment_status','shipping_address',
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
    shipment_status = serializers.SerializerMethodField()

    def get_shipment_status(self, obj):
        shipment_status_obj = OrderedProduct.objects.filter(order__id=obj.id)
        if shipment_status_obj:
            return shipment_status_obj.last().get_shipment_status_display()
        return ""

    def to_representation(self, instance):
        representation = super(GramMappedOrderSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        return representation

    class Meta:
        model = GramMappedOrder
        fields = ('id','ordered_cart','order_no','billing_address','shipping_address','total_mrp','total_discount_amount',
                  'total_tax_amount','total_final_amount','order_status', 'shipment_status','ordered_by','received_by','last_modified_by',
                  'created_at','modified_at','rt_order_order_product')


# class DispatchSerializer(serializers.ModelSerializer):


#     class Meta:
#         model = Dispatch
#         fields = '__all__'

class DispatchSerializer(serializers.ModelSerializer):
    shipment_status = serializers.CharField(
                                        source='get_shipment_status_display')
    order = serializers.SlugRelatedField(read_only=True, slug_field='order_no')
    shipment_weight = serializers.SerializerMethodField()
    payment_approval_status = serializers.SerializerMethodField()
    online_payment_approval_status = serializers.SerializerMethodField()

    created_at = serializers.DateTimeField()
    shipment_payment = serializers.SerializerMethodField()
    trip_status = serializers.SerializerMethodField()
    discounted_credit_note = serializers.SerializerMethodField()
    discounted_credit_note_pk = serializers.SerializerMethodField()

    def get_trip_status(self, obj):
        if obj.trip:
            return obj.trip.trip_status

    def get_payment_approval_status(self, obj):
        return obj.payment_approval_status()

    def get_online_payment_approval_status(self, obj):
        return obj.online_payment_approval_status()


    def get_shipment_payment(self, obj):
        return ""
        # from payments.models import Payment as InvoicePayment
        # payment_data = {}
        # payment = InvoicePayment.objects.filter(shipment=obj)
        # if payment.exists():
        #     payment_data = payment.values('paid_amount', 'reference_no', 'description', 'payment_mode_name')

        # return payment_data

    def shipment_weight(self, obj):
        return obj.shipment_weight

    def get_discounted_credit_note_pk(self, obj):
        if obj.order.ordered_cart.cart_type == 'DISCOUNTED':
            if obj.credit_note.filter(credit_note_type = 'DISCOUNTED').exists():
                return obj.credit_note.filter(credit_note_type = 'DISCOUNTED').first().id
        else:
            return "-"

    def get_discounted_credit_note(self, obj):
        if obj.order.ordered_cart.cart_type == 'DISCOUNTED':
            if obj.credit_note.filter(credit_note_type = 'DISCOUNTED').exists():
                return obj.credit_note.filter(credit_note_type = 'DISCOUNTED').first().credit_note_id
        else:
            return "-"

    class Meta:
        model = Dispatch
        fields = ('pk', 'trip', 'order', 'shipment_status', 'invoice_no',
                  'shipment_address', 'invoice_city', 'invoice_amount',
                  'created_at', 'shipment_weight','shipment_payment', 'trip_status',
                  'payment_approval_status', 'online_payment_approval_status', 'discounted_credit_note', 'discounted_credit_note_pk')
        read_only_fields = ('shipment_address', 'invoice_city', 'invoice_amount',
                 'shipment_payment', 'trip_status', 'shipment_weight',
                 'payment_approval_status', 'online_payment_approval_status',
                 'invoice_no', 'discounted_credit_note', 'discounted_credit_note_pk')



class CommercialShipmentSerializer(serializers.ModelSerializer):
    shipment_status = serializers.CharField(
                                        source='get_shipment_status_display')
    order = serializers.SlugRelatedField(read_only=True, slug_field='order_no')
    cash_to_be_collected = serializers.SerializerMethodField()
    shipment_weight = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    shipment_payment = serializers.SerializerMethodField()
    payment_approval_status = serializers.SerializerMethodField()
    online_payment_approval_status = serializers.SerializerMethodField()
    trip_status = serializers.SerializerMethodField()
    paid_amount_shipment = serializers.SerializerMethodField()
    discounted_credit_note = serializers.SerializerMethodField()
    discounted_credit_note_pk = serializers.SerializerMethodField()

    def get_trip_status(self, obj):
        if obj.trip:
            return obj.trip.trip_status

    def get_paid_amount_shipment(self, obj):
        if obj.total_paid_amount:
            return obj.total_paid_amount
        else:
            return 0

    def get_payment_approval_status(self, obj):
        return obj.payment_approval_status()

    def get_online_payment_approval_status(self, obj):
        return obj.online_payment_approval_status()

    def get_shipment_payment(self, obj):
        return ""

    def shipment_weight(self, obj):
        return obj.shipment_weight

    def get_cash_to_be_collected(self, obj):
        return obj.cash_to_be_collected()

    def get_discounted_credit_note_pk(self, obj):
        if obj.order.ordered_cart.cart_type == 'DISCOUNTED':
            if obj.credit_note.filter(credit_note_type = 'DISCOUNTED').exists():
                return obj.credit_note.filter(credit_note_type = 'DISCOUNTED').first().id
        else:
            return "-"

    def get_discounted_credit_note(self, obj):
        if obj.order.ordered_cart.cart_type == 'DISCOUNTED':
            if obj.credit_note.filter(credit_note_type = 'DISCOUNTED').exists():
                return obj.credit_note.filter(credit_note_type = 'DISCOUNTED').first().credit_note_id
        else:
            return "-"

    class Meta:
        model = OrderedProduct
        fields = ('pk', 'trip', 'order', 'shipment_status', 'invoice_no',
                  'shipment_address', 'invoice_city', 'invoice_amount',
                  'created_at', 'cash_to_be_collected', 'shipment_payment',
                   'trip_status', 'paid_amount_shipment', 'shipment_weight',
                   'payment_approval_status', 'online_payment_approval_status', 'discounted_credit_note', 'discounted_credit_note_pk')
        read_only_fields = ('shipment_address', 'invoice_city', 'invoice_amount',
                    'cash_to_be_collected', 'shipment_payment', 'trip_status',
                     'paid_amount_shipment', 'shipment_weight', 'payment_approval_status',
                     'online_payment_approval_status', 'invoice_no', 'discounted_credit_note', 'discounted_credit_note_pk')


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
        raise serializers.ValidationError(_('Sorry! This order cannot be cancelled'),)
        order = self.context.get('order')
        if order.order_status == 'CANCELLED':
            raise serializers.ValidationError(_('This order is already cancelled!'),)
        if order.order_status == Order.COMPLETED:
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
    total_paid_amount = serializers.SerializerMethodField()
    order = ShipmentOrderSerializer()
    shop_open_time = serializers.SerializerMethodField()
    shop_close_time = serializers.SerializerMethodField()
    break_start_time = serializers.SerializerMethodField()
    break_end_time = serializers.SerializerMethodField()
    off_day = serializers.SerializerMethodField()
    sales_executive = serializers.SerializerMethodField()

    def get_sales_executive(self, obj):
        shop_user_mapping = obj.order.buyer_shop.shop_user.filter(status=True, employee_group__name='Sales Executive').last()
        sales_executive = None
        if shop_user_mapping:
            sales_executive = shop_user_mapping.employee
        serializer = ShopExecutiveUserSerializer(sales_executive)
        return serializer.data


    def get_total_paid_amount(self, obj):
        return obj.total_paid_amount

    def get_shop_timings(self, obj):
        shop_timing = ShopTiming.objects.filter(shop=obj.order.buyer_shop)
        if shop_timing.exists():
            final_timing = shop_timing.last()
            return [final_timing.open_timing, final_timing.closing_timing,
            final_timing.break_start_time, final_timing.break_end_time,
            final_timing.off_day]

    def get_shop_open_time(self, obj):
        shop_timings = self.get_shop_timings(obj)
        if shop_timings:
            return shop_timings[0]

    def get_shop_close_time(self, obj):
        shop_timings = self.get_shop_timings(obj)
        if shop_timings:
            return shop_timings[1]

    def get_break_start_time(self, obj):
        shop_timings = self.get_shop_timings(obj)
        if shop_timings:
            return shop_timings[2]

    def get_break_end_time(self, obj):
        shop_timings = self.get_shop_timings(obj)
        if shop_timings:
            return shop_timings[3]

    def get_off_day(self, obj):
        shop_timings = self.get_shop_timings(obj)
        if shop_timings:
            return shop_timings[4]

    class Meta:
        model = OrderedProduct
        fields = ('shipment_id', 'invoice_no', 'shipment_status', 'payment_mode', 'invoice_amount', 'order',
            'total_paid_amount', 'shop_open_time', 'shop_close_time',
            'break_start_time', 'break_end_time', 'off_day', 'sales_executive')


class ShipmentStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderedProduct
        fields = ('shipment_status',)


class ShipmentDetailSerializer(serializers.ModelSerializer):
    ordered_product_status = serializers.ReadOnlyField()
    product_short_description = serializers.ReadOnlyField()
    mrp = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    price_to_retailer = serializers.SerializerMethodField()
    #cash_discount = serializers.ReadOnlyField()
    #loyalty_incentive = serializers.ReadOnlyField()
    #margin = serializers.ReadOnlyField()
    product_image = serializers.SerializerMethodField()

    def get_product_image(self, obj):
        return obj.product.product_pro_image.last().image.url if obj.product.product_pro_image.last() else ''

    def get_price_to_retailer(self, obj):
        if obj.ordered_product.order.ordered_cart.cart_type == 'DISCOUNTED':
            if obj.discounted_price:
                return obj.discounted_price
            cart_product = obj.ordered_product.order.ordered_cart.rt_cart_list.get(cart_product=obj.product)
            return cart_product.discounted_price
        else:
            if obj.effective_price:
                return obj.effective_price

            cart_product = obj.ordered_product.order.ordered_cart.rt_cart_list.get(cart_product=obj.product)
            shipped_qty_in_pack = math.ceil(obj.shipped_qty/cart_product.cart_product_case_size)
            return cart_product.cart_product_price.get_per_piece_price(shipped_qty_in_pack)


    class Meta:
        model = RetailerOrderedProductMapping
        fields = ('ordered_product', 'ordered_product_status', 'product', 'product_short_description', 'mrp','price_to_retailer',
                  #'cash_discount', 'loyalty_incentive', 'margin',
                  'shipped_qty',  'returned_qty','returned_damage_qty', 'product_image')


class OrderHistoryUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserWithName
        fields = ('first_name', 'last_name', 'phone_number')


class OrderHistoryTripSerializer(serializers.ModelSerializer):
    dispatch_no = serializers.ReadOnlyField()
    delivery_boy = OrderHistoryUserSerializer()

    class Meta:
        model = Trip
        fields = ('dispatch_no', 'delivery_boy')


class ShopExecutiveUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'phone_number')

class TripSerializer(serializers.ModelSerializer):
    trip_id = serializers.ReadOnlyField()
    total_trip_amount = serializers.SerializerMethodField()
    trip_return_amount = serializers.SerializerMethodField()
    cash_to_be_collected = serializers.SerializerMethodField()
    no_of_shipments = serializers.ReadOnlyField()
    trip_status = serializers.CharField(
                                        source='get_trip_status_display')

    def get_total_trip_amount(self, obj):
        return obj.total_trip_amount_value #total_trip_amount()

    def get_cash_to_be_collected(self, obj):
        return obj.cash_collected_by_delivery_boy()

    def get_trip_return_amount(self, obj):
        try:
            return round(float(obj.total_trip_amount_value) - float(obj.cash_to_be_collected()),2)
        except:
            return 0


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

    def product_sub_total_dt(self, obj):
        price_per_piece = float(obj.cart_product_price.get_per_piece_price(obj.qty))
        return round((price_per_piece * float(obj.no_of_pieces)), 2)

    def product_inner_case_size_dt(self, obj):
        if int(obj.qty) == 0:
            return 0
        return int(int(obj.no_of_pieces) // int(obj.qty))

    class Meta:
        model = CartProductMapping
        fields = ('id', 'cart', 'cart_product', 'qty', 'qty_error_msg', 'no_of_pieces', 'product_sub_total',
                  'cart_product_price', 'product_inner_case_size')


class SellerOrderedCartListSerializer(serializers.ModelSerializer):
    rt_cart_list = SellerCartProductMappingListSerializer(many=True)
    class Meta:
        model = Cart
        fields = ('id','order_id','cart_status','rt_cart_list')

class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'shop_name')


class SellerOrderListSerializer(serializers.ModelSerializer):
    ordered_cart = SellerOrderedCartListSerializer()
    order_status = serializers.SerializerMethodField()
    rt_order_order_product = serializers.SerializerMethodField()
    is_ordered_by_sales = serializers.SerializerMethodField('is_ordered_by_sales_dt')
    shop_name = serializers.SerializerMethodField('shop_name_dt')
    shop_id = serializers.SerializerMethodField('shop_id_dt')
    trip_details = serializers.SerializerMethodField()
    shipment_status = serializers.SerializerMethodField()
    order_status_detail = serializers.SerializerMethodField()

    def get_shipment_status(self, obj):
        shipment_status_obj = OrderedProduct.objects.filter(order__id=obj.id)
        if shipment_status_obj:
            return shipment_status_obj.last().get_shipment_status_display()
        return ""

    def get_order_status(self, obj):
        if obj.order_status in [Order.ORDERED, Order.PICKUP_CREATED, Order.PICKING_ASSIGNED, Order.PICKING_COMPLETE,
                                Order.FULL_SHIPMENT_CREATED, Order.PARTIAL_SHIPMENT_CREATED, Order.READY_TO_DISPATCH]:
            return 'New'
        elif obj.order_status in [Order.DISPATCHED]:
            return 'In Transit'
        elif obj.order_status in [Order.PARTIAL_DELIVERED, Order.DELIVERED, Order.CLOSED, Order.COMPLETED]:
            return 'Completed'
        return obj.order_status

    def get_order_status_detail(self, obj):
        return obj.get_order_status_display()

    def get_trip_details(self, obj):
        qs = Trip.objects.filter(rt_invoice_trip__order_id=obj.id)
        serializer = OrderHistoryTripSerializer(instance=qs, many=True)
        return serializer.data

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
        fields = ('id', 'ordered_cart', 'order_no', 'total_final_amount', 'order_status', 'shipment_status',
                  'created_at', 'modified_at', 'rt_order_order_product', 'is_ordered_by_sales', 'shop_name','shop_id',
                  'trip_details', 'order_status_detail')


class ShipmentReschedulingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentRescheduling
        fields = ('shipment', 'rescheduling_reason', 'rescheduling_date')


class ShipmentNotAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentNotAttempt
        fields = ('shipment', 'not_attempt_reason',)


class ShipmentReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderedProduct
        fields = ('id', 'return_reason')


class OrderedProductBatchSerializer(serializers.ModelSerializer):
    reason_for_rejection = serializers.SerializerMethodField()
    is_crate_used_in_picking = serializers.SerializerMethodField()

    class Meta:
        model = OrderedProductBatch
        fields = ('id', 'batch_id', 'quantity', 'ordered_pieces', 'delivered_qty', 'already_shipped_qty',
                  'expiry_date', 'returned_qty', 'damaged_qty', 'returned_damage_qty', 'pickup_quantity', 'expired_qty',
                  'missing_qty', 'rejected_qty', 'reason_for_rejection', 'is_crate_used_in_picking',
                  'created_at', 'modified_at')

    @staticmethod
    def get_reason_for_rejection(obj):
        return obj.get_reason_for_rejection_display()

    @staticmethod
    def get_is_crate_used_in_picking(obj):
        return obj.rt_pickup_batch_mapping.last().pickup.pickup_crates.exists()

class CrateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crate
        fields = ('id', 'crate_id')


class ProductPackagingSerializer(serializers.ModelSerializer):
    crate = CrateSerializer()
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.get_status_display()

    class Meta:
        model = ShipmentPackaging
        fields = ('id', 'packaging_type', 'crate', 'status')


class ProductPackagingDetailsSerializer(serializers.ModelSerializer):

    shipment_packaging = ProductPackagingSerializer(read_only=True)

    class Meta:
        model = ShipmentPackagingMapping
        fields = ('quantity', 'shipment_packaging')


class RetailerOrderedProductMappingSerializer(serializers.ModelSerializer):
    # This serializer is used to fetch the products for a shipment
    product = ProductSerializer(read_only=True)
    product_price = serializers.SerializerMethodField()
    product_total_price = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()
    rt_ordered_product_mapping = OrderedProductBatchSerializer(read_only=True, many=True)
    last_modified_by = UserSerializer(read_only=True)
    shipment_product_packaging = ProductPackagingDetailsSerializer(read_only=True, many=True)

    class Meta:
        model = RetailerOrderedProductMapping
        fields = ('id', 'ordered_qty', 'shipped_qty', 'product', 'product_price', 'product_total_price', 'is_qc_done',
                  'product_type', 'selling_price', 'shipped_qty', 'delivered_qty', 'returned_qty', 'damaged_qty',
                  'returned_damage_qty', 'expired_qty', 'missing_qty', 'rejected_qty', 'last_modified_by', 'created_at',
                  'modified_at', 'effective_price', 'discounted_price', 'delivered_at_price', 'cancellation_date',
                  'picked_pieces', 'rt_ordered_product_mapping', 'shipment_product_packaging')

    def validate(self, data):

        if 'product' in self.initial_data and self.initial_data['product']:
            try:
                product = Product.objects.get(id=self.initial_data['product'])
                data['product'] = product
            except:
                raise serializers.ValidationError("Invalid product")
        else:
            raise serializers.ValidationError("'product' | This is mandatory")

        product_damaged_qty = 0
        product_expired_qty = 0
        product_missing_qty = 0
        product_rejected_qty = 0

        # Batch Validations
        if 'rt_ordered_product_mapping' not in self.initial_data or \
                not isinstance(self.initial_data['rt_ordered_product_mapping'], list) or \
                not self.initial_data['rt_ordered_product_mapping']:
            raise serializers.ValidationError("'rt_ordered_product_mapping' | This is mandatory")

        for product_batch in self.initial_data['rt_ordered_product_mapping']:
            if 'batch_id' not in product_batch or not product_batch['batch_id']:
                raise serializers.ValidationError("'batch_id' | This is mandatory.")

            if 'total_qc_qty' not in product_batch or product_batch['total_qc_qty'] is None:
                raise serializers.ValidationError("'total_qc_qty' | This is mandatory.")

            if 'rejected_qty' not in product_batch or product_batch['rejected_qty'] is None:
                raise serializers.ValidationError("'rejected_qty' | This is mandatory.")
            try:
                total_qc_qty = int(product_batch['total_qc_qty'])
                rejected_qty = int(product_batch['rejected_qty'])
            except:
                raise serializers.ValidationError("'total_qc_qty' & 'rejected_qty' | Invalid quantity.")

            if rejected_qty > 0 and \
                    ('reason_for_rejection' not in product_batch or
                     product_batch['reason_for_rejection'] not in OrderedProductBatch.REJECTION_REASON_CHOICE):
                raise serializers.ValidationError("'reason_for_rejection' | This is mandatory "
                                                  "if rejected quantity is greater than zero.")

            if 'id' in product_batch and product_batch['id']:
                product_batch_instance = OrderedProductBatch.objects.filter(id=product_batch['id']).last()

                if product_batch_instance.ordered_product_mapping.ordered_product.shipment_status != 'QC_STARTED':
                    raise serializers.ValidationError("Shipment updation is not allowed.")

                if product_batch_instance.batch_id != product_batch['batch_id']:
                    raise serializers.ValidationError("'batch_id' | Invalid batch.")

                missing_qty = product_batch_instance.pickup_quantity - total_qc_qty
                product_batch['missing_qty'] = missing_qty
                product_missing_qty += missing_qty
                product_rejected_qty += rejected_qty

                batch_shipped_qty = total_qc_qty - rejected_qty

                if batch_shipped_qty < 0 or float(product_batch_instance.pickup_quantity) != float(
                        batch_shipped_qty + product_batch['missing_qty'] + product_batch['rejected_qty']):
                    raise serializers.ValidationError("Sorry Quantity mismatch!! Picked pieces must be equal to sum of "
                                                      "(QC pieces + missing pieces.)")
                product_batch['quantity'] = batch_shipped_qty
            else:
                raise serializers.ValidationError("'rt_ordered_product_mapping.id' | This is mandatory.")

        # Shipment's Product mapping Id Validation
        if 'id' not in self.initial_data and self.initial_data['id'] is None:
            raise serializers.ValidationError("'id' | This is mandatory.")

        mapping_instance = RetailerOrderedProductMapping.objects.filter(id=self.initial_data['id']).last()

        if mapping_instance.ordered_product.shipment_status != 'QC_STARTED':
            raise serializers.ValidationError("Shipment updation is not allowed.")

        # if mapping_instance.is_qc_done:
        #     raise serializers.ValidationError("This product is already QC Passed.")

        if mapping_instance.product != product:
            raise serializers.ValidationError("Product updation is not allowed.")

        shipped_qty = mapping_instance.picked_pieces - (product_damaged_qty + product_expired_qty +
                                                        product_missing_qty + product_rejected_qty)
        if shipped_qty < 0 or float(mapping_instance.picked_pieces) != float(
                shipped_qty + product_damaged_qty + product_expired_qty + product_missing_qty +
                product_rejected_qty):
            raise serializers.ValidationError("Sorry Quantity mismatch!! Picked pieces must be equal to sum of "
                                              "(total qc pieces + missing pieces)")

        warehouse_id = mapping_instance.ordered_product.order.seller_shop.id

        if 'packaging' in self.initial_data and self.initial_data['packaging']:
            if shipped_qty == 0:
                raise serializers.ValidationError("To be shipped quantity is zero, packaging is not required")
            total_product_qty = 0
            for package_obj in self.initial_data['packaging']:
                if 'type' not in package_obj or not package_obj['type']:
                    raise serializers.ValidationError("'package type' | This is mandatory")
                if package_obj['type'] not in [ShipmentPackaging.CRATE, ShipmentPackaging.SACK, ShipmentPackaging.BOX]:
                    raise serializers.ValidationError("'packaging type' | Invalid packaging type")
                if package_obj['type'] == ShipmentPackaging.CRATE:
                    validate_crates = validate_shipment_crates_list(package_obj, warehouse_id,
                                                                    mapping_instance.ordered_product)
                    if 'error' in validate_crates:
                        raise serializers.ValidationError(validate_crates['error'])
                    for crate_obj in validate_crates['data']['packages']:
                        total_product_qty += crate_obj['quantity']
                elif package_obj['type'] in [ShipmentPackaging.SACK, ShipmentPackaging.BOX]:
                    validated_packages = validate_shipment_package_list(package_obj)
                    if 'error' in validated_packages:
                        raise serializers.ValidationError(validated_packages['error'])
                    for package in validated_packages['data']['packages']:
                        total_product_qty += package['quantity']
            if total_product_qty != int(shipped_qty):
                raise serializers.ValidationError("Total quantity packaged should match total shipped quantity.")
        elif shipped_qty > 0:
            raise serializers.ValidationError("'packaging' | This is mandatory")

        data['packaging'] = self.initial_data.get('packaging')
        data['damaged_qty'] = product_damaged_qty
        data['expired_qty'] = product_expired_qty
        data['missing_qty'] = product_missing_qty
        data['rejected_qty'] = product_rejected_qty
        data['shipped_qty'] = shipped_qty
        data['is_qc_done'] = True
        data['warehouse_id'] = warehouse_id

        return data

    def create_update_shipment_packaging(self, shipment, packaging_type, warehouse_id, crate, updated_by):
        if packaging_type == ShipmentPackaging.CRATE:
            instance, created = ShipmentPackaging.objects.get_or_create(
                shipment=shipment, packaging_type=packaging_type, warehouse_id=warehouse_id, crate=crate,
                defaults={'created_by': updated_by, 'updated_by': updated_by})
        else:
            instance = ShipmentPackaging.objects.create(
                shipment=shipment, packaging_type=packaging_type, warehouse_id=warehouse_id, crate=crate,
                created_by=updated_by, updated_by=updated_by)
        return instance

    def create_shipment_packaging_mapping(self, shipment_packaging, ordered_product, quantity, updated_by):
        return ShipmentPackagingMapping.objects.create(
            shipment_packaging=shipment_packaging, ordered_product=ordered_product, quantity=quantity,
            created_by=updated_by, updated_by=updated_by)

    def update_product_batch_data(self, product_batch_instance, validated_data):
        try:

            process_shipments_instance = product_batch_instance.update(**validated_data)
            product_batch_instance.last().save()
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update Ordered Product Mapping"""
        ordered_product_batches = self.initial_data['rt_ordered_product_mapping']
        packaging = validated_data['packaging']

        try:
            process_shipments_instance = super().update(instance, validated_data)
            # process_shipments_instance.save()
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        for product_batch in ordered_product_batches:
            product_batch_instance = OrderedProductBatch.objects.filter(id=product_batch['id'])
            product_batch_id = product_batch.pop('id')
            product_batch.pop('total_qc_qty')
            self.update_product_batch_data(product_batch_instance, product_batch)

        if packaging:
            if ShipmentPackagingMapping.objects.filter(ordered_product=process_shipments_instance).exists():
                shipment_packaging_ids = list(ShipmentPackagingMapping.objects.filter(ordered_product=process_shipments_instance)\
                                                                     .values_list('shipment_packaging_id', flat=True))
                ShipmentPackagingMapping.objects.filter(ordered_product=process_shipments_instance).delete()

                ShipmentPackaging.objects.filter(id__in=shipment_packaging_ids, packaging_details__isnull=True).delete()

            for package_obj in packaging:
                if package_obj['type'] == ShipmentPackaging.CRATE:
                    for crate in package_obj['packages']:
                        crate_instance = Crate.objects.filter(
                            crate_id=crate['crate_id'], warehouse__id=validated_data['warehouse_id'],
                            crate_type=Crate.DISPATCH).last()
                        shipment_packaging = self.create_update_shipment_packaging(
                            process_shipments_instance.ordered_product, package_obj['type'],
                            validated_data['warehouse_id'], crate_instance, validated_data['last_modified_by'])

                        self.create_shipment_packaging_mapping(
                            shipment_packaging, process_shipments_instance, int(crate['quantity']),
                            validated_data['last_modified_by'])

                elif package_obj['type'] in [ShipmentPackaging.BOX, ShipmentPackaging.SACK]:
                    for package in package_obj['packages']:
                        shipment_packaging = self.create_update_shipment_packaging(
                            process_shipments_instance.ordered_product, package_obj['type'],
                            validated_data['warehouse_id'], None, validated_data['last_modified_by'])

                        self.create_shipment_packaging_mapping(
                            shipment_packaging, process_shipments_instance, int(package['quantity']),
                            validated_data['last_modified_by'])
        return process_shipments_instance

    @staticmethod
    def get_product_price(obj):
        """
        Get effective product price per piece from OrderedProductMapping instance if available,
        else get the price instance from CartProductMapping and calculate effective price
        applicable per piece based on shipped quantity
        """
        product_price = 0
        if obj.effective_price:
            product_price = obj.effective_price
        else:
            cart_product_mapping = CartProductMapping.objects.filter(
                cart_product=obj.product, cart=obj.ordered_product.order.ordered_cart).last()
            if cart_product_mapping and cart_product_mapping.cart_product_price:
                cart_product_price = cart_product_mapping.cart_product_price
                cart_product_case_size = cart_product_mapping.no_of_pieces/cart_product_mapping.qty
                shipped_qty_in_pack = math.ceil(obj.shipped_qty / cart_product_case_size)
                product_price = round(cart_product_price.get_per_piece_price(shipped_qty_in_pack), 2)
        return product_price

    def get_product_total_price(self, obj):
        self.product_total_price = float(obj.effective_price) * float(obj.shipped_qty)
        return round(self.product_total_price, 2)

    @staticmethod
    def get_product_type(obj):
        return obj.get_product_type_display()


class ShipmentProductSerializer(serializers.ModelSerializer):
    shop_owner_name = serializers.SerializerMethodField()
    shop_owner_number = serializers.SerializerMethodField()
    order_created_date = serializers.SerializerMethodField()
    rt_order_product_order_product_mapping = RetailerOrderedProductMappingSerializer(read_only=True, many=True)
    order_no = serializers.SerializerMethodField()

    def get_order_no(self, obj):
        return obj.order.order_no

    class Meta:
        model = OrderedProduct
        fields = ('id', 'order_no', 'invoice_no', 'shipment_status', 'invoice_amount', 'payment_mode', 'shipment_address',
                  'shop_owner_name', 'shop_owner_number', 'order_created_date',
                  'rt_order_product_order_product_mapping')

    @staticmethod
    def get_shop_owner_number(obj):
        shop_owner_number = obj.order.buyer_shop.shop_owner.phone_number
        return shop_owner_number

    @staticmethod
    def get_shop_owner_name(obj):
        shop_owner_name = obj.order.buyer_shop.shop_owner.first_name + obj.order.buyer_shop.shop_owner.last_name
        return shop_owner_name

    @staticmethod
    def get_order_created_date(obj):
        return obj.order.created_at

class AddressSerializer(serializers.ModelSerializer):
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()

    def get_city(self, obj):
        return obj.city.city_name

    def get_state(self, obj):
        return obj.state.state_name

    class Meta:
        model=Address
        fields=("pincode", "nick_name", "address_line1", "address_contact_name", "address_contact_number",
                "address_type", 'city', 'state')

class OrderSerializerForShipment(serializers.ModelSerializer):
    seller_shop = ShopSerializer()
    buyer_shop = ShopSerializer()
    shipping_address = AddressSerializer()

    class Meta:
        model=Order
        fields = ('order_no', 'seller_shop', 'buyer_shop', 'shipping_address')


class ShipmentQCSerializer(serializers.ModelSerializer):
    """ Serializer for Shipment QC"""
    order = OrderSerializerForShipment(read_only=True)
    created_date = serializers.SerializerMethodField()
    qc_area = QCAreaSerializer(read_only=True)
    qc_desk = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField()

    def get_qc_desk(self, obj):
        return QCDeskSerializer(obj.qc_area.qc_desk_areas.filter(desk_enabled=True).last()).data if obj.qc_area else None

    def get_created_date(self, obj):
        return obj.created_at.strftime("%d/%b/%y %H:%M")

    def get_status(self, obj):
        return obj.get_shipment_status_display()

    class Meta:
        model = OrderedProduct
        fields = ('id', 'order', 'status', 'shipment_status', 'invoice_no', 'invoice_amount', 'payment_mode', 'qc_area',
                  'qc_desk', 'created_date')


    def validate(self, data):
        """Validates the Shipment update requests"""

        if 'id' in self.initial_data and self.initial_data['id']:
            if 'status' in self.initial_data and self.initial_data['status']:
                try:
                    shipment = OrderedProduct.objects.get(id=self.initial_data['id'])
                    shipment_status = shipment.shipment_status
                except Exception as e:
                    raise serializers.ValidationError("Invalid Shipment")
                status = self.initial_data['status']
                if status == shipment_status:
                    raise serializers.ValidationError(f'Shipment already in {status}')
                elif (shipment_status not in [OrderedProduct.SHIPMENT_CREATED, OrderedProduct.QC_STARTED,
                                              OrderedProduct.READY_TO_SHIP]) \
                    or (shipment_status == OrderedProduct.SHIPMENT_CREATED and status != OrderedProduct.QC_STARTED) \
                    or (shipment_status == OrderedProduct.QC_STARTED and status != OrderedProduct.READY_TO_SHIP) \
                    or (shipment_status == OrderedProduct.READY_TO_SHIP and status != OrderedProduct.MOVED_TO_DISPATCH):
                    raise serializers.ValidationError(f'Invalid status | {shipment_status}-->{status} not allowed')

                user = self.initial_data.pop('user')
                if status in [OrderedProduct.QC_STARTED, OrderedProduct.READY_TO_SHIP] and \
                        not shipment.qc_area.qc_desk_areas.filter(desk_enabled=True, qc_executive=user).exists():
                    raise serializers.ValidationError("Logged in user is not allowed to perform QC for this shipment")
                elif status == OrderedProduct.READY_TO_SHIP and\
                        shipment.rt_order_product_order_product_mapping.filter(is_qc_done=False).exists():
                    product_qc_pending = shipment.rt_order_product_order_product_mapping.filter(is_qc_done=False).first()
                    raise serializers.ValidationError(f'QC is not yet completed for {product_qc_pending.product}')
                elif status == OrderedProduct.MOVED_TO_DISPATCH and \
                    shipment.shipment_packaging.filter(status=ShipmentPackaging.DISPATCH_STATUS_CHOICES.PACKED).exists():
                    raise serializers.ValidationError(' Some item/s still not ready for dispatch')
                elif status == OrderedProduct.MOVED_TO_DISPATCH and \
                    not shipment.shipment_packaging.filter(
                        status=ShipmentPackaging.DISPATCH_STATUS_CHOICES.READY_TO_DISPATCH).exists():
                    raise serializers.ValidationError('There is no package to be dispatched in this shipment')
                if status == OrderedProduct.READY_TO_SHIP and \
                    not shipment.rt_order_product_order_product_mapping.filter(shipped_qty__gt=0).exists():
                    status = OrderedProduct.QC_REJECTED
                data['shipment_status'] = status

            else:
                raise serializers.ValidationError("Only status update is allowed")
        else:
            raise serializers.ValidationError("Shipment creation is not allowed.")

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            shipment_instance = super().update(instance, validated_data)
            self.post_shipment_status_change(shipment_instance)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return shipment_instance

    def post_shipment_status_change(self, shipment_instance):
        '''
            Update the QCArea assignment mapping on shipment QC start
            Release Picking Crates on Shipment QC DOne
        '''
        info_logger.info(f"post_shipment_status_change|Shipment ID {shipment_instance.id}")
        if shipment_instance.shipment_status == OrderedProduct.QC_STARTED:
            send_update_to_qcdesk(shipment_instance)
            info_logger.info(f"post_shipment_status_change|QCDesk Mapping updated|Shipment ID {shipment_instance.id}")
        elif shipment_instance.shipment_status in [OrderedProduct.READY_TO_SHIP, OrderedProduct.QC_REJECTED]:
            release_picking_crates(shipment_instance.order)
            self.update_order_status_post_qc_done(shipment_instance)
            info_logger.info(f"post_shipment_status_change|shipment_status {shipment_instance.shipment_status} "
                             f"|Picking Crates released|OrderNo {shipment_instance.order.order_no}")

    @staticmethod
    def update_order_status_post_qc_done(shipment_instance):
        if shipment_instance.shipment_status == OrderedProduct.READY_TO_SHIP:
            total_shipped_qty = shipment_instance.order.rt_order_order_product \
                .aggregate(total_shipped_qty=Sum('rt_order_product_order_product_mapping__shipped_qty')) \
                .get('total_shipped_qty')
            total_ordered_qty = shipment_instance.order.ordered_cart.rt_cart_list \
                .aggregate(total_ordered_qty=Sum('no_of_pieces')) \
                .get('total_ordered_qty')

            if total_ordered_qty == total_shipped_qty:
                shipment_instance.order.order_status = Order.FULL_SHIPMENT_CREATED
            else:
                shipment_instance.order.order_status = Order.PARTIAL_SHIPMENT_CREATED
        elif shipment_instance.shipment_status == OrderedProduct.QC_REJECTED:
            shipment_instance.order.order_status = Order.QC_FAILED
        shipment_instance.order.save()


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ('id', 'city_name')

class ShipmentPincodeFilterSerializer(serializers.ModelSerializer):
    city = CitySerializer()

    class Meta:
        model = Pincode
        fields = ('id', 'pincode', 'city')

class ShipmentSerializerForDispatch(serializers.ModelSerializer):
    class Meta:
        model = OrderedProduct
        fields = ('id', 'invoice_no', 'order_no')

class DispatchItemDetailsSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)

    def get_product(self, obj):
        return ProductSerializer(obj.ordered_product.product).data

    class Meta:
        model = ShipmentPackagingMapping
        fields = ('id', 'product', 'quantity')


class DispatchItemsSerializer(serializers.ModelSerializer):
    packaging_details = DispatchItemDetailsSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()
    crate = CrateSerializer(read_only=True)
    packaging_type = serializers.CharField(read_only=True)
    shipment = ShipmentSerializerForDispatch(read_only=True)

    @staticmethod
    def get_status(obj):
        return obj.get_status_display()


    @staticmethod
    def get_reason_for_rejection(obj):
        return obj.get_reason_for_rejection_display()

    class Meta:
        model = ShipmentPackaging
        fields = ('id', 'shipment', 'packaging_type', 'crate', 'status', 'reason_for_rejection', 'created_by', 'packaging_details')


    def validate(self, data):
        if 'shipment_id' not in self.initial_data or not self.initial_data['shipment_id']:
            raise serializers.ValidationError("'shipment_id' | This is required")
        elif 'id' not in self.initial_data or not self.initial_data['id']:
            raise serializers.ValidationError("'id' | This is required")
        elif 'is_ready_for_dispatch' not in self.initial_data:
            raise serializers.ValidationError("'is_ready_for_dispatch' | This is required.")
        elif self.initial_data['is_ready_for_dispatch'] not in [True, False]:
            raise serializers.ValidationError("'is_ready_for_dispatch' | This can only be True/False")
        data['status'] = ShipmentPackaging.DISPATCH_STATUS_CHOICES.READY_TO_DISPATCH

        if not self.initial_data['is_ready_for_dispatch']:
            if 'reason_for_rejection' not in self.initial_data or not self.initial_data['reason_for_rejection']:
                raise serializers.ValidationError("'reason_for_rejection' | This is required")
            elif int(self.initial_data['reason_for_rejection']) not in ShipmentPackaging.REASON_FOR_REJECTION:
                raise serializers.ValidationError("'reason_for_rejection' | This is invalid")
            data['reason_for_rejection'] = self.initial_data['reason_for_rejection']
            data['status'] = ShipmentPackaging.DISPATCH_STATUS_CHOICES.REJECTED

        shipment = OrderedProduct.objects.filter(id=self.initial_data['shipment_id']).last()
        if shipment.shipment_status != OrderedProduct.READY_TO_SHIP:
            raise serializers.ValidationError("Shipment is not in QC Passed state")
        package_mapping = ShipmentPackaging.objects.get(id=self.initial_data['id'])
        if package_mapping.status != ShipmentPackaging.DISPATCH_STATUS_CHOICES.PACKED:
            raise serializers.ValidationError("Package already marked ready for dispatch")
        return data


    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            package_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return package_instance


class DispatchDashboardSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    qc_done = serializers.IntegerField()
    moved_to_dispatch = serializers.IntegerField()
    # ready_to_dispatch = serializers.IntegerField()
    # out_for_delivery = serializers.IntegerField()
    # rescheduled = serializers.IntegerField()


class OrderPaymentStatusChangeSerializers(serializers.ModelSerializer):
    seller_shop = ShopSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'order_no', 'seller_shop', 'order_status', 'received_by', 'created_at', 'modified_at')

    def validate(self, data):

        if 'id' in self.initial_data and self.initial_data['id']:
            if Order.objects.filter(id=self.initial_data['id'],
                                    ordered_cart__cart_type='ECOM').exists():
                order_instance = Order.objects.filter(id=self.initial_data['id']).last()
            else:
                raise serializers.ValidationError(f"Order not found for Id {self.initial_data['id']}.")
        else:
            raise serializers.ValidationError("'id' | This is mandatory")

        if 'order_no' in self.initial_data and self.initial_data['order_no']:
            order_no = self.initial_data['order_no']
            if order_instance.order_no != order_no:
                raise Exception("'order_no' | Invalid order_no for selected order.")

        if 'order_status' not in self.initial_data and not self.initial_data['order_status']:
            raise serializers.ValidationError("'order_status' | This is mandatory.")
        order_status = self.initial_data['order_status']

        if order_instance.order_status not in [Order.PAYMENT_PENDING, Order.PAYMENT_FAILED] or \
                order_instance.order_status == order_status:
            raise serializers.ValidationError(f"Order status can't update")

        if self.context.get('app-type', None) == 3 and order_instance.order_status == Order.PAYMENT_PENDING and \
                order_status not in [Order.PAYMENT_FAILED, Order.PAYMENT_APPROVED, Order.PAYMENT_COD]:
            raise serializers.ValidationError(f"Please Provide valid Payment status")

        elif self.context.get('app-type', None) == 2 and order_instance.order_status == Order.PAYMENT_PENDING and \
                order_status != Order.PAYMENT_COD:
            raise serializers.ValidationError(f"Please Provide valid Payment status")

        if 'payment_id' not in self.initial_data and not self.initial_data['payment_id']:
            raise serializers.ValidationError("'payment_id' | This is mandatory.")

        if PosPayment.objects.filter(id=self.initial_data['payment_id']).exists():
            payment_instance = PosPayment.objects.filter(id=self.initial_data['payment_id']).last()
        else:
            raise serializers.ValidationError(f"Payment not found for Id {self.initial_data['id']}.")

        if payment_instance.order != order_instance:
            raise serializers.ValidationError(f"Invalid payment {payment_instance} for the order {order_instance}")

        if 'payment_type_id' not in self.initial_data or not self.initial_data['payment_type_id']:
            raise serializers.ValidationError("'payment_type_id' | This is mandatory")
        payment_type_instance = PaymentType.objects.filter(id=int(self.initial_data['payment_type_id'])).last()
        if not payment_type_instance:
            raise serializers.ValidationError(f"'payment_type_id' | "
                                              f"{self.initial_data['payment_type_id']} not found.")

        if order_instance.order_app_type == Order.POS_WALKIN:
            if payment_type_instance.app != 'pos':
                raise serializers.ValidationError(f"'payment_type_id' | Invalid choice "
                                                  f"{self.initial_data['payment_type_id']}.")
        if order_instance.order_app_type == Order.POS_ECOMM:
            if payment_type_instance.app != 'ecom':
                raise serializers.ValidationError(f"'payment_type_id' | Invalid choice "
                                                  f"{self.initial_data['payment_type_id']}.")

        transaction_id = ""
        if 'transaction_id' in self.initial_data and self.initial_data['transaction_id']:
            transaction_id = self.initial_data['transaction_id']

        payment_status = None
        payment_mode = None
        if order_status == Order.PAYMENT_FAILED:
            payment_status = PosPayment.PAYMENT_FAILED
            data['order_status'] = Order.PAYMENT_FAILED
        elif order_status == Order.PAYMENT_COD:
            data['order_status'] = Order.ORDERED
        elif order_status == 'PAYMENT_APPROVED':
            if payment_type_instance.type == 'online':
                if 'payment_mode' not in self.initial_data or not self.initial_data['payment_mode']:
                    raise serializers.ValidationError("'payment_mode' | This is mandatory")
                if not any(self.initial_data['payment_mode'] in i for i in PosPayment.MODE_CHOICES):
                    raise serializers.ValidationError(f"'payment_mode' | Invalid choice "
                                                      f"{self.initial_data['payment_mode']}.")
                payment_mode = self.initial_data['payment_mode']
            payment_status = PosPayment.PAYMENT_APPROVED
            data['order_status'] = Order.ORDERED

        data['payment_instance'] = payment_instance
        data['payment'] = {}
        data['payment']['order'] = order_instance
        data['payment']['payment_type'] = payment_type_instance
        data['payment']['payment_status'] = payment_status
        data['payment']['payment_mode'] = payment_mode
        data['payment']['transaction_id'] = transaction_id

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update Order"""
        payment_instance = validated_data.pop("payment_instance", None)
        payment_obj = validated_data.pop("payment", None)
        try:
            order_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        if payment_instance:
            payment_instance.order = payment_obj['order']
            payment_instance.payment_type = payment_obj['payment_type']
            payment_instance.payment_status = payment_obj['payment_status']
            payment_instance.payment_mode = payment_obj['payment_mode']
            payment_instance.transaction_id = payment_obj['transaction_id']
            payment_instance.save()

        return order_instance
