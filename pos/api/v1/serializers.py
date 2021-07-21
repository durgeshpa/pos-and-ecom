from decimal import Decimal
import datetime
import calendar
import re

from django.utils.translation import ugettext_lazy as _
from django.db.models import Q, Sum, F
from django.db import transaction
from rest_framework import serializers

from addresses.models import Pincode
from pos.models import RetailerProduct, RetailerProductImage, Vendor, PosCart, PosCartProductMapping, PosGRNOrder, \
    PosGRNOrderProductMapping, Payment, PaymentType
from pos.tasks import mail_to_vendor_on_po_creation
from retailer_to_sp.models import CartProductMapping, Cart, Order, OrderReturn, ReturnItems, \
    OrderedProductMapping
from accounts.api.v1.serializers import PosUserSerializer, PosShopUserSerializer
from pos.common_functions import RewardCls, PosInventoryCls
from products.models import Product
from retailer_backend.validators import ProductNameValidator
from coupon.models import Coupon, CouponRuleSet, RuleSetProductMapping, DiscountValue
from retailer_backend.utils import SmallOffsetPagination
from shops.models import Shop
from wms.models import PosInventory, PosInventoryState, PosInventoryChange
from marketing.models import ReferralCode
from accounts.models import User


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
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False, default='',
                                        max_length=255)
    product_ean_code = serializers.CharField(required=True, max_length=100)
    stock_qty = serializers.IntegerField(min_value=0, default=0)
    linked_product_id = serializers.IntegerField(required=False, default=None, min_value=1, allow_null=True)
    images = serializers.ListField(required=False, default=None, child=serializers.ImageField(), max_length=3)

    @staticmethod
    def validate_linked_product_id(value):
        if value and not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Linked GramFactory Product not found! Please try again")
        return value

    def validate(self, attrs):
        sp, mrp, shop_id, linked_pid, ean = attrs['selling_price'], attrs['mrp'], attrs['shop_id'], attrs[
            'linked_product_id'], attrs['product_ean_code']

        if sp > mrp:
            raise serializers.ValidationError("Selling Price should be equal to OR less than MRP")

        if not attrs['product_ean_code'].isdigit():
            raise serializers.ValidationError("Product Ean Code should be a number")

        if RetailerProduct.objects.filter(shop=shop_id, product_ean_code=ean, mrp=mrp).exists():
            raise serializers.ValidationError("Product already exists in catalog.")

        return attrs


class RetailerProductResponseSerializer(serializers.ModelSerializer):
    linked_product = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    stock_qty = serializers.SerializerMethodField()

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
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False,
                                        default=None, max_length=255)
    stock_qty = serializers.IntegerField(required=False, default=0)
    status = serializers.ChoiceField(choices=['active', 'deactivated'], required=False, default=None)
    images = serializers.ListField(required=False, allow_null=True, child=serializers.ImageField())
    image_ids = serializers.ListField(required=False, default=None, child=serializers.IntegerField())

    def validate(self, attrs):
        shop_id, pid = attrs['shop_id'], attrs['product_id']

        product = RetailerProduct.objects.filter(id=pid, shop_id=shop_id).last()
        if not product:
            raise serializers.ValidationError("Product not found!")

        sp = attrs['selling_price'] if attrs['selling_price'] else product.selling_price
        mrp = attrs['mrp'] if attrs['mrp'] else product.mrp
        ean = attrs['product_ean_code'] if attrs['product_ean_code'] else product.product_ean_code

        image_count = 0
        if 'images' in attrs and attrs['images']:
            image_count = len(attrs['images'])
        if 'image_ids' in attrs and attrs['image_ids']:
            image_count += len(attrs['image_ids'])
        if image_count > 3:
            raise serializers.ValidationError("images : Ensure this field has no more than 3 elements.")

        if (attrs['selling_price'] or attrs['mrp']) and sp > mrp:
            raise serializers.ValidationError("Selling Price should be equal to OR less than MRP")

        if 'product_ean_code' in attrs and attrs['product_ean_code']:
            if not attrs['product_ean_code'].isdigit():
                raise serializers.ValidationError("Product Ean Code should be a number")

        if RetailerProduct.objects.filter(shop=shop_id, product_ean_code=ean, mrp=mrp).exclude(id=pid).exists():
            raise serializers.ValidationError("Product already exists in catalog.")

        return attrs


