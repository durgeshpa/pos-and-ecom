import logging
import math
import datetime

from django.db import transaction
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.db.models import Sum, Q, F, FloatField
from decimal import Decimal
from rest_framework import serializers

from accounts.models import UserWithName
from addresses.models import Address, Pincode, City
from products.models import (Product, ProductPrice, ProductImage, Tax, ProductTaxMapping, ProductOption, Size, Color,
                             Fragrance, Flavor, Weight, PackageSize, ParentProductImage, SlabProductPrice, PriceSlab)
from retailer_backend.utils import getStrToYearDate
from retailer_to_sp.common_validators import validate_shipment_crates_list, validate_shipment_package_list
from retailer_to_sp.models import (CartProductMapping, Cart, Order, OrderedProduct, Note, CustomerCare, Payment,
                                   Dispatch, Feedback, OrderedProductMapping as RetailerOrderedProductMapping,
                                   Trip, PickerDashboard, ShipmentRescheduling, OrderedProductBatch, ShipmentPackaging,
                                   ShipmentPackagingMapping, DispatchTrip, DispatchTripShipmentMapping,
                                   DispatchTripShipmentPackages, ShipmentNotAttempt, PACKAGE_VERIFY_CHOICES,
                                   LastMileTripShipmentMapping, ShopCrate, DispatchTripCrateMapping)

from retailer_to_gram.models import (Cart as GramMappedCart, CartProductMapping as GramMappedCartProductMapping,
                                     Order as GramMappedOrder, OrderedProduct as GramMappedOrderedProduct,
                                     Payment as GramMappedPayment)
from coupon.models import Coupon
from sp_to_gram.models import OrderedProductMapping
from gram_to_brand.models import GRNOrderProductMapping
from shops.models import Shop, ShopTiming
from accounts.api.v1.serializers import UserSerializer
from addresses.api.v1.serializers import AddressSerializer
from coupon.serializers import CouponSerializer
from wms.api.v2.serializers import QCDeskSerializer, QCAreaSerializer
from wms.common_functions import release_picking_crates, send_update_to_qcdesk
from wms.models import Crate, WarehouseAssortment, Zone

User = get_user_model()

info_logger = logging.getLogger('file-info')


class ChoicesSerializer(serializers.ChoiceField):

    def to_representation(self, obj):
        if obj == '' and self.allow_blank:
            return obj
        return {'id': obj, 'description': self._choices[obj]}


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
        fields = ('order','invoice_no','invoice_link', 'shipment_status')

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
        fields = ('id', 'batch_id', 'quantity', 'ordered_pieces', 'delivered_qty',
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
    is_fully_delivered = serializers.SerializerMethodField()

    class Meta:
        model = RetailerOrderedProductMapping
        fields = ('id', 'ordered_qty', 'shipped_qty', 'product', 'product_price', 'product_total_price', 'is_qc_done',
                  'product_type', 'selling_price', 'shipped_qty', 'delivered_qty', 'returned_qty', 'damaged_qty',
                  'returned_damage_qty', 'expired_qty', 'missing_qty', 'rejected_qty', 'last_modified_by', 'created_at',
                  'modified_at', 'effective_price', 'discounted_price', 'delivered_at_price', 'cancellation_date',
                  'picked_pieces', 'rt_ordered_product_mapping', 'shipment_product_packaging', 'is_fully_delivered')

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
            self.mark_crate_used(instance)
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

    def mark_crate_used(self, packaging_instance):
        info_logger.info(f"mark_crate_used|Packaging instance {packaging_instance}")
        shop_crate_instance = ShopCrate.objects.update_or_create(
            shop=packaging_instance.warehouse, crate=packaging_instance.crate, defaults={'is_available': False})
        info_logger.info(f"mark_crate_used|Marked| {shop_crate_instance}")

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

    def get_is_fully_delivered(self, obj):
        return True if obj.shipped_qty == obj.delivered_qty else False


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
    dispatch_center = ShopSerializer()
    shipping_address = AddressSerializer()

    class Meta:
        model=Order
        fields = ('order_no', 'seller_shop', 'buyer_shop', 'dispatch_delivery', 'dispatch_center', 'shipping_address')


class ShipmentQCSerializer(serializers.ModelSerializer):
    """ Serializer for Shipment QC"""
    order = OrderSerializerForShipment(read_only=True)
    created_date = serializers.SerializerMethodField()
    qc_area = QCAreaSerializer(read_only=True)
    qc_desk = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField()

    def get_qc_desk(self, obj):
        return QCDeskSerializer(obj.qc_area.qc_desk_areas.filter(desk_enabled=True).last()).data

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
            try:
                shipment = OrderedProduct.objects.get(id=self.initial_data['id'])
                shipment_status = shipment.shipment_status
            except Exception as e:
                raise serializers.ValidationError("Invalid Shipment")
            shipment_reschedule = {}
            shipment_not_attempt = {}
            if 'status' in self.initial_data and self.initial_data['status']:
                status = self.initial_data['status']
                if status == shipment_status:
                    raise serializers.ValidationError(f'Shipment already in {status}')
                elif status in [OrderedProduct.RESCHEDULED, OrderedProduct.NOT_ATTEMPT]:
                    if shipment_status != OrderedProduct.FULLY_DELIVERED_AND_COMPLETED:
                        raise serializers.ValidationError(f'Invalid status | {shipment_status}->{status} not allowed')
                    if shipment_status == OrderedProduct.RESCHEDULED:
                        if ShipmentRescheduling.objects.filter(shipment=shipment).exists():
                            raise serializers.ValidationError('A shipment cannot be rescheduled more than once.')
                        if 'rescheduling_reason' not in self.initial_data or \
                                not self.initial_data['rescheduling_reason']:
                            raise serializers.ValidationError(f"'rescheduling_reason' | This is mandatory")
                        if not any(self.initial_data['rescheduling_reason'] in i for i in
                                   ShipmentRescheduling.RESCHEDULING_REASON):
                            raise serializers.ValidationError(f"'rescheduling_reason' | Invalid choice")
                        if 'rescheduling_date' not in self.initial_data or not self.initial_data['rescheduling_date']:
                            raise serializers.ValidationError(f"'rescheduling_date' | This is mandatory")
                        rescheduling_date = getStrToYearDate(self.initial_data['rescheduling_date'])
                        if rescheduling_date < datetime.date.today() or \
                                rescheduling_date > (datetime.date.today() + datetime.timedelta(days=3)):
                            raise serializers.ValidationError("'rescheduling_date' | The date must be within 3 days!")
                        shipment_reschedule['rescheduling_reason'] = self.initial_data['rescheduling_reason']
                        shipment_reschedule['rescheduling_date'] = rescheduling_date
                    if shipment_status == OrderedProduct.NOT_ATTEMPT:
                        if ShipmentNotAttempt.objects.filter(
                                shipment=shipment, created_at__date=datetime.now().date()).exists():
                            raise serializers.ValidationError(
                                'A shipment cannot be mark not attempt more than once in a day.')
                        if 'not_attempt_reason' not in self.initial_data or \
                                not self.initial_data['not_attempt_reason']:
                            raise serializers.ValidationError(f"'not_attempt_reason' | This is mandatory")
                        if not any(self.initial_data['not_attempt_reason'] in i for i in
                                   ShipmentNotAttempt.NOT_ATTEMPT_REASON):
                            raise serializers.ValidationError(f"'not_attempt_reason' | Invalid choice")
                        shipment_not_attempt['not_attempt_reason'] = self.initial_data['not_attempt_reason']
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

            elif 'return_reason' in self.initial_data and self.initial_data['return_reason']:
                if shipment_status not in [OrderedProduct.PARTIALLY_DELIVERED_AND_COMPLETED,
                                           OrderedProduct.FULLY_RETURNED_AND_COMPLETED]:
                    raise serializers.ValidationError(f"Updating 'return_reason' at {shipment_status} not allowed")
                return_reason = self.initial_data['return_reason']
                if return_reason not in OrderedProduct.RETURN_REASON:
                    raise serializers.ValidationError(f"'return_reason' | Invalid choice")
                data['return_reason'] = return_reason
            else:
                raise serializers.ValidationError("Only status / return_reason update is allowed")
        else:
            raise serializers.ValidationError("Shipment creation is not allowed.")

        data['shipment_reschedule'] = shipment_reschedule
        data['shipment_not_attempt'] = shipment_not_attempt
        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        shipment_reschedule = validated_data.pop("shipment_reschedule", None)
        shipment_not_attempt = validated_data.pop("shipment_not_attempt", None)
        try:
            shipment_instance = super().update(instance, validated_data)
            self.post_shipment_status_change(shipment_instance, shipment_reschedule, shipment_not_attempt)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return shipment_instance

    def create_shipment_reschedule(self, shipment_instance, rescheduling_reason, rescheduling_date):
        """Create shipment rescheduled"""
        info_logger.info(f"create_shipment_reschedule|Reschedule Started|Shipment ID {shipment_instance.id}")
        if not ShipmentRescheduling.objects.filter(shipment=shipment_instance).exists():
            ShipmentRescheduling.objects.create(
                shipment=shipment_instance, rescheduling_reason=rescheduling_reason, rescheduling_date=rescheduling_date,
                created_by=shipment_instance.updated_by)
        else:
            raise Exception(f"create_shipment_reschedule|Reschedule already exists|Shipment ID {shipment_instance.id}")

        info_logger.info(f"create_shipment_reschedule|Rescheduled|Shipment ID {shipment_instance.id}")

    def create_shipment_not_attempt(self, shipment_instance, not_attempt_reason):
        """Create shipment not attempt"""
        info_logger.info(f"create_shipment_not_attempt|Not Attempt Started|Shipment ID {shipment_instance.id}")
        if not ShipmentNotAttempt.objects.filter(
                shipment=shipment_instance, created_at__date=datetime.datetime.now().date()).exists():
            ShipmentNotAttempt.objects.create(
                shipment=shipment_instance, not_attempt_reason=not_attempt_reason,
                created_by=shipment_instance.updated_by)
        else:
            raise Exception(f"create_shipment_not_attempt|Not attempt more than once in a day not allowed|Shipment ID "
                            f"{shipment_instance.id}")

        info_logger.info(f"create_shipment_not_attempt|Not Attempted|Shipment ID {shipment_instance.id}")

    def post_shipment_status_change(self, shipment_instance, shipment_reschedule, shipment_not_attempt):
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
        elif shipment_instance.shipment_status == OrderedProduct.RESCHEDULED:
            if 'rescheduling_reason' in shipment_reschedule and 'rescheduling_date' in shipment_reschedule:
                self.create_shipment_reschedule(
                    shipment_instance, shipment_reschedule['rescheduling_reason'],
                    shipment_reschedule['rescheduling_date'])
                info_logger.info(f"post_shipment_status_change|Rescheduled|Shipment ID {shipment_instance.id}")
        elif shipment_instance.shipment_status == OrderedProduct.NOT_ATTEMPT:
            if 'not_attempt_reason' in shipment_not_attempt:
                self.create_shipment_not_attempt(shipment_instance, shipment_not_attempt['not_attempt_reason'])
                info_logger.info(f"post_shipment_status_change|Not Attempted|Shipment ID {shipment_instance.id}")


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
        fields = ('id', 'invoice_no', 'order_no', 'shipment_status')

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
    is_return_verified = serializers.SerializerMethodField()

    def get_is_return_verified(self, obj):
        return True if obj.status in [ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_VERIFIED,
                               ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_MISSING,
                               ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_DAMAGED] else False

    @staticmethod
    def get_status(obj):
        return obj.get_status_display()


    @staticmethod
    def get_reason_for_rejection(obj):
        return obj.get_reason_for_rejection_display()

    class Meta:
        model = ShipmentPackaging
        fields = ('id', 'shipment', 'packaging_type', 'crate', 'status', 'reason_for_rejection', 'created_by',
                  'packaging_details', 'is_return_verified')


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


class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'phone_number',)


class DispatchTripSerializers(serializers.ModelSerializer):
    seller_shop = ShopSerializer(read_only=True)
    source_shop = ShopSerializer(read_only=True)
    destination_shop = ShopSerializer(read_only=True)
    delivery_boy = UserSerializers(read_only=True)

    class Meta:
        model = DispatchTrip
        fields = ('id', 'seller_shop', 'source_shop', 'destination_shop', 'dispatch_no', 'delivery_boy', 'vehicle_no',
                  'trip_status',)


class DispatchTripShipmentPackagesSerializers(serializers.ModelSerializer):
    shipment_packaging = DispatchItemsSerializer(read_only=True)

    class Meta:
        model = DispatchTripShipmentPackages
        fields = ('id', 'shipment_packaging', 'package_status',)


