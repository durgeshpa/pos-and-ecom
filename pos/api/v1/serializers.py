from decimal import Decimal
import datetime
import calendar
import re
import math

from django.db.models.functions import Cast
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q, Sum, F, Func, Value, CharField, FloatField, Count, Case, When
from django.db import transaction, models
from rest_framework import serializers
from django.core.validators import FileExtensionValidator

from addresses.models import Pincode
from pos.models import RetailerProduct, RetailerProductImage, Vendor, PosCart, PosCartProductMapping, PosGRNOrder, \
    PosGRNOrderProductMapping, Payment, PaymentType, Document, MeasurementCategory, MeasurementUnit, PosReturnGRNOrder, PosReturnItems
from pos.tasks import mail_to_vendor_on_po_creation, mail_to_vendor_on_order_return_creation, genrate_debit_note_pdf
from retailer_to_sp.models import CartProductMapping, Cart, Order, OrderReturn, ReturnItems, \
    OrderedProductMapping, OrderedProduct
from accounts.api.v1.serializers import PosUserSerializer, PosShopUserSerializer
from pos.common_functions import RewardCls, PosInventoryCls, RetailerProductCls, get_default_qty
from pos.common_validators import get_validate_grn_order, get_validate_vendor
from products.models import Product
from retailer_backend.validators import ProductNameValidator
from coupon.models import Coupon, CouponRuleSet, RuleSetProductMapping, DiscountValue
from retailer_backend.utils import SmallOffsetPagination
from shops.models import Shop, PosShopUserMapping
from wms.models import PosInventory, PosInventoryState, PosInventoryChange
from marketing.models import ReferralCode
from accounts.models import User
from ecom.models import Address
from ecom.api.v1.serializers import EcomOrderAddressSerializer


class RetailerProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailerProductImage
        fields = ('id', 'image_name', 'image_alt_text', 'image')


class ImageFileSerializer(serializers.Serializer):
    image = serializers.ImageField()


class RetailerProductCreateSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    product_name = serializers.CharField(required=True, validators=[ProductNameValidator], max_length=100)
    mrp = serializers.DecimalField(max_digits=6, decimal_places=2, required=True, min_value=0.01)
    selling_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=True, min_value=0.01)
    add_offer_price = serializers.BooleanField(default=False)
    offer_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=None, min_value=0.01)
    offer_start_date = serializers.DateField(required=False, default=None)
    offer_end_date = serializers.DateField(required=False, default=None)
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False, default='',
                                        max_length=255)
    product_ean_code = serializers.CharField(required=False, default=None, max_length=100, allow_null=True)
    stock_qty = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, default=0, min_value=0)
    linked_product_id = serializers.IntegerField(required=False, default=None, min_value=1, allow_null=True)
    images = serializers.ListField(required=False, default=None, child=serializers.ImageField(), max_length=3)
    is_discounted = serializers.BooleanField(default=False)
    online_enabled = serializers.BooleanField(default = True)
    online_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, min_value=0.01)
    ean_not_available = serializers.BooleanField(default=False)
    product_pack_type = serializers.ChoiceField(choices=['packet', 'loose'], default='packet')
    measurement_category = serializers.CharField(required=False, default=None)
    measurement_category_id = serializers.IntegerField(required=False, default=None)
    purchase_pack_size = serializers.IntegerField(default=1)

    @staticmethod
    def validate_linked_product_id(value):
        if value and not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Linked GramFactory Product not found! Please try again")
        return value

    def validate(self, attrs):
        if attrs['ean_not_available']:
            attrs['product_ean_code'] = None
        elif not attrs['product_ean_code']:
            raise serializers.ValidationError("Please provide EAN Code")

        sp, mrp, shop_id, linked_pid, ean = attrs['selling_price'], attrs['mrp'], attrs['shop_id'], attrs[
            'linked_product_id'], attrs['product_ean_code']

        if ean and RetailerProduct.objects.filter(shop=shop_id, product_ean_code=ean, mrp=mrp,
                                                  is_deleted=False).exists():
            raise serializers.ValidationError("Product with same ean and mrp already exists in catalog.")

        if sp > mrp:
            raise serializers.ValidationError("Selling Price should be equal to OR less than MRP")

        if 'online_price' in attrs and attrs['online_price'] > mrp:
            raise serializers.ValidationError("Online Price should be equal to OR less than MRP")

        image_count = 0
        if 'images' in attrs and attrs['images']:
            image_count = len(attrs['images'])
        if image_count > 3:
            raise serializers.ValidationError("images : Ensure this field has no more than 3 elements.")

        if attrs['add_offer_price']:
            offer_price, offer_sd, offer_ed = attrs['offer_price'], attrs['offer_start_date'], attrs['offer_end_date']

            if offer_price is None:
                raise serializers.ValidationError('Please provide offer price')

            if offer_price and offer_price > sp:
                raise serializers.ValidationError("Offer Price should be equal to OR less than Selling Price")

            if offer_sd is None:
                raise serializers.ValidationError('Please provide offer start date')
            if offer_ed is None:
                raise serializers.ValidationError('Please provide offer end date')
            if offer_sd > offer_ed:
                raise serializers.ValidationError('Offer end date should be greater than or equal to offer start date')
            if offer_sd < datetime.date.today():
                raise serializers.ValidationError("Offer start date should be greater than or equal to today's date.")
        else:
            attrs['offer_price'], attrs['offer_start_date'], attrs['offer_end_date'] = None, None, None

        if attrs['product_pack_type'] == 'loose':
            try:
                measurement_category = MeasurementCategory.objects.get(category=attrs['measurement_category'].lower())
                attrs['measurement_category_id'] = measurement_category.id
                MeasurementUnit.objects.get(category=measurement_category, default=True)
            except:
                raise serializers.ValidationError("Please provide a valid measurement category for Loose Product")
            attrs['purchase_pack_size'] = 1
        else:
            attrs['stock_qty'] = int(attrs['stock_qty'])

        return attrs


class RetailerProductResponseSerializer(serializers.ModelSerializer):
    linked_product = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    stock_qty = serializers.SerializerMethodField()
    discounted_product = serializers.SerializerMethodField()

    @staticmethod
    def get_linked_product(obj):
        return obj.linked_product.product_name if obj.linked_product else ''

    @staticmethod
    def get_images(obj):
        return RetailerProductImageSerializer(obj.retailer_product_image, many=True).data

    @staticmethod
    def get_stock_qty(obj):
        inv_available = PosInventoryState.objects.get(inventory_state=PosInventoryState.AVAILABLE)
        pos_inv = PosInventory.objects.filter(product=obj, inventory_state=inv_available).last()
        return pos_inv.quantity if pos_inv else 0

    @staticmethod
    def get_discounted_product(obj):
        if obj.sku_type != 4 and hasattr(obj, 'discounted_product'):
            return RetailerProductResponseSerializer(obj.discounted_product).data

    class Meta:
        model = RetailerProduct
        fields = '__all__'


class RetailerProductUpdateSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    product_id = serializers.IntegerField(required=True, min_value=1)
    product_ean_code = serializers.CharField(required=False, default=None, max_length=100)
    product_name = serializers.CharField(required=False, validators=[ProductNameValidator], default=None,
                                         max_length=100)
    mrp = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=None, min_value=0.01)
    selling_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=None,
                                             min_value=0.01)
    offer_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=None, min_value=0.01)
    offer_start_date = serializers.DateField(required=False, default=None)
    offer_end_date = serializers.DateField(required=False, default=None)
    add_offer_price = serializers.BooleanField(default=None)
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False,
                                        default=None, max_length=255)
    stock_qty = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, default=0, min_value=0)
    status = serializers.ChoiceField(choices=['active', 'deactivated'], required=False, default=None)
    images = serializers.ListField(required=False, allow_null=True, child=serializers.ImageField())
    image_ids = serializers.ListField(required=False, default=None, child=serializers.IntegerField())
    is_discounted = serializers.BooleanField(default=False)
    discounted_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=None,
                                                min_value=0.01)
    discounted_stock = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, default=0, min_value=0)
    online_enabled = serializers.BooleanField(default = True)
    online_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, min_value=0.01)
    ean_not_available = serializers.BooleanField(default=None)
    product_pack_type = serializers.ChoiceField(choices=['packet', 'loose'],required=False)
    purchase_pack_size = serializers.IntegerField(default=None)
    reason_for_update = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    measurement_category = serializers.CharField(required=False, default=None)
    measurement_category_id = serializers.IntegerField(required=False, default=None)

    def validate(self, attrs):
        shop_id, pid = attrs['shop_id'], attrs['product_id']
        if attrs['ean_not_available']:
            attrs['product_ean_code'] = None
        elif attrs['ean_not_available'] is not None and not attrs['product_ean_code']:
            raise serializers.ValidationError("Please provide EAN Code")

        product = RetailerProduct.objects.filter(id=pid, shop_id=shop_id).last()
        if not product:
            raise serializers.ValidationError("Product not found!")

        sp = attrs['selling_price'] if attrs['selling_price'] else product.selling_price
        mrp = attrs['mrp'] if attrs['mrp'] else product.mrp
        ean = attrs['product_ean_code'] if attrs['product_ean_code'] else product.product_ean_code

        if ean and RetailerProduct.objects.filter(sku_type=product.sku_type, shop=shop_id, product_ean_code=ean,
                                                  mrp=mrp, is_deleted=False).exclude(id=pid).exists():
            raise serializers.ValidationError("Another product with same ean and mrp exists in catalog.")

        if (attrs['selling_price'] or attrs['mrp']) and sp > mrp:
            raise serializers.ValidationError("Selling Price should be equal to OR less than MRP")

        if 'online_price' in attrs and attrs['online_price'] > mrp:
            raise serializers.ValidationError("Online Price should be less than or equal to mrp")

        image_count = 0
        if 'images' in attrs and attrs['images']:
            image_count = len(attrs['images'])
        if 'image_ids' in attrs and attrs['image_ids']:
            image_count += len(attrs['image_ids'])
        if image_count > 3:
            raise serializers.ValidationError("images : Ensure this field has no more than 3 elements.")

        if attrs['add_offer_price']:
            offer_price, offer_sd, offer_ed = attrs['offer_price'], attrs['offer_start_date'], attrs['offer_end_date']

            if offer_price is None:
                raise serializers.ValidationError('Please provide offer price')

            if offer_price and offer_price > sp:
                raise serializers.ValidationError("Offer Price should be equal to OR less than Selling Price")

            if offer_sd is None:
                raise serializers.ValidationError('Please provide offer start date')
            if offer_ed is None:
                raise serializers.ValidationError('Please provide offer end date')
            if offer_sd > offer_ed:
                raise serializers.ValidationError('Offer end date should be greater than or equal to offer start date')
            # if offer_sd < datetime.date.today():
            #     raise serializers.ValidationError("Offer start date should be greater than or equal to today's date.")
        else:
            attrs['offer_price'], attrs['offer_start_date'], attrs['offer_end_date'] = None, None, None

        is_discounted = attrs['is_discounted']
        if is_discounted:
            # creating from discounted product
            if product.sku_type == 4:
                raise serializers.ValidationError("This product is already discounted. Further discounted product"
                                                  " cannot be created.")
            if 'discounted_price' not in attrs:
                raise serializers.ValidationError("Discounted price is required to create discounted product")
            elif 'discounted_stock' not in attrs:
                raise serializers.ValidationError("Discounted stock is required to create discounted product")
            elif attrs['discounted_price'] <= 0 :
                raise serializers.ValidationError("Discounted Price should be greater than 0")
            elif attrs['discounted_price'] >= sp:
                raise serializers.ValidationError("Discounted Price should be less than selling price")
            elif attrs['discounted_stock'] < 0:
                raise serializers.ValidationError("Invalid discounted stock")

            if product.product_pack_type == 'packet':
                attrs['discounted_stock'] = int(attrs['discounted_stock'])

        if product.product_pack_type == 'packet':
            attrs['stock_qty'] = int(attrs['stock_qty'])
        else:
            attrs['purchase_pack_size'] = 1

        if 'stock_qty' in self.initial_data and self.initial_data['stock_qty'] is not None\
                and 'reason_for_update' not in self.initial_data:
            raise serializers.ValidationError("reason for update is required for stock update")

        if attrs.get('product_pack_type') == 'loose':
            try:
                measurement_category = MeasurementCategory.objects.get(category=attrs['measurement_category'].lower())
                attrs['measurement_category_id'] = measurement_category.id
                MeasurementUnit.objects.get(category=measurement_category, default=True)
            except:
                raise serializers.ValidationError("Please provide a valid measurement category for Loose Product")
            attrs['purchase_pack_size'] = 1
        else:
            attrs['stock_qty'] = int(attrs.get('stock_qty'))

        return attrs


class RetailerProductsSearchSerializer(serializers.ModelSerializer):
    """
        RetailerProduct data for BASIC cart
    """
    is_discounted = serializers.SerializerMethodField()
    default_measurement_unit = serializers.SerializerMethodField()
    measurement_category = serializers.SerializerMethodField()
    product_pack_type = serializers.CharField(source='get_product_pack_type_display')
    image = serializers.SerializerMethodField()
    current_stock = serializers.SerializerMethodField()

    @staticmethod
    def get_default_measurement_unit(obj):
        if obj.measurement_category:
            return MeasurementUnit.objects.get(category=obj.measurement_category, default=True).unit
        return None

    @staticmethod
    def get_measurement_category(obj):
        return obj.measurement_category.get_category_display() if obj.measurement_category else None

    @staticmethod
    def get_is_discounted(obj):
        return obj.sku_type == 4

    @staticmethod
    def get_image(obj):
        retailer_object = obj.retailer_product_image.last()
        if retailer_object is None:
            if obj.linked_product:
                linked_product = obj.linked_product.product_pro_image.all()
                if linked_product:
                    image = linked_product[0].image.url
                    return image
                else:
                    parent_product = obj.linked_product.parent_product.parent_product_pro_image.all()
                    if parent_product:
                        image = parent_product[0].image.url
                        return image
            else:
                return None
        else:
            image = retailer_object.image.url
            return image

    @staticmethod
    def get_current_stock(obj):
        current_stock = PosInventory.objects.filter(product=obj.id, inventory_state=
        PosInventoryState.objects.get(inventory_state=PosInventoryState.AVAILABLE)).last().quantity
        return current_stock

    class Meta:
        model = RetailerProduct
        fields = ('id', 'name', 'selling_price', 'online_price', 'mrp', 'is_discounted', 'image',
                  'product_pack_type', 'measurement_category', 'default_measurement_unit', 'current_stock')


class BasicCartProductMappingSerializer(serializers.ModelSerializer):
    """
        Basic Cart Product Mapping Data
    """
    retailer_product = RetailerProductsSearchSerializer()
    product_price = serializers.SerializerMethodField('product_price_dt')
    offer_price_applied = serializers.SerializerMethodField()
    product_sub_total = serializers.SerializerMethodField('product_sub_total_dt')
    display_text = serializers.SerializerMethodField('display_text_dt')
    qty = serializers.SerializerMethodField()
    qty_unit = serializers.SerializerMethodField()
    units = serializers.SerializerMethodField()

    @staticmethod
    def get_offer_price_applied(obj):
        return obj.retailer_product.offer_price and obj.retailer_product.offer_start_date <= datetime.date.today() <= obj.retailer_product.offer_end_date

    def product_price_dt(self, obj):
        """
            Product price single
        """
        return obj.selling_price

    def product_sub_total_dt(self, obj):
        """
            Cart Product sub total / selling price
        """
        return Decimal(self.product_price_dt(obj)) * Decimal(obj.qty)

    def display_text_dt(self, obj):
        """
            If combo offer on product, display whether offer is applied or more products should be added
        """
        display_text = ''
        if obj.selling_price > 0:
            offers = obj.cart.offers
            for offer in offers:
                if offer['coupon_type'] == 'catalog' and offer['available_type'] != 'none' and \
                        offer['item_id'] == obj.retailer_product.id:
                    display_text = offer['display_text']
        return display_text

    @staticmethod
    def get_qty(obj):
        if obj.retailer_product.product_pack_type == 'loose':
            default_unit = MeasurementUnit.objects.get(category=obj.retailer_product.measurement_category, default=True)
            if obj.qty_conversion_unit:
                return obj.qty * default_unit.conversion / obj.qty_conversion_unit.conversion
            else:
                return obj.qty * default_unit.conversion / default_unit.conversion
        else:
            return int(obj.qty)

    @staticmethod
    def get_qty_unit(obj):
        if obj.retailer_product.product_pack_type == 'loose':
            if obj.qty_conversion_unit:
                return obj.qty_conversion_unit.unit
            else:
                return MeasurementUnit.objects.get(category=obj.retailer_product.measurement_category,
                                                   default=True).unit
        else:
            return None

    @staticmethod
    def get_units(obj):
        if obj.retailer_product.product_pack_type == 'loose':
            return MeasurementUnit.objects.filter(
                category=obj.retailer_product.measurement_category).values_list('unit', flat=True)
        return None

    class Meta:
        model = CartProductMapping
        fields = ('id', 'retailer_product', 'qty', 'product_price', 'offer_price_applied', 'product_sub_total',
                  'display_text', 'qty_unit', 'units')