class RetailerProductsSearchSerializer(serializers.ModelSerializer):
    """
        RetailerProduct data for BASIC cart
    """

    class Meta:
        model = RetailerProduct
        fields = ('id', 'name', 'selling_price', 'mrp')


class BasicCartProductMappingSerializer(serializers.ModelSerializer):
    """
        Basic Cart Product Mapping Data
    """
    retailer_product = RetailerProductsSearchSerializer()
    product_price = serializers.SerializerMethodField('product_price_dt')
    product_sub_total = serializers.SerializerMethodField('product_sub_total_dt')
    display_text = serializers.SerializerMethodField('display_text_dt')

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

    class Meta:
        model = CartProductMapping
        fields = ('id', 'retailer_product', 'qty', 'product_price', 'product_sub_total', 'display_text')


class BasicCartSerializer(serializers.ModelSerializer):
    """
        Basic Cart Data
    """
    rt_cart_list = serializers.SerializerMethodField('rt_cart_list_dt')
    items_count = serializers.SerializerMethodField('items_count_dt')
    total_quantity = serializers.SerializerMethodField('total_quantity_dt')
    total_amount = serializers.SerializerMethodField('total_amount_dt')

    class Meta:
        model = Cart
        fields = ('id', 'cart_no', 'cart_status', 'rt_cart_list', 'items_count', 'total_quantity', 'total_amount',
                  'created_at', 'modified_at')

    def rt_cart_list_dt(self, obj):
        """
         Search and pagination on cart
        """
        qs = obj.rt_cart_list.filter(product_type=1)
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
            qty += int(cart_pro.qty)
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
            total_amount += Decimal(cart_pro.selling_price) * Decimal(cart_pro.qty)
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
        fields = ('payment_type', 'transaction_id',)


class BasicOrderListSerializer(serializers.ModelSerializer):
    """
        Order List For Basic Cart
    """
    buyer = PosUserSerializer()
    order_status = serializers.CharField(source='get_order_status_display')
    order_no = serializers.CharField()
    order_amount = serializers.ReadOnlyField()
    created_at = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField('payment_data')

    def get_created_at(self, obj):
        return obj.created_at.strftime("%b %d, %Y %-I:%M %p")

    def payment_data(self, obj):
        if not obj.rt_payment_retailer_order.filter(payment_type__enabled=True).exists():
            return None
        return PaymentSerializer(obj.rt_payment_retailer_order.filter(payment_type__enabled=True).last()).data

    class Meta:
        model = Order
        fields = ('id', 'order_status', 'order_amount', 'order_no', 'buyer', 'created_at', 'payment')


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

    def get_status(self, obj):
        return obj.return_id.status

    class Meta:
        model = ReturnItems
        fields = ('return_qty', 'status')


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

    def get_qty(self, obj):
        """
            qty purchased
        """
        return obj.shipped_qty

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
        fields = ('retailer_product', 'selling_price', 'qty', 'product_subtotal', 'rt_return_ordered_product')


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
        block[cb][1] = "Paid Amount: " + str(self.get_order_total(obj)).rstrip('0').rstrip('.')

        discount = self.get_discount_amount(obj)
        redeem_points_value = self.get_redeem_points_value(obj)
        if discount and redeem_points_value:
            block[cb][1] += '-(' + str(discount).rstrip('0').rstrip('.') + '+' + str(redeem_points_value).rstrip(
                '0').rstrip('.') + ') = Rs.' + str(obj.order_amount).rstrip('0').rstrip('.')
            block[cb][2] = '(Rs.' + str(discount).rstrip('0').rstrip('.') + ' off coupon, Rs.' + str(
                redeem_points_value).rstrip('0').rstrip('.') + ' off reward points)'
        elif discount:
            block[cb][1] += '-' + str(discount).rstrip('0').rstrip('.') + ' = Rs.' + str(obj.order_amount).rstrip(
                '0').rstrip('.')
            block[cb][2] = '(Rs.' + str(discount).rstrip('0').rstrip('.') + ' off coupon)'
        elif redeem_points_value:
            block[cb][1] += '-' + str(redeem_points_value).rstrip('0').rstrip('.') + ' = Rs.' + str(
                obj.order_amount).rstrip('0').rstrip('.')

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

    def get_order_total(self, obj):
        return round(obj.order_amount + self.get_discount_amount(obj) + self.get_redeem_points_value(obj), 2)

    def get_discount_amount(self, obj):
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

    @staticmethod
    def get_shop_id(obj):
        return obj.id

    class Meta:
        model = Shop
        fields = ('shop_id', 'shop_name')


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

    @staticmethod
    def get_product_id(obj):
        return obj.ordered_product.retailer_product.id

    @staticmethod
    def get_product_name(obj):
        return obj.ordered_product.retailer_product.name

    @staticmethod
    def get_selling_price(obj):
        return obj.ordered_product.selling_price

    class Meta:
        model = ReturnItems
        fields = ('product_id', 'product_name', 'selling_price', 'return_qty', 'return_value')


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
        fields = ('return_value', 'discount_adjusted', 'refund_points_value', 'refund_amount', 'return_items')