class DispatchTripShipmentMappingSerializer(serializers.ModelSerializer):
    trip = DispatchTripSerializers(read_only=True)
    shipment = ShipmentSerializerForDispatch(read_only=True)
    trip_shipment_mapped_packages = DispatchTripShipmentPackagesSerializers(read_only=True, many=True)
    shipment_status = serializers.CharField(read_only=True)
    shipment_health = serializers.CharField(read_only=True)

    class Meta:
        model = DispatchTripShipmentMapping
        fields = ('id', 'trip', 'shipment', 'shipment_status', 'shipment_health', 'trip_shipment_mapped_packages',)

    def validate(self, data):
        if 'shipment_id' not in self.initial_data or not self.initial_data['shipment_id']:
            raise serializers.ValidationError("'shipment_id' | This is required")

        elif 'trip_id' not in self.initial_data or not self.initial_data['trip_id']:
            raise serializers.ValidationError("'trip_id' | This is required")

        trip_shipment_mapping = DispatchTripShipmentMapping.objects.filter(
                                            trip_id=self.initial_data['trip_id'],
                                            shipment_id=self.initial_data['shipment_id']).last()
        if not trip_shipment_mapping:
            raise serializers.ValidationError("Invalid invoice for the this trip")

        if trip_shipment_mapping.trip_shipment_mapped_packages.count() != \
            trip_shipment_mapping.shipment.shipment_packaging.filter(
                status=ShipmentPackaging.DISPATCH_STATUS_CHOICES.READY_TO_DISPATCH).count():
            raise serializers.ValidationError("Some packages are still pending to be loaded for this invoice, "
                                              "can't mark invoice as added")
        data['shipment_status'] = DispatchTripShipmentMapping.LOADED_FOR_DC
        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            trip_shipment = super().update(instance, validated_data)

            if trip_shipment.trip.trip_type == DispatchTrip.FORWARD:
                trip_shipment.shipment.shipment_status = OrderedProduct.READY_TO_DISPATCH
                trip_shipment.shipment.save()

        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return trip_shipment


class DispatchTripCrudSerializers(serializers.ModelSerializer):
    seller_shop = ShopSerializer(read_only=True)
    source_shop = ShopSerializer(read_only=True)
    destination_shop = ShopSerializer(read_only=True)
    delivery_boy = UserSerializers(read_only=True)
    created_by = UserSerializers(read_only=True)
    updated_by = UserSerializers(read_only=True)
    # shipments_details = DispatchTripShipmentMappingSerializer(read_only=True, many=True)

    class Meta:
        model = DispatchTrip
        fields = ('id', 'seller_shop', 'source_shop', 'destination_shop', 'dispatch_no', 'delivery_boy', 'vehicle_no',
                  'trip_status', 'trip_type', 'starts_at', 'completed_at', 'opening_kms', 'closing_kms', 'no_of_crates',
                  'no_of_packets', 'no_of_sacks', 'no_of_crates_check', 'no_of_packets_check', 'no_of_sacks_check',
                  'no_of_shipments', 'trip_amount',
                  'created_at', 'updated_at', 'created_by', 'updated_by')

    def validate(self, data):

        if 'seller_shop' in self.initial_data and self.initial_data['seller_shop']:
            try:
                seller_shop = Shop.objects.get(id=self.initial_data['seller_shop'], shop_type__shop_type='sp')
                data['seller_shop'] = seller_shop
            except:
                raise serializers.ValidationError("Invalid seller_shop")
        else:
            raise serializers.ValidationError("'seller_shop' | This is mandatory")

        if 'source_shop' in self.initial_data and self.initial_data['source_shop']:
            try:
                source_shop = Shop.objects.get(id=self.initial_data['source_shop'],
                                               shop_type__shop_type__in=['sp', 'dc'])
                data['source_shop'] = source_shop
            except:
                raise serializers.ValidationError("Invalid source_shop")
        else:
            raise serializers.ValidationError("'source_shop' | This is mandatory")

        if 'destination_shop' in self.initial_data and self.initial_data['destination_shop']:
            try:
                destination_shop = Shop.objects.get(id=self.initial_data['destination_shop'],
                                                    shop_type__shop_type__in=['sp', 'dc'])
                data['destination_shop'] = destination_shop
            except:
                raise serializers.ValidationError("Invalid destination_shop")
        else:
            raise serializers.ValidationError("'destination_shop' | This is mandatory")

        if self.initial_data['source_shop'] == self.initial_data['destination_shop']:
            raise serializers.ValidationError("Invalid source & destination | Source & Destination can't be same.")

        if 'delivery_boy' in self.initial_data and self.initial_data['delivery_boy']:
            delivery_boy = User.objects.filter(id=self.initial_data['delivery_boy'],
                                               shop_employee__shop=seller_shop).last()
            if not delivery_boy:
                raise serializers.ValidationError("Invalid delivery_boy | User not found for " + str(seller_shop))
            if delivery_boy and delivery_boy.groups.filter(name='Delivery Boy').exists():
                data['delivery_boy'] = delivery_boy
            else:
                raise serializers.ValidationError("Delivery Boy does not have required permission.")
        else:
            raise serializers.ValidationError("'delivery_boy' | This is mandatory")

        if 'trip_type' in self.initial_data and self.initial_data['trip_type']:
            if any(self.initial_data['trip_type'] in i for i in DispatchTrip.DISPATCH_TRIP_TYPE):
                data['trip_type'] = self.initial_data['trip_type']
            else:
                raise serializers.ValidationError("Invalid type choice")

        if 'id' in self.initial_data and self.initial_data['id']:
            if not DispatchTrip.objects.filter(
                    id=self.initial_data['id'], seller_shop=seller_shop, source_shop=source_shop,
                    destination_shop=destination_shop).exists():
                raise serializers.ValidationError("Seller, Source & Destination shops updation are not allowed.")
            dispatch_trip = DispatchTrip.objects.filter(
                    id=self.initial_data['id'], seller_shop=seller_shop, source_shop=source_shop,
                    destination_shop=destination_shop).last()
            if 'vehicle_no' in self.initial_data and self.initial_data['vehicle_no']:
                if dispatch_trip.trip_status != DispatchTrip.NEW and \
                        dispatch_trip.vehicle_no != self.initial_data['vehicle_no']:
                    raise serializers.ValidationError(f"vehicle no updation not allowed at trip status "
                                                      f"{dispatch_trip.trip_status}")
                data['vehicle_no'] = self.initial_data['vehicle_no']
        else:
            if 'vehicle_no' in self.initial_data and self.initial_data['vehicle_no']:
                if (DispatchTrip.objects.filter(trip_status__in=[DispatchTrip.NEW, DispatchTrip.STARTED],
                                                vehicle_no=self.initial_data['vehicle_no']).exists() or
                        Trip.objects.filter(trip_status__in=[Trip.READY, Trip.STARTED],
                                            vehicle_no=self.initial_data['vehicle_no']).exists()):
                    raise serializers.ValidationError(f"This vehicle {self.initial_data['vehicle_no']} is already "
                                                      f"in use for another trip ")
                data['vehicle_no'] = self.initial_data['vehicle_no']
            else:
                raise serializers.ValidationError("'vehicle_no' | This is mandatory")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new DispatchTrip"""
        shipments_details = validated_data.pop("shipments_details", None)
        try:
            dispatch_trip_instance = DispatchTrip.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return dispatch_trip_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update DispatchTrip"""
        shipments_details = validated_data.pop("shipments_details", None)
        try:
            dispatch_trip_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return dispatch_trip_instance