class BasicCartSerializer(serializers.ModelSerializer):
    """
        Basic Cart Data
    """
    rt_cart_list = serializers.SerializerMethodField('rt_cart_list_dt')
    items_count = serializers.SerializerMethodField('items_count_dt')
    total_quantity = serializers.SerializerMethodField('total_quantity_dt')
    total_amount = serializers.SerializerMethodField('total_amount_dt')
    product_discount_from_mrp = serializers.SerializerMethodField()
    total_discount = serializers.SerializerMethodField()
    amount_payable = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('id', 'cart_no', 'rt_cart_list', 'items_count', 'total_quantity', 'total_amount',
                  'product_discount_from_mrp', 'total_discount', 'amount_payable')

    def get_product_discount_from_mrp(self, obj):
        total_amount = 0
        for cart_pro in obj.rt_cart_list.all():
            mrp = cart_pro.retailer_product.mrp if cart_pro.retailer_product.mrp else cart_pro.selling_price
            total_amount += (Decimal(mrp) - Decimal(cart_pro.selling_price)) * Decimal(cart_pro.qty)
        return total_amount

    def rt_cart_list_dt(self, obj):
        """
         Search and pagination on cart
        """
        qs = obj.rt_cart_list.filter(product_type=1).select_related('retailer_product',
                                                                    'retailer_product__measurement_category',
                                                                    'qty_conversion_unit').order_by('-id')
        search_text = self.context.get('search_text')
        # Search on name, ean and sku
        if search_text:
            qs = qs.filter(Q(retailer_product__sku__icontains=search_text)
                           | Q(retailer_product__name__icontains=search_text)
                           | Q(retailer_product__product_ean_code__icontains=search_text))

        if self.context.get('request'):
            qs = SmallOffsetPagination().paginate_queryset(qs, self.context.get('request'))

        # Order Cart In Purchased And Free Products
        cart_products = BasicCartProductMappingSerializer(qs, many=True, context=self.context).data
        product_offer_map = {}
        cart_free_product = {}

        for offer in obj.offers:
            if offer['coupon_type'] == 'catalog' and offer['type'] == 'combo':
                product_offer_map[offer['item_id']] = offer
            if offer['coupon_type'] == 'cart' and offer['type'] == 'free_product':
                cart_free_product = {
                    'cart_free_product': 1,
                    'id': offer['free_item_id'],
                    'mrp': offer['free_item_mrp'],
                    'name': offer['free_item_name'],
                    'qty': offer['free_item_qty'],
                    'display_text': 'FREE on orders above ₹' + str(offer['cart_minimum_value']).rstrip('0').rstrip('.')
                }

        for cart_product in cart_products:
            if cart_product['retailer_product']['id'] in product_offer_map:
                offer = product_offer_map[cart_product['retailer_product']['id']]
                free_product = {
                    'id': offer['free_item_id'],
                    'mrp': offer['free_item_mrp'],
                    'name': offer['free_item_name'],
                    'qty': offer['free_item_qty_added']
                }
                cart_product['free_product'] = free_product

        if cart_free_product:
            cart_products.append(cart_free_product)

        return cart_products

    def items_count_dt(self, obj):
        """
            Total Types Of Products
        """
        free_items = 0
        product_added = []
        for offer in obj.offers:
            if offer['type'] == 'combo' and offer['free_item_id'] not in product_added:
                free_items += 1
                product_added += [offer['free_item_id']]
            if offer['type'] == 'free_product':
                free_items += 1
        return obj.rt_cart_list.filter(product_type=1).count() + free_items

    def total_quantity_dt(self, obj):
        """
            Total Quantity Of All Products
        """
        qty = 0
        for cart_pro in obj.rt_cart_list.filter(product_type=1):
            qty += cart_pro.qty
        free_item_qty = 0
        for offer in obj.offers:
            if offer['type'] == 'combo':
                free_item_qty += int(offer['free_item_qty_added'])
            if offer['type'] == 'free_product':
                free_item_qty += int(offer['free_item_qty'])
        return qty + free_item_qty

    def total_amount_dt(self, obj):
        """
            Total Amount For all Products
        """
        total_amount = 0
        for cart_pro in obj.rt_cart_list.all():
            total_amount += Decimal(cart_pro.selling_price) * Decimal(cart_pro.qty)
        return total_amount

    @staticmethod
    def get_total_discount(obj):
        discount = 0
        offers = obj.offers
        if offers:
            array = list(filter(lambda d: d['type'] in ['discount'], offers))
            for i in array:
                discount += i['discount_value']
        return round(discount, 2)

    def get_amount_payable(self, obj):
        sub_total = float(self.total_amount_dt(obj)) - self.get_total_discount(obj)
        sub_total = math.floor(sub_total)
        return round(sub_total, 2)


class CheckoutSerializer(serializers.ModelSerializer):
    """
        Checkout Serializer - After products are added
    """
    total_discount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    redeem_points_value = serializers.SerializerMethodField()
    amount_payable = serializers.SerializerMethodField()
    buyer = PosUserSerializer()
    reward_detail = serializers.SerializerMethodField()

    @staticmethod
    def get_redeem_points_value(obj):
        redeem_points_value = 0
        if obj.redeem_factor:
            redeem_points_value = round(obj.redeem_points / obj.redeem_factor, 2)
        return redeem_points_value

    @staticmethod
    def get_reward_detail(obj):
        return RewardCls.reward_detail_cart(obj, obj.redeem_points)

    def get_total_amount(self, obj):
        """
            Total amount of products added
        """
        total_amount = 0
        for cart_pro in obj.rt_cart_list.all():
            if self.context['app_type']=='2':
                total_amount += Decimal(cart_pro.selling_price) * Decimal(cart_pro.qty)
            else:
                total_amount += Decimal(cart_pro.retailer_product.online_price) * Decimal(cart_pro.qty)
        return total_amount

    def get_total_discount(self, obj):
        """
            Discounts applied on cart
        """
        discount = 0
        offers = obj.offers
        if offers:
            array = list(filter(lambda d: d['type'] in ['discount'], offers))
            for i in array:
                discount += i['discount_value']
        return round(discount, 2)

    def get_amount_payable(self, obj):
        """
            Get Payable amount - (Total - Discount)
        """
        sub_total = float(self.get_total_amount(obj)) - self.get_total_discount(obj) - float(
            self.get_redeem_points_value(obj))
        sub_total = math.floor(sub_total)
        return round(sub_total, 2)

    class Meta:
        model = Cart
        fields = ('id', 'total_amount', 'total_discount', 'redeem_points_value', 'amount_payable', 'buyer',
                  'reward_detail')


class PaymentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentType
        fields = ('id', 'type', 'enabled')


class PaymentSerializer(serializers.ModelSerializer):
    payment_type = PaymentTypeSerializer()

    class Meta:
        model = Payment
        fields = ('payment_type', 'transaction_id', 'amount')


class BasicOrderListSerializer(serializers.ModelSerializer):
    """
        Order List For Basic Cart
    """
    buyer = PosUserSerializer()
    order_status = serializers.CharField(source='get_order_status_display')
    order_no = serializers.CharField()
    order_amount = serializers.ReadOnlyField()
    created_at = serializers.SerializerMethodField()
    invoice_amount = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField('payment_data')
    delivery_persons = serializers.SerializerMethodField()

    def get_created_at(self, obj):
        return obj.created_at.strftime("%b %d, %Y %-I:%M %p")

    def get_invoice_amount(self, obj):
        ordered_product = obj.rt_order_order_product.last()
        return round((ordered_product.invoice_amount_final), 2) if ordered_product else(obj.order_amount)

    def payment_data(self, obj):
        if not obj.rt_payment_retailer_order.exists():
            return None
        return PaymentSerializer(obj.rt_payment_retailer_order.all(), many=True).data

    def get_delivery_persons(self, obj):

        if obj.order_status == "out_for_delivery":
            x = User.objects.filter(id=obj.delivery_person_id)[:1:]

            return {"name": x[0].first_name, "phone_number": x[0].phone_number}

        #     return obj

        return None

    class Meta:
        model = Order
        fields = ('id', 'order_status', 'order_amount', 'order_no', 'buyer', 'created_at', 'payment', 'invoice_amount',
                  'delivery_persons')


class BasicCartListSerializer(serializers.ModelSerializer):
    """
        List of active/pending carts
    """
    total_amount = serializers.SerializerMethodField('total_amount_dt')
    buyer = PosUserSerializer()
    created_at = serializers.SerializerMethodField()

    @staticmethod
    def get_created_at(obj):
        return obj.created_at.strftime("%b %d, %Y %-I:%M %p")

    @staticmethod
    def total_amount_dt(obj):
        """
            Total Amount For all Products
        """
        total_amount = 0
        for cart_pro in obj.rt_cart_list.all():
            selling_price = cart_pro.selling_price if cart_pro.selling_price else cart_pro.retailer_product.selling_price
            total_amount += Decimal(selling_price) * Decimal(cart_pro.qty)
        return total_amount

    @staticmethod
    def get_total_discount(obj):
        """
            Discount on cart
        """
        discount = 0
        offers = obj.offers
        if offers:
            array = list(filter(lambda d: d['type'] in ['discount'], offers))
            for i in array:
                discount += i['discount_value'] if 'discount_value' in i else 0
        return round(discount, 2)

    class Meta:
        model = Cart
        fields = ('id', 'cart_no', 'cart_status', 'total_amount', 'buyer', 'created_at')


class OrderedDashBoardSerializer(serializers.Serializer):
    """
        Get Order, User, Product & total_final_amount count
    """

    shop_name = serializers.CharField()
    orders = serializers.IntegerField()
    registered_users = serializers.IntegerField(required=False)
    products = serializers.IntegerField(required=False)
    revenue = serializers.DecimalField(max_digits=9, decimal_places=2, required=False)


class ReturnItemsSerializer(serializers.ModelSerializer):
    """
        Single return item detail
    """
    status = serializers.SerializerMethodField()
    return_qty = serializers.SerializerMethodField()
    qty_unit = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.return_id.status

    @staticmethod
    def get_return_qty(obj):
        product = obj.ordered_product.retailer_product
        cart_product = CartProductMapping.objects.filter(retailer_product=product, cart=obj.ordered_product.ordered_product.order.ordered_cart).last()
        if product.product_pack_type == 'loose':
            default_unit = MeasurementUnit.objects.get(category=product.measurement_category, default=True)
            return obj.return_qty * default_unit.conversion / cart_product.qty_conversion_unit.conversion
        else:
            return int(obj.return_qty)

    @staticmethod
    def get_qty_unit(obj):
        cart_product = CartProductMapping.objects.filter(retailer_product=obj.ordered_product.retailer_product,
                                                         cart=obj.ordered_product.ordered_product.order.ordered_cart).last()
        return cart_product.qty_conversion_unit.unit if cart_product.retailer_product.product_pack_type == 'loose' else None

    class Meta:
        model = ReturnItems
        fields = ('return_qty', 'status', 'qty_unit')


class OrderReturnSerializer(serializers.ModelSerializer):
    """
        Return for an order
    """
    refund_points_value = serializers.SerializerMethodField()

    @staticmethod
    def get_refund_points_value(obj):
        refund_points_value = 0
        redeem_factor = obj.order.ordered_cart.redeem_factor
        if redeem_factor:
            refund_points_value = round(obj.refund_points / redeem_factor, 2)
        return refund_points_value

    class Meta:
        model = OrderReturn
        fields = ('id', 'return_reason', 'refund_amount', 'refund_points', 'refund_points_value', 'status')


class BasicOrderProductDetailSerializer(serializers.ModelSerializer):
    """
        Get single ordered product detail
    """
    retailer_product = RetailerProductsSearchSerializer()
    product_subtotal = serializers.SerializerMethodField()
    qty = serializers.SerializerMethodField()
    rt_return_ordered_product = ReturnItemsSerializer(many=True)
    qty_unit = serializers.SerializerMethodField()

    def get_qty(self, obj):
        """
            qty purchased
        """
        product = obj.retailer_product
        cart_product = CartProductMapping.objects.filter(retailer_product=product,
                                                         cart=obj.ordered_product.order.ordered_cart).last()
        if product.product_pack_type == 'loose':
            default_unit = MeasurementUnit.objects.get(category=product.measurement_category, default=True)
            return obj.shipped_qty * default_unit.conversion / cart_product.qty_conversion_unit.conversion
        else:
            return int(obj.shipped_qty)

    @staticmethod
    def get_qty_unit(obj):
        cart_product = CartProductMapping.objects.filter(retailer_product=obj.retailer_product,
                                                         cart=obj.ordered_product.order.ordered_cart).last()

        if cart_product.retailer_product.product_pack_type == 'loose':
            if cart_product.qty_conversion_unit:
                return cart_product.qty_conversion_unit.unit
            else:
                return MeasurementUnit.objects.get(category=cart_product.retailer_product.measurement_category, default=True).unit
        else:
            return None

    def get_product_subtotal(self, obj):
        """
            Received amount for product
        """
        return obj.selling_price * obj.shipped_qty

    def get_received_effective_price(self, obj):
        """
            Effective price for product after cart discount
        """
        return obj.effective_price * obj.shipped_qty

    class Meta:
        model = OrderedProductMapping
        fields = ('retailer_product', 'selling_price', 'qty', 'qty_unit', 'product_subtotal', 'rt_return_ordered_product')


class BasicOrderSerializer(serializers.ModelSerializer):
    """
        Pos Order detail
    """
    products = serializers.SerializerMethodField()
    ongoing_return = serializers.SerializerMethodField('ongoing_return_dt')

    @staticmethod
    def ongoing_return_dt(obj):
        ongoing_ret = obj.rt_return_order.filter(status='created').last()
        return OrderReturnSerializer(ongoing_ret).data if ongoing_ret else {}

    def get_products(self, obj):
        """
            Get ordered products details
        """
        changed_products = self.context.get('changed_products', None)
        return_summary = 1 if changed_products else 0
        qs = OrderedProductMapping.objects.filter(ordered_product__order=obj, product_type=1)
        if changed_products:
            qs = qs.filter(retailer_product__id__in=changed_products)
        products = BasicOrderProductDetailSerializer(qs, many=True).data
        # cart offers - map free product to purchased
        product_offer_map = {}
        cart_free_product = {}
        for offer in obj.ordered_cart.offers:
            if offer['coupon_type'] == 'catalog' and offer['type'] == 'combo':
                product_offer_map[offer['item_id']] = offer
            if offer['coupon_type'] == 'cart' and offer['type'] == 'free_product':
                cart_free_product = {
                    'cart_free_product': 1,
                    'id': offer['free_item_id'],
                    'mrp': offer['free_item_mrp'],
                    'name': offer['free_item_name'],
                    'qty': offer['free_item_qty'],
                    'display_text': 'FREE on orders above ₹' + str(offer['cart_minimum_value']).rstrip('0').rstrip('.')
                }

        all_returns = obj.rt_return_order.prefetch_related('rt_return_list').filter(order=obj)
        return_item_ongoing = {}
        return_item_map = {}
        for return_obj in all_returns:
            return_item_detail = return_obj.free_qty_map
            if return_item_detail:
                if return_obj.status == 'created':
                    for combo in return_item_detail:
                        return_item_ongoing[combo['item_id']] = combo['free_item_return_qty']
                else:
                    for combo in return_item_detail:
                        if combo['item_id'] in return_item_map:
                            return_item_map[combo['item_id']] += combo['free_item_return_qty']
                        else:
                            return_item_map[combo['item_id']] = combo['free_item_return_qty']

        for product in products:
            product['already_returned_qty'], product['return_qty'] = 0, 0
            rt_return_ordered_product = product.pop('rt_return_ordered_product', None)
            if rt_return_ordered_product:
                for return_item in rt_return_ordered_product:
                    if return_item['status'] == 'created':
                        product['return_qty'] = return_item['return_qty']
                    else:
                        product['already_returned_qty'] = product['already_returned_qty'] + return_item[
                            'return_qty'] if 'already_returned_qty' in product else return_item['return_qty']
            product['display_text'] = ''
            # map purchased product with free product
            if product['retailer_product']['id'] in product_offer_map:
                free_prod_info = self.get_free_product_text(product_offer_map, return_item_ongoing, return_item_map,
                                                            return_summary, product)
                if free_prod_info:
                    product.update(free_prod_info)

        if cart_free_product:
            return_qty = return_item_ongoing['free_product'] if 'free_product' in return_item_ongoing else 0
            if (return_summary and return_qty) or not return_summary:
                cart_free_product['already_returned_qty'] = return_item_map[
                    'free_product'] if 'free_product' in return_item_map else 0
                cart_free_product['return_qty'] = return_qty
                products.append(cart_free_product)
        return products

    @staticmethod
    def get_free_product_text(product_offer_map, return_item_ongoing, return_item_map, return_summary, product):
        offer = product_offer_map[product['retailer_product']['id']]
        free_return_qty = return_item_ongoing[offer['item_id']] if offer['item_id'] in return_item_ongoing else 0
        free_already_return_qty = return_item_map[offer['item_id']] if offer['item_id'] in return_item_map else 0
        original_qty = offer['free_item_qty_added']
        display_text = str(offer['free_item_name']) + ' (MRP ₹' + str(offer['free_item_mrp']) + ') | ' \
                       + 'Original qty: ' + str(original_qty)
        if free_already_return_qty:
            display_text += ' | Already returned qty: ' + str(free_already_return_qty)
        if return_summary:
            if not free_return_qty:
                return None
            else:
                display_text += ' | Return qty: ' + str(free_return_qty)
        display_text += ' | Offer: Buy ' + str(offer['item_qty']) + ' Get ' + str(offer['free_item_qty'])
        free_product = {
            'id': offer['free_item_id'],
            'mrp': offer['free_item_mrp'],
            'name': offer['free_item_name'],
            'qty': offer['free_item_qty_added'],
            'already_returned_qty': free_already_return_qty,
            'return_qty': free_return_qty
        }
        return {'free_product': free_product, 'display_text': display_text}

    def total_discount_amount_dt(self, obj):
        """
            Discount on cart
        """
        discount = 0
        offers = obj.ordered_cart.offers
        if offers:
            array = list(filter(lambda d: d['type'] in ['discount'], offers))
            for i in array:
                discount += i['discount_value']
        return round(discount, 2)

    class Meta:
        model = Order
        fields = ('id', 'order_no', 'products', 'ongoing_return')