class BasicOrderDetailSerializer(serializers.ModelSerializer):
    """
        Pos Order detail
    """
    order_summary = serializers.SerializerMethodField()
    return_summary = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    creation_date = serializers.SerializerMethodField()

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
            product['returned_subtotal'] = round(float(product['selling_price']) * product['returned_qty'], 2)
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

    class Meta:
        model = Order
        fields = ('id', 'order_no', 'creation_date', 'order_status', 'items', 'order_summary', 'return_summary')


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ('id', 'company_name', 'vendor_name', 'contact_person_name', 'phone_number', 'alternate_phone_number',
                  'email', 'address', 'pincode', 'gst_number', 'retailer_shop', 'status')

    def validate(self, attrs):
        city = Pincode.objects.filter(pincode=attrs['pincode']).last()
        if not city:
            raise serializers.ValidationError("Invalid Pincode")
        return attrs


class VendorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ('id', 'vendor_name')


class POProductSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()

    class Meta:
        model = PosCartProductMapping
        fields = ('product_id', 'price', 'qty')


class POSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    vendor_id = serializers.IntegerField()
    products = POProductSerializer(many=True)

    class Meta:
        model = PosCart
        fields = ('id', 'vendor_id', 'products')

    def validate(self, attrs):
        # Validate vendor id
        shop = self.context.get('shop')
        if not Vendor.objects.filter(id=attrs['vendor_id'], retailer_shop=shop).exists():
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
                if not mapping or not mapping.is_grn_done:
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
                                                     price=product['price'])
            mail_to_vendor_on_po_creation(cart)
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
                mapping.save()
                updated_pid += [product['product_id']]
            PosCartProductMapping.objects.filter(cart=cart, is_grn_done=False).exclude(
                product_id__in=updated_pid).delete()
            po_status = cart.status
            if PosCartProductMapping.objects.filter(cart=cart, is_grn_done=True).exists() and updated_pid:
                po_status = PosCart.PARTIAL_DELIVERED
            cart.vendor_id, cart.last_modified_by, cart.status = validated_data['vendor_id'], user, po_status
            cart.save()
            if self.context.get('send_mail', False):
                mail_to_vendor_on_po_creation(cart)


class POProductGetSerializer(serializers.ModelSerializer):
    grned_qty = serializers.SerializerMethodField()

    def get_grned_qty(self, obj):
        already_grn = obj.product.pos_product_grn_order_product.filter(grn_order__order__ordered_cart=obj.cart). \
            aggregate(Sum('received_qty')).get('received_qty__sum')
        return already_grn if already_grn else 0

    class Meta:
        model = PosCartProductMapping
        fields = ('product_id', 'product_name', 'price', 'qty', 'grned_qty')