class DispatchTripStatusChangeSerializers(serializers.ModelSerializer):
    seller_shop = ShopSerializer(read_only=True)
    source_shop = ShopSerializer(read_only=True)
    destination_shop = ShopSerializer(read_only=True)
    delivery_boy = UserSerializers(read_only=True)
    created_by = UserSerializers(read_only=True)
    updated_by = UserSerializers(read_only=True)
    # shipments_details = DispatchTripShipmentMappingSerializer(read_only=True, many=True)

    class Meta:
        model = DispatchTrip
        fields = ('id', 'seller_shop', 'source_shop', 'destination_shop', 'dispatch_no', 'delivery_boy', 'vehicle_no',
                  'trip_status', 'starts_at', 'completed_at', 'opening_kms', 'closing_kms', 'no_of_crates',
                  'no_of_packets', 'no_of_sacks', 'no_of_crates_check', 'no_of_packets_check', 'no_of_sacks_check',
                  'created_at', 'updated_at', 'created_by', 'updated_by')

    def validate(self, data):

        if 'id' in self.initial_data and self.initial_data['id']:
            if not DispatchTrip.objects.filter(id=self.initial_data['id']).exists():
                raise serializers.ValidationError("Only status updation is allowed.")
            dispatch_trip = DispatchTrip.objects.filter(id=self.initial_data['id']).last()
        else:
            raise serializers.ValidationError("'id' | This is mandatory")

        if 'seller_shop' in self.initial_data and self.initial_data['seller_shop']:
            try:
                seller_shop = Shop.objects.get(id=self.initial_data['seller_shop'], shop_type__shop_type='sp')
                if dispatch_trip.seller_shop != seller_shop:
                    raise Exception("'seller_shop' | Invalid seller_shop for selected trip.")
            except:
                raise serializers.ValidationError("'seller_shop' | Invalid seller shop")

        if 'source_shop' in self.initial_data and self.initial_data['source_shop']:
            try:
                source_shop = Shop.objects.get(id=self.initial_data['source_shop'],
                                               shop_type__shop_type__in=['sp', 'dc'])
                if dispatch_trip.source_shop != source_shop:
                    raise Exception("'source_shop' | Invalid source_shop for selected trip.")
            except:
                raise serializers.ValidationError("'source_shop' | Invalid source shop")

        if 'destination_shop' in self.initial_data and self.initial_data['destination_shop']:
            try:
                destination_shop = Shop.objects.get(id=self.initial_data['destination_shop'],
                                                    shop_type__shop_type__in=['sp', 'dc'])
                if dispatch_trip.destination_shop != destination_shop:
                    raise Exception("'destination_shop' | Invalid destination_shop for selected trip.")
            except:
                raise serializers.ValidationError("'destination_shop' | Invalid destination shop")

        if 'delivery_boy' in self.initial_data and self.initial_data['delivery_boy']:
            try:
                delivery_boy = User.objects.filter(id=self.initial_data['delivery_boy'],
                                                   shop_employee__shop=seller_shop).last()
                if dispatch_trip.delivery_boy != delivery_boy:
                    raise Exception("'delivery_boy' | Invalid delivery_boy for selected trip.")
            except:
                raise serializers.ValidationError("'delivery_boy' | Invalid delivery boy")

        if 'trip_status' in self.initial_data and self.initial_data['trip_status']:
            trip_status = self.initial_data['trip_status']
            if trip_status not in [DispatchTrip.NEW, DispatchTrip.STARTED, DispatchTrip.COMPLETED,
                                   DispatchTrip.UNLOADING, DispatchTrip.CLOSED, DispatchTrip.VERIFIED,
                                   DispatchTrip.CANCELLED]:
                raise serializers.ValidationError("'trip_status' | Invalid status for the selected trip.")
            if dispatch_trip.trip_status == trip_status:
                raise serializers.ValidationError(f"Trip status is already {str(trip_status)}.")
            if dispatch_trip.trip_status in [DispatchTrip.VERIFIED, DispatchTrip.CANCELLED]:
                raise serializers.ValidationError(f"Trip status can't update, already {str(dispatch_trip.trip_status)}")
            if (dispatch_trip.trip_status == DispatchTrip.NEW and
                trip_status not in [DispatchTrip.STARTED, DispatchTrip.CANCELLED]) or \
                    (dispatch_trip.trip_status == DispatchTrip.STARTED and trip_status != DispatchTrip.COMPLETED) or \
                    (dispatch_trip.trip_status == DispatchTrip.COMPLETED and trip_status != DispatchTrip.UNLOADING) or \
                    (dispatch_trip.trip_status == DispatchTrip.UNLOADING and trip_status != DispatchTrip.CLOSED) or \
                    (dispatch_trip.trip_status == DispatchTrip.CLOSED and trip_status != DispatchTrip.VERIFIED):
                raise serializers.ValidationError(
                    f"'trip_status' | Trip status can't be {str(trip_status)} at the moment.")

            if trip_status == DispatchTrip.STARTED:
                if 'opening_kms' in self.initial_data and self.initial_data['opening_kms']>=0:
                    try:
                        opening_kms = int(self.initial_data['opening_kms'])
                        data['opening_kms'] = opening_kms
                    except:
                        raise serializers.ValidationError("'opening_kms' | Invalid value")
                else:
                     raise serializers.ValidationError("'opening_kms' | This is mandatory")

                if not dispatch_trip.shipments_details.exists():
                    raise serializers.ValidationError("Load shipments to the trip to start.")

                if dispatch_trip.shipments_details.filter(
                        shipment_status=DispatchTripShipmentMapping.LOADING_FOR_DC).exists():
                    raise serializers.ValidationError(
                        "The trip can not start until and unless all shipments get loaded.")

            if trip_status == DispatchTrip.COMPLETED:
                if 'closing_kms' in self.initial_data and self.initial_data['closing_kms']:
                    try:
                        closing_kms = int(self.initial_data['closing_kms'])
                        data['closing_kms'] = closing_kms
                    except:
                        raise serializers.ValidationError("'closing_kms' | Invalid value")
                else:
                     raise serializers.ValidationError("'closing_kms' | This is mandatory")

            if trip_status == DispatchTrip.CLOSED:
                if dispatch_trip.shipments_details.filter(
                        shipment_status=DispatchTripShipmentMapping.UNLOADING_AT_DC).exists():
                    raise serializers.ValidationError(
                        "The trip can not complete until and unless all shipments get unloaded.")

            if trip_status == DispatchTrip.VERIFIED:
                if DispatchTripShipmentPackages.objects.filter(
                        trip_shipment__trip=dispatch_trip, package_status=DispatchTripShipmentPackages.UNLOADED,
                        is_return_verified=False).exists():
                    return serializers.ValidationError(
                        "The trip can not verify until and unless all unloaded packages get verified.")

            data['trip_status'] = trip_status
        else:
            raise serializers.ValidationError("'trip_status' | This is mandatory")

        return data

    def unloading_added_shipments_to_trip(self, dispatch_trip):
        shipment_details = dispatch_trip.shipments_details.filter(
            shipment_status=DispatchTripShipmentMapping.LOADED_FOR_DC)
        shipment_details.update(shipment_status=DispatchTripShipmentMapping.UNLOADING_AT_DC)

    def dispatch_added_shipments_to_trip(self, dispatch_trip):
        shipment_details = dispatch_trip.shipments_details.all()
        for shipment_detail in shipment_details:
            # if shipment_detail.shipment.shipment_status == OrderedProduct.READY_TO_DISPATCH:
            #     shipment_detail.shipment.shipment_status = OrderedProduct.IN_TRANSIT_TO_DISPATCH
            #     shipment_detail.shipment.save()
            shipment_packagings = shipment_detail.trip_shipment_mapped_packages.all()
            for mapping in shipment_packagings:
                if mapping.package_status in [DispatchTripShipmentPackages.LOADED,
                                              DispatchTripShipmentPackages.DAMAGED_AT_LOADING,
                                              DispatchTripShipmentPackages.MISSING_AT_LOADING] and \
                        mapping.shipment_packaging.status == ShipmentPackaging.DISPATCH_STATUS_CHOICES.READY_TO_DISPATCH:
                    mapping.shipment_packaging.status = ShipmentPackaging.DISPATCH_STATUS_CHOICES.DISPATCHED
                    mapping.shipment_packaging.save()

    def cancel_added_shipments_to_trip(self, dispatch_trip):
        shipment_details = dispatch_trip.shipments_details.all()
        for mapping in shipment_details:
            if mapping.shipment.shipment_status == OrderedProduct.READY_TO_DISPATCH:
                mapping.shipment.shipment_status = OrderedProduct.MOVED_TO_DISPATCH
                mapping.shipment.save()
        DispatchTripShipmentPackages.objects.filter(
            trip_shipment__in=shipment_details).update(package_status=DispatchTripShipmentPackages.CANCELLED)
        shipment_details.update(shipment_status=DispatchTripShipmentMapping.CANCELLED)

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update DispatchTrip"""
        shipments_details = validated_data.pop("shipments_details", None)
        try:
            dispatch_trip_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        if validated_data['trip_status'] == DispatchTrip.STARTED:
            self.dispatch_added_shipments_to_trip(dispatch_trip_instance)

        if validated_data['trip_status'] == DispatchTrip.UNLOADING:
            self.unloading_added_shipments_to_trip(dispatch_trip_instance)

        if validated_data['trip_status'] == DispatchTrip.CANCELLED:
            self.cancel_added_shipments_to_trip(dispatch_trip_instance)

        return dispatch_trip_instance


class LastMileTripShipmentMappingSerializers(serializers.ModelSerializer):
    trip = DispatchTripSerializers(read_only=True)

    class Meta:
        model = LastMileTripShipmentMapping
        fields = ('id', 'trip')


class ShipmentReschedulingListingSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = ShipmentRescheduling
        fields = ('shipment', 'rescheduling_reason', 'rescheduling_date', 'created_by', 'created_at', 'modified_at',)


class ShipmentNotAttemptListingSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = ShipmentNotAttempt
        fields = ('shipment', 'not_attempt_reason', 'created_by', 'created_at', 'modified_at',)


class DispatchShipmentSerializers(serializers.ModelSerializer):
    trip = serializers.SerializerMethodField()
    shop_owner = serializers.SerializerMethodField()
    order_created_date = serializers.SerializerMethodField()
    shipment_status = ChoicesSerializer(choices=OrderedProduct.SHIPMENT_STATUS, required=True)
    not_attempt = serializers.SerializerMethodField()
    rescheduling = serializers.SerializerMethodField()

    @staticmethod
    def get_trip(obj):
        dispatch_trip = obj.trip_shipment.last()
        last_mile_trip = obj.last_mile_trip_shipment.last()
        if dispatch_trip and last_mile_trip:
            if dispatch_trip.created_at > last_mile_trip.created_at:
                return DispatchTripShipmentMappingSerializer(dispatch_trip, read_only=True).data
            return LastMileTripShipmentMappingSerializers(last_mile_trip, read_only=True).data
        elif dispatch_trip:
            return DispatchTripShipmentMappingSerializer(dispatch_trip, read_only=True).data
        elif last_mile_trip:
            return LastMileTripShipmentMappingSerializers(last_mile_trip, read_only=True).data
        return None

    @staticmethod
    def get_not_attempt(obj):
        if obj.not_attempt_shipment.exists():
            return ShipmentNotAttemptListingSerializer(obj.not_attempt_shipment.last(), read_only=True).data
        return None

    @staticmethod
    def get_rescheduling(obj):
        if obj.rescheduling_shipment.exists():
            return ShipmentReschedulingListingSerializer(obj.rescheduling_shipment.last(), read_only=True).data
        return None

    @staticmethod
    def get_shop_owner(obj):
        return UserSerializers(obj.order.buyer_shop.shop_owner, read_only=True).data

    @staticmethod
    def get_order_created_date(obj):
        return obj.order.created_at.strftime("%d/%b/%Y")

    class Meta:
        model = OrderedProduct
        fields = ('id', 'trip', 'invoice_no', 'shipment_status', 'shipment_address', 'shop_owner',
                  'order_created_date', 'no_of_crates', 'no_of_packets', 'no_of_sacks', 'no_of_crates_check',
                  'no_of_packets_check', 'no_of_sacks_check', 'is_customer_notified', 'not_attempt', 'rescheduling')


class OrderDetailForShipmentSerializer(serializers.ModelSerializer):
    seller_shop = ShopSerializer()
    buyer_shop = ShopSerializer()
    dispatch_center = ShopSerializer()
    shipping_address = AddressSerializer()
    order_status = serializers.CharField(source='get_order_status_display')
    received_by = UserSerializer(read_only=True)

    def to_representation(self, instance):
        representation = super(OrderDetailForShipmentSerializer, self).to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d - %H:%M:%S")
        return representation

    class Meta:
        model = Order
        fields = ('id', 'order_no', 'seller_shop', 'buyer_shop', 'dispatch_delivery', 'dispatch_center',
                  'shipping_address', 'total_mrp', 'total_discount_amount', 'total_tax_amount', 'total_final_amount',
                  'order_status', 'received_by', 'created_at', 'modified_at')

class ShipmentDetailTripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ('id', 'trip_id', 'seller_shop', 'source_shop', 'dispatch_no', 'vehicle_no', 'delivery_boy',
                  'trip_status')

class ShipmentDetailsByCrateSerializer(serializers.ModelSerializer):
    shop_owner_name = serializers.SerializerMethodField()
    shop_owner_number = serializers.SerializerMethodField()
    shipment_status = serializers.SerializerMethodField()
    order = OrderDetailForShipmentSerializer(read_only=True)
    shipment_crates_packaging = serializers.SerializerMethodField()
    total_shipment_crates = serializers.SerializerMethodField()
    trip = serializers.SerializerMethodField()
    trip_belongs_to = serializers.SerializerMethodField()

    def get_trip(self, obj):
        return ShipmentDetailTripSerializer(obj.last_mile_trip_shipment.last().trip
                                            if obj.last_mile_trip_shipment.exists() else obj.trip).data


    def get_trip_belongs_to(self, obj):
        if obj.last_mile_trip_shipment.last():
            if obj.last_mile_trip_shipment.last().trip.source_shop.shop_type.shop_type == 'sp':
                return "WAREHOUSE"
            elif obj.last_mile_trip_shipment.last().trip.source_shop.shop_type.shop_type == 'dc':
                return "DISPATCH"
        return None

    def get_shipment_status(self, obj):
        return obj.get_shipment_status_display()

    def get_shop_owner_number(self, obj):
        shop_owner_number = obj.order.buyer_shop.shop_owner.phone_number
        return shop_owner_number

    def get_shop_owner_name(self, obj):
        shop_owner_name = obj.order.buyer_shop.shop_owner.first_name + obj.order.buyer_shop.shop_owner.last_name
        return shop_owner_name

    def get_shipment_crates_packaging(self, obj):
        if obj:
            return DispatchItemsSerializer(obj.shipment_packaging.filter(
                packaging_type=ShipmentPackaging.CRATE, crate__isnull=False, movement_type=ShipmentPackaging.DISPATCH),
                read_only=True, many=True).data
        return None

    def get_total_shipment_crates(self, obj):
        if obj:
            return obj.shipment_packaging.filter(packaging_type=ShipmentPackaging.CRATE, crate__isnull=False).count()
        return None

    class Meta:
        model = OrderedProduct
        fields = ('id', 'invoice_no', 'shipment_status', 'invoice_amount', 'order', 'payment_mode', 'shipment_address',
                  'shop_owner_name', 'shop_owner_number', 'shipment_crates_packaging', 'total_shipment_crates', 'trip',
                  'trip_belongs_to')


class ShipmentPackageSerializer(serializers.ModelSerializer):
    trip_loading_status = serializers.SerializerMethodField()
    crate = CrateSerializer(read_only=True)
    packaging_type = ChoicesSerializer(choices=ShipmentPackaging.PACKAGING_TYPE_CHOICES, required=True)
    shipment = ShipmentSerializerForDispatch(read_only=True)
    is_return_verified = serializers.SerializerMethodField()

    def get_is_return_verified(self, obj):
        return True if obj.status in [ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_VERIFIED,
                               ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_MISSING,
                               ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_DAMAGED] else False

    def get_trip_loading_status(self, obj):
        return obj.trip_packaging_details.last().package_status \
            if obj.trip_packaging_details.filter(~Q(package_status=DispatchTripShipmentPackages.CANCELLED)).exists() else None

    class Meta:
        model = ShipmentPackaging
        fields = ('id', 'shipment', 'packaging_type', 'crate', 'return_remark', 'trip_loading_status',
                  'is_return_verified')

    def validate(self, data):

        if 'shop' in self.initial_data and self.initial_data['shop']:
            try:
                shop = Shop.objects.get(id=self.initial_data['shop'], shop_type__shop_type__in=['sp', 'dc'])
                data['warehouse'] = shop
            except:
                raise serializers.ValidationError("Invalid shop")
        else:
            raise serializers.ValidationError("'shop' | This is mandatory")

        if 'crate_id' in self.initial_data and self.initial_data['crate_id']:
            if not Crate.objects.filter(crate_id=self.initial_data['crate_id'], crate_type=Crate.DISPATCH,
                                        shop_crates__shop=shop).exists():
                raise serializers.ValidationError("'crate_id' | Invalid crate selected.")
            crate = Crate.objects.filter(crate_id=self.initial_data['crate_id'], crate_type=Crate.DISPATCH,
                                         shop_crates__shop=shop).last()
            data['crate'] = crate
        else:
            raise serializers.ValidationError("'crate_id' | This is mandatory")

        if 'shipment_id' in self.initial_data and self.initial_data['shipment_id']:
            if not OrderedProduct.objects.filter(id=self.initial_data['shipment_id']).exists():
                raise serializers.ValidationError("'shipment_id' | Invalid shipment selected.")
            shipment = OrderedProduct.objects.filter(id=self.initial_data['shipment_id']).last()
            data['shipment'] = shipment
        else:
            raise serializers.ValidationError("'shipment_id' | This is mandatory")

        if ShipmentPackaging.objects.filter(crate=crate, shipment=shipment).exists():
            shipment_packaging = ShipmentPackaging.objects.filter(warehouse=shop, crate=crate, shipment=shipment).last()
        else:
            raise serializers.ValidationError("Shipment packaging not found for selected shipment and crate.")

        if 'status' in self.initial_data and self.initial_data['status']:
            if self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.OK:
                status = ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_VERIFIED
            elif self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.DAMAGED:
                status = ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_DAMAGED
            elif self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.MISSING:
                status = ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_MISSING
            else:
                raise serializers.ValidationError("'status' | Invalid status for the selected shipment packaging.")
            if shipment_packaging.status == status:
                raise serializers.ValidationError(f"Packaging status is already {str(status)}.")
            if shipment_packaging.status not in [ShipmentPackaging.DISPATCH_STATUS_CHOICES.REJECTED,
                                                 ShipmentPackaging.DISPATCH_STATUS_CHOICES.DISPATCHED,
                                                 ShipmentPackaging.DISPATCH_STATUS_CHOICES.DELIVERED]:
                raise serializers.ValidationError(f"Invalid Crate status  | can't update")

            if status in [ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_MISSING,
                          ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_DAMAGED]:
                if 'return_remark' in self.initial_data and self.initial_data['return_remark']:
                    if any(self.initial_data['return_remark'] in i for i in ShipmentPackaging.RETURN_REMARK_CHOICES):
                        data['return_remark'] = self.initial_data['return_remark']
                    else:
                        raise serializers.ValidationError("'return_remark' | Invalid remark.")
                else:
                    raise serializers.ValidationError("'return_remark' | This is mandatory for missing or damage.")
            data['status'] = status
        else:
            raise serializers.ValidationError("'status' | This is mandatory")

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update ShipmentPackaging"""
        try:
            packaging_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        # self.post_shipment_packaging_status_change(packaging_instance.shipment)
        self.mark_crate_available(packaging_instance)
        return packaging_instance

    def post_shipment_packaging_status_change(self, shipment_instance):
        '''
            Update the Shipment status on all crates scanned for fully delivered shipment
        '''
        info_logger.info(f"post_shipment_packaging_status_change|Shipment ID {shipment_instance.id}")
        if shipment_instance.shipment_status == OrderedProduct.DELIVERED:
            if not shipment_instance.shipment_packaging.filter(
                    ~Q(status__in=[ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_VERIFIED,
                                   ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_MISSING,
                                   ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_DAMAGED]),
                    packaging_type=ShipmentPackaging.CRATE).exists():
                shipment_instance.shipment_status = OrderedProduct.FULLY_DELIVERED_AND_VERIFIED
                shipment_instance.save()
            info_logger.info(f"post_shipment_packaging_status_change|Shipment status updated|Shipment ID "
                             f"{shipment_instance.id}")

    def mark_crate_available(self, packaging_instance):
        info_logger.info(f"mark_crate_used|Packaging instance {packaging_instance}")
        shop_crate_instance = ShopCrate.objects.update_or_create(
            shop=packaging_instance.warehouse, crate=packaging_instance.crate, defaults={'is_available': True})
        info_logger.info(f"mark_crate_used|Marked| {shop_crate_instance}")