class OrderReturnCheckoutSerializer(serializers.ModelSerializer):
    """
        Get refund amount on checkout
    """
    buyer = PosUserSerializer()
    return_info = serializers.SerializerMethodField()

    def get_return_info(self, obj):
        ongoing_return = obj.rt_return_order.filter(status='created').last()
        if not ongoing_return:
            return []
        block, cb = dict(), 1
        block[cb] = dict()
        block[cb][1] = "Invoice Amount: " + str(self.get_invoice_total(obj)).rstrip('0').rstrip('.')

        discount = self.get_discount_amount(obj)
        redeem_points_value = self.get_redeem_points_value(obj)
        if discount and redeem_points_value:
            block[cb][1] += '-(' + str(discount).rstrip('0').rstrip('.') + '+' + str(redeem_points_value).rstrip(
                '0').rstrip('.') + ') = Rs.' + str(self.get_invoice_final(obj)).rstrip('0').rstrip('.')
            block[cb][2] = '(Rs.' + str(discount).rstrip('0').rstrip('.') + ' off coupon, Rs.' + str(
                redeem_points_value).rstrip('0').rstrip('.') + ' off reward points)'
        elif discount:
            block[cb][1] += '-' + str(discount).rstrip('0').rstrip('.') + ' = Rs.' + str(self.get_invoice_final(obj)).rstrip(
                '0').rstrip('.')
            block[cb][2] = '(Rs.' + str(discount).rstrip('0').rstrip('.') + ' off coupon)'
        elif redeem_points_value:
            block[cb][1] += '-' + str(redeem_points_value).rstrip('0').rstrip('.') + ' = Rs.' + str(
                self.get_invoice_final(obj)).rstrip('0').rstrip('.')

        returns = OrderReturn.objects.filter(order=obj, status='completed')
        return_value, discount_adjusted, points_adjusted, refunded_amount = 0, 0, 0, 0.00
        for ret in returns:
            return_value += ret.return_value
            discount_adjusted += ret.discount_adjusted
            points_adjusted += ret.refund_points
            refunded_amount += max(0, ret.refund_amount)
        returned_oints_value = 0
        if obj.ordered_cart.redeem_factor:
            returned_oints_value = round(points_adjusted / obj.ordered_cart.redeem_factor, 2)
        if returns.exists():
            cb += 1
            block[cb] = dict()
            block[cb][1] = 'Previous returned amount: Rs.' + str(refunded_amount).rstrip('0').rstrip('.')
            block[cb][2] = '(Rs.' + str(refunded_amount).rstrip('0').rstrip('.') + ' paid on return of ' + str(
                return_value).rstrip('0').rstrip('.') + '.'
            block[cb][2] += ' Rs.' + str(discount_adjusted).rstrip('0').rstrip(
                '.') + ' coupon adjusted.)' if discount_adjusted else ')'

        cb += 1
        block[cb] = dict()
        block[cb][1] = 'Amount to be returned: Rs.' + str(self.get_refund_amount(obj)).rstrip('0').rstrip('.')

        block_array = []
        for b in block:
            lines_dict, lines_array = block[b], []
            for key in lines_dict:
                lines_array.append(lines_dict[key])
            block_array.append(lines_array)
        return block_array

    @staticmethod
    def get_redeem_points_value(obj):
        redeem_points_value = 0
        if obj.ordered_cart.redeem_factor:
            redeem_points_value = round(obj.ordered_cart.redeem_points / obj.ordered_cart.redeem_factor, 2)
        return redeem_points_value

    def get_invoice_total(self, obj):
        ordered_product = OrderedProduct.objects.get(order=obj)
        return round(ordered_product.invoice_subtotal, 2)

    def get_invoice_final(self, obj):
        ordered_product = OrderedProduct.objects.get(order=obj)
        return round(ordered_product.invoice_amount_final, 2)

    def get_discount_amount(self, obj):
        ordered_product = OrderedProduct.objects.get(order=obj)
        return round(ordered_product.invoice_subtotal - ordered_product.invoice_amount_total, 2)

    @staticmethod
    def get_cart_offers(obj):
        offers = obj.ordered_cart.offers
        cart_offers = []
        for offer in offers:
            if offer['coupon_type'] == 'cart' and offer['type'] == 'discount':
                cart_offers.append(offer)
        return cart_offers

    @staticmethod
    def get_refund_amount(obj):
        ongoing_return = obj.rt_return_order.filter(status='created').last()
        return round(ongoing_return.refund_amount, 2) if ongoing_return else 0

    class Meta:
        model = Order
        fields = ('id', 'return_info', 'order_status', 'buyer')


def coupon_name_validation(coupon_name):
    """
       Check that the Coupon name should be unique.
   """
    if coupon_name:
        if CouponRuleSet.objects.filter(rulename=coupon_name).exists():
            raise serializers.ValidationError(_("This Coupon Name has already been registered."))


def combo_offer_name_validation(combo_offer_name):
    """
        Check that the Combo Offer name should be unique.
    """
    if combo_offer_name:
        if CouponRuleSet.objects.filter(rulename=combo_offer_name).exists():
            raise serializers.ValidationError(_("This Offer name has already been registered."))


def validate_retailer_product(retailer_product, product_type):
    """
        Check that the product is present in RetailerProduct.
    """
    if not RetailerProduct.objects.filter(id=retailer_product).exists():
        raise serializers.ValidationError(_("{} Product Invalid".format(product_type)))


def discount_validation(data):
    """
         Check that the discount value should be less then discount_qty_amount.
    """
    if data['is_percentage']:
        if data['discount_value'] > 100:
            raise serializers.ValidationError("Discount percentage cannot be greater than 100")
        current_flat_value = (data['discount_value'] / 100) * data['order_value']
        if data['max_discount'] and current_flat_value > data['max_discount']:
            raise serializers.ValidationError(
                "Given Maximum Discount should be greater than or equal to {}".format(current_flat_value))
    else:
        if data['discount_value'] > data['order_value']:
            raise serializers.ValidationError("Discount Value must be less than Order Value")


def date_validation(data):
    """
        Check that the start date is before the expiry date.
    """
    if data['start_date'] > data['end_date']:
        raise serializers.ValidationError("End Date should be greater than Start Date")
    """
        Check that the expiry date is before the today.
    """
    if data['end_date'] < datetime.date.today():
        raise serializers.ValidationError("End Date should be greater than today's date")


class OfferCreateSerializer(serializers.Serializer):
    offer_type = serializers.ChoiceField(choices=[1, 2, 3])
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)

    def validate(self, data):
        date_validation(data)
        return data


class OfferGetSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True, min_value=1)
    shop_id = serializers.IntegerField()

    def validate(self, data):
        coupon = Coupon.objects.filter(id=data['id'], shop_id=data['shop_id']).last()
        if not coupon:
            raise serializers.ValidationError("Invalid coupon id")
        return data


class OfferUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True, min_value=1)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    is_active = serializers.BooleanField(required=False)
    offer_type = serializers.SerializerMethodField()
    shop_id = serializers.IntegerField()

    def validate(self, data):
        if data.get('start_date') and data.get('end_date'):
            date_validation(data)
        return data

    @staticmethod
    def get_offer_type(obj):
        coupon = Coupon.objects.filter(id=obj['id'], shop_id=obj['shop_id']).last()
        if not coupon:
            raise serializers.ValidationError("Invalid coupon id")
        rule = coupon.rule
        return 3 if rule.free_product else (1 if rule.discount else 2)


class RetailerProductSerializer(serializers.ModelSerializer):
    primary_product_id = serializers.SerializerMethodField()
    primary_product_name = serializers.SerializerMethodField()

    @staticmethod
    def get_primary_product_id(obj):
        return obj.id

    @staticmethod
    def get_primary_product_name(obj):
        return obj.name

    class Meta:
        model = RetailerProduct
        fields = ('primary_product_id', 'primary_product_name')


class RetailerFreeProductSerializer(serializers.ModelSerializer):
    free_product_id = serializers.SerializerMethodField()
    free_product_name = serializers.SerializerMethodField()

    @staticmethod
    def get_free_product_id(obj):
        return obj.id

    @staticmethod
    def get_free_product_name(obj):
        return obj.name

    class Meta:
        model = RetailerProduct
        fields = ('free_product_id', 'free_product_name')


class DiscountSerializer(serializers.ModelSerializer):
    discount_value = serializers.DecimalField(required=False, max_digits=12, decimal_places=2)

    class Meta:
        model = DiscountValue
        fields = ('discount_value', 'is_percentage', 'max_discount')


class CouponOfferSerializer(serializers.Serializer):
    coupon_name = serializers.CharField(required=True, max_length=50)
    order_value = serializers.DecimalField(required=True, max_digits=12, decimal_places=2, min_value=0.01)
    is_percentage = serializers.BooleanField(default=0)
    discount_value = serializers.DecimalField(required=True, max_digits=6, decimal_places=2, min_value=0.01)
    max_discount = serializers.DecimalField(max_digits=6, decimal_places=2, default=0, min_value=0)

    def validate(self, data):
        coupon_name_validation(data.get('coupon_name'))
        discount_validation(data)
        return data


class ComboOfferSerializer(serializers.Serializer):
    coupon_name = serializers.CharField(required=True, max_length=50)
    primary_product_id = serializers.IntegerField(required=True, min_value=1)
    primary_product_name = serializers.SerializerMethodField()
    primary_product_qty = serializers.IntegerField(required=True, min_value=1, max_value=99999)
    free_product_id = serializers.IntegerField(required=True, min_value=1)
    free_product_name = serializers.SerializerMethodField()
    free_product_qty = serializers.IntegerField(required=True, min_value=1, max_value=99999)

    def validate(self, data):
        validate_retailer_product(data.get('primary_product_id'), 'Primary')
        validate_retailer_product(data.get('free_product_id'), 'Free')
        combo_offer_name_validation(data.get('coupon_name'))
        return data

    @staticmethod
    def get_primary_product_name(obj):
        product = RetailerProduct.objects.filter(id=obj['primary_product_id']).last()
        return product.name if product else ''

    @staticmethod
    def get_free_product_name(obj):
        product = RetailerProduct.objects.filter(id=obj['free_product_id']).last()
        return product.name if product else ''


class FreeProductOfferSerializer(serializers.Serializer):
    coupon_name = serializers.CharField(required=True, max_length=50)
    order_value = serializers.DecimalField(required=True, max_digits=12, decimal_places=2, min_value=0.01)
    free_product_id = serializers.IntegerField(required=True, min_value=1)
    free_product_name = serializers.SerializerMethodField()
    free_product_qty = serializers.IntegerField(required=True, min_value=1, max_value=99999)

    def validate(self, data):
        validate_retailer_product(data.get('free_product_id'), 'Free')
        combo_offer_name_validation(data.get('coupon_name'))
        return data

    @staticmethod
    def get_free_product_name(obj):
        product = RetailerProduct.objects.get(id=obj['free_product_id'])
        return product.name if product else ''


class FreeProductOfferUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True, min_value=1)
    coupon_name = serializers.CharField(required=False, max_length=50)

    def validate(self, data):
        if data.get('coupon_name'):
            coupon_name_validation(data.get('coupon_name'))
        return data


class CouponOfferUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True, min_value=1)
    coupon_name = serializers.CharField(required=False, max_length=50)

    def validate(self, data):
        if data.get('coupon_name'):
            coupon_name_validation(data.get('coupon_name'))
        return data


class ComboOfferUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True, min_value=1)
    coupon_name = serializers.CharField(required=False, max_length=50)

    def validate(self, data):
        if data.get('coupon_name'):
            combo_offer_name_validation(data.get('coupon_name'))
        return data


class ComboGetSerializer(serializers.ModelSerializer):
    retailer_free_product = RetailerFreeProductSerializer()
    retailer_primary_product = RetailerProductSerializer()
    primary_product_qty = serializers.SerializerMethodField()

    @staticmethod
    def get_primary_product_qty(obj):
        return obj.purchased_product_qty

    class Meta:
        model = RuleSetProductMapping
        fields = ('retailer_primary_product', 'retailer_free_product', 'primary_product_qty', 'free_product_qty')


class CouponGetSerializer(serializers.ModelSerializer):
    offer_type = serializers.SerializerMethodField()
    details = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()

    def get_details(self, obj):
        offer_type = self.get_offer_type(obj)
        rule = obj.rule
        if offer_type == 1:
            response = DiscountSerializer(rule.discount).data
            response['order_value'] = rule.cart_qualifying_min_sku_value
        elif offer_type == 3:
            response = RetailerFreeProductSerializer(rule.free_product).data
            response['order_value'] = rule.cart_qualifying_min_sku_value
            response['free_product_qty'] = rule.free_product_qty
        else:
            data = ComboGetSerializer(RuleSetProductMapping.objects.get(rule=rule)).data
            response = dict()
            response['primary_product_qty'] = data['primary_product_qty']
            response['free_product_qty'] = data['free_product_qty']
            response.update(data['retailer_primary_product'])
            response.update(data['retailer_free_product'])
        return response

    @staticmethod
    def get_offer_type(obj):
        rule = obj.rule
        return 3 if rule.free_product else (1 if rule.discount else 2)

    @staticmethod
    def get_end_date(obj):
        return obj.expiry_date

    class Meta:
        model = Coupon
        fields = ('id', 'offer_type', 'coupon_name', 'details', 'start_date', 'end_date')


class CouponListSerializer(serializers.ModelSerializer):
    offer_type = serializers.SerializerMethodField()
    details = serializers.SerializerMethodField()

    def get_details(self, obj):
        offer_type = self.get_offer_type(obj)
        response = dict()
        if offer_type == 1:
            response = DiscountSerializer(obj.rule.discount).data
            response['order_value'] = obj.rule.cart_qualifying_min_sku_value
        elif offer_type == 3:
            response['order_value'] = obj.rule.cart_qualifying_min_sku_value
        return response

    @staticmethod
    def get_offer_type(obj):
        rule = obj.rule
        return 3 if rule.free_product else (1 if rule.discount else 2)

    class Meta:
        model = Coupon
        fields = ('id', 'offer_type', 'coupon_name', 'coupon_code', 'details', 'is_active')


class PosShopSerializer(serializers.ModelSerializer):
    shop_id = serializers.SerializerMethodField()
    shop_name = serializers.SerializerMethodField()

    @staticmethod
    def get_shop_id(obj):
        return obj.shop.id

    @staticmethod
    def get_shop_name(obj):
        return obj.shop.shop_name

    class Meta:
        model = PosShopUserMapping
        fields = ('shop_id', 'shop_name', 'user_type', 'is_delivery_person')


class BasicCartUserViewSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    is_mlm = serializers.BooleanField(default=False)
    referral_code = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)

    def validate(self, attrs):
        phone_number, email, referral_code, shop_id = attrs.get('phone_number'), attrs.get('email'), \
                                                      attrs.get('referral_code'), attrs.get('shop_id')

        if not phone_number:
            raise serializers.ValidationError("Please provide phone number")
        if not re.match(r'^[6-9]\d{9}$', phone_number):
            raise serializers.ValidationError("Please provide a valid phone number")

        if phone_number == '9999999999' and attrs.get('is_mlm'):
            raise serializers.ValidationError("Default Number (9999999999) cannot be registered for rewards!")

        user = User.objects.filter(phone_number=phone_number).last()
        if user and ReferralCode.is_marketing_user(user) and attrs.get('is_mlm'):
            raise serializers.ValidationError("User is already registered for rewards.")

        if referral_code:
            if not ReferralCode.objects.filter(referral_code=referral_code).exists():
                raise serializers.ValidationError("Referral Code Invalid!")

        return attrs


class InventoryReportSerializer(serializers.ModelSerializer):
    product_id = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    stock_value = serializers.SerializerMethodField()

    @staticmethod
    def get_product_id(obj):
        return obj.product.id

    @staticmethod
    def get_product_name(obj):
        return obj.product.name

    @staticmethod
    def get_stock(obj):
        return obj.quantity

    @staticmethod
    def get_stock_value(obj):
        sp = obj.product.selling_price
        return round(float(obj.quantity) * float(sp), 2) if obj.quantity > 0 else 0

    class Meta:
        model = PosInventory
        fields = ('product_id', 'product_name', 'stock', 'stock_value')


class InventoryLogReportSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    transaction_type = serializers.SerializerMethodField()

    @staticmethod
    def get_created_at(obj):
        return obj.created_at.strftime("%b %d, %Y")

    @staticmethod
    def get_transaction_type(obj):
        return obj.transaction_type.replace('_', ' ').title()

    class Meta:
        model = PosInventoryChange
        fields = ('created_at', 'transaction_type', 'transaction_id', 'quantity')