class POGetSerializer(serializers.ModelSerializer):
    po_products = POProductGetSerializer(many=True)
    raised_by = PosShopUserSerializer()
    last_modified_by = PosShopUserSerializer()

    class Meta:
        model = PosCart
        fields = ('id', 'vendor_id', 'vendor_name', 'po_no', 'status', 'po_products', 'raised_by', 'last_modified_by',
                  'created_at', 'modified_at')


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
            '-created_at')[:3].values_list('price', flat=True)

    class Meta:
        model = RetailerProduct
        fields = ('selling_price', 'stock_qty', 'po_price_history')


class POListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PosCart
        fields = ('id', 'po_no', 'vendor_name', 'status')


class PosGrnProductSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()

    class Meta:
        model = PosGRNOrderProductMapping
        fields = ('product_id', 'received_qty')


class PosGrnOrderCreateSerializer(serializers.ModelSerializer):
    po_id = serializers.IntegerField()
    products = PosGrnProductSerializer(many=True)

    class Meta:
        model = PosGRNOrder
        fields = ('po_id', 'products')

    def validate(self, attrs):
        shop = self.context.get('shop')
        # Validate po id
        po = PosCart.objects.filter(id=attrs['po_id'], retailer_shop=shop).prefetch_related('po_products',
                                                                                            'po_products__product').last()
        if not po:
            raise serializers.ValidationError("Invalid PO Id")
        if po.status == PosCart.CANCELLED:
            raise serializers.ValidationError("This PO was cancelled")
        if po.status == PosCart.DELIVERED:
            raise serializers.ValidationError("PO completely delivered")

        grn_products = {int(i['product']): i['received_qty_sum'] for i in PosGRNOrderProductMapping.objects.filter(
            grn_order__order=po.pos_po_order).values('product').annotate(received_qty_sum=Sum(F('received_qty')))}

        # Validate products
        product_added = False
        for product in attrs['products']:
            product['product_id'] = int(product['product_id'])
            po_product = po.po_products.filter(product_id=product['product_id']).last()
            if not po_product:
                raise serializers.ValidationError("Product Id Invalid {}".format(product['product_id']))
            product_added = True if int(product['received_qty']) > 0 else product_added
            product_obj = po_product.product
            already_grned_qty = grn_products[product['product_id']] if product['product_id'] in grn_products else 0
            if int(product['received_qty']) + already_grned_qty > po_product.qty:
                raise serializers.ValidationError(
                    "{}. (Received quantity) + (Already grned quantity) cannot be greater than PO quantity".format(
                        product_obj.name))
        if not product_added:
            raise serializers.ValidationError("Please provide grn info for atleast one product")
        attrs['po'] = po
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            user, shop, products = self.context.get('user'), self.context.get('shop'), validated_data['products']
            grn_order = PosGRNOrder.objects.create(order=validated_data['po'].pos_po_order, added_by=user,
                                                   last_modified_by=user)
            for product in products:
                if product['received_qty'] > 0:
                    PosGRNOrderProductMapping.objects.create(grn_order=grn_order, product_id=product['product_id'],
                                                             received_qty=product['received_qty'])
                    PosInventoryCls.grn_inventory(product['product_id'], PosInventoryState.NEW,
                                                  PosInventoryState.AVAILABLE, product['received_qty'], user,
                                                  grn_order.grn_id, PosInventoryChange.GRN_ADD)
            po = validated_data['po']
            total_grn_qty = PosGRNOrderProductMapping.objects.filter(grn_order__order=po.pos_po_order).aggregate(
                Sum('received_qty')).get('received_qty__sum')
            total_grn_qty = total_grn_qty if total_grn_qty else 0
            po_status = PosCart.PARTIAL_DELIVERED if total_grn_qty > 0 else PosCart.OPEN
            total_po_qty = PosCartProductMapping.objects.filter(cart=po).aggregate(Sum('qty')).get('qty__sum')
            po.status = PosCart.DELIVERED if total_po_qty == total_grn_qty else po_status
            po.save()
            return grn_order