class VerifyRescheduledShipmentPackageSerializer(serializers.ModelSerializer):
    packaging_details = DispatchItemDetailsSerializer(many=True, read_only=True)
    crate = CrateSerializer(read_only=True)
    packaging_type = ChoicesSerializer(choices=ShipmentPackaging.PACKAGING_TYPE_CHOICES, required=True)

    class Meta:
        model = ShipmentPackaging
        fields = ('id', 'packaging_type', 'crate', 'status', 'return_remark', 'reason_for_rejection','packaging_details')

    def validate(self, data):

        if 'package_id' in self.initial_data and self.initial_data['package_id']:
            if ShipmentPackaging.objects.filter(id=self.initial_data['package_id']).exists():
                shipment_packaging = ShipmentPackaging.objects.filter(id=self.initial_data['package_id']).last()
            else:
                raise serializers.ValidationError("Shipment packaging not found for selected shipment and crate.")
        else:
            raise serializers.ValidationError("'package_id' | This is mandatory")

        if 'shipment_id' in self.initial_data and self.initial_data['shipment_id']:
            if not OrderedProduct.objects.filter(
                    id=self.initial_data['shipment_id'], shipment__shipment_status=OrderedProduct.RESCHEDULED).exists():
                raise serializers.ValidationError("'shipment_id' | Invalid shipment selected.")
            shipment = OrderedProduct.objects.filter(
                id=self.initial_data['shipment_id'], shipment__shipment_status=OrderedProduct.RESCHEDULED).last()
            if shipment != shipment_packaging.shipment:
                raise serializers.ValidationError("'shipment_id' | Invalid shipment for the selected package")
            data['shipment'] = shipment
        else:
            raise serializers.ValidationError("'shipment_id' | This is mandatory")

        if 'trip_id' in self.initial_data and self.initial_data['trip_id']:
            if not Trip.objects.filter(id=self.initial_data['trip_id'],  trip_status=Trip.COMPLETED).exists():
                raise serializers.ValidationError("'Trip' | Invalid trip.")
            trip = Trip.objects.filter(id=self.initial_data['trip_id'],  trip_status=Trip.COMPLETED).last()
            if not LastMileTripShipmentMapping.objects.filter(trip=trip, shipment=shipment).exists():
                raise serializers.ValidationError("'shipment_id' | Invalid shipment for the selected trip")
        else:
            raise serializers.ValidationError("'trip_id' | This is mandatory")

        if 'status' in self.initial_data and self.initial_data['status']:
            if self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.OK:
                status = ShipmentPackaging.DISPATCH_STATUS_CHOICES.READY_TO_DISPATCH
            elif self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.DAMAGED:
                status = ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_DAMAGED
            elif self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.MISSING:
                status = ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_MISSING
            else:
                raise serializers.ValidationError("'status' | Invalid status for the selected shipment packaging.")
            if shipment_packaging.status == status:
                raise serializers.ValidationError(f"Packaging status is already {str(status)}.")
            if shipment_packaging.status not in [ShipmentPackaging.DISPATCH_STATUS_CHOICES.REJECTED,
                                                 ShipmentPackaging.DISPATCH_STATUS_CHOICES.DISPATCHED,
                                                 ShipmentPackaging.DISPATCH_STATUS_CHOICES.DELIVERED]:
                raise serializers.ValidationError(f"Current status is  {str(shipment_packaging.status)} | can't update")

            if status in [ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_MISSING,
                          ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_DAMAGED]:
                if 'return_remark' in self.initial_data and self.initial_data['return_remark']:
                    if any(self.initial_data['return_remark'] in i for i in ShipmentPackaging.RETURN_REMARK_CHOICES):
                        data['return_remark'] = self.initial_data['return_remark']
                    else:
                        raise serializers.ValidationError("'return_remark' | Invalid remark.")
                else:
                    raise serializers.ValidationError("'return_remark' | This is mandatory for missing or damage.")
            data['status'] = self.initial_data['status']
        else:
            raise serializers.ValidationError("'status' | This is mandatory")

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update ShipmentPackaging"""
        try:
            packaging_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return packaging_instance


class SummarySerializer(serializers.Serializer):
    total_invoices = serializers.IntegerField()
    total_crates = serializers.IntegerField()
    total_packets = serializers.IntegerField()
    total_sack = serializers.IntegerField()
    weight = serializers.IntegerField()


class TripSummarySerializer(serializers.Serializer):
    trip_data = SummarySerializer(read_only=True)
    non_trip_data = SummarySerializer(read_only=True)


class DispatchInvoiceSerializer(serializers.ModelSerializer):
    order = OrderSerializerForShipment(read_only=True)
    trip = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()

    def get_trip(self, obj):
        return DispatchTripSerializers(obj.trip_shipment.last().trip).data \
                if obj.trip_shipment.filter(shipment_status__in=[
                                                 DispatchTripShipmentMapping.LOADED_FOR_DC,
                                                 DispatchTripShipmentMapping.UNLOADING_AT_DC,
                                                 DispatchTripShipmentMapping.UNLOADED_AT_DC]).exists() else None

    def get_created_date(self, obj):
        return obj.created_at.strftime("%d/%b/%y %H:%M")

    class Meta:
        model = OrderedProduct
        fields = ('id', 'order', 'shipment_status', 'invoice_no', 'invoice_amount', 'trip', 'created_date')


class DispatchCenterCrateSerializer(serializers.ModelSerializer):
    crate = CrateSerializer(read_only=True)
    trip = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()

    def get_trip(self, obj):
        return DispatchTripSerializers(obj.crate.crate_trips.last().trip).data \
            if not obj.is_available and obj.crate.crate_trips.exists() else None

    def get_created_date(self, obj):
        return obj.created_at.strftime("%d/%b/%y %H:%M")

    class Meta:
        model = ShopCrate
        fields = ('id', 'trip', 'crate', 'created_date')


class DispatchCenterShipmentPackageSerializer(serializers.ModelSerializer):
    crate = CrateSerializer(read_only=True)
    trip = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()
    shipment = ShipmentSerializerForDispatch()
    packaging_type = ChoicesSerializer(choices=ShipmentPackaging.PACKAGING_TYPE_CHOICES, required=False)
    trip_loading_status = serializers.SerializerMethodField()

    def get_trip_loading_status(self, obj):
        return obj.trip_packaging_details.last().package_status \
            if obj.trip_packaging_details.filter(~Q(package_status=DispatchTripShipmentPackages.CANCELLED)).exists() else None

    def get_trip(self, obj):
        if obj.status == 'READY_TO_DISPATCH' and obj.shipment.packaged_at:
            return DispatchTripSerializers(obj.shipment.last_trip).data
        return None

    def get_created_date(self, obj):
        return obj.created_at.strftime("%d/%b/%y %H:%M")

    class Meta:
        model = ShipmentPackaging
        fields = ('id', 'trip', 'shipment', 'packaging_type', 'crate', 'reason_for_rejection',
                  'movement_type', 'return_remark', 'created_date', 'trip_loading_status')


class LoadVerifyCrateSerializer(serializers.ModelSerializer):

    trip = DispatchTripSerializers(read_only=True)
    crate = CrateSerializer(read_only=True)
    crate_status = ChoicesSerializer(choices=DispatchTripCrateMapping.CRATE_STATUS, required=False)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = DispatchTripCrateMapping
        fields = ('trip', 'crate', 'crate_status', 'created_by', 'updated_by')

    def validate(self, data):
        # Validate request data
        if 'id' in self.initial_data:
            raise serializers.ValidationError('Updation is not allowed')
        if 'trip_id' not in self.initial_data or not self.initial_data['trip_id']:
            raise serializers.ValidationError("'trip_id' | This is required.")
        try:
            trip = DispatchTrip.objects.get(id=self.initial_data['trip_id'])
            data['trip'] = trip
        except:
            raise serializers.ValidationError("invalid Trip ID")

        # Check for trip status
        if trip.trip_status != DispatchTrip.NEW:
            raise serializers.ValidationError(f"Trip is in {trip.trip_status} state, cannot load empty crate")

        if 'crate_id' in self.initial_data and self.initial_data['crate_id']:
            if Crate.objects.filter(id=self.initial_data['crate_id'], crate_type=Crate.DISPATCH,
                                    shop_crates__shop=trip.source_shop, shop_crates__is_available=True).exists():
                crate = Crate.objects.filter(id=self.initial_data['crate_id'], crate_type=Crate.DISPATCH,
                                             shop_crates__shop=trip.source_shop, shop_crates__is_available=True).last()
                data['crate'] = crate
            else:
                raise serializers.ValidationError("'crate_id' | Invalid crate selected.")
        else:
            raise serializers.ValidationError("'crate_id' | This is mandatory")

        # Check if crate already scanned
        if trip.trip_empty_crates.filter(crate=crate).exists():
            raise serializers.ValidationError("This package has already been verified.")
        if 'status' not in self.initial_data or not self.initial_data['status']:
            raise serializers.ValidationError("'status' | This is required.")
        elif self.initial_data['status'] not in [1, 2]:
            raise serializers.ValidationError("Invalid status choice")

        status = DispatchTripCrateMapping.LOADED
        if self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.DAMAGED:
            status = DispatchTripCrateMapping.DAMAGED_AT_LOADING

        data['trip'] = trip
        data['crate'] = crate
        data['crate_status'] = status

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new DispatchTrip Package Mapping"""
        try:
            instance = DispatchTripCrateMapping.objects.create(**validated_data)
            self.post_crate_load_trip_update(instance)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return instance

    def post_crate_load_trip_update(self, trip_crate_mapping):
        info_logger.info(f"post_crate_load_trip_update|trip_crate_mapping {trip_crate_mapping}")
        # Update total no of empty crates
        trip = trip_crate_mapping.trip
        if trip_crate_mapping.crate_status == DispatchTripCrateMapping.LOADED:
            trip.no_of_empty_crates = trip.no_of_empty_crates + 1
            trip.save()

        # Make crate used at source
        shop = trip_crate_mapping.trip.source_shop
        crate = trip_crate_mapping.crate
        shop_crate_instance = ShopCrate.objects.update_or_create(
            shop=shop, crate=crate, defaults={'is_available': False})
        info_logger.info(f"Crate marked used| {shop_crate_instance}")


class UnloadVerifyCrateSerializer(serializers.ModelSerializer):
    trip = DispatchTripSerializers(read_only=True)
    crate = CrateSerializer(read_only=True)
    crate_status = ChoicesSerializer(choices=DispatchTripCrateMapping.CRATE_STATUS, required=False)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = DispatchTripCrateMapping
        fields = ('trip', 'crate', 'crate_status', 'created_by', 'updated_by')

    def validate(self, data):
        # Validate request data
        if 'id' in self.initial_data:
            raise serializers.ValidationError('Updation is not allowed')
        if 'trip_id' not in self.initial_data or not self.initial_data['trip_id']:
            raise serializers.ValidationError("'trip_id' | This is required.")
        try:
            trip = DispatchTrip.objects.get(id=self.initial_data['trip_id'])
            data['trip'] = trip
        except:
            raise serializers.ValidationError("invalid Trip ID")

        # Check for trip status
        if trip.trip_status != DispatchTrip.UNLOADING:
            raise serializers.ValidationError(f"Trip is in {trip.trip_status} state, cannot unload empty crate")

        if 'crate_id' in self.initial_data and self.initial_data['crate_id']:
            if not Crate.objects.filter(id=self.initial_data['crate_id'], crate_type=Crate.DISPATCH).exists():
                raise serializers.ValidationError("'crate_id' | Invalid crate selected.")
            crate = Crate.objects.filter(id=self.initial_data['crate_id'], crate_type=Crate.DISPATCH).last()
            data['crate'] = crate
        else:
            raise serializers.ValidationError("'crate_id' | This is mandatory")

        # Check if crate already scanned
        if not trip.trip_empty_crates.filter(
                crate=crate, crate_status__in=[
                    DispatchTripCrateMapping.LOADED, DispatchTripCrateMapping.DAMAGED_AT_LOADING,
                    DispatchTripCrateMapping.MISSING_AT_LOADING]).exists():
            raise serializers.ValidationError("This crate was not loaded to the trip.")
        if trip.trip_empty_crates.filter(
                crate=crate, crate_status__in=[
                    DispatchTripCrateMapping.UNLOADED, DispatchTripCrateMapping.DAMAGED_AT_UNLOADING,
                    DispatchTripCrateMapping.MISSING_AT_UNLOADING]).exists():
            raise serializers.ValidationError("This crate has already been verified.")

        if 'status' not in self.initial_data or not self.initial_data['status']:
            raise serializers.ValidationError("'status' | This is required.")
        elif self.initial_data['status'] not in PACKAGE_VERIFY_CHOICES._db_values:
            raise serializers.ValidationError("Invalid status choice")

        status = DispatchTripCrateMapping.UNLOADED
        if self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.DAMAGED:
            status = DispatchTripCrateMapping.DAMAGED_AT_UNLOADING
        elif self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.MISSING:
            status = DispatchTripCrateMapping.MISSING_AT_UNLOADING

        data['trip'] = trip
        data['crate'] = crate
        data['crate_status'] = status

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        """update DispatchTrip Package Mapping"""
        try:
            instance = super().update(instance, validated_data)
            self.post_crate_unload_trip_update(instance)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return instance

    def post_crate_unload_trip_update(self, trip_crate_mapping):
        info_logger.info(f"post_crate_unload_trip_update|trip_crate_mapping {trip_crate_mapping}")
        # Make crate available at destination
        shop = trip_crate_mapping.trip.destination_shop
        crate = trip_crate_mapping.crate
        shop_crate_instance = ShopCrate.objects.update_or_create(
            shop=shop, crate=crate, defaults={'is_available': True})
        info_logger.info(f"Crate marked available| {shop_crate_instance}")