class SalesReportSerializer(serializers.Serializer):
    offset = serializers.IntegerField(default=0)
    limit = serializers.IntegerField(default=10)
    report_type = serializers.ChoiceField(choices=('daily', 'monthly', 'invoice'), default='daily')
    date_filter = serializers.ChoiceField(choices=('today', 'yesterday', 'this_week', 'last_week', 'this_month',
                                                   'last_month', 'this_year'), required=False, allow_null=True,
                                          allow_blank=True)
    start_date = serializers.DateField(required=False, default=datetime.date.today)
    end_date = serializers.DateField(required=False, default=datetime.date.today)
    sort_by = serializers.ChoiceField(choices=('date', 'month', 'sale', 'returns', 'effective_sale'), default=None)
    sort_order = serializers.ChoiceField(choices=(1, -1), required=False, default=-1)

    def validate(self, attrs):
        date_filter = attrs.get('date_filter')
        sort_by = attrs.get('sort_by')

        if attrs.get('report_type') == 'monthly':
            if date_filter and date_filter not in ['this_month', 'last_month', 'this_year']:
                raise serializers.ValidationError("Invalid Date Filter For Monthly Reports!")
            sort_by = sort_by if sort_by else 'month'
            if sort_by == 'date':
                raise serializers.ValidationError("Invalid Sort Field For Monthly Reports!")
        else:
            sort_by = sort_by if sort_by else 'date'

        attrs['sort_by'] = 'created_at__' + sort_by if sort_by in ['date', 'month'] else sort_by

        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError("End Date Must Be Greater Than Start Date")
        return attrs


class SalesReportResponseSerializer(serializers.Serializer):
    date = serializers.SerializerMethodField()
    month = serializers.SerializerMethodField()
    order_count = serializers.IntegerField(read_only=True)
    sale = serializers.FloatField(read_only=True)
    returns = serializers.FloatField(read_only=True)
    effective_sale = serializers.FloatField(read_only=True)
    invoice_no = serializers.CharField(read_only=True)

    @staticmethod
    def get_date(obj):
        return obj['created_at__date'].strftime("%b %d, %Y") if 'created_at__date' in obj else None

    @staticmethod
    def get_month(obj):
        return calendar.month_name[obj['created_at__month']] + ', ' + str(
            obj['created_at__year']) if 'created_at__month' in obj else None


class CustomerReportSerializer(serializers.Serializer):
    date_filter = serializers.ChoiceField(choices=('today', 'yesterday', 'this_week', 'last_week', 'this_month',
                                                   'last_month', 'this_year'), required=False, allow_null=True,
                                          allow_blank=True)
    start_date = serializers.DateField(required=False, default=datetime.date.today)
    end_date = serializers.DateField(required=False, default=datetime.date.today)
    sort_by = serializers.ChoiceField(choices=('date', 'order_count', 'sale', 'returns', 'effective_sale'),
                                      default='date')
    sort_order = serializers.ChoiceField(choices=(1, -1), required=False, default=-1)

    def validate(self, attrs):
        sort_by = attrs.get('sort_by')
        sort_by = sort_by if sort_by else 'date'
        attrs['sort_by'] = 'created_at' if sort_by in ['date'] else sort_by

        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError("End Date Must Be Greater Than Start Date")
        return attrs


class CustomerReportResponseSerializer(serializers.Serializer):
    phone_number = serializers.CharField(read_only=True)
    name = serializers.SerializerMethodField()
    date_added = serializers.SerializerMethodField()
    loyalty_points = serializers.IntegerField(read_only=True)
    order_count = serializers.IntegerField(read_only=True)
    sale = serializers.FloatField(read_only=True)
    returns = serializers.FloatField(read_only=True)
    effective_sale = serializers.FloatField(read_only=True)

    @staticmethod
    def get_date_added(obj):
        return obj['created_at'].strftime("%b %d, %Y") if 'created_at' in obj else None

    @staticmethod
    def get_name(obj):
        first_name, last_name = obj['user__first_name'], obj['user__last_name']
        if first_name:
            return first_name + ' ' + last_name if last_name else first_name
        return None


class CustomerReportDetailResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    order_id = serializers.CharField(read_only=True)
    points_added = serializers.IntegerField(read_only=True)
    points_redeemed = serializers.IntegerField(read_only=True)
    sale = serializers.FloatField(read_only=True)
    returns = serializers.FloatField(read_only=True)
    effective_sale = serializers.FloatField(read_only=True)
    date = serializers.SerializerMethodField()

    @staticmethod
    def get_date(obj):
        return obj['created_at__date'].strftime("%b %d, %Y") if 'created_at__date' in obj else None


class ReturnItemsGetSerializer(serializers.ModelSerializer):
    """
        Single return item detail
    """
    product_id = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    selling_price = serializers.SerializerMethodField()
    return_qty = serializers.SerializerMethodField()
    qty_unit = serializers.SerializerMethodField()

    @staticmethod
    def get_product_id(obj):
        return obj.ordered_product.retailer_product.id

    @staticmethod
    def get_product_name(obj):
        return obj.ordered_product.retailer_product.name

    @staticmethod
    def get_selling_price(obj):
        return obj.ordered_product.selling_price

    @staticmethod
    def get_return_qty(obj):
        product = obj.ordered_product.retailer_product
        cart_product = CartProductMapping.objects.filter(retailer_product=product,
                                                         cart=obj.ordered_product.ordered_product.order.ordered_cart).last()
        if product.product_pack_type == 'loose':
            default_unit = MeasurementUnit.objects.get(category=product.measurement_category, default=True)
            if cart_product.qty_conversion_unit:
                return obj.return_qty * default_unit.conversion / cart_product.qty_conversion_unit.conversion
            else:
                return obj.return_qty * default_unit.conversion / default_unit.conversion
        else:
            return int(obj.return_qty)

    @staticmethod
    def get_qty_unit(obj):
        cart_product = CartProductMapping.objects.filter(retailer_product=obj.ordered_product.retailer_product,
                                                         cart=obj.ordered_product.ordered_product.order.ordered_cart).last()
        return cart_product.qty_conversion_unit.unit if cart_product.retailer_product.product_pack_type == 'loose' else None

    class Meta:
        model = ReturnItems
        fields = ('product_id', 'product_name', 'selling_price', 'return_qty', 'qty_unit', 'return_value')


class OrderReturnGetSerializer(serializers.ModelSerializer):
    return_items = serializers.SerializerMethodField()
    refund_points_value = serializers.SerializerMethodField()
    refund_amount = serializers.SerializerMethodField()

    @staticmethod
    def get_refund_amount(obj):
        return max(obj.refund_amount, 0)

    @staticmethod
    def get_return_items(obj):
        qs = ReturnItems.objects.filter(return_id=obj, ordered_product__product_type=1)
        return_items = ReturnItemsGetSerializer(qs, many=True).data

        product_offer_map, cart_free_product = {}, {}
        for offer in obj.order.ordered_cart.offers:
            if offer['coupon_type'] == 'catalog' and offer['type'] == 'combo':
                product_offer_map[offer['item_id']] = offer
            if offer['coupon_type'] == 'cart' and offer['type'] == 'free_product':
                cart_free_product = {'cart_free_product': 1, 'id': offer['free_item_id'], 'mrp': offer['free_item_mrp'],
                                     'name': offer['free_item_name'], 'qty': offer['free_item_qty'],
                                     'display_text': 'FREE on orders above ₹' + str(offer['cart_minimum_value']).rstrip(
                                         '0').rstrip('.')}

        free_products_return = obj.free_qty_map
        free_return_item_map = {}
        if free_products_return:
            for combo in free_products_return:
                free_return_item_map[combo['item_id']] = combo['free_item_return_qty']

        for ret in return_items:
            ret['free_product_return'] = 0
            if ret['product_id'] in free_return_item_map:
                ret['free_product_return'] = 1
                offer = product_offer_map[ret['product_id']]
                ret['free_product_text'] = 'Returned ' + str(free_return_item_map[ret['product_id']]) + ' items of ' \
                                           + offer['free_item_name'] + ' | Buy ' + str(offer['item_qty']) + ' Get ' + \
                                           str(offer['free_item_qty'])

        if 'free_product' in free_return_item_map and int(free_return_item_map['free_product']) > 0:
            cart_free_product['return_qty'] = free_return_item_map['free_product']
            return_items.append(cart_free_product)

        return return_items

    @staticmethod
    def get_refund_points_value(obj):
        refund_points_value = 0
        redeem_factor = obj.order.ordered_cart.redeem_factor
        if redeem_factor:
            refund_points_value = round(obj.refund_points / redeem_factor, 2)
        return refund_points_value

    class Meta:
        model = OrderReturn
        fields = ('id', 'return_value', 'discount_adjusted', 'refund_points_value', 'refund_amount', 'return_items')


class BasicOrderDetailSerializer(serializers.ModelSerializer):
    """
        Pos Order detail
    """
    order_summary = serializers.SerializerMethodField()
    return_summary = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    buyer = PosUserSerializer()
    creation_date = serializers.SerializerMethodField()
    order_status_display = serializers.CharField(source='get_order_status_display')
    payment = serializers.SerializerMethodField('payment_data')

    @staticmethod
    def get_creation_date(obj):
        return obj.created_at.strftime("%b %d, %Y %-I:%M %p")

    def get_order_summary(self, obj):
        order_summary = dict()
        discount = self.get_discount(obj)
        redeem_points_value = self.get_redeem_points_value(obj)
        order_value = round(obj.order_amount + discount + redeem_points_value, 2)
        order_summary['order_value'], order_summary['discount'], order_summary['redeem_points_value'], order_summary[
            'amount_paid'] = order_value, discount, redeem_points_value, obj.order_amount
        order_summary['payments'] = PaymentSerializer(obj.rt_payment_retailer_order.all(), many=True).data
        return order_summary

    @staticmethod
    def get_return_summary(obj):
        returns = OrderReturn.objects.filter(order=obj, status='completed')
        return_value, discount_adjusted, points_adjusted, refund_amount = 0, 0, 0, 0
        for ret in returns:
            return_value += ret.return_value
            discount_adjusted += ret.discount_adjusted
            points_adjusted += ret.refund_points
            refund_amount += max(0, ret.refund_amount)
        points_value = 0
        if obj.ordered_cart.redeem_factor:
            points_value = round(points_adjusted / obj.ordered_cart.redeem_factor, 2)
        return_summary = dict()
        return_summary['return_value'], return_summary['discount_adjusted'], return_summary[
            'points_adjusted'], return_summary[
            'amount_returned'] = return_value, discount_adjusted, points_value, refund_amount
        return return_summary

    def get_items(self, obj):
        """
            Get ordered products details
        """
        qs = OrderedProductMapping.objects.filter(ordered_product__order=obj, product_type=1)
        products = BasicOrderProductDetailSerializer(qs, many=True).data
        # cart offers - map free product to purchased
        product_offer_map, cart_free_product = {}, {}
        for offer in obj.ordered_cart.offers:
            if offer['coupon_type'] == 'catalog' and offer['type'] == 'combo':
                product_offer_map[offer['item_id']] = offer
            if offer['coupon_type'] == 'cart' and offer['type'] == 'free_product':
                cart_free_product = {'cart_free_product': 1, 'id': offer['free_item_id'], 'mrp': offer['free_item_mrp'],
                                     'name': offer['free_item_name'], 'qty': offer['free_item_qty'],
                                     'display_text': 'FREE on orders above ₹' + str(offer['cart_minimum_value']).rstrip(
                                         '0').rstrip('.')}

        completed_returns = OrderReturn.objects.filter(order=obj, status='completed')
        return_item_map = {}
        for return_obj in completed_returns:
            return_item_detail = return_obj.free_qty_map
            if return_item_detail:
                for combo in return_item_detail:
                    if combo['item_id'] in return_item_map:
                        return_item_map[combo['item_id']] += combo['free_item_return_qty']
                    else:
                        return_item_map[combo['item_id']] = combo['free_item_return_qty']

        for product in products:
            product['returned_qty'] = 0
            rt_return_ordered_product = product.pop('rt_return_ordered_product', None)
            if rt_return_ordered_product:
                for return_item in rt_return_ordered_product:
                    if return_item['status'] != 'created':
                        product['returned_qty'] = product['returned_qty'] + return_item['return_qty'
                        ] if 'returned_qty' in product else return_item['return_qty']
            product['returned_subtotal'] = round(Decimal(product['selling_price']) * product['returned_qty'], 2)
            # map purchased product with free product
            if product['retailer_product']['id'] in product_offer_map:
                free_prod_info = self.get_free_product_text(product_offer_map, return_item_map, product)
                if free_prod_info:
                    product.update(free_prod_info)

        if cart_free_product:
            cart_free_product['returned_qty'] = return_item_map[
                'free_product'] if 'free_product' in return_item_map else 0
            products.append(cart_free_product)
        return products

    @staticmethod
    def get_free_product_text(product_offer_map, return_item_map, product):
        offer = product_offer_map[product['retailer_product']['id']]
        free_already_return_qty = return_item_map[offer['item_id']] if offer['item_id'] in return_item_map else 0
        display_text = ['Free - ' + str(offer['free_item_qty_added']) + ' items of ' + str(
            offer['free_item_name']) + ' on purchase of ' + str(product['qty']) + ' items | Buy ' + str(offer[
                                                                                                            'item_qty']) + ' Get ' + str(
            offer['free_item_qty'])]
        if free_already_return_qty:
            display_text += ['Free return - ' + str(free_already_return_qty) + ' items of ' + str(
                offer['free_item_name']) + ' on return of ' + str(product['returned_qty']) + ' items']
        return {'free_product': 1, 'display_text': display_text}

    @staticmethod
    def get_redeem_points_value(obj):
        redeem_points_value = 0
        if obj.ordered_cart.redeem_factor:
            redeem_points_value = round(obj.ordered_cart.redeem_points / obj.ordered_cart.redeem_factor, 2)
        return redeem_points_value

    def get_discount(self, obj):
        discount = 0
        offers = self.get_cart_offers(obj)
        for offer in offers:
            discount += float(offer['discount_value'])
        return round(discount, 2)

    @staticmethod
    def get_cart_offers(obj):
        offers = obj.ordered_cart.offers
        cart_offers = []
        for offer in offers:
            if offer['coupon_type'] == 'cart' and offer['type'] == 'discount':
                cart_offers.append(offer)
        return cart_offers

    def payment_data(self, obj):
        if not obj.rt_payment_retailer_order.exists():
            return None
        return PaymentSerializer(obj.rt_payment_retailer_order.all(), many=True).data

    class Meta:
        model = Order
        fields = ('id', 'order_no', 'creation_date', 'order_status', 'items', 'order_summary', 'return_summary',
                  'delivery_person', 'buyer', 'order_status_display','payment')


class AddressCheckoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ('type', 'complete_address')


class VendorSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    alternate_phone_number = serializers.CharField(required=False, default=None, allow_null=True)

    class Meta:
        model = Vendor
        fields = ('id', 'company_name', 'vendor_name', 'contact_person_name', 'phone_number', 'alternate_phone_number',
                  'email', 'address', 'pincode', 'gst_number', 'retailer_shop', 'status')

    def validate(self, attrs):

        city = Pincode.objects.filter(pincode=attrs['pincode']).last()
        if not city:
            raise serializers.ValidationError("Invalid Pincode")

        shop = self.context.get('shop')
        if 'id' in attrs:
            if not Vendor.objects.filter(retailer_shop=shop, id=attrs['id']).exists():
                raise serializers.ValidationError("Invalid vendor id")

        if attrs['alternate_phone_number'] and not re.match(r'^[6-9]\d{9}$', attrs['alternate_phone_number']):
            raise serializers.ValidationError("Please provide a valid alternate phone number")

        return attrs

    def update(self, vendor_id, validated_data):
        vendor_obj = Vendor.objects.filter(id=vendor_id).last()
        vendor_obj.company_name, vendor_obj.vendor_name = validated_data['company_name'], validated_data['vendor_name']
        vendor_obj.contact_person_name = validated_data['contact_person_name']
        vendor_obj.phone_number = validated_data['phone_number']
        vendor_obj.alternate_phone_number = validated_data['alternate_phone_number']
        vendor_obj.email, vendor_obj.address = validated_data['email'], validated_data['address']
        vendor_obj.pincode, vendor_obj.gst_number = validated_data['pincode'], validated_data['gst_number']
        vendor_obj.status = validated_data['status']
        vendor_obj.save()


class VendorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ('id', 'vendor_name', 'contact_person_name', 'phone_number', 'status')


class POProductSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()
    qty_unit = serializers.CharField(default=None)
    pack_size = serializers.IntegerField(default=1)

    def validate(self, attrs):
        # qty w.r.t pack type
        qty_unit = None
        product = RetailerProduct.objects.filter(id=attrs['product_id']).last()
        if product.product_pack_type == 'loose':
            attrs['qty'], qty_unit = get_default_qty(attrs['qty_unit'], product, attrs['qty'])
            attrs['pack_size'] = 1
        else:
            attrs['pack_size'] = product.purchase_pack_size
            attrs['qty'] = int(attrs['qty'])
        attrs['qty_unit'] = qty_unit
        return attrs

    class Meta:
        model = PosCartProductMapping
        fields = ('product_id', 'price', 'qty', 'qty_unit', 'pack_size', 'is_bulk')


class POSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    vendor_id = serializers.IntegerField()
    products = POProductSerializer(many=True)
    send_mail = serializers.BooleanField(required=False, default=0)

    class Meta:
        model = PosCart
        fields = ('id', 'vendor_id', 'products', 'send_mail')

    def validate(self, attrs):
        # Validate vendor id
        shop = self.context.get('shop')
        if not Vendor.objects.filter(id=attrs['vendor_id']).exists():
            raise serializers.ValidationError("Invalid Vendor Id")

        # Validate products
        for product_dict in attrs['products']:
            product = RetailerProduct.objects.filter(id=product_dict['product_id'],
                                                     shop=self.context.get('shop')).last()
            if not product:
                raise serializers.ValidationError("Product Id Invalid {}".format(product_dict['product_id']))
            if float(product_dict['price']) > float(product.mrp):
                raise serializers.ValidationError(
                    "Price cannot be greater than product MRP ({}) for product {}".format(product.mrp, product.name))

        # Check if update - check cart id and if grn is done on products
        if 'id' in attrs:
            cart = PosCart.objects.filter(id=attrs['id'], retailer_shop=shop).last()
            if not cart:
                raise serializers.ValidationError("Purchase order not found!")
            products_updatable, products_given = [], attrs['products']
            for product in products_given:
                mapping = PosCartProductMapping.objects.filter(cart=cart, product=product['product_id']).last()
                if mapping and mapping.is_grn_done and (
                        round(float(product['price']), 2) != round(float(mapping.price), 2) or
                        round(float(product['qty']), 3) != round(float(mapping.qty), 3)):
                    raise serializers.ValidationError("Cannot edit products whose grn is done.")
                products_updatable += [product]
            attrs['products'] = products_updatable
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            user, shop, cart_products = self.context.get('user'), self.context.get('shop'), validated_data['products']
            cart = PosCart.objects.create(vendor_id=validated_data['vendor_id'], retailer_shop=shop, raised_by=user,
                                          last_modified_by=user)
            for product in cart_products:
                PosCartProductMapping.objects.create(cart=cart, product_id=product['product_id'], qty=product['qty'],
                                                     price=product['price'], qty_conversion_unit_id=product['qty_unit'],
                                                     pack_size=product['pack_size'])
            mail_to_vendor_on_po_creation.delay(cart.id)
            return cart

    def update(self, cart_id, validated_data):
        with transaction.atomic():
            user, shop, cart_products = self.context.get('user'), self.context.get('shop'), validated_data['products']
            cart = PosCart.objects.get(id=cart_id)
            updated_pid = []
            for product in cart_products:
                mapping, created = PosCartProductMapping.objects.get_or_create(cart=cart,
                                                                               product_id=product['product_id'])
                mapping.qty, mapping.price = product['qty'], product['price']
                mapping.qty_conversion_unit_id = product['qty_unit']
                mapping.pack_size = product['pack_size']
                mapping.save()
                updated_pid += [product['product_id']]
            PosCartProductMapping.objects.filter(cart=cart, is_grn_done=False).exclude(
                product_id__in=updated_pid).delete()
            # status po
            total_grn_qty = PosGRNOrderProductMapping.objects.filter(grn_order__order=cart.pos_po_order).aggregate(
                Sum('received_qty')).get('received_qty__sum')
            total_grn_qty = total_grn_qty if total_grn_qty else 0
            po_status = PosCart.PARTIAL_DELIVERED if total_grn_qty > 0 else PosCart.OPEN
            total_po_qty = PosCartProductMapping.objects.filter(cart=cart).aggregate(Sum('qty')).get('qty__sum')
            po_status = PosCart.DELIVERED if total_po_qty == total_grn_qty else po_status
            cart.last_modified_by, cart.status = user, po_status
            cart.save()
            if validated_data['send_mail']:
                mail_to_vendor_on_po_creation.delay(cart.id)


class POProductGetSerializer(serializers.ModelSerializer):
    mrp = serializers.SerializerMethodField()
    grned_qty = serializers.SerializerMethodField()
    po_price_history = serializers.SerializerMethodField()
    qty = serializers.SerializerMethodField()
    qty_unit = serializers.SerializerMethodField()
    units = serializers.SerializerMethodField()

    @staticmethod
    def get_po_price_history(obj):
        product = obj.product
        return PosCartProductMapping.objects.filter(cart__retailer_shop=product.shop, product=product).order_by(
            '-created_at').annotate(date=Func(F('created_at'), Value('DD Mon YYYY'),
                                              function='to_char', output_field=CharField()))[:3].values('price', 'date')

    @staticmethod
    def get_grned_qty(obj):
        already_grn = obj.product.pos_product_grn_order_product.filter(grn_order__order__ordered_cart=obj.cart). \
            aggregate(Sum('received_qty')).get('received_qty__sum')
        if already_grn:
            if obj.product.product_pack_type == 'loose':
                default_unit = MeasurementUnit.objects.get(category=obj.product.measurement_category, default=True)
                if obj.qty_conversion_unit:
                    return Decimal(already_grn) * default_unit.conversion / obj.qty_conversion_unit.conversion
                else:
                    return round(Decimal(already_grn) * default_unit.conversion / default_unit.conversion, 3)
            else:
                return int(already_grn)
        return 0

    @staticmethod
    def get_mrp(obj):
        return obj.product.mrp

    @staticmethod
    def get_qty(obj):
        return obj.qty_given

    @staticmethod
    def get_qty_unit(obj):
        return obj.given_qty_unit

    @staticmethod
    def get_units(obj):
        if obj.product.product_pack_type == 'loose':
            return MeasurementUnit.objects.filter(
                category=obj.product.measurement_category).values_list('unit', flat=True)
        return None

    class Meta:
        model = PosCartProductMapping
        fields = ('product_id', 'product_name', 'product_pack_type', 'mrp', 'price', 'qty', 'qty_unit', 'grned_qty', 'po_price_history',
                  'is_grn_done', 'units', 'pack_size', 'is_bulk')


class POGetSerializer(serializers.ModelSerializer):
    po_products = serializers.SerializerMethodField()
    raised_by = PosShopUserSerializer()
    last_modified_by = PosShopUserSerializer()
    total_price = serializers.SerializerMethodField()

    @staticmethod
    def get_total_price(obj):
        tp = obj.po_products.aggregate(
            total_price=Sum(
                Case(
                    When(is_bulk=True, then=(F('price') * F('qty'))),
                    default=(F('price') * F('pack_size') * F('qty')),
                    output_field=FloatField()
                )))['total_price']
        return round(tp, 2) if tp else tp

    def get_po_products(self, obj):
        search_text = self.context['search_text']
        resp_obj = PosCartProductMapping.objects.filter(cart=obj)
        if search_text:
            resp_obj = resp_obj.filter(Q(product__name__icontains=search_text)
                                       | Q(product__product_ean_code__icontains=search_text)
                                       | Q(product__sku__icontains=search_text))

        return SmallOffsetPagination().paginate_queryset(
            POProductGetSerializer(resp_obj, many=True).data, self.context['request'])

    class Meta:
        model = PosCart
        fields = ('id', 'vendor_id', 'vendor_name', 'po_no', 'status', 'po_products', 'total_price', 'raised_by',
                  'last_modified_by', 'created_at', 'modified_at')


class POProductInfoSerializer(serializers.ModelSerializer):
    stock_qty = serializers.SerializerMethodField()
    po_price_history = serializers.SerializerMethodField()

    @staticmethod
    def get_stock_qty(obj):
        inv_available = PosInventoryState.objects.get(inventory_state=PosInventoryState.AVAILABLE)
        inv = PosInventory.objects.filter(product=obj, inventory_state=inv_available).last()
        return inv.quantity if inv else None

    @staticmethod
    def get_po_price_history(obj):
        return PosCartProductMapping.objects.filter(cart__retailer_shop=obj.shop, product=obj).order_by(
            '-created_at').annotate(date=Func(F('created_at'), Value('DD Mon YYYY'),
                                              function='to_char', output_field=CharField()))[:3].values('price', 'date')

    class Meta:
        model = RetailerProduct
        fields = ('name', 'selling_price', 'stock_qty', 'po_price_history')


class POListSerializer(serializers.ModelSerializer):
    grn_id = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    total_qty = serializers.SerializerMethodField()
    total_pieces = serializers.SerializerMethodField()

    @staticmethod
    def get_total_qty(obj):
        return obj.po_products.aggregate(Sum('qty')).get('qty__sum')

    @staticmethod
    def get_total_pieces(obj):
        tp = obj.po_products.aggregate(
            total_price=Sum(
                Case(
                    When(is_bulk=True, then=(F('qty'))),
                    default=(F('qty') * F('pack_size')),
                    output_field=FloatField()
                )))['total_price']
        return round(tp, 2) if tp else tp

    @staticmethod
    def get_total_price(obj):
        tp = obj.po_products.aggregate(
            total_price=Sum(
                Case(
                    When(is_bulk=True, then=(F('price') * F('qty'))),
                    default=(F('price') * F('pack_size') * F('qty')),
                    output_field=FloatField()
                )))['total_price']
        return round(tp, 2) if tp else tp

    @staticmethod
    def get_date(obj):
        return obj.created_at.strftime("%b %d, %Y %-I:%M %p")

    @staticmethod
    def get_grn_id(obj):
        grn = PosGRNOrder.objects.filter(order=obj.pos_po_order).last()
        return grn.id if grn else None

    class Meta:
        model = PosCart
        fields = ('id', 'po_no', 'vendor_name', 'grn_id', 'total_price', 'status', 'date', 'total_qty', 'total_pieces')


class PosGrnProductSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()
    pack_size = serializers.IntegerField(default=1)

    class Meta:
        model = PosGRNOrderProductMapping
        fields = ('product_id', 'received_qty', 'pack_size')


class PosGrnOrderCreateSerializer(serializers.ModelSerializer):
    po_id = serializers.IntegerField()
    products = PosGrnProductSerializer(many=True)
    invoice = serializers.FileField(required=True, validators=[FileExtensionValidator(
        allowed_extensions=['pdf'])])
    invoice_no = serializers.CharField(required=True, max_length=100)
    invoice_date = serializers.DateField(required=True)
    invoice_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, min_value=0.01)

    class Meta:
        model = PosGRNOrder
        fields = ('po_id', 'products', 'invoice', 'invoice_no', 'invoice_date', 'invoice_amount')

    def validate(self, attrs):
        shop = self.context.get('shop')
        # Validate po id
        po = PosCart.objects.filter(id=attrs['po_id'], retailer_shop=shop).prefetch_related('po_products',
                                                                                            'po_products__product').last()
        if not po:
            raise serializers.ValidationError("Invalid PO Id")
        if po.status == PosCart.CANCELLED:
            raise serializers.ValidationError("This PO was cancelled")
        # if po.status == PosCart.DELIVERED:
        #     raise serializers.ValidationError("PO completely delivered")

        # **** Limit GRN to 1
        if PosGRNOrder.objects.filter(order=po.pos_po_order).exists():
            raise serializers.ValidationError("GRN already created for this PO")

        # grn_products = {int(i['product']): i['received_qty_sum'] for i in PosGRNOrderProductMapping.objects.filter(
        #     grn_order__order=po.pos_po_order).values('product').annotate(received_qty_sum=Sum(F('received_qty')))}

        # Validate products
        product_added = False
        for product in attrs['products']:
            product['product_id'] = int(product['product_id'])
            po_product = po.po_products.filter(product_id=product['product_id']).last()
            if not po_product:
                raise serializers.ValidationError("Product Id Invalid {}".format(product['product_id']))
            # product_added = True if int(product['received_qty']) > 0 else product_added
            product_added = True
            product_obj = po_product.product
            # qty w.r.t pack type
            if product_obj.product_pack_type == 'loose':
                if po_product.qty_conversion_unit:
                    product['received_qty'], qty_unit = get_default_qty(po_product.qty_conversion_unit.unit, product_obj,
                                                                        product['received_qty'])
                else:
                    product['received_qty'], qty_unit = get_default_qty(MeasurementUnit.objects.get(category=po_product.product.measurement_category, default=True).unit,
                                                                        product_obj, product['received_qty'])
                product['pack_size'] = 1
            else:
                # product['received_qty'] = int(product['received_qty'] * po_product.pack_size)
                product['pack_size'] = po_product.pack_size
            # already_grned_qty = grn_products[product['product_id']] if product['product_id'] in grn_products else 0
            # if int(product['received_qty']) + already_grned_qty > po_product.qty:
            #     raise serializers.ValidationError(
            #         "{}. (Received quantity) + (Already grned quantity) cannot be greater than PO quantity".format(
            #             product_obj.name))
            if round(float(product['received_qty']), 3) > round(float(po_product.qty), 3):
                raise serializers.ValidationError(
                    "{}. Received quantity cannot be greater than PO quantity".format(
                        product_obj.name))
        if not product_added:
            raise serializers.ValidationError("Please provide grn info for atleast one product")
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            user, shop, products = self.context.get('user'), self.context.get('shop'), validated_data['products']
            po = PosCart.objects.get(id=validated_data['po_id'])

            grn_order = PosGRNOrder.objects.create(order=po.pos_po_order, added_by=user, last_modified_by=user,
                                                   invoice_no=validated_data['invoice_no'],
                                                   invoice_amount=validated_data['invoice_amount'],
                                                   invoice_date=validated_data['invoice_date'])
            for product in products:
                product['received_qty'] = round(Decimal(product['received_qty']), 3)
                if product['received_qty'] > 0:
                    PosGRNOrderProductMapping.objects.create(grn_order=grn_order, product_id=product['product_id'],
                                                             received_qty=product['received_qty'],
                                                             pack_size=product['pack_size'])

                    # if PosCartProductMapping.objects.filter(
                    #         cart=po, product_id=product['product_id'], is_bulk=True).exists():
                    #     product['pack_size'] = 1
                    PosInventoryCls.grn_inventory(product['product_id'], PosInventoryState.NEW,
                                                  PosInventoryState.AVAILABLE, product['received_qty'], user,
                                                  grn_order.grn_id, PosInventoryChange.GRN_ADD,
                                                  product['pack_size'])
            total_grn_qty = PosGRNOrderProductMapping.objects.filter(grn_order__order=po.pos_po_order).aggregate(
                Sum('received_qty')).get('received_qty__sum')
            total_grn_qty = total_grn_qty if total_grn_qty else 0
            po_status = PosCart.PARTIAL_DELIVERED if total_grn_qty > 0 else PosCart.OPEN
            total_po_qty = PosCartProductMapping.objects.filter(cart=po).aggregate(Sum('qty')).get('qty__sum')
            po.status = PosCart.DELIVERED if total_po_qty == total_grn_qty else po_status
            po.save()
            # Upload invoice
            if 'invoice' in validated_data and validated_data['invoice']:
                Document.objects.create(grn_order=grn_order, document=validated_data['invoice'],
                                        document_number=validated_data['invoice_no'])
            return grn_order