class PosGrnOrderUpdateSerializer(serializers.ModelSerializer):
    grn_id = serializers.IntegerField()
    products = PosGrnProductSerializer(many=True)

    class Meta:
        model = PosGRNOrder
        fields = ('grn_id', 'products')

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

        grn_products = {int(i['product']): i['received_qty_sum'] for i in PosGRNOrderProductMapping.objects.filter(
            grn_order__order=grn_order.order).exclude(grn_order=grn_order).values('product').annotate(
            received_qty_sum=Sum(F('received_qty')))}

        # Validate products
        product_added = False
        for product in attrs['products']:
            product['product_id'] = int(product['product_id'])
            po_product = grn_order.order.ordered_cart.po_products.filter(product_id=product['product_id']).last()
            if not po_product:
                raise serializers.ValidationError("Product Id Invalid {}".format(product['product_id']))
            product_added = True if int(product['received_qty']) > 0 else product_added
            product_obj = po_product.product
            already_grned_qty = grn_products[product['product_id']] if product['product_id'] in grn_products else 0
            if int(product['received_qty']) + already_grned_qty > po_product.qty:
                raise serializers.ValidationError(
                    "{}. (Received quantity) + (Already grned quantity) cannot be greater than PO quantity".format(
                        product_obj.name))
        if not product_added:
            raise serializers.ValidationError("Please provide grn info for atleast one product")
        return attrs

    def update(self, grn_id, validated_data):
        with transaction.atomic():
            user, shop, products = self.context.get('user'), self.context.get('shop'), validated_data['products']
            grn_order = PosGRNOrder.objects.get(id=grn_id)
            grn_order.last_modified_by = user
            grn_order.save()
            for product in products:
                mapping, _ = PosGRNOrderProductMapping.objects.get_or_create(grn_order=grn_order,
                                                                             product_id=product['product_id'])
                qty_change = product['received_qty'] - mapping.received_qty
                mapping.received_qty = product['received_qty']
                mapping.save()
                if qty_change != 0:
                    PosInventoryCls.grn_inventory(product['product_id'], PosInventoryState.AVAILABLE,
                                                  PosInventoryState.AVAILABLE, qty_change, user,
                                                  grn_order.grn_id, PosInventoryChange.GRN_UPDATE)
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
            return grn_order


class GrnListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PosGRNOrder
        fields = ('id', 'po_no', 'vendor_name', 'po_status')


class GrnOrderProductGetSerializer(serializers.ModelSerializer):
    other_grned_qty = serializers.SerializerMethodField()

    def get_other_grned_qty(self, obj):
        exclude_grn = self.context.get('exclude_grn')
        already_grn = obj.product.pos_product_grn_order_product.filter(grn_order__order__ordered_cart=obj.cart).exclude(
            grn_order=exclude_grn). \
            aggregate(Sum('received_qty')).get('received_qty__sum')
        return already_grn if already_grn else 0

    class Meta:
        model = PosCartProductMapping
        fields = ('product_id', 'product_name', 'price', 'qty', 'other_grned_qty')


class GrnOrderGetSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    added_by = PosShopUserSerializer()
    last_modified_by = PosShopUserSerializer()

    @staticmethod
    def get_products(obj):
        po_products = PosCartProductMapping.objects.filter(cart=obj.order.ordered_cart)
        po_products_data = GrnOrderProductGetSerializer(po_products, context={'exclude_grn': obj}, many=True).data

        grn_products = {int(i['product_id']): i['received_qty'] for i in PosGRNOrderProductMapping.objects.filter(
            grn_order=obj).values('product_id', 'received_qty')}

        for po_pr in po_products_data:
            po_pr['curr_grn_received_qty'] = 0
            if po_pr['product_id'] in grn_products:
                po_pr['curr_grn_received_qty'] = grn_products[po_pr['product_id']]

        return po_products_data

    class Meta:
        model = PosGRNOrder
        fields = ('id', 'po_no', 'po_status', 'vendor_name', 'products', 'added_by', 'last_modified_by',
                  'created_at', 'modified_at')