class LoadVerifyPackageSerializer(serializers.ModelSerializer):

    trip_shipment = DispatchTripShipmentMappingSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = DispatchTripShipmentPackages
        fields = ('trip_shipment', 'created_by', 'updated_by')

    def validate(self, data):
        # Validate request data
        if 'id' in self.initial_data:
            raise serializers.ValidationError('Updating package is not allowed')
        if 'trip_id' not in self.initial_data or not self.initial_data['trip_id']:
            raise serializers.ValidationError("'trip_id' | This is required.")
        try:
            trip = DispatchTrip.objects.get(id=self.initial_data['trip_id'])
        except:
            raise serializers.ValidationError("invalid Trip ID")

        # Check for trip status
        if trip.trip_status != DispatchTrip.NEW:
            raise serializers.ValidationError(f"Trip is in {trip.trip_status} state, cannot load package")

        if 'package_id' not in self.initial_data or not self.initial_data['package_id']:
            raise serializers.ValidationError("'package_id' | This is required.")

        if trip.trip_type == DispatchTrip.FORWARD:
            package = ShipmentPackaging.objects.filter(
                id=self.initial_data['package_id'], warehouse=trip.source_shop, movement_type__in=[
                    ShipmentPackaging.DISPATCH, ShipmentPackaging.RESCHEDULED, ShipmentPackaging.NOT_ATTEMPT],
                shipment__order__seller_shop=trip.seller_shop).last()
            if not package:
                raise serializers.ValidationError("Invalid package for the trip")

            # Check for shipment status
            if package.shipment.shipment_status != OrderedProduct.MOVED_TO_DISPATCH:
                raise serializers.ValidationError(f"The invoice is in {package.shipment.shipment_status} state, "
                                                  f"cannot load package")
            if package.shipment.trip_shipment.exclude(
                    Q(trip=trip) | Q(shipment_status=DispatchTripShipmentMapping.CANCELLED)).exists():
                raise serializers.ValidationError(f"The invoice is already being added to another trip, "
                                                  f"cannot add this package")

            # Check for package status
            if package.status != ShipmentPackaging.DISPATCH_STATUS_CHOICES.READY_TO_DISPATCH:
                raise serializers.ValidationError(f"Package is in {package.status} state, Cannot be loaded")

        elif trip.trip_type == DispatchTrip.BACKWARD:
            package = ShipmentPackaging.objects.filter(
                id=self.initial_data['package_id'], warehouse=trip.source_shop,
                movement_type=ShipmentPackaging.RETURNED, shipment__order__seller_shop=trip.seller_shop).last()
            if not package:
                raise serializers.ValidationError("Invalid package for the trip")

            # Check for shipment status
            if package.shipment.shipment_status not in [OrderedProduct.FULLY_RETURNED_AND_VERIFIED,
                                                        OrderedProduct.PARTIALLY_DELIVERED_AND_VERIFIED]:
                raise serializers.ValidationError(f"The invoice is in {package.shipment.shipment_status} state, "
                                                  f"cannot load package")

            # Check for package status
            if package.status != ShipmentPackaging.DISPATCH_STATUS_CHOICES.PACKED:
                raise serializers.ValidationError(f"Package is in {package.status} state, Cannot be loaded")

        else:
            raise serializers.ValidationError(f"Trip is of {trip.trip_type} type, cannot load package")

        # Check if package already scanned
        if package.trip_packaging_details.filter(~Q(package_status=DispatchTripShipmentPackages.CANCELLED)).exists():
            raise serializers.ValidationError("This package has already been verified.")
        if 'status' not in self.initial_data or not self.initial_data['status']:
            raise serializers.ValidationError("'status' | This is required.")
        elif self.initial_data['status'] not in PACKAGE_VERIFY_CHOICES._db_values:
            raise serializers.ValidationError("Invalid status choice")

        # Check if invoice loading already completed
        if DispatchTripShipmentMapping.objects.filter(trip=trip, shipment=package.shipment,
                                                      shipment_status=DispatchTripShipmentMapping.LOADED_FOR_DC).exists():
            raise serializers.ValidationError("The invoice loading is already completed.")

        trip_shipment = None
        if DispatchTripShipmentMapping.objects.filter(
                trip=trip, shipment=package.shipment,
                shipment_status=DispatchTripShipmentMapping.LOADING_FOR_DC).exists():
            trip_shipment = DispatchTripShipmentMapping.objects.filter(
                trip=trip, shipment=package.shipment, shipment_status=DispatchTripShipmentMapping.LOADING_FOR_DC).last()
            current_invoice_being_loaded = trip_shipment.shipment
            if current_invoice_being_loaded != package.shipment:
                raise serializers.ValidationError(f"Please scan the remaining box in invoice no."
                                                  f" {current_invoice_being_loaded.invoice_no}")

        status = DispatchTripShipmentPackages.LOADED
        if self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.DAMAGED:
            status = DispatchTripShipmentPackages.DAMAGED_AT_LOADING
        elif self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.MISSING:
            status = DispatchTripShipmentPackages.MISSING_AT_LOADING

        shipment_health = trip_shipment.shipment_health if trip_shipment else DispatchTripShipmentMapping.OKAY
        if status == DispatchTripShipmentPackages.DAMAGED_AT_LOADING and shipment_health == DispatchTripShipmentMapping.PARTIALLY_MISSING:
            shipment_health = DispatchTripShipmentMapping.PARTIALLY_MISSING_DAMAGED
        elif status == DispatchTripShipmentPackages.MISSING_AT_LOADING and shipment_health == DispatchTripShipmentMapping.PARTIALLY_DAMAGED:
            shipment_health = DispatchTripShipmentMapping.PARTIALLY_MISSING_DAMAGED
        elif status == DispatchTripShipmentPackages.DAMAGED_AT_LOADING:
            shipment_health = DispatchTripShipmentMapping.PARTIALLY_DAMAGED
        elif status == DispatchTripShipmentPackages.MISSING_AT_LOADING:
            shipment_health = DispatchTripShipmentMapping.PARTIALLY_MISSING

        data['trip_shipment_mapping'] = {}
        data['trip_shipment_mapping']['trip'] = trip
        data['trip_shipment_mapping']['shipment'] = package.shipment
        data['trip_shipment_mapping']['shipment_status'] = DispatchTripShipmentMapping.LOADING_FOR_DC
        data['trip_shipment_mapping']['shipment_health'] = shipment_health

        data['trip_package_mapping'] = {}
        data['trip_package_mapping']['trip_shipment'] = trip_shipment
        data['trip_package_mapping']['shipment_packaging'] = package
        data['trip_package_mapping']['package_status'] = status

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new DispatchTrip Package Mapping"""
        try:
            trip_shipment = validated_data['trip_package_mapping']['trip_shipment']
            if not trip_shipment:
                trip_shipment = DispatchTripShipmentMapping.objects.create(**validated_data['trip_shipment_mapping'])
            else:
                trip_shipment.shipment_health = validated_data['trip_shipment_mapping']['shipment_health']
                trip_shipment.save()
            validated_data['trip_package_mapping']['trip_shipment'] = trip_shipment
            trip_package_mapping = DispatchTripShipmentPackages.objects.create(**validated_data['trip_package_mapping'])
            self.post_package_load_trip_update(trip_package_mapping, trip_shipment)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return trip_package_mapping

    def post_package_load_trip_update(self, trip_package_mapping, trip_shipment):
        # Update total no of shipments, crates, boxes, sacks, weight
        trip = trip_shipment.trip
        if trip_package_mapping.package_status == DispatchTripShipmentPackages.LOADED:
            if trip_package_mapping.shipment_packaging.packaging_type == ShipmentPackaging.CRATE:
                trip.no_of_crates = trip.no_of_crates + 1
            elif trip_package_mapping.shipment_packaging.packaging_type == ShipmentPackaging.BOX:
                trip.no_of_packets = trip.no_of_packets + 1
            elif trip_package_mapping.shipment_packaging.packaging_type == ShipmentPackaging.SACK:
                trip.no_of_sacks = trip.no_of_sacks + 1
            package_weight = trip_package_mapping.shipment_packaging.packaging_details.all()\
                .aggregate(total_weight=Sum(F('ordered_product__product__weight_value') * F('quantity'),
                                            output_field=FloatField())).get('total_weight')
            trip.weight = trip.weight + package_weight
        trip.save()
        if trip.trip_type == DispatchTrip.BACKWARD:
            trip_package_mapping.shipment_packaging.package_status \
                = ShipmentPackaging.DISPATCH_STATUS_CHOICES.READY_TO_DISPATCH
            trip_package_mapping.shipment_packaging.save()



class UnloadVerifyPackageSerializer(serializers.ModelSerializer):
    trip_shipment = DispatchTripShipmentMappingSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = DispatchTripShipmentPackages
        fields = ('trip_shipment', 'created_by', 'updated_by')

    def validate(self, data):
        # Validate request data

        if 'trip_id' not in self.initial_data or not self.initial_data['trip_id']:
            raise serializers.ValidationError("'trip_id' | This is required.")
        try:
            trip = DispatchTrip.objects.get(id=self.initial_data['trip_id'])
        except:
            raise serializers.ValidationError("invalid Trip ID")

        # Check for trip status
        if trip.trip_status != DispatchTrip.UNLOADING:
            raise serializers.ValidationError(f"Trip is in {trip.trip_status} state, cannot unload package")

        if 'package_id' not in self.initial_data or not self.initial_data['package_id']:
            raise serializers.ValidationError("'package_id' | This is required.")
        try:
            package = ShipmentPackaging.objects.get(id=self.initial_data['package_id'])
        except:
            raise serializers.ValidationError("Invalid Package ID")

        # Check for package status
        # if package.status != ShipmentPackaging.DISPATCH_STATUS_CHOICES.DISPATCHED:
        #     raise serializers.ValidationError(f"Package is in {package.status} state, Can't be unloaded")

        # Check if invoice loading already completed
        if DispatchTripShipmentMapping.objects.filter(
                trip=trip, shipment=package.shipment,
                shipment_status=DispatchTripShipmentMapping.UNLOADED_AT_DC).exists():
            raise serializers.ValidationError("The invoice unloading is already completed.")

        # Check if package is loaded in trip
        if not package.trip_packaging_details.filter(package_status=DispatchTripShipmentPackages.LOADED).exists():
            raise serializers.ValidationError("This package was not loaded in the trip.")

        if 'status' not in self.initial_data or not self.initial_data['status']:
            raise serializers.ValidationError("'status' | This is required.")
        elif self.initial_data['status'] not in PACKAGE_VERIFY_CHOICES._db_values:
            raise serializers.ValidationError("Invalid status choice")

        trip_shipment = DispatchTripShipmentMapping.objects.filter(
            trip=trip, shipment=package.shipment, shipment_status=DispatchTripShipmentMapping.UNLOADING_AT_DC).last()
        if not trip_shipment:
            raise serializers.ValidationError("Invalid shipment to unload for the trip.")

        status = DispatchTripShipmentPackages.UNLOADED
        if self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.DAMAGED:
            status = DispatchTripShipmentPackages.DAMAGED_AT_UNLOADING
        elif self.initial_data['status'] == PACKAGE_VERIFY_CHOICES.MISSING:
            status = DispatchTripShipmentPackages.MISSING_AT_UNLOADING

        shipment_health = trip_shipment.shipment_health
        if status == DispatchTripShipmentPackages.DAMAGED_AT_UNLOADING and \
                shipment_health == DispatchTripShipmentMapping.PARTIALLY_MISSING:
            shipment_health = DispatchTripShipmentMapping.PARTIALLY_MISSING_DAMAGED
        elif status == DispatchTripShipmentPackages.MISSING_AT_UNLOADING and \
                shipment_health == DispatchTripShipmentMapping.PARTIALLY_DAMAGED:
            shipment_health = DispatchTripShipmentMapping.PARTIALLY_MISSING_DAMAGED
        elif status == DispatchTripShipmentPackages.DAMAGED_AT_UNLOADING:
            shipment_health = DispatchTripShipmentMapping.PARTIALLY_DAMAGED
        elif status == DispatchTripShipmentPackages.MISSING_AT_UNLOADING:
            shipment_health = DispatchTripShipmentMapping.PARTIALLY_MISSING

        data['trip_shipment_mapping'] = {}
        data['trip_shipment_mapping']['trip'] = trip
        data['trip_shipment_mapping']['shipment'] = package.shipment
        data['trip_shipment_mapping']['shipment_status'] = DispatchTripShipmentMapping.UNLOADING_AT_DC
        data['trip_shipment_mapping']['shipment_health'] = shipment_health

        data['trip_package_mapping'] = {}
        data['trip_package_mapping']['trip_shipment'] = trip_shipment
        data['trip_package_mapping']['shipment_packaging'] = package
        data['trip_package_mapping']['package_status'] = status

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        """update DispatchTrip Package Mapping"""
        try:
            trip_package_mapping = super().update(instance, validated_data['trip_package_mapping'])
            trip_shipment = validated_data['trip_package_mapping']['trip_shipment']
            trip_shipment.shipment_status = validated_data['trip_shipment_mapping']['shipment_status']
            trip_shipment.shipment_health = validated_data['trip_shipment_mapping']['shipment_health']
            trip_shipment.save()
            self.post_package_unload_trip_update(trip_package_mapping, trip_shipment)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return trip_package_mapping

    def post_package_unload_trip_update(self, trip_package_mapping, trip_shipment):
        """
            Update shipment status to MOVED_TO_DISPATCH once all packages are verified on trip
            Update trip shipment mapped as UNLOADED_AT_DC once all packages are verified for that to shipment
        """
        shipment = trip_shipment.shipment
        if not trip_shipment.trip_shipment_mapped_packages.filter(
                package_status=DispatchTripShipmentPackages.LOADED).exists():
            trip_shipment.shipment_status = DispatchTripShipmentMapping.UNLOADED_AT_DC
            trip_shipment.save()
            if trip_shipment.trip.trip_type == DispatchTrip.FORWARD \
                    and shipment.shipment_status == OrderedProduct.READY_TO_DISPATCH:
                shipment.shipment_status = OrderedProduct.MOVED_TO_DISPATCH
                shipment.save()


class TripShipmentMappingSerializer(serializers.ModelSerializer):
    trip = DispatchTripSerializers(read_only=True)
    shipment = ShipmentSerializerForDispatch(read_only=True)
    trip_shipment_mapped_packages = DispatchTripShipmentPackagesSerializers(read_only=True, many=True)
    shipment_status = serializers.CharField(read_only=True)
    shipment_health = serializers.CharField(read_only=True)

    class Meta:
        model = DispatchTripShipmentMapping
        fields = ('id', 'trip', 'shipment', 'shipment_status', 'shipment_health', 'trip_shipment_mapped_packages',)

    def validate(self, data):
        if 'trip_id' not in self.initial_data or not self.initial_data['trip_id']:
            raise serializers.ValidationError("'trip_id' | This is required")
        try:
            trip = DispatchTrip.objects.get(id=self.initial_data['trip_id'])
        except:
            raise serializers.ValidationError("invalid Trip ID")

        if trip.trip_status != DispatchTrip.NEW:
            raise serializers.ValidationError(f"Trip is already in {trip.trip_status} state, cannot remove invoice.")

        if 'shipment_id' not in self.initial_data or not self.initial_data['shipment_id']:
            raise serializers.ValidationError("'shipment_id' | This is required")

        try:
            shipment = OrderedProduct.objects.get(id=self.initial_data['shipment_id'])
        except:
            raise serializers.ValidationError("invalid Shipment ID")

        data['shipment_status'] = DispatchTripShipmentMapping.CANCELLED
        return data


    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            trip_shipment_mapping = super().update(instance, validated_data)
            self.post_shipment_remove_change(trip_shipment_mapping)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return trip_shipment_mapping

    def post_shipment_remove_change(self, trip_shipment_mapping):
        DispatchTripShipmentPackages.objects.filter(trip_shipment=trip_shipment_mapping)\
            .update(package_status=DispatchTripShipmentPackages.CANCELLED)
        trip_shipment_mapping.trip.weight = trip_shipment_mapping.trip.get_trip_weight()
        package_data = trip_shipment_mapping.trip.get_package_data()
        trip_shipment_mapping.trip.no_of_crates = package_data['no_of_crates']
        trip_shipment_mapping.trip.no_of_packets = package_data['no_of_packs']
        trip_shipment_mapping.trip.no_of_sacks = package_data['no_of_sacks']
        trip_shipment_mapping.trip.save()
        if trip_shipment_mapping.trip.trip_type == DispatchTrip.FORWARD and \
                trip_shipment_mapping.shipment.shipment_status == OrderedProduct.READY_TO_DISPATCH:
            trip_shipment_mapping.shipment.shipment_status = OrderedProduct.MOVED_TO_DISPATCH
            trip_shipment_mapping.shipment.save()


class LastMileTripShipmentMappingListSerializers(serializers.ModelSerializer):
    shipment = DispatchShipmentSerializers(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = LastMileTripShipmentMapping
        fields = ('id', 'trip', 'shipment', 'shipment_status', 'created_at', 'updated_at', 'created_by', 'updated_by')


class LastMileTripCrudSerializers(serializers.ModelSerializer):
    seller_shop = ShopSerializer(read_only=True)
    source_shop = ShopSerializer(read_only=True)
    delivery_boy = UserSerializers(read_only=True)
    # status = serializers.SerializerMethodField()
    # last_mile_trip_shipments_details = LastMileTripShipmentMappingListSerializers(read_only=True, many=True)

    class Meta:
        model = Trip
        fields = ('id', 'trip_id', 'seller_shop', 'source_shop', 'dispatch_no', 'vehicle_no', 'delivery_boy',
                  'e_way_bill_no', 'trip_status', 'starts_at', 'completed_at', 'opening_kms', 'closing_kms',
                  'no_of_crates', 'no_of_packets', 'no_of_sacks', 'no_of_crates_check', 'no_of_packets_check',
                  'no_of_sacks_check', 'trip_amount', 'no_of_shipments', 'created_at', 'modified_at')

    def validate(self, data):

        if 'seller_shop' in self.initial_data and self.initial_data['seller_shop']:
            try:
                seller_shop = Shop.objects.get(id=self.initial_data['seller_shop'], shop_type__shop_type='sp')
                data['seller_shop'] = seller_shop
            except:
                raise serializers.ValidationError("Invalid seller_shop")
        else:
            raise serializers.ValidationError("'seller_shop' | This is mandatory")

        if 'source_shop' in self.initial_data and self.initial_data['source_shop']:
            try:
                source_shop = Shop.objects.get(id=self.initial_data['source_shop'],
                                               shop_type__shop_type__in=['sp', 'dc'])
                data['source_shop'] = source_shop
            except:
                raise serializers.ValidationError("Invalid source_shop")
        else:
            raise serializers.ValidationError("'source_shop' | This is mandatory")

        if 'delivery_boy' in self.initial_data and self.initial_data['delivery_boy']:
            delivery_boy = User.objects.filter(id=self.initial_data['delivery_boy'],
                                               shop_employee__shop=seller_shop).last()
            if not delivery_boy:
                raise serializers.ValidationError("Invalid delivery_boy | User not found for " + str(seller_shop))
            if delivery_boy.groups.filter(name='Delivery Boy').exists():
                data['delivery_boy'] = delivery_boy
            else:
                raise serializers.ValidationError("Delivery Boy does not have required permission.")
        else:
            raise serializers.ValidationError("'delivery_boy' | This is mandatory")

        if 'id' in self.initial_data and self.initial_data['id']:
            if not Trip.objects.filter(
                    id=self.initial_data['id'], seller_shop=seller_shop, source_shop=source_shop,
                    delivery_boy=delivery_boy).exists():
                raise serializers.ValidationError("Seller shop/ source shop / delivery boy updation are not allowed.")
            trip_instance = Trip.objects.filter(
                id=self.initial_data['id'], seller_shop=seller_shop, delivery_boy=delivery_boy).last()
            if 'trip_status' in self.initial_data and self.initial_data['trip_status']:
                trip_status = self.initial_data['trip_status']
                if trip_status not in [Trip.READY, Trip.STARTED, Trip.COMPLETED, Trip.RETURN_VERIFIED,
                                       Trip.PAYMENT_VERIFIED, Trip.CANCELLED]:
                    raise serializers.ValidationError("'trip_status' | Invalid status for the selected trip.")
                if trip_instance.trip_status == trip_status:
                    raise serializers.ValidationError(f"Trip status is already {str(trip_status)}.")
                if trip_instance.trip_status in [Trip.PAYMENT_VERIFIED, Trip.CANCELLED]:
                    raise serializers.ValidationError(
                        f"Trip status can't update, already {str(trip_instance.trip_status)}")
                if (trip_instance.trip_status == Trip.READY and
                    trip_status not in [Trip.STARTED, Trip.CANCELLED]) or \
                        (trip_instance.trip_status == Trip.STARTED and trip_status != Trip.COMPLETED) or \
                        (trip_instance.trip_status == Trip.COMPLETED and trip_status != Trip.RETURN_VERIFIED) or \
                        (trip_instance.trip_status == Trip.RETURN_VERIFIED and trip_status != Trip.PAYMENT_VERIFIED):
                    raise serializers.ValidationError(
                        f"'trip_status' | Trip status can't be {str(trip_status)} at the moment.")

                if trip_status == Trip.STARTED:
                    if 'opening_kms' in self.initial_data and self.initial_data['opening_kms']:
                        try:
                            opening_kms = int(self.initial_data['opening_kms'])
                            data['opening_kms'] = opening_kms
                        except:
                            raise serializers.ValidationError("'opening_kms' | Invalid value")
                    else:
                        raise serializers.ValidationError("'opening_kms' | This is mandatory")

                    if not trip_instance.last_mile_trip_shipments_details.exists():
                        raise serializers.ValidationError("Load shipments to the trip to start.")

                    if trip_instance.last_mile_trip_shipments_details.filter(
                            shipment_status=LastMileTripShipmentMapping.LOADING_FOR_DC).exists():
                        raise serializers.ValidationError(
                            "The trip can not start until and unless all shipments get loaded.")

                if trip_status == Trip.COMPLETED:
                    if 'closing_kms' in self.initial_data and self.initial_data['closing_kms']:
                        try:
                            closing_kms = int(self.initial_data['closing_kms'])
                            data['closing_kms'] = closing_kms
                        except:
                            raise serializers.ValidationError("'closing_kms' | Invalid value")
                    else:
                        raise serializers.ValidationError("'closing_kms' | This is mandatory")

                if trip_status == Trip.RETURN_VERIFIED:
                    if trip_instance.last_mile_trip_shipments_details.filter(~Q(shipment__shipment_status__in=[
                        OrderedProduct.FULLY_DELIVERED_AND_VERIFIED,  OrderedProduct.FULLY_RETURNED_AND_VERIFIED,
                            OrderedProduct.PARTIALLY_DELIVERED_AND_VERIFIED])).exists():
                        raise serializers.ValidationError(
                            "The trip can not return verified until and unless all shipments get verified.")
            else:
                raise serializers.ValidationError("'trip_status' | This is mandatory")

            if 'vehicle_no' in self.initial_data and self.initial_data['vehicle_no']:
                if trip_instance.trip_status != Trip.READY and \
                        trip_instance.vehicle_no != self.initial_data['vehicle_no']:
                    raise serializers.ValidationError(f"vehicle no updation not allowed at trip status "
                                                      f"{trip_instance.trip_status}")
                data['vehicle_no'] = self.initial_data['vehicle_no']
        else:
            if 'vehicle_no' in self.initial_data and self.initial_data['vehicle_no']:
                if (DispatchTrip.objects.filter(trip_status__in=[DispatchTrip.NEW, DispatchTrip.STARTED],
                                                vehicle_no=self.initial_data['vehicle_no']).exists() or
                        Trip.objects.filter(trip_status__in=[Trip.READY, Trip.STARTED],
                                            vehicle_no=self.initial_data['vehicle_no']).exists()):
                    raise serializers.ValidationError(f"This vehicle {self.initial_data['vehicle_no']} is already "
                                                      f"in use for another trip ")
                data['vehicle_no'] = self.initial_data['vehicle_no']
            else:
                raise serializers.ValidationError("'vehicle_no' | This is mandatory")

            data['trip_status'] = Trip.READY
        return data

    def mark_shipments_as_out_for_delivery_on_trip_start(self, last_mile_trip):
        shipment_details = last_mile_trip.last_mile_trip_shipments_details.all()
        for shipment_detail in shipment_details:
            if shipment_detail.shipment.shipment_status == OrderedProduct.READY_TO_DISPATCH:
                shipment_detail.shipment.shipment_status = OrderedProduct.OUT_FOR_DELIVERY
                shipment_detail.shipment.save()

    def mark_shipments_as_fully_delivered_and_completed_on_trip_complete(self, last_mile_trip):
        shipment_details = last_mile_trip.last_mile_trip_shipments_details.all()
        for shipment_detail in shipment_details:
            if shipment_detail.shipment.shipment_status == OrderedProduct.OUT_FOR_DELIVERY:
                shipment_detail.shipment.shipment_status = OrderedProduct.FULLY_DELIVERED_AND_COMPLETED
                shipment_detail.shipment.save()

    def cancel_added_shipments_to_trip(self, last_mile_trip):
        shipment_details = last_mile_trip.last_mile_trip_shipments_details.all()
        # for mapping in shipment_details:
        #     if mapping.shipment.shipment_status == OrderedProduct.READY_TO_DISPATCH:
        #         mapping.shipment.shipment_status = OrderedProduct.MOVED_TO_DISPATCH
        #         mapping.shipment.save()
        shipment_details.update(shipment_status=LastMileTripShipmentMapping.CANCELLED)

    @transaction.atomic
    def create(self, validated_data):
        """create a new Last Mile Trip"""
        last_mile_trip_shipments_details = validated_data.pop("last_mile_trip_shipments_details", None)
        try:
            trip_instance = Trip.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return trip_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update Last Mile Trip"""
        last_mile_trip_shipments_details = validated_data.pop("last_mile_trip_shipments_details", None)
        try:
            trip_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        if validated_data['trip_status'] == Trip.STARTED:
            self.mark_shipments_as_out_for_delivery_on_trip_start(trip_instance)

        if validated_data['trip_status'] == Trip.COMPLETED:
            self.mark_shipments_as_fully_delivered_and_completed_on_trip_complete(trip_instance)

        if validated_data['trip_status'] == Trip.CANCELLED:
            self.cancel_added_shipments_to_trip(trip_instance)

        return trip_instance