class PosGrnOrderUpdateSerializer(serializers.ModelSerializer):
    grn_id = serializers.IntegerField()
    products = PosGrnProductSerializer(many=True)
    invoice = serializers.FileField(required=False, allow_null=True, validators=[FileExtensionValidator(
        allowed_extensions=['pdf'])])
    invoice_no = serializers.CharField(required=True, max_length=100)
    invoice_date = serializers.DateField(required=True)
    invoice_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, min_value=0.01)

    class Meta:
        model = PosGRNOrder
        fields = ('grn_id', 'products', 'invoice', 'invoice_no', 'invoice_date', 'invoice_amount')

    def validate(self, attrs):
        shop = self.context.get('shop')
        # Validate grn id
        grn_order = PosGRNOrder.objects.filter(id=attrs['grn_id'],
                                               order__ordered_cart__retailer_shop=shop).select_related(
            'order__ordered_cart').last()
        if not grn_order:
            raise serializers.ValidationError("Invalid Grn Id")
        if grn_order.order.ordered_cart.status == PosCart.CANCELLED:
            raise serializers.ValidationError("The PO was cancelled")

        # grn_products = {int(i['product']): i['received_qty_sum'] for i in PosGRNOrderProductMapping.objects.filter(
        #     grn_order__order=grn_order.order).exclude(grn_order=grn_order).values('product').annotate(
        #     received_qty_sum=Sum(F('received_qty')))}

        # Validate products
        product_added = False
        for product in attrs['products']:
            product['product_id'] = int(product['product_id'])
            po_product = grn_order.order.ordered_cart.po_products.filter(product_id=product['product_id']).last()
            if not po_product:
                raise serializers.ValidationError("Product Id Invalid {}".format(product['product_id']))
            product_added = True
            # product_added = True if int(product['received_qty']) > 0 else product_added
            product_obj = po_product.product
            # qty w.r.t pack type
            if product_obj.product_pack_type == 'loose':
                if po_product.qty_conversion_unit:
                    product['received_qty'], qty_unit = get_default_qty(po_product.qty_conversion_unit.unit, product_obj,
                                                                    product['received_qty'])
                else:
                    product['received_qty'], qty_unit = get_default_qty(MeasurementUnit.objects.get(category=po_product.product.measurement_category, default=True).unit,
                                                                        product_obj, product['received_qty'])
                product['pack_size'] = 1
            else:
                # product['received_qty'] = int(product['received_qty'] * po_product.pack_size)
                product['pack_size'] = po_product.pack_size
            # already_grned_qty = grn_products[product['product_id']] if product['product_id'] in grn_products else 0
            # if int(product['received_qty']) + already_grned_qty > po_product.qty:
            #     raise serializers.ValidationError(
            #         "{}. (Received quantity) + (Already grned quantity) cannot be greater than PO quantity".format(
            #             product_obj.name))
            if round(float(product['received_qty']), 3) > round(float(po_product.qty), 3):
                raise serializers.ValidationError(
                    "{}. Received quantity cannot be greater than PO quantity".format(
                        product_obj.name))
        if not product_added:
            raise serializers.ValidationError("Please provide grn info for atleast one product")
        return attrs

    def update(self, grn_id, validated_data):
        with transaction.atomic():
            user, shop, products = self.context.get('user'), self.context.get('shop'), validated_data['products']
            grn_order = PosGRNOrder.objects.get(id=grn_id)
            grn_order.last_modified_by = user
            grn_order.invoice_no = validated_data['invoice_no']
            grn_order.invoice_amount = validated_data['invoice_amount']
            grn_order.invoice_date = validated_data['invoice_date']
            grn_order.save()
            for product in products:
                mapping, _ = PosGRNOrderProductMapping.objects.get_or_create(grn_order=grn_order,
                                                                             product_id=product['product_id'])
                qty_change = round(Decimal(product['received_qty']), 3) - mapping.received_qty
                mapping.received_qty = round(Decimal(product['received_qty']), 3)
                mapping.pack_size = product['pack_size']
                mapping.save()
                # if PosCartProductMapping.objects.filter(
                #         cart=grn_order.order.ordered_cart, product_id=product['product_id'], is_bulk=True).exists():
                #     product['pack_size'] = 1
                if qty_change != 0:
                    PosInventoryCls.grn_inventory(product['product_id'], PosInventoryState.AVAILABLE,
                                                  PosInventoryState.AVAILABLE, qty_change, user,
                                                  grn_order.grn_id, PosInventoryChange.GRN_UPDATE,
                                                  product['pack_size'])
            total_grn_qty = PosGRNOrderProductMapping.objects.filter(
                grn_order__order=grn_order.order.ordered_cart.pos_po_order).aggregate(
                Sum('received_qty')).get('received_qty__sum')
            total_grn_qty = total_grn_qty if total_grn_qty else 0
            po_status = PosCart.PARTIAL_DELIVERED if total_grn_qty > 0 else PosCart.OPEN
            total_po_qty = PosCartProductMapping.objects.filter(cart=grn_order.order.ordered_cart).aggregate(
                Sum('qty')).get(
                'qty__sum')
            po_status = PosCart.DELIVERED if total_po_qty == total_grn_qty else po_status
            PosCart.objects.filter(id=grn_order.order.ordered_cart.id).update(status=po_status)
            # Upload invoice
            if 'invoice' in validated_data and validated_data['invoice']:
                doc, _ = Document.objects.get_or_create(grn_order=grn_order)
                doc.document = validated_data['invoice']
                doc.document_number = validated_data['invoice_no']
                doc.save()
            return grn_order


class GrnListSerializer(serializers.ModelSerializer):
    grn_total_price = serializers.SerializerMethodField()

    @staticmethod
    def get_grn_total_price(obj):
        po_products = PosCartProductMapping.objects.filter(cart=obj.order.ordered_cart)

        grn_products = {int(i['product_id']): i['received_qty'] for i in PosGRNOrderProductMapping.objects.filter(
            grn_order=obj).values('product_id', 'received_qty')}

        total_price = None
        if po_products:
            total_price = 0
            for po_pr in po_products:
                if po_pr.product.id in grn_products and po_pr.is_bulk:
                    total_price += float(grn_products[po_pr.product.id]) * float(po_pr.price)
                elif po_pr.product.id in grn_products:
                    total_price += float(grn_products[po_pr.product.id]) * float(po_pr.price) * float(po_pr.pack_size)
            total_price = round(total_price, 2)
        return total_price

    class Meta:
        model = PosGRNOrder
        fields = ('id', 'po_no', 'vendor_name', 'po_status', 'grn_total_price')


class GrnOrderProductGetSerializer(serializers.ModelSerializer):
    other_grned_qty = serializers.SerializerMethodField()
    curr_grn_received_qty = serializers.SerializerMethodField()
    # qty = serializers.SerializerMethodField()
    qty_unit = serializers.SerializerMethodField()
    previous_grn_returned_qty = serializers.SerializerMethodField()
    product_pack_type = serializers.SerializerMethodField()

    @staticmethod
    def get_product_pack_type(obj):
        return obj.product.product_pack_type

    @staticmethod
    def get_curr_grn_received_qty(obj):
        grn_order = PosGRNOrder.objects.filter(order=obj.cart.pos_po_order).last()
        grn_product = PosGRNOrderProductMapping.objects.filter(grn_order=grn_order, product=obj.product).last()
        if grn_product:
            if obj.product.product_pack_type == 'loose':
                default_unit = MeasurementUnit.objects.get(category=obj.product.measurement_category, default=True)
                if obj.qty_conversion_unit:
                    return Decimal(grn_product.received_qty) * default_unit.conversion / obj.qty_conversion_unit.conversion
                else:
                    return round(Decimal(grn_product.received_qty) * default_unit.conversion / default_unit.conversion, 3)
            else:
                return int(grn_product.received_qty)
        return 0

    @staticmethod
    def get_previous_grn_returned_qty(obj):
        grn_order = PosGRNOrder.objects.filter(order=obj.cart.pos_po_order).last()
        previous_return_qty = PosReturnItems.objects.filter(
            grn_return_id__grn_ordered_id=grn_order, product=obj.product,
            grn_return_id__status=PosReturnGRNOrder.RETURN_STATUS.RETURNED, is_active=True). \
            aggregate(total_qty=Sum('return_qty'))
        previous_return_qty = previous_return_qty.get('total_qty', None)
        if previous_return_qty:
            if obj.product.product_pack_type == 'loose':
                default_unit = MeasurementUnit.objects.get(category=obj.product.measurement_category, default=True)
                if obj.qty_conversion_unit:
                    return Decimal(previous_return_qty) * default_unit.conversion / obj.qty_conversion_unit.conversion
                else:
                    return Decimal(previous_return_qty) * default_unit.conversion / default_unit.conversion
            else:
                return int(previous_return_qty)
        return 0

    # @staticmethod
    # def get_qty(obj):
    #     return obj.qty_given

    @staticmethod
    def get_qty_unit(obj):
        return obj.given_qty_unit

    def get_other_grned_qty(self, obj):
        exclude_grn = self.context.get('exclude_grn')
        already_grn = obj.product.pos_product_grn_order_product.filter(grn_order__order__ordered_cart=obj.cart).exclude(
            grn_order=exclude_grn). \
            aggregate(Sum('received_qty')).get('received_qty__sum')
        if already_grn:
            if obj.product.product_pack_type == 'loose':
                default_unit = MeasurementUnit.objects.get(category=obj.product.measurement_category, default=True)
                if obj.qty_conversion_unit:
                    return Decimal(already_grn) * default_unit.conversion / obj.qty_conversion_unit.conversion
                else:
                    return Decimal(already_grn) * default_unit.conversion / default_unit.conversion
            else:
                return int(already_grn)
        return 0

    class Meta:
        model = PosCartProductMapping
        fields = ('product_id', 'product_name', 'price', 'qty', 'qty_unit', 'other_grned_qty', 'curr_grn_received_qty',
                  'pack_size', 'previous_grn_returned_qty', 'product_pack_type', 'is_bulk')


class GrnInvoiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Document
        fields = ('document', )


class GrnOrderGetSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    pos_grn_invoice = GrnInvoiceSerializer()
    added_by = PosShopUserSerializer()
    last_modified_by = PosShopUserSerializer()
    po_total_price = serializers.SerializerMethodField()
    current_grn_total_price = serializers.SerializerMethodField()

    @staticmethod
    def get_current_grn_total_price(obj):
        po_products = PosCartProductMapping.objects.filter(cart=obj.order.ordered_cart)

        grn_products = {int(i['product_id']): i['received_qty'] for i in PosGRNOrderProductMapping.objects.filter(
            grn_order=obj).values('product_id', 'received_qty',)}

        total_price = None
        if po_products:
            total_price = 0
            for po_pr in po_products:
                if po_pr.product.id in grn_products and po_pr.is_bulk:
                    total_price += float(grn_products[po_pr.product.id]) * float(po_pr.price)
                elif po_pr.product.id in grn_products:
                    total_price += float(grn_products[po_pr.product.id]) * float(po_pr.price) * float(po_pr.pack_size)
            total_price = round(total_price, 2)
        return total_price

    @staticmethod
    def get_po_total_price(obj):
        tp = obj.order.ordered_cart.po_products.aggregate(
            total_price=Sum(
                Case(
                    When(is_bulk=True, then=(F('price') * F('qty'))),
                    default=(F('price') * F('pack_size') * F('qty')),
                    output_field=FloatField()
                )))['total_price']
        return round(tp, 2) if tp else tp

    @staticmethod
    def get_products(obj):
        po_products = PosCartProductMapping.objects.filter(cart=obj.order.ordered_cart)
        po_products_data = GrnOrderProductGetSerializer(po_products, context={'exclude_grn': obj}, many=True).data

        return po_products_data

    class Meta:
        model = PosGRNOrder
        fields = ('id', 'po_no', 'po_status', 'vendor_name', 'products', 'invoice_no', 'invoice_amount', 'invoice_date',
                  'pos_grn_invoice', 'po_total_price', 'current_grn_total_price', 'added_by', 'last_modified_by',
                  'created_at', 'modified_at')


class PosShopUserMappingListSerializer(serializers.ModelSerializer):
    phone_number = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    def get_phone_number(self, obj):
        return obj.user.phone_number

    def get_email(self, obj):
        return obj.user.email

    def get_name(self, obj):
        first_name, last_name, name = obj.user.first_name, obj.user.last_name, '-'
        if first_name:
            name = first_name + ' ' + last_name if last_name else first_name
        return name

    class Meta:
        model = PosShopUserMapping
        fields = ('id', 'user_id', 'phone_number', 'name', 'email', 'user_type', 'status', 'is_delivery_person')


class MeasurementCategorySerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='get_category_display')
    default_unit = serializers.SerializerMethodField()
    units = serializers.SerializerMethodField()

    @staticmethod
    def get_default_unit(obj):
        default_unit = MeasurementUnit.objects.filter(default=True, category=obj).last()
        return default_unit.unit if default_unit else None

    @staticmethod
    def get_units(obj):
        return MeasurementUnit.objects.filter(category=obj).values_list('unit', flat=True)

    class Meta:
        model = MeasurementCategory
        fields = ('id', 'category', 'default_unit', 'units')


class RetailerProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = RetailerProduct
        fields = ('id', 'name', 'product_pack_type', 'mrp')


class PosInventoryProductMappingSerializer(serializers.ModelSerializer):
    product = RetailerProductSerializer(read_only=True)
    # inventory_state = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()

    # def get_inventory_state(self, obj):
    #     return PosInventoryState.objects.filter(inventory_state=obj.inventory_state).last().inventory_state

    def get_available_quantity(self, obj):
        return obj.quantity

    class Meta:
        model = PosInventory
        fields = ('product', 'available_quantity',)


class PosGRNOrderProductMappingSerializer(serializers.ModelSerializer):
    product = RetailerProductSerializer(read_only=True)
    received_qty = serializers.SerializerMethodField()
    qty_unit = serializers.SerializerMethodField()
    product_pack_type = serializers.SerializerMethodField()

    @staticmethod
    def get_qty_unit(obj):
        return obj.given_qty_unit

    @staticmethod
    def get_received_qty(obj):
        return obj.qty_given

    class Meta:
        model = PosGRNOrderProductMapping
        fields = ('product', 'received_qty', 'qty_unit', 'pack_size', 'product_pack_type')

    @staticmethod
    def get_product_pack_type(obj):
        return obj.product.product_pack_type

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['product']:
            representation['product_id'] = representation['product']['id']
            representation['product_name'] = representation['product']['name']
        else:
            representation['product_id'] = None
            representation['product_name'] = None
        representation.pop('product')
        return representation


class PosReturnItemsSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()
    return_qty = serializers.SerializerMethodField()
    qty_unit = serializers.SerializerMethodField()
    total_return_qty = serializers.SerializerMethodField()
    other_return_qty = serializers.SerializerMethodField()

    class Meta:
        model = PosReturnItems
        fields = ('id', 'product', 'return_qty', 'other_return_qty', 'total_return_qty', 'qty_unit', 'pack_size')

    @staticmethod
    def get_qty_unit(obj):
        return obj.given_qty_unit

    @staticmethod
    def get_return_qty(obj):
        return obj.qty_given

    @staticmethod
    def get_product(obj):
        po_products_data = PosGRNOrderProductMapping.objects.filter(
            grn_order=obj.grn_return_id.grn_ordered_id, product_id=obj.product.id)
        return PosGRNOrderProductMappingSerializer(po_products_data, many=True).data

    @staticmethod
    def get_total_return_qty(obj):
        total_returned = PosReturnItems.objects.filter(
            grn_return_id__grn_ordered_id=obj.grn_return_id.grn_ordered_id, product=obj.product,
            is_active=True).aggregate(total=Sum('return_qty'))['total']
        if total_returned:
            po_product = PosCartProductMapping.objects.filter(
                cart=obj.grn_return_id.grn_ordered_id.order.ordered_cart, product=obj.product).last()
            if obj.product.product_pack_type == 'loose':
                default_unit = MeasurementUnit.objects.get(category=obj.product.measurement_category, default=True)
                if po_product.qty_conversion_unit:
                    return round(Decimal(total_returned) * default_unit.conversion / po_product.qty_conversion_unit.conversion, 3)
                else:
                    return round(
                        Decimal(total_returned) * default_unit.conversion / default_unit.conversion,
                        3)
            else:
                return int(total_returned)
        return 0

    @staticmethod
    def get_other_return_qty(obj):
        other_return = PosReturnItemsSerializer.get_total_return_qty(obj) - (obj.return_qty if obj.is_active else 0)

        if other_return:
            po_product = PosCartProductMapping.objects.filter(
                cart=obj.grn_return_id.grn_ordered_id.order.ordered_cart, product=obj.product).last()
            if obj.product.product_pack_type == 'loose':
                default_unit = MeasurementUnit.objects.get(category=obj.product.measurement_category, default=True)
                if po_product.qty_conversion_unit:
                    return round(Decimal(other_return) * default_unit.conversion / po_product.qty_conversion_unit.conversion,
                             3)
                else:
                    return round(
                        Decimal(other_return) * default_unit.conversion / default_unit.conversion,
                        3)
            else:
                return int(other_return)
        return 0


class GrnOrderGetListSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    po_total_price = serializers.SerializerMethodField()
    current_grn_total_price = serializers.SerializerMethodField()

    @staticmethod
    def get_current_grn_total_price(obj):
        po_products = PosCartProductMapping.objects.filter(cart=obj.order.ordered_cart)

        grn_products = {int(i['product_id']): i['received_qty'] for i in PosGRNOrderProductMapping.objects.filter(
            grn_order=obj).values('product_id', 'received_qty')}

        total_price = None
        if po_products:
            total_price = 0
            for po_pr in po_products:
                if po_pr.product.id in grn_products and po_pr.is_bulk:
                    total_price += float(grn_products[po_pr.product.id]) * float(po_pr.price)
                elif po_pr.product.id in grn_products:
                    total_price += float(grn_products[po_pr.product.id]) * float(po_pr.price) * float(po_pr.pack_size)
            total_price = round(total_price, 2)
        return total_price

    @staticmethod
    def get_po_total_price(obj):
        tp = obj.order.ordered_cart.po_products.aggregate(
            total_price=Sum(
                Case(
                    When(is_bulk=True, then=(F('price') * F('qty'))),
                    default=(F('price') * F('pack_size') * F('qty')),
                    output_field=FloatField()
                )))['total_price']
        return round(tp, 2) if tp else tp

    def get_products(self, obj):
        po_products = PosCartProductMapping.objects.filter(cart=obj.order.ordered_cart)
        po_products_data = GrnOrderProductGetSerializer(po_products, context={'exclude_grn': obj}, many=True).data

        return po_products_data

    class Meta:
        model = PosGRNOrder
        fields = ('id', 'grn_id', 'vendor_name', 'po_no', 'po_status', 'invoice_no', 'invoice_amount',
                  'po_total_price', 'current_grn_total_price', 'products',)