class LastMileTripShipmentsSerializer(serializers.ModelSerializer):
    order = OrderSerializerForShipment(read_only=True)
    trip = serializers.SerializerMethodField()

    @staticmethod
    def get_trip(obj):
        if obj.last_mile_trip_shipment.exists():
            return DispatchTripSerializers(obj.last_mile_trip_shipment.last().trip).data
        elif obj.trip:
            return DispatchTripSerializers(obj.trip).data
        return None

    class Meta:
        model = OrderedProduct
        fields = ('id', 'order', 'shipment_status', 'invoice_no', 'invoice_amount', 'trip', 'created_at', 'modified_at')


class VerifyReturnShipmentProductsSerializer(serializers.ModelSerializer):
    # This serializer is used to fetch the products for a shipment
    product = ProductSerializer(read_only=True)
    rt_ordered_product_mapping = OrderedProductBatchSerializer(read_only=True, many=True)
    last_modified_by = UserSerializer(read_only=True)
    shipment_product_packaging = ProductPackagingDetailsSerializer(read_only=True, many=True, source='return_pkg')
    is_fully_delivered = serializers.SerializerMethodField()


    class Meta:
        model = RetailerOrderedProductMapping
        fields = ('id', 'ordered_qty', 'shipped_qty', 'product', 'is_qc_done', 'selling_price', 'shipped_qty',
                  'delivered_qty', 'returned_qty', 'damaged_qty', 'returned_damage_qty', 'expired_qty', 'missing_qty',
                  'rejected_qty', 'effective_price', 'discounted_price', 'delivered_at_price', 'cancellation_date',
                  'picked_pieces', 'rt_ordered_product_mapping', 'shipment_product_packaging', 'last_modified_by',
                  'is_fully_delivered', 'created_at', 'modified_at')

    def validate(self, data):

        if 'product' in self.initial_data and self.initial_data['product']:
            try:
                product = Product.objects.get(id=self.initial_data['product'])
                data['product'] = product
            except:
                raise serializers.ValidationError("Invalid product")
        else:
            raise serializers.ValidationError("'product' | This is mandatory")

        product_returned_qty = 0
        product_returned_damage_qty = 0

        # Batch Validations
        if 'rt_ordered_product_mapping' not in self.initial_data or \
                not isinstance(self.initial_data['rt_ordered_product_mapping'], list) or \
                not self.initial_data['rt_ordered_product_mapping']:
            raise serializers.ValidationError("'rt_ordered_product_mapping' | This is mandatory")

        rt_ordered_product_mapping = []
        for product_batch in self.initial_data['rt_ordered_product_mapping']:
            if 'batch_id' not in product_batch or not product_batch['batch_id']:
                raise serializers.ValidationError("'batch_id' | This is mandatory.")

            if 'returned_qty' not in product_batch or product_batch['returned_qty'] is None or \
                    'returned_damage_qty' not in product_batch or product_batch['returned_damage_qty'] is None:
                raise serializers.ValidationError("'returned_qty', 'returned_damage_qty' | These are mandatory.")
            try:
                batch_returned_qty = int(product_batch['returned_qty'])
                batch_returned_damage_qty = int(product_batch['returned_damage_qty'])
            except:
                raise serializers.ValidationError("'returned_qty', 'returned_damage_qty' | Invalid quantity.")

            product_returned_qty += batch_returned_qty
            product_returned_damage_qty += batch_returned_damage_qty

            if 'id' in product_batch and product_batch['id']:
                product_batch_instance = OrderedProductBatch.objects.filter(id=product_batch['id']).last()

                if product_batch_instance.ordered_product_mapping.ordered_product.shipment_status not in [
                    OrderedProduct.FULLY_DELIVERED_AND_COMPLETED, OrderedProduct.FULLY_RETURNED_AND_COMPLETED,
                    OrderedProduct.PARTIALLY_DELIVERED_AND_COMPLETED,
                    OrderedProduct.RESCHEDULED, OrderedProduct.NOT_ATTEMPT]:
                    raise serializers.ValidationError("Shipment updation is not allowed.")

                if product_batch_instance.batch_id != product_batch['batch_id']:
                    raise serializers.ValidationError("'batch_id' | Invalid batch.")
                if batch_returned_qty < 0 or batch_returned_damage_qty < 0 or \
                        float(product_batch_instance.quantity) < (
                        float(batch_returned_qty + batch_returned_damage_qty)):
                    raise serializers.ValidationError("Sorry Quantity mismatch!! Sum of Delivered, Returned & Damaged "
                                                      "Quantity should be equals to Already Shipped Quantity")
                product_batch['returned_qty'] = batch_returned_qty
                product_batch['returned_damage_qty'] = batch_returned_damage_qty
                product_batch['delivered_qty'] = product_batch_instance.quantity - (
                        batch_returned_qty + batch_returned_damage_qty)
                rt_ordered_product_mapping.append(product_batch)
            else:
                raise serializers.ValidationError("'rt_ordered_product_mapping.id' | This is mandatory.")
        data['rt_ordered_product_mapping'] = rt_ordered_product_mapping
        # Shipment's Product mapping Id Validation
        if 'id' not in self.initial_data and self.initial_data['id'] is None:
            raise serializers.ValidationError("'id' | This is mandatory.")

        mapping_instance = RetailerOrderedProductMapping.objects.filter(id=self.initial_data['id']).last()

        if mapping_instance.ordered_product.shipment_status not in [
            OrderedProduct.FULLY_DELIVERED_AND_COMPLETED, OrderedProduct.FULLY_RETURNED_AND_COMPLETED,
            OrderedProduct.PARTIALLY_DELIVERED_AND_COMPLETED,
            OrderedProduct.RESCHEDULED, OrderedProduct.NOT_ATTEMPT]:
            raise serializers.ValidationError("Shipment updation is not allowed.")

        # if mapping_instance.is_return_verified:
        #     raise serializers.ValidationError("This product is already verified.")

        if mapping_instance.product != product:
            raise serializers.ValidationError("Product updation is not allowed.")
        """
            Returned pieces, damaged return pieces must be positive values
            Returned pieces + damaged return pieces <= Shipped pieces
        """
        if product_returned_qty < 0 or product_returned_damage_qty < 0 or \
                float(mapping_instance.shipped_qty) < float(product_returned_qty + product_returned_damage_qty):
            raise serializers.ValidationError("Sorry Quantity mismatch!! Sum of Returned, Damaged Quantity "
                                              "should be lesser than Shipped Quantity")

        # Delivered pieces = Shipped pieces - Returned Pieces - Damaged return
        product_delivered_qty = float(mapping_instance.shipped_qty) - \
                                float(product_returned_qty + product_returned_damage_qty)

        warehouse_id = mapping_instance.ordered_product.packaged_at

        total_product_returned_qty = float(product_returned_qty + product_returned_damage_qty)
        # Make Packaging for Dispatch Trips only, Validation: Seller shop is not same as Source shop
        if mapping_instance.ordered_product.packaged_at != mapping_instance.ordered_product.order.seller_shop:
            if 'packaging' in self.initial_data and self.initial_data['packaging']:
                if total_product_returned_qty == float("0"):
                    raise serializers.ValidationError("To be returned quantity is zero, packaging is not required")
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
                if total_product_qty != int(total_product_returned_qty):
                    raise serializers.ValidationError("Total quantity packaged should match total returned quantity.")
            elif total_product_returned_qty > 0:
                raise serializers.ValidationError("'packaging' | This is mandatory")
            data['packaging'] = self.initial_data.get('packaging')

        data['delivered_qty'] = product_delivered_qty
        data['returned_damage_qty'] = product_returned_damage_qty
        data['is_return_verified'] = True
        data['warehouse_id'] = warehouse_id

        return data

    def get_is_fully_delivered(self, obj):
        return True if obj.shipped_qty == obj.delivered_qty else False

    def get_movement_type(self, shipment_instance):
        if shipment_instance.shipment_status in [OrderedProduct.FULLY_DELIVERED_AND_COMPLETED,
                                                 OrderedProduct.FULLY_RETURNED_AND_COMPLETED,
                                                 OrderedProduct.PARTIALLY_DELIVERED_AND_COMPLETED]:
            return ShipmentPackaging.RETURNED
        if shipment_instance.shipment_status == OrderedProduct.RESCHEDULED:
            return ShipmentPackaging.RESCHEDULED
        if shipment_instance.shipment_status == OrderedProduct.NOT_ATTEMPT:
            return ShipmentPackaging.NOT_ATTEMPT
        return ShipmentPackaging.DISPATCH

    def create_update_shipment_packaging(self, shipment, packaging_type, warehouse_id, crate, updated_by,
                                         movement_type=ShipmentPackaging.DISPATCH):
        if packaging_type == ShipmentPackaging.CRATE:
            instance, created = ShipmentPackaging.objects.get_or_create(
                shipment=shipment, packaging_type=packaging_type, warehouse_id=warehouse_id, crate=crate,
                movement_type=movement_type, defaults={'created_by': updated_by, 'updated_by': updated_by})
        else:
            instance = ShipmentPackaging.objects.create(
                shipment=shipment, packaging_type=packaging_type, warehouse_id=warehouse_id, crate=crate,
                movement_type=movement_type, created_by=updated_by, updated_by=updated_by)
        return instance

    def create_shipment_packaging_mapping(self, shipment_packaging, ordered_product, quantity, updated_by):
        return ShipmentPackagingMapping.objects.create(
            shipment_packaging=shipment_packaging, ordered_product=ordered_product, quantity=quantity,
            created_by=updated_by, updated_by=updated_by)

    def update_product_batch_data(self, product_batch_instance, validated_data):
        try:
            process_shipments_instance = product_batch_instance.update(**validated_data)
            # To create putaway for Last mile trip
            # Validate: Seller shop is same as Source shop
            shipment = product_batch_instance.last().ordered_product_mapping.ordered_product
            if shipment.packaged_at == shipment.order.seller_shop:
                product_batch_instance.last().save()
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update Ordered Product Mapping"""
        ordered_product_batches = validated_data.pop('rt_ordered_product_mapping')
        packaging = validated_data.pop("packaging", None)

        try:
            shipment_map_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        for product_batch in ordered_product_batches:
            product_batch_instance = OrderedProductBatch.objects.filter(id=product_batch['id'])
            product_batch_id = product_batch.pop('id')
            self.update_product_batch_data(product_batch_instance, product_batch)

        movement_type = self.get_movement_type(shipment_map_instance.ordered_product)
        if packaging:
            for package_obj in packaging:
                if package_obj['type'] == ShipmentPackaging.CRATE:
                    for crate in package_obj['packages']:
                        crate_instance = Crate.objects.filter(
                            crate_id=crate['crate_id'], warehouse__id=validated_data['warehouse_id'],
                            crate_type=Crate.DISPATCH).last()
                        shipment_packaging = self.create_update_shipment_packaging(
                            shipment_map_instance.ordered_product, package_obj['type'],
                            validated_data['warehouse_id'], crate_instance, validated_data['last_modified_by'],
                            movement_type)

                        self.create_shipment_packaging_mapping(
                            shipment_packaging, shipment_map_instance, int(crate['quantity']),
                            validated_data['last_modified_by'])

                elif package_obj['type'] in [ShipmentPackaging.BOX, ShipmentPackaging.SACK]:
                    for package in package_obj['packages']:
                        shipment_packaging = self.create_update_shipment_packaging(
                            shipment_map_instance.ordered_product, package_obj['type'],
                            validated_data['warehouse_id'], None, validated_data['last_modified_by'], movement_type)

                        self.create_shipment_packaging_mapping(
                            shipment_packaging, shipment_map_instance, int(package['quantity']),
                            validated_data['last_modified_by'])
        return shipment_map_instance


class ShipmentCratesValidatedSerializer(serializers.ModelSerializer):
    """ Serializer for Complete verify a Shipment"""
    order = OrderSerializerForShipment(read_only=True)
    status = serializers.SerializerMethodField()
    all_returned_crates_validated = serializers.SerializerMethodField()

    @staticmethod
    def get_status(obj):
        return obj.get_shipment_status_display()

    @staticmethod
    def get_all_returned_crates_validated(obj):
        if not obj.shipment_packaging.filter(
                ~Q(status__in=[ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_VERIFIED,
                               ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_MISSING,
                               ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_DAMAGED]),
                packaging_type=ShipmentPackaging.CRATE).exists():
            return True
        return False

    class Meta:
        model = OrderedProduct
        fields = ('id', 'status', 'invoice_no', 'invoice_amount', 'all_returned_crates_validated',
                  'order', 'created_at')


class ShipmentCompleteVerifySerializer(serializers.ModelSerializer):
    """ Serializer for Complete verify a Shipment"""
    order = OrderSerializerForShipment(read_only=True)
    status = serializers.SerializerMethodField()
    qc_area = QCAreaSerializer(read_only=True)

    def get_status(self, obj):
        return obj.get_shipment_status_display()

    class Meta:
        model = OrderedProduct
        fields = ('id', 'order', 'status', 'invoice_no', 'invoice_amount', 'payment_mode', 'qc_area', 'created_at')

    def validate(self, data):
        """Validate the Shipment requests to complete verify"""

        if 'id' in self.initial_data and self.initial_data['id']:
            try:
                shipment = OrderedProduct.objects.get(id=self.initial_data['id'])
                shipment_status = shipment.shipment_status
            except Exception as e:
                raise serializers.ValidationError("Invalid Shipment")
            if shipment_status not in [OrderedProduct.FULLY_DELIVERED_AND_COMPLETED,
                                       OrderedProduct.PARTIALLY_DELIVERED_AND_COMPLETED,
                                       OrderedProduct.FULLY_RETURNED_AND_COMPLETED,
                                       OrderedProduct.RESCHEDULED]:
                raise serializers.ValidationError(f"Shipment not in valid state to complete verify.")

            if shipment.shipment_packaging.filter(
                    ~Q(status__in=[ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_VERIFIED,
                                   ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_MISSING,
                                   ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_DAMAGED]),
                    packaging_type=ShipmentPackaging.CRATE).exists():
                raise serializers.ValidationError(f"All crates are not verified for shipment status "
                                                  f"{shipment.shipment_status} | Id { shipment.pk }")

            if shipment_status in [OrderedProduct.PARTIALLY_DELIVERED_AND_COMPLETED,
                                   OrderedProduct.FULLY_RETURNED_AND_COMPLETED]:
                if shipment.rt_order_product_order_product_mapping.filter(
                        returned_qty__gt=0, is_return_verified=False).exists():
                    raise serializers.ValidationError(f"All returned products verification needed for shipment status "
                                                      f"{shipment.shipment_status} | Id { shipment.pk }")

            if shipment_status == OrderedProduct.RESCHEDULED:
                if shipment.shipment_packaging.filter(
                        ~Q(status__in=[ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_VERIFIED,
                                       ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_MISSING,
                                       ShipmentPackaging.DISPATCH_STATUS_CHOICES.RETURN_DAMAGED])).exists():
                    raise serializers.ValidationError(f"All packages are not verified for shipment status "
                                                      f"{shipment.shipment_status} | Id {shipment.pk}")
                data['shipment_status'] = OrderedProduct.RESCHEDULED

            elif shipment_status == OrderedProduct.PARTIALLY_DELIVERED_AND_COMPLETED:
                data['shipment_status'] = OrderedProduct.PARTIALLY_DELIVERED_AND_VERIFIED

            elif shipment_status == OrderedProduct.FULLY_RETURNED_AND_COMPLETED:
                data['shipment_status'] = OrderedProduct.FULLY_RETURNED_AND_VERIFIED

            elif shipment_status == OrderedProduct.FULLY_DELIVERED_AND_COMPLETED:
                data['shipment_status'] = OrderedProduct.FULLY_DELIVERED_AND_VERIFIED
        else:
            raise serializers.ValidationError("Shipment creation is not allowed.")

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            shipment_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return shipment_instance


class LastMileTripStatusChangeSerializers(serializers.ModelSerializer):
    seller_shop = ShopSerializer(read_only=True)
    delivery_boy = UserSerializers(read_only=True)
    last_mile_trip_shipments_details = LastMileTripShipmentMappingListSerializers(read_only=True, many=True)

    class Meta:
        model = Trip
        fields = ('id', 'trip_id', 'seller_shop', 'dispatch_no', 'vehicle_no', 'delivery_boy', 'e_way_bill_no',
                  'trip_status', 'starts_at', 'completed_at', 'opening_kms', 'closing_kms', 'no_of_crates',
                  'no_of_packets', 'no_of_sacks', 'no_of_crates_check', 'no_of_packets_check', 'no_of_sacks_check',
                  'trip_amount', 'received_amount', 'total_received_amount', 'received_cash_amount',
                  'received_online_amount',  'cash_to_be_collected_value', 'total_trip_shipments',
                  'total_delivered_shipments', 'total_returned_shipments', 'total_pending_shipments',
                  'total_rescheduled_shipments', 'total_trip_amount_value', 'total_pending_shipments',
                  'total_rescheduled_shipments', 'total_return_amount', 'no_of_shipments',
                  'last_mile_trip_shipments_details', 'created_at', 'modified_at')

    def validate(self, data):

        if 'id' in self.initial_data and self.initial_data['id']:
            if Trip.objects.filter(id=self.initial_data['id']).exists():
                trip_instance = Trip.objects.filter(id=self.initial_data['id']).last()
            else:
                raise serializers.ValidationError("Seller shop updation are not allowed.")
        else:
            raise serializers.ValidationError("'id' | This is mandatory")

        if 'vehicle_no' in self.initial_data and self.initial_data['vehicle_no']:
            vehicle_no = self.initial_data['vehicle_no']
            if trip_instance.vehicle_no != vehicle_no:
                raise Exception("'vehicle_no' | Invalid vehicle_no for selected trip.")

        if 'seller_shop' in self.initial_data and self.initial_data['seller_shop']:
            try:
                seller_shop = Shop.objects.get(id=self.initial_data['seller_shop'], shop_type__shop_type='sp')
                if trip_instance.seller_shop != seller_shop:
                    raise Exception("'seller_shop' | Invalid seller_shop for selected trip.")
            except:
                raise serializers.ValidationError("'seller_shop' | Invalid seller shop")

        if 'delivery_boy' in self.initial_data and self.initial_data['delivery_boy']:
            try:
                delivery_boy = User.objects.filter(
                    id=self.initial_data['delivery_boy'], shop_employee__shop=seller_shop).last()
                if trip_instance.delivery_boy != delivery_boy:
                    raise Exception("'delivery_boy' | Invalid delivery_boy for selected trip.")
            except:
                raise serializers.ValidationError("Invalid delivery_boy | User not found for " + str(seller_shop))

        if 'trip_status' in self.initial_data and self.initial_data['trip_status']:
            trip_status = self.initial_data['trip_status']
            if trip_status != Trip.RETURN_VERIFIED:
                raise serializers.ValidationError("'trip_status' | Invalid status for the selected trip.")
        else:
            trip_status = Trip.RETURN_VERIFIED

        if trip_instance.trip_status != Trip.COMPLETED or trip_instance.trip_status == trip_status:
            raise serializers.ValidationError(f"Trip status can't update, already {str(trip_instance.trip_status)}")
        if trip_instance.trip_status == Trip.COMPLETED and trip_status != Trip.RETURN_VERIFIED:
            raise serializers.ValidationError(f"'trip_status' | Trip status can't be {str(trip_status)} at the moment.")

        if trip_instance.trip_status == Trip.COMPLETED and trip_status == Trip.RETURN_VERIFIED:
            trip_shipment_mappings = trip_instance.last_mile_trip_shipments_details.all()
            if not trip_shipment_mappings:
                raise serializers.ValidationError("No shipments added to the trip.")

            for mapping in trip_shipment_mappings:
                if mapping.shipment.rt_order_product_order_product_mapping.filter(
                        returned_qty__gt=0, is_return_verified=False).exists():
                    return serializers.ValidationError(
                        f"Please verify all crates for the shipment {mapping.shipment}.")

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update Last Mile Trip"""
        try:
            trip_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return trip_instance


class PackagesUnderTripSerializer(serializers.ModelSerializer):
    packaging_details = DispatchItemDetailsSerializer(many=True, read_only=True)
    status = ChoicesSerializer(choices=ShipmentPackaging.DISPATCH_STATUS_CHOICES)
    crate = CrateSerializer(read_only=True)
    packaging_type = serializers.CharField(read_only=True)
    shipment = ShipmentSerializerForDispatch(read_only=True)
    trip_loading_status = serializers.SerializerMethodField()

    def get_trip_loading_status(self, obj):
        return obj.trip_packaging_details.last().package_status \
            if obj.trip_packaging_details.filter(~Q(package_status=DispatchTripShipmentPackages.CANCELLED)).exists() else None

    @staticmethod
    def get_reason_for_rejection(obj):
        return obj.get_reason_for_rejection_display()

    class Meta:
        model = ShipmentPackaging
        fields = ('id', 'shipment', 'packaging_type', 'crate', 'status', 'reason_for_rejection', 'packaging_details',
                  'trip_loading_status')


class ShipmentPackagingBatchInfoSerializer(serializers.ModelSerializer):
    product_batch_no = serializers.CharField(read_only=True)
    return_qty = serializers.IntegerField(read_only=True)

    class Meta:
        model = ShipmentPackagingMapping
        fields = ('id', 'product_batch_no', 'return_qty')