class ReturnGrnOrderSerializer(serializers.ModelSerializer):
    grn_product_return = serializers.SerializerMethodField()
    grn_id = serializers.SerializerMethodField()
    last_modified_by = PosShopUserSerializer(read_only=True)

    class Meta:
        model = PosReturnGRNOrder
        fields = ('id', 'pr_number', 'po_no', 'grn_ordered_id', 'grn_id', 'grn_product_return', 'status',
                  'last_modified_by', 'debit_note_number', 'debit_note', 'created_at', 'modified_at')

    def validate(self, data):
        shop = self.context.get('shop')
        if not 'grn_ordered_id' in self.initial_data or not self.initial_data['grn_ordered_id']:
            raise serializers.ValidationError(_('grn_ordered_id is required'))

        pos_grn_obj = get_validate_grn_order(int(self.initial_data['grn_ordered_id']), shop)
        if 'error' in pos_grn_obj:
            raise serializers.ValidationError(pos_grn_obj['error'])
        data['grn_ordered_id'] = pos_grn_obj['grn_ordered_id']

        if 'status' not in self.initial_data or self.initial_data['status'] != PosReturnGRNOrder.CANCELLED:
            if 'grn_product_return' not in self.initial_data or type(self.initial_data['grn_product_return']) != list:
                raise serializers.ValidationError("Provide return item details")
            # Check return item details
            pos_order_products_mapping = PosGRNOrderProductMapping.objects.filter(grn_order=data['grn_ordered_id'].id)
            all_ordered_products = pos_order_products_mapping.values_list('product_id', flat=True)

            product_list = []
            for rtn_product in self.initial_data['grn_product_return']:

                if 'product_id' not in rtn_product or 'return_qty' not in rtn_product or not rtn_product['product_id'] \
                        or rtn_product['return_qty'] is None:
                    raise serializers.ValidationError("'product_id' and 'return_qty' are mandatory for "
                                                      "every return product object.")

                if rtn_product['return_qty'] <= 0:
                    raise serializers.ValidationError("return_qty must be greater than 0.")

                if rtn_product['product_id'] not in all_ordered_products:
                    raise serializers.ValidationError("Invalid product for the selected order.")

                if rtn_product['product_id'] in product_list:
                    product_name = PosGRNOrderProductMapping.objects.filter(grn_order=data['grn_ordered_id'].id,
                                                                            product=rtn_product['product_id']).\
                        values_list('product__name', flat=True).last()
                    raise serializers.ValidationError(f"product '{product_name}' getting repeated.")
                product_list.append(rtn_product['product_id'])

                total_ordered_qty = pos_order_products_mapping.filter(product_id=rtn_product['product_id']). \
                    last().received_qty

                previous_return_qty = PosReturnItems.objects.filter(
                    grn_return_id__grn_ordered_id=pos_grn_obj['grn_ordered_id'].id, product_id=rtn_product['product_id'],
                    grn_return_id__status=PosReturnGRNOrder.RETURN_STATUS.RETURNED, is_active=True,
                    grn_return_id__grn_ordered_id__order__ordered_cart__retailer_shop=shop). \
                    aggregate(total_qty=Sum('return_qty'))

                po_product = PosCartProductMapping.objects.filter(cart=pos_grn_obj['grn_ordered_id'].order.ordered_cart, product_id=rtn_product['product_id']).select_related('product').last()

                if po_product.product.product_pack_type == 'loose':
                    if po_product.qty_conversion_unit:
                        rtn_product['return_qty'], qty_unit = get_default_qty(po_product.qty_conversion_unit.unit,
                                                                              po_product.product,
                                                                              rtn_product['return_qty'])
                    else:
                        rtn_product['return_qty'], qty_unit = get_default_qty(MeasurementUnit.objects.get(category=po_product.product.measurement_category,default=True).unit,
                                                                              po_product.product,
                                                                              rtn_product['return_qty'])
                    rtn_product['pack_size'] = 1
                else:
                    rtn_product['return_qty'] = int(rtn_product['return_qty'])
                    rtn_product['pack_size'] = po_product.pack_size

                if 'id' in self.initial_data and self.initial_data['id']:
                    if PosReturnGRNOrder.objects.filter(id=self.initial_data['id'],
                                                        status=PosReturnGRNOrder.CANCELLED,
                                                        grn_ordered_id__order__ordered_cart__retailer_shop=shop).exists():
                        raise serializers.ValidationError("This Order is cancelled, can't modify")

                    if rtn_product['return_qty'] > total_ordered_qty:
                        raise serializers.ValidationError("Return Qty is greater than the delivered qty.")

                    obj = PosReturnGRNOrder.objects.filter(
                        grn_ordered_id=pos_grn_obj['grn_ordered_id'], grn_order_return__product=rtn_product['product_id'],
                        grn_order_return__is_active=True, status=PosReturnGRNOrder.RETURNED,
                        grn_ordered_id__order__ordered_cart__retailer_shop=shop). \
                        exclude(id=self.initial_data['id']). \
                        aggregate(total_product_qty=Sum('grn_order_return__return_qty'))

                    if rtn_product['return_qty'] > (total_ordered_qty -
                                                    (obj['total_product_qty'] if obj['total_product_qty'] else 0)):
                        raise serializers.ValidationError("Return Qty is greater than the delivered qty.")
                else:
                    if rtn_product['return_qty'] > (total_ordered_qty -
                                                    (previous_return_qty['total_qty'] if previous_return_qty['total_qty'] else 0)):
                        raise serializers.ValidationError("Return Qty is greater than the remaining delivered qty.")

            data['grn_product_return'] = self.initial_data['grn_product_return']

        instance_id = self.instance.id if self.instance else None
        if 'status' in data and data['status'] == PosReturnGRNOrder.CANCELLED and instance_id:
            if PosReturnGRNOrder.objects.filter(id=instance_id, status=PosReturnGRNOrder.CANCELLED,
                                                grn_ordered_id__order__ordered_cart__retailer_shop=shop).exists():
                raise serializers.ValidationError("This Order is already cancelled")

            # post_return_item = PosReturnItems.objects.filter(grn_return_id=instance_id)
            # products = post_return_item.values_list('product_id', flat=True)
            # for postret_item in self.initial_data['grn_product_return']:
            #     if postret_item['product_id'] not in products:
            #         raise serializers.ValidationError("Invalid product for the selected order.")
            #     if postret_item['return_qty'] not in products:
            #         raise serializers.ValidationError("Invalid return_qty for the selected order.")
            # raise serializers.ValidationError("This Order Return was cancelled")

        return data

    def get_grn_product_return(self, obj):
        order_return_status = self.context.get('status')
        shop = self.context.get('shop')
        status = True
        if order_return_status == 'CANCELLED':
            status = False
        po_products_data = PosReturnItemsSerializer(
            PosReturnItems.objects.filter(
                grn_return_id=obj.id, grn_return_id__status=order_return_status, is_active=status,
                grn_return_id__grn_ordered_id__order__ordered_cart__retailer_shop=shop), many=True).data
        return po_products_data

    def get_grn_id(self, obj):
        return obj.grn_ordered_id.grn_id

    @transaction.atomic
    def create(self, validated_data):
        """ return grn product """
        grn_products_return = validated_data.pop('grn_product_return', None)
        try:
            grn_return_id = PosReturnGRNOrder.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        if grn_return_id.status == PosReturnGRNOrder.RETURNED and grn_products_return:
            self.create_return_items(grn_return_id, grn_products_return)
        return PosReturnGRNOrder.objects.get(id=grn_return_id.id)

    @transaction.atomic
    def update(self, instance, validated_data):
        """ update returned grn product."""
        grn_products_return = validated_data.pop('grn_product_return', None)
        try:
            # call super to save modified instance along with the validated data
            grn_return_id = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        if grn_return_id.status == PosReturnGRNOrder.RETURNED and grn_products_return:
            self.update_return_items(grn_return_id, grn_products_return)
        else:
            self.update_cancel_return(grn_return_id, instance)
        return grn_return_id

    def create_return_items(self, grn_return_id, grn_products_return):
        for grn_product_return in grn_products_return:
            pos_return_items_obj, created = PosReturnItems.objects.get_or_create(
                grn_return_id=grn_return_id, product_id=grn_product_return['product_id'], defaults={})
            pos_return_items_obj.return_qty = pos_return_items_obj.return_qty + grn_product_return['return_qty']
            pos_return_items_obj.pack_size = grn_product_return['pack_size']
            pos_return_items_obj.save()
            PosInventoryCls.grn_inventory(grn_product_return['product_id'], PosInventoryState.AVAILABLE,
                                          PosInventoryState.AVAILABLE, -(grn_product_return['return_qty']),
                                          grn_return_id.last_modified_by, grn_return_id.grn_ordered_id.grn_id,
                                          PosInventoryChange.RETURN, grn_product_return['pack_size'])

        mail_to_vendor_on_order_return_creation.delay(grn_return_id.id)

    def update_return_items(self, grn_return_id, grn_products_return):
        self.manage_nonexisting_return_products(grn_return_id, grn_products_return)
        for grn_product_return in grn_products_return:
            pos_return_items_obj, created = PosReturnItems.objects.get_or_create(
                grn_return_id=grn_return_id, product_id=grn_product_return['product_id'], defaults={})
            pos_return_items_obj.pack_size = grn_product_return['pack_size']

            current_return_qty = 0
            existing_return_qty = 0

            if pos_return_items_obj.is_active:
                existing_return_qty = pos_return_items_obj.return_qty
                current_return_qty = grn_product_return['return_qty']
                pos_return_items_obj.return_qty = current_return_qty
                pos_return_items_obj.save()
            else:
                pos_return_items_obj.is_active = True
                current_return_qty = grn_product_return['return_qty']
                pos_return_items_obj.return_qty = current_return_qty
                pos_return_items_obj.save()

            if created:
                PosInventoryCls.grn_inventory(grn_product_return['product_id'], PosInventoryState.AVAILABLE,
                                              PosInventoryState.AVAILABLE, -current_return_qty,
                                              grn_return_id.last_modified_by, grn_return_id.grn_ordered_id.grn_id,
                                              PosInventoryChange.RETURN, grn_product_return['pack_size'])

            elif current_return_qty == existing_return_qty:
                pass

            elif existing_return_qty > current_return_qty:
                PosInventoryCls.grn_inventory(grn_product_return['product_id'], PosInventoryState.AVAILABLE,
                                              PosInventoryState.AVAILABLE, (existing_return_qty-current_return_qty),
                                              grn_return_id.last_modified_by, grn_return_id.grn_ordered_id.grn_id,
                                              PosInventoryChange.RETURN, grn_product_return['pack_size'])
            else:
                PosInventoryCls.grn_inventory(grn_product_return['product_id'], PosInventoryState.AVAILABLE,
                                              PosInventoryState.AVAILABLE, -(current_return_qty-existing_return_qty),
                                              grn_return_id.last_modified_by, grn_return_id.grn_ordered_id.grn_id,
                                              PosInventoryChange.RETURN, grn_product_return['pack_size'])
        if grn_return_id.debit_note is not None:
            grn_return_id.debit_note = None
            grn_return_id.save()

        mail_to_vendor_on_order_return_creation.delay(grn_return_id.id)

    def update_cancel_return(self, grn_return_id, instance_id,):

        post_return_item = PosReturnItems.objects.filter(grn_return_id=instance_id)
        products = post_return_item.values('product_id', 'return_qty', 'pack_size')
        for grn_product_return in products:
            PosInventoryCls.grn_inventory(grn_product_return['product_id'], PosInventoryState.AVAILABLE,
                                          PosInventoryState.AVAILABLE, grn_product_return['return_qty'],
                                          grn_return_id.last_modified_by,
                                          grn_return_id.grn_ordered_id.grn_id, PosInventoryChange.RETURN,
                                          grn_product_return['pack_size'])
            PosReturnItems.objects.filter(grn_return_id=grn_return_id,
                                          product=grn_product_return['product_id']).update(is_active=False)

        if grn_return_id.debit_note is not None:
            grn_return_id.debit_note = None
            grn_return_id.debit_note_number = None
            grn_return_id.save()

    def manage_nonexisting_return_products(self, grn_return_id, grn_products_return):
        post_return_item = PosReturnItems.objects.filter(grn_return_id=grn_return_id, is_active=True)
        post_return_item_dict = post_return_item.values('product_id', 'return_qty')
        products = [sub['product_id'] for sub in post_return_item_dict]
        products_dict = {sub['product_id']: sub['return_qty'] for sub in post_return_item_dict}
        grn_products = [sub['product_id'] for sub in grn_products_return]
        for product in [item for item in products if item not in grn_products]:
            po_product = PosCartProductMapping.objects.filter(cart=grn_return_id.grn_ordered_id.order.ordered_cart,
                                                              product_id=product).select_related('product').last()
            PosInventoryCls.grn_inventory(product, PosInventoryState.AVAILABLE,
                                          PosInventoryState.AVAILABLE, products_dict[product],
                                          grn_return_id.last_modified_by,
                                          grn_return_id.grn_ordered_id.grn_id, PosInventoryChange.RETURN,
                                          po_product.pack_size)
            # PosReturnItems.objects.filter(grn_return_id=grn_return_id, product=product).delete()
            PosReturnItems.objects.filter(grn_return_id=grn_return_id, product=product).update(is_active=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%b %d %Y %I:%M%p")
        if representation['modified_at']:
            representation['modified_at'] = instance.modified_at.strftime("%b %d %Y %I:%M%p")
        return representation


class PosEcomOrderProductDetailSerializer(serializers.ModelSerializer):
    """
        Get single ordered product detail
    """
    retailer_product = RetailerProductsSearchSerializer()
    product_subtotal = serializers.SerializerMethodField()
    product_invoice_subtotal = serializers.SerializerMethodField()
    picked_qty = serializers.SerializerMethodField()
    rt_return_ordered_product = serializers.SerializerMethodField()

    def get_rt_return_ordered_product(self, obj):
        ordered_product = OrderedProductMapping.objects.filter(ordered_product__order__ordered_cart=obj.cart,
                                                               product_type=obj.product_type,
                                                               retailer_product=obj.retailer_product).last()
        if ordered_product:
            return ReturnItemsSerializer(ordered_product.rt_return_ordered_product, many=True).data
        else:
            return None

    def get_picked_qty(self, obj):
        """
            qty purchased
        """
        ordered_product = OrderedProductMapping.objects.filter(ordered_product__order__ordered_cart=obj.cart,
                                                               product_type=obj.product_type,
                                                               retailer_product=obj.retailer_product).last()
        return ordered_product.shipped_qty if ordered_product else None

    def get_product_subtotal(self, obj):
        """
            order subtotal
        """
        return obj.selling_price * obj.qty

    def get_product_invoice_subtotal(self, obj):
        """
            Received amount for product
        """
        picked_qty = self.get_picked_qty(obj)
        return obj.selling_price * picked_qty if picked_qty else None

    class Meta:
        model = CartProductMapping
        fields = ('retailer_product', 'selling_price', 'qty', 'picked_qty', 'product_subtotal', 'product_invoice_subtotal',
                  'rt_return_ordered_product')


class PosEcomOrderDetailSerializer(serializers.ModelSerializer):
    """
        Pos-Ecom Order detail
    """
    order_summary = serializers.SerializerMethodField()
    return_summary = serializers.SerializerMethodField()
    invoice_summary = serializers.SerializerMethodField()
    invoice_amount = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    creation_date = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    order_update = serializers.SerializerMethodField()
    delivery_person = serializers.SerializerMethodField()
    order_status_display = serializers.CharField(source='get_order_status_display')
    payment = serializers.SerializerMethodField('payment_data')

    @staticmethod
    def get_order_update(obj):
        ret = dict()
        if obj.order_status == Order.PICKUP_CREATED:
            return {Order.OUT_FOR_DELIVERY: 'Mark Out For Delivery'}
        elif obj.order_status == Order.OUT_FOR_DELIVERY:
            return {Order.DELIVERED: 'Mark Delivered'}
        return ret

    @staticmethod
    def get_invoice_amount_total(obj):
        ordered_product = OrderedProduct.objects.filter(order=obj).last()
        return round(ordered_product.invoice_amount_total, 2) if ordered_product else None

    @staticmethod
    def get_invoice_amount_final(obj):
        ordered_product = OrderedProduct.objects.filter(order=obj).last()
        return round(ordered_product.invoice_amount_final, 2) if ordered_product else None

    @staticmethod
    def get_invoice_amount(obj):
        ordered_product = OrderedProduct.objects.filter(order=obj).last()
        return round(ordered_product.invoice_amount_final, 2) if ordered_product else None

    @staticmethod
    def get_invoice_subtotal(obj):
        ordered_product = OrderedProduct.objects.filter(order=obj).last()
        return ordered_product.invoice_subtotal if ordered_product else None

    @staticmethod
    def get_creation_date(obj):
        return obj.created_at.strftime("%b %d, %Y %-I:%M %p")

    def get_order_summary(self, obj):
        order_summary = dict()
        discount = self.get_discount(obj)
        redeem_points_value = self.get_redeem_points_value(obj)
        order_value = round(obj.order_amount + discount + redeem_points_value, 2)
        order_summary['order_value'], order_summary['discount'], order_summary['redeem_points_value'], order_summary[
            'amount_paid'] = order_value, discount, redeem_points_value, obj.order_amount
        payment_obj = obj.rt_payment_retailer_order.all().last()
        order_summary['payment_type'] = payment_obj.payment_type.type
        order_summary['transaction_id'] = payment_obj.transaction_id
        return order_summary

    def get_invoice_summary(self, obj):
        invoice_summary = dict()
        invoice_summary['invoice_value'] = self.get_invoice_subtotal(obj)
        invoice_summary['invoice_amount'], invoice_summary['invoice_discount'] = None, None
        if invoice_summary['invoice_value']:
            invoice_summary['redeem_points_value'] = self.get_redeem_points_value(obj)
            invoice_summary['invoice_discount'] = round(invoice_summary['invoice_value'] - self.get_invoice_amount_total(obj), 2)
            invoice_summary['invoice_amount'] = self.get_invoice_amount_final(obj)
        return invoice_summary

    @staticmethod
    def get_return_summary(obj):
        returns = OrderReturn.objects.filter(order=obj, status='completed')
        return_value, discount_adjusted, points_adjusted, refund_amount = 0, 0, 0, 0
        for ret in returns:
            return_value += ret.return_value
            discount_adjusted += ret.discount_adjusted
            points_adjusted += ret.refund_points
            refund_amount += max(0, ret.refund_amount)
        points_value = 0
        if obj.ordered_cart.redeem_factor:
            points_value = round(points_adjusted / obj.ordered_cart.redeem_factor, 2)
        return_summary = dict()
        return_summary['return_value'], return_summary['discount_adjusted'], return_summary[
            'points_adjusted'], return_summary[
            'amount_returned'] = return_value, discount_adjusted, points_value, refund_amount
        return return_summary

    def get_items(self, obj):
        """
            Get cart/ordered products details
        """
        qs = obj.ordered_cart.rt_cart_list.filter(product_type=1)
        products = PosEcomOrderProductDetailSerializer(qs, many=True).data
        # cart offers - map free product to purchased
        product_offer_map, cart_free_product = {}, {}
        for offer in obj.ordered_cart.offers:
            if offer['coupon_type'] == 'catalog' and offer['type'] == 'combo':
                product_offer_map[offer['item_id']] = offer
            if offer['coupon_type'] == 'cart' and offer['type'] == 'free_product':
                cart_free_product = {'cart_free_product': 1, 'id': offer['free_item_id'], 'mrp': offer['free_item_mrp'],
                                     'name': offer['free_item_name'], 'qty': offer['free_item_qty'],
                                     'display_text': 'FREE on orders above ₹' + str(offer['cart_minimum_value']).rstrip(
                                         '0').rstrip('.')}

        completed_returns = OrderReturn.objects.filter(order=obj, status='completed')
        return_item_map = {}
        for return_obj in completed_returns:
            return_item_detail = return_obj.free_qty_map
            if return_item_detail:
                for combo in return_item_detail:
                    if combo['item_id'] in return_item_map:
                        return_item_map[combo['item_id']] += combo['free_item_return_qty']
                    else:
                        return_item_map[combo['item_id']] = combo['free_item_return_qty']

        free_picked_map = {}
        free_picked_products = OrderedProductMapping.objects.filter(ordered_product__order=obj, product_type=0)
        for pp in free_picked_products:
            free_picked_map[pp.retailer_product.id] = pp.shipped_qty

        for product in products:
            product['returned_qty'] = 0
            rt_return_ordered_product = product.pop('rt_return_ordered_product', None)
            if rt_return_ordered_product:
                for return_item in rt_return_ordered_product:
                    if return_item['status'] != 'created':
                        product['returned_qty'] = product['returned_qty'] + return_item['return_qty'
                        ] if 'returned_qty' in product else return_item['return_qty']
            product['returned_subtotal'] = round(float(product['selling_price']) * product['returned_qty'], 2)
            # map purchased product with free product
            if product['retailer_product']['id'] in product_offer_map:
                free_prod_info = self.get_free_product_text(product_offer_map, return_item_map, product, free_picked_map)
                if free_prod_info:
                    product.update(free_prod_info)

        if cart_free_product:
            cart_free_product['picked_qty'] = 0
            cart_free_product['returned_qty'] = return_item_map[
                'free_product'] if 'free_product' in return_item_map else 0
            if int(cart_free_product['id']) in free_picked_map:
                cart_free_product['picked_qty'] = free_picked_map[int(cart_free_product['id'])]
            products.append(cart_free_product)
        return products

    @staticmethod
    def get_free_product_text(product_offer_map, return_item_map, product, free_picked_map):
        offer = product_offer_map[product['retailer_product']['id']]
        free_already_return_qty = return_item_map[offer['item_id']] if offer['item_id'] in return_item_map else 0
        display_text = ['Free - ' + str(offer['free_item_qty_added']) + ' items of ' + str(
            offer['free_item_name']) + ' on purchase of ' + str(product['qty']) + ' items | Buy ' + str(offer[
                                                                                                            'item_qty']) + ' Get ' + str(
            offer['free_item_qty'])]

        if int(offer['free_item_id']) in free_picked_map:
            display_text += ['Picked ' + str(free_picked_map[int(offer['free_item_id'])]) + ' items']
        if free_already_return_qty:
            display_text += ['Free return - ' + str(free_already_return_qty) + ' items of ' + str(
                offer['free_item_name']) + ' on return of ' + str(product['returned_qty']) + ' items']
        return {'free_product': 1, 'display_text': display_text}

    @staticmethod
    def get_redeem_points_value(obj):
        redeem_points_value = 0
        if obj.ordered_cart.redeem_factor:
            redeem_points_value = round(obj.ordered_cart.redeem_points / obj.ordered_cart.redeem_factor, 2)
        return redeem_points_value

    def get_discount(self, obj):
        discount = 0
        offers = self.get_cart_offers(obj)
        for offer in offers:
            discount += float(offer['discount_value'])
        return round(discount, 2)

    @staticmethod
    def get_cart_offers(obj):
        offers = obj.ordered_cart.offers
        cart_offers = []
        for offer in offers:
            if offer['coupon_type'] == 'cart' and offer['type'] == 'discount':
                cart_offers.append(offer)
        return cart_offers

    @staticmethod
    def get_address(obj):
        if obj.ordered_cart.cart_type == 'ECOM' and hasattr(obj, 'ecom_address_order'):
            return EcomOrderAddressSerializer(obj.ecom_address_order).data
        return None

    @staticmethod
    def get_delivery_person(obj):
        return obj.delivery_person.first_name + ' - ' + obj.delivery_person.phone_number if obj.delivery_person else None

    def payment_data(self, obj):
        if not obj.rt_payment_retailer_order.exists():
            return None
        return PaymentSerializer(obj.rt_payment_retailer_order.all(), many=True).data

    class Meta:
        model = Order
        fields = ('id', 'order_no', 'creation_date', 'order_status', 'items', 'order_summary', 'return_summary',
                  'invoice_summary',
                  'invoice_amount', 'address', 'order_update', 'ecom_estimated_delivery_time', 'delivery_person',
                  'order_status_display', 'payment')


class PRNReturnItemsSerializer(serializers.ModelSerializer):
    returned_product = serializers.SerializerMethodField()
    return_qty = serializers.SerializerMethodField()
    total_return_qty = serializers.SerializerMethodField()
    return_price = serializers.SerializerMethodField()

    class Meta:
        model = PosReturnItems
        fields = ('pack_size', 'return_qty', 'return_price', 'total_return_qty', 'returned_product')

    @staticmethod
    def get_return_qty(obj):
        return obj.qty_given

    @staticmethod
    def get_total_return_qty(obj):
        return obj.return_qty

    @staticmethod
    def get_return_price(obj):
        return obj.selling_price

    @staticmethod
    def get_returned_product(obj):
        i_state_obj = PosInventoryState.objects.get(inventory_state=PosInventoryState.AVAILABLE)
        product_in_inventory = PosInventory.objects.filter(product=obj.product.id,
                                                           product__shop=obj.product.shop,
                                                           inventory_state=i_state_obj)
        return PosInventoryProductMappingSerializer(product_in_inventory, many=True).data


class VendorInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ('id', 'vendor_name', 'phone_number', 'email')


class PRNOrderSerializer(serializers.ModelSerializer):
    product_return = serializers.SerializerMethodField()
    last_modified_by = PosShopUserSerializer(read_only=True)
    vendor_id = VendorInfoSerializer(read_only=True)

    class Meta:
        model = PosReturnGRNOrder
        fields = ('id', 'pr_number', 'status', 'vendor_id', 'product_return', 'last_modified_by',
                  'debit_note_number', 'debit_note', 'created_at', 'modified_at')

    def validate(self, data):
        shop = self.context.get('shop')

        if not 'vendor_id' in self.initial_data or not self.initial_data['vendor_id']:
            raise serializers.ValidationError(_('vendor_id is required'))

        vendor_obj = get_validate_vendor(int(self.initial_data['vendor_id']), shop)
        if 'error' in vendor_obj:
            raise serializers.ValidationError(vendor_obj['error'])
        data['vendor_id'] = vendor_obj['vendor_id']

        if 'status' not in self.initial_data or self.initial_data['status'] != PosReturnGRNOrder.CANCELLED:
            if 'product_return' not in self.initial_data or type(self.initial_data['product_return']) != list:
                raise serializers.ValidationError("Provide return item details")

            # Check return item details
            for rtn_product in self.initial_data['product_return']:
                if 'product_id' not in rtn_product or 'return_qty' not in rtn_product or 'return_price' not in \
                        rtn_product or not rtn_product['product_id'] or not rtn_product['return_qty'] or \
                        not rtn_product['return_price']:
                    raise serializers.ValidationError("'product_id', 'return_qty' and 'return_price' are mandatory for "
                                                      "every return product object.")

                if rtn_product['return_qty'] <= 0:
                    raise serializers.ValidationError("return_qty must be greater than 0.")

                if not RetailerProduct.objects.filter(id=int(rtn_product['product_id']), is_deleted=False, shop=shop):
                    raise serializers.ValidationError(f"please select valid product {rtn_product['product_id']}")

                product = RetailerProduct.objects.filter(id=int(rtn_product['product_id']), is_deleted=False, shop=shop).last()
                if product.mrp < rtn_product['return_price']:
                    raise serializers.ValidationError(f"product return price {rtn_product['return_price']} can not be "
                                                      f"more then product mrp {product.mrp}")

                if product.product_pack_type == 'loose':
                    rtn_product['return_qty'], qty_unit = get_default_qty(
                        MeasurementUnit.objects.get(category=product.measurement_category,
                                                    default=True).unit, product, rtn_product['return_qty'])

                    rtn_product['pack_size'] = 1
                else:
                    rtn_product['return_qty'] = int(rtn_product['return_qty'])
                    rtn_product['pack_size'] = product.purchase_pack_size

                i_state_obj = PosInventoryState.objects.get(inventory_state=PosInventoryState.AVAILABLE)
                product_in_inventory = PosInventory.objects.filter(product=int(rtn_product['product_id']),
                                                                   product__shop=shop,
                                                                   inventory_state=i_state_obj)
                if not product_in_inventory:
                    raise serializers.ValidationError(f"product not available in inventory")

                if product_in_inventory.last().quantity < rtn_product['return_qty'] * rtn_product['pack_size']:
                    raise serializers.ValidationError(f"your available quantity is {product_in_inventory.last().quantity} "
                                                      f"you can't return {(rtn_product['return_qty'] * rtn_product['pack_size'])}")

            data['product_return'] = self.initial_data['product_return']

            instance_id = self.instance.id if self.instance else None
            if 'status' in data and data['status'] == PosReturnGRNOrder.CANCELLED and instance_id:
                if PosReturnGRNOrder.objects.filter(id=instance_id, status=PosReturnGRNOrder.CANCELLED,
                                                    grn_ordered_id__order__ordered_cart__retailer_shop=shop).exists():
                    raise serializers.ValidationError("This Order is already cancelled")

        return data

    def get_product_return(self, obj):
        order_return_status = self.context.get('status')
        shop = self.context.get('shop')
        status = True
        if order_return_status == 'CANCELLED':
            status = False
        po_products_data = PRNReturnItemsSerializer(
            PosReturnItems.objects.filter(
                grn_return_id=obj.id, grn_return_id__status=order_return_status, is_active=status,
                grn_return_id__vendor_id__retailer_shop=shop), many=True).data
        return po_products_data

    @transaction.atomic
    def create(self, validated_data):
        """ return product """
        products_return = validated_data.pop('product_return', None)
        try:
            grn_return_id = PosReturnGRNOrder.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        if grn_return_id.status == PosReturnGRNOrder.RETURNED and products_return:
            self.create_return_items(grn_return_id, products_return)
        return PosReturnGRNOrder.objects.get(id=grn_return_id.id)

    def create_return_items(self, grn_return_id, products_return):
        for product_return in products_return:
            pos_return_items_obj, created = PosReturnItems.objects.get_or_create(
                grn_return_id=grn_return_id, product_id=product_return['product_id'],
                defaults={})
            pos_return_items_obj.selling_price = round(float(product_return['return_price']), 2)
            pos_return_items_obj.pack_size = product_return['pack_size']
            pos_return_items_obj.return_qty = pos_return_items_obj.return_qty + product_return['return_qty']
            pos_return_items_obj.save()

            PosInventoryCls.grn_inventory(product_return['product_id'], PosInventoryState.AVAILABLE,
                                          PosInventoryState.AVAILABLE, -(product_return['return_qty']),
                                          grn_return_id.last_modified_by, grn_return_id.id, PosInventoryChange.RETURN,
                                          product_return['pack_size'])

        mail_to_vendor_on_order_return_creation.delay(grn_return_id.id)

    @transaction.atomic
    def update(self, instance, validated_data):
        """ update returned product."""
        products_return = validated_data.pop('product_return', None)
        try:
            # call super to save modified instance along with the validated data
            grn_return_id = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        if grn_return_id.status == PosReturnGRNOrder.RETURNED and products_return:
            self.update_return_items(grn_return_id, products_return)
        else:
            self.update_cancel_return(grn_return_id, instance)
        return grn_return_id

    def update_return_items(self, grn_return_id, grn_products_return):
        self.manage_nonexisting_return_products(grn_return_id, grn_products_return)
        for grn_product_return in grn_products_return:
            pos_return_items_obj, created = PosReturnItems.objects.get_or_create(
                grn_return_id=grn_return_id, product_id=grn_product_return['product_id'],
                defaults={})

            existing_return_qty = 0
            if pos_return_items_obj.is_active:
                existing_return_qty = pos_return_items_obj.return_qty

            current_return_qty = grn_product_return['return_qty']
            pos_return_items_obj.return_qty = current_return_qty
            pos_return_items_obj.is_active = True
            pos_return_items_obj.pack_size = grn_product_return['pack_size']
            pos_return_items_obj.selling_price = round(float(grn_product_return['return_price']), 2)
            pos_return_items_obj.save()

            if created:
                PosInventoryCls.grn_inventory(grn_product_return['product_id'], PosInventoryState.AVAILABLE,
                                              PosInventoryState.AVAILABLE, -current_return_qty,
                                              grn_return_id.last_modified_by, grn_return_id.id,
                                              PosInventoryChange.RETURN, grn_product_return['pack_size'])

            elif current_return_qty == existing_return_qty:
                pass

            elif existing_return_qty > current_return_qty:
                PosInventoryCls.grn_inventory(grn_product_return['product_id'], PosInventoryState.AVAILABLE,
                                              PosInventoryState.AVAILABLE, (existing_return_qty-current_return_qty),
                                              grn_return_id.last_modified_by, grn_return_id.id,
                                              PosInventoryChange.RETURN, grn_product_return['pack_size'])
            else:
                PosInventoryCls.grn_inventory(grn_product_return['product_id'], PosInventoryState.AVAILABLE,
                                              PosInventoryState.AVAILABLE, -(current_return_qty-existing_return_qty),
                                              grn_return_id.last_modified_by, grn_return_id.id,
                                              PosInventoryChange.RETURN, grn_product_return['pack_size'])
        if grn_return_id.debit_note is not None:
            grn_return_id.debit_note = None
            grn_return_id.save()

        mail_to_vendor_on_order_return_creation.delay(grn_return_id.id)

    def update_cancel_return(self, grn_return_id, instance_id,):

        post_return_item = PosReturnItems.objects.filter(grn_return_id=instance_id)
        products = post_return_item.values('product_id', 'return_qty')
        for grn_product_return in products:
            PosInventoryCls.grn_inventory(grn_product_return['product_id'], PosInventoryState.AVAILABLE,
                                          PosInventoryState.AVAILABLE, grn_product_return['return_qty'],
                                          grn_return_id.last_modified_by,
                                          grn_return_id.id, PosInventoryChange.RETURN,
                                          grn_product_return['pack_size'])
            PosReturnItems.objects.filter(grn_return_id=grn_return_id,
                                          product=grn_product_return['product_id']).update(is_active=False)

        if grn_return_id.debit_note is not None:
            grn_return_id.debit_note = None
            grn_return_id.debit_note_number = None
            grn_return_id.save()

    def manage_nonexisting_return_products(self, grn_return_id, grn_products_return):
        post_return_item = PosReturnItems.objects.filter(grn_return_id=grn_return_id, is_active=True)
        post_return_item_dict = post_return_item.values('product_id', 'return_qty', 'pack_size')
        products = [sub['product_id'] for sub in post_return_item_dict]
        products_dict = {sub['product_id']: sub['return_qty'] for sub in post_return_item_dict}
        product_pack_size_dict = {sub['product_id']: sub['pack_size'] for sub in post_return_item_dict}
        grn_products = [sub['product_id'] for sub in grn_products_return]
        for product in [item for item in products if item not in grn_products]:
            PosInventoryCls.grn_inventory(product, PosInventoryState.AVAILABLE,
                                          PosInventoryState.AVAILABLE, products_dict[product],
                                          grn_return_id.last_modified_by,
                                          grn_return_id.id, PosInventoryChange.RETURN,
                                          product_pack_size_dict[product])
            # PosReturnItems.objects.filter(grn_return_id=grn_return_id, product=product).delete()
            PosReturnItems.objects.filter(grn_return_id=grn_return_id, product=product).update(is_active=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%b %d %Y %I:%M%p")
        if representation['modified_at']:
            representation['modified_at'] = instance.modified_at.strftime("%b %d %Y %I:%M%p")
        return representation