class DetailedShipmentPackagingMappingInfoSerializer(serializers.ModelSerializer):
    packaging_product_details = ShipmentPackagingBatchInfoSerializer(read_only=True, many=True)
    product = serializers.SerializerMethodField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    return_qty = serializers.IntegerField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)

    def get_product(self, obj):
        return ProductSerializer(obj.ordered_product.product).data

    class Meta:
        model = ShipmentPackagingMapping
        fields = ('id', 'product', 'quantity', 'return_qty', 'is_verified', 'packaging_product_details')


class DetailedShipmentPackageInfoSerializer(serializers.ModelSerializer):
    packaging_details = DetailedShipmentPackagingMappingInfoSerializer(many=True, read_only=True)
    status = ChoicesSerializer(choices=ShipmentPackaging.DISPATCH_STATUS_CHOICES, required=False)
    reason_for_rejection = ChoicesSerializer(choices=ShipmentPackaging.REASON_FOR_REJECTION, required=False)
    crate = CrateSerializer(read_only=True)
    packaging_type = serializers.CharField(read_only=True)
    shipment = ShipmentSerializerForDispatch(read_only=True)

    class Meta:
        model = ShipmentPackaging
        fields = ('id', 'shipment', 'packaging_type', 'crate', 'status', 'reason_for_rejection',
                  'packaging_details', 'created_by')


class MarkShipmentPackageVerifiedSerializer(serializers.ModelSerializer):
    shipment_packaging = DetailedShipmentPackageInfoSerializer(read_only=True)
    trip_shipment = DispatchTripShipmentMappingSerializer(read_only=True)
    package_status = ChoicesSerializer(choices=DispatchTripShipmentPackages.PACKAGE_STATUS, required=False)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = DispatchTripShipmentPackages
        fields = ('id', 'shipment_packaging', 'trip_shipment', 'package_status', 'is_return_verified',
                  'created_at', 'created_by', 'updated_at', 'updated_by')

    def validate(self, data):
        # Validate request data

        if 'trip_id' not in self.initial_data or not self.initial_data['trip_id']:
            raise serializers.ValidationError("'trip_id' | This is required.")
        try:
            trip = DispatchTrip.objects.get(id=self.initial_data['trip_id'])
        except:
            raise serializers.ValidationError("invalid Trip ID")

        # Check for trip status
        if trip.trip_status != DispatchTrip.CLOSED:
            raise serializers.ValidationError(f"Trip is in {trip.trip_status} state, cannot verify package")

        if 'package_id' not in self.initial_data or not self.initial_data['package_id']:
            raise serializers.ValidationError("'package_id' | This is required.")
        try:
            package = ShipmentPackaging.objects.get(id=self.initial_data['package_id'])
        except:
            raise serializers.ValidationError("Invalid Package ID")

        if DispatchTripShipmentPackages.objects.filter(trip_shipment__trip=trip, shipment_packaging=package).exists():
            trip_shipment_map = DispatchTripShipmentPackages.objects.filter(
                trip_shipment__trip=trip, shipment_packaging=package).last()
            if trip_shipment_map.is_return_verified:
                return serializers.ValidationError("This package is already verified.")
            if trip_shipment_map.package_status != DispatchTripShipmentPackages.UNLOADED:
                return serializers.ValidationError(f"Package is in {trip_shipment_map.package_status} state, "
                                                   f"cannot verify at the moment")
        else:
            return serializers.ValidationError("Invalid package to the Trip")

        if 'force_verify' not in self.initial_data or self.initial_data['force_verify'] is False:
            if ShipmentPackagingMapping.objects.filter(shipment_packaging=package, is_verified=False).exists():
                return serializers.ValidationError("This shipment has unverified products.")

        data['is_return_verified'] = True

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        """update Dispatch Trip Shipment Package"""
        try:
            trip_shipment_package = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return trip_shipment_package


class ShipmentPackageZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ('id', 'zone_number', 'name')


class ShipmentPackageProductSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()
    product_brand = serializers.SerializerMethodField()
    zone = serializers.SerializerMethodField()

    def get_product_image(self, obj):
        if ProductImage.objects.filter(product=obj).exists():
            product_image = ProductImage.objects.filter(product=obj)[0].image.url
            return product_image
        else:
            return None

    def get_product_brand(self, obj):
        return obj.product_brand.brand_name

    def get_zone(self, obj):
        return ShipmentPackageZoneSerializer(WarehouseAssortment.objects.filter(
            product=obj.parent_product, warehouse=self.context.get('shop')).last().zone).data

    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'product_brand', 'product_inner_case_size', 'product_case_size',
                  'product_image', 'product_mrp', 'product_ean_code', 'zone')


class ShipmentPackageProductsSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField(read_only=True)
    batches = serializers.SerializerMethodField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    return_qty = serializers.IntegerField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)

    def get_product(self, obj):
        return ShipmentPackageProductSerializer(obj.ordered_product.product).data

    def get_batches(self, obj):
        return OrderedProductBatchSerializer(
            obj.ordered_product.product.rt_ordered_product_mapping.all(), many=True).data

    class Meta:
        model = ShipmentPackagingMapping
        fields = ('id', 'product', 'batches', 'quantity', 'return_qty', 'is_verified')
