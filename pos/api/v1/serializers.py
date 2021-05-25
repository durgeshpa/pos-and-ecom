from decimal import Decimal
import datetime

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from django.db.models import Q, Sum

from pos.models import RetailerProduct, RetailerProductImage
from retailer_to_sp.models import CartProductMapping, Cart, Order, OrderedProduct, OrderReturn, ReturnItems, \
    OrderedProductMapping
from accounts.api.v1.serializers import PosUserSerializer
from pos.common_functions import get_invoice_and_link
from products.models import Product
from retailer_backend.validators import ProductNameValidator
from coupon.models import Coupon, CouponRuleSet, RuleSetProductMapping, DiscountValue
from retailer_backend.utils import SmallOffsetPagination


class RetailerProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailerProductImage
        fields = ('image_name', 'image_alt_text', 'image')


class RetailerProductCreateSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    product_name = serializers.CharField(required=True, validators=[ProductNameValidator], max_length=100)
    mrp = serializers.DecimalField(max_digits=6, decimal_places=2, required=True, min_value=0.01)
    selling_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=True, min_value=0.01)
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False, default='',
                                        max_length=255)
    product_ean_code = serializers.CharField(required=True, max_length=100)
    linked_product_id = serializers.IntegerField(required=False, default=None, min_value=1)
    images = serializers.ListField(required=False, default=None, child=serializers.ImageField(), max_length=3)

    @staticmethod
    def validate_linked_product_id(value):
        if value and not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Linked GramFactory Product not found! Please try again")
        return value

    def validate(self, attrs):
        sp, mrp, name, shop_id, linked_pid, ean = attrs['selling_price'], attrs['mrp'], attrs['product_name'], attrs[
            'shop_id'], attrs['linked_product_id'], attrs['product_ean_code']

        if sp > mrp:
            raise serializers.ValidationError("Selling Price cannot be greater than MRP")

        if RetailerProduct.objects.filter(shop=shop_id, product_ean_code=ean, mrp=mrp).exists():
            raise serializers.ValidationError("Product {} with same mrp & ean code already exists.".format(name))

        if linked_pid and RetailerProduct.objects.filter(shop=shop_id, mrp=mrp, linked_product_id=linked_pid).exists():
            raise serializers.ValidationError(
                "Product {} with same mrp & linked GF product already exists.".format(name))
        return attrs


class RetailerProductResponseSerializer(serializers.ModelSerializer):
    linked_product = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    @staticmethod
    def get_linked_product(obj):
        return obj.linked_product.product_name if obj.linked_product else ''

    @staticmethod
    def get_images(obj):
        return RetailerProductImageSerializer(obj.retailer_product_image, many=True).data

    class Meta:
        model = RetailerProduct
        fields = '__all__'


class RetailerProductUpdateSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    product_id = serializers.IntegerField(required=True, min_value=1)
    product_ean_code = serializers.CharField(required=False, default=None, max_length=100)
    product_name = serializers.CharField(required=False, validators=[ProductNameValidator], default=None, max_length=100)
    mrp = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=None, min_value=0.01)
    selling_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=None,
                                             min_value=0.01)
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False,
                                        default=None, max_length=255)
    status = serializers.ChoiceField(choices=['active', 'deactivated'], required=False, default=None)
    images = serializers.ListField(required=False, allow_null=True, child=serializers.ImageField(), max_length=3)

    def validate(self, attrs):
        shop_id, pid = attrs['shop_id'], attrs['product_id']

        product = RetailerProduct.objects.filter(id=pid, shop_id=shop_id).last()
        if not product:
            raise serializers.ValidationError("Product not found!")

        sp = attrs['selling_price'] if attrs['selling_price'] else product.selling_price
        mrp = attrs['mrp'] if attrs['mrp'] else product.mrp
        name = attrs['product_name'] if attrs['product_name'] else product.name
        ean = attrs['product_ean_code'] if attrs['product_ean_code'] else product.product_ean_code

        if (attrs['selling_price'] or attrs['mrp']) and sp > mrp:
            raise serializers.ValidationError("Selling Price cannot be greater than MRP")

        if RetailerProduct.objects.filter(shop=shop_id, product_ean_code=ean, mrp=mrp).exclude(id=pid).exists():
            raise serializers.ValidationError("Product {} with same mrp & ean code already exists.".format(name))

        if product.linked_product_id and RetailerProduct.objects.filter(
                shop=shop_id, mrp=mrp, linked_product_id=product.linked_product_id).exclude(id=pid).exists():
            raise serializers.ValidationError(
                "Product {} with same mrp & linked GF product already exists.".format(name))
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
    total_discount = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField('sub_total_dt')

    class Meta:
        model = Cart
        fields = ('id', 'cart_no', 'cart_status', 'rt_cart_list', 'items_count', 'total_quantity', 'total_amount', 'offers',
                  'total_discount', 'sub_total', 'created_at', 'modified_at')

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
                    'coupon_code': offer['coupon_code']
                }

        for cart_product in cart_products:
            if cart_product['retailer_product']['id'] in product_offer_map:
                offer = product_offer_map[cart_product['retailer_product']['id']]
                free_product = {
                    'id': offer['free_item_id'],
                    'mrp': offer['free_item_mrp'],
                    'name': offer['free_item_name'],
                    'qty': offer['free_item_qty_added'],
                    'coupon_code': offer['coupon_code']
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

    def get_total_discount(self, obj):
        """
            Discount on cart
        """
        discount = 0
        offers = obj.offers
        if offers:
            array = list(filter(lambda d: d['type'] in ['discount'], offers))
            for i in array:
                discount += i['discount_value']
        return round(discount, 2)

    def sub_total_dt(self, obj):
        """
            Final To be paid amount
        """
        sub_total = float(self.total_amount_dt(obj)) - self.get_total_discount(obj)
        return round(sub_total, 2)


class CheckoutSerializer(serializers.ModelSerializer):
    """
        Checkout Serializer - After products are added
    """
    total_discount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    amount_payable = serializers.SerializerMethodField()
    buyer = PosUserSerializer()

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
        sub_total = float(self.get_total_amount(obj)) - self.get_total_discount(obj)
        return round(sub_total, 2)

    class Meta:
        model = Cart
        fields = ('id', 'total_amount', 'total_discount', 'amount_payable', 'buyer')


class BasicOrderListSerializer(serializers.ModelSerializer):
    """
        Order List For Basic Cart
    """
    buyer = PosUserSerializer()
    order_status = serializers.CharField(source='get_order_status_display')
    order_no = serializers.CharField()
    order_amount = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = ('id', 'order_status', 'order_amount', 'order_no', 'buyer')


class BasicCartListSerializer(serializers.ModelSerializer):
    """
        List of active/pending carts
    """
    total_amount = serializers.SerializerMethodField('total_amount_dt')
    # total_discount = serializers.SerializerMethodField()
    # sub_total = serializers.SerializerMethodField('sub_total_dt')

    def total_amount_dt(self, obj):
        """
            Total Amount For all Products
        """
        total_amount = 0
        for cart_pro in obj.rt_cart_list.all():
            selling_price = cart_pro.selling_price if cart_pro.selling_price else cart_pro.retailer_product.selling_price
            total_amount += Decimal(selling_price) * Decimal(cart_pro.qty)
        return total_amount

    def get_total_discount(self, obj):
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

    def sub_total_dt(self, obj):
        """
            Final To be paid amount
        """
        sub_total = float(self.total_amount_dt(obj)) - self.get_total_discount(obj)
        return round(sub_total, 2)

    class Meta:
        model = Cart
        fields = ('id', 'cart_no', 'cart_status', 'total_amount')


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
        fields = ('return_qty', 'new_sp', 'status')


class OrderReturnSerializer(serializers.ModelSerializer):
    """
        Return for an order
    """

    class Meta:
        model = OrderReturn
        fields = ('id', 'return_reason', 'refund_amount', 'status')


class BasicOrderProductDetailSerializer(serializers.ModelSerializer):
    """
        Get single ordered product detail
    """
    retailer_product = RetailerProductsSearchSerializer()
    product_subtotal = serializers.SerializerMethodField()
    received_effective_price = serializers.SerializerMethodField()
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
        fields = ('retailer_product', 'selling_price', 'effective_price', 'qty', 'product_subtotal',
                  'received_effective_price', 'rt_return_ordered_product')


class BasicOrderSerializer(serializers.ModelSerializer):
    """
        Pos Order detail
    """
    # buyer = PosUserSerializer()
    # total_discount_amount = serializers.SerializerMethodField('total_discount_amount_dt')
    # refunded_amount = serializers.SerializerMethodField('refunded_amount_dt')
    products = serializers.SerializerMethodField()
    # invoice = serializers.SerializerMethodField('invoice_dt')
    ongoing_return = serializers.SerializerMethodField('ongoing_return_dt')

    def ongoing_return_dt(self, obj):
        ongoing_ret = obj.rt_return_order.filter(status='created').last()
        return OrderReturnSerializer(ongoing_ret).data if ongoing_ret else {}

    def refunded_amount_dt(self, obj):
        amt = obj.rt_return_order.filter(status='completed').aggregate(amt=Sum('refund_amount'))
        return round(amt['amt']) if amt['amt'] else 0

    def get_products(self, obj):
        """
            Get ordered products details
        """
        qs = OrderedProductMapping.objects.filter(ordered_product__order=obj, product_type=1)
        products = BasicOrderProductDetailSerializer(qs, many=True).data
        # car offers - map free product to purchased
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
                    'coupon_code': offer['coupon_code']
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
            product['already_returned_qty'] = 0
            product['return_qty'] = 0
            rt_return_ordered_product = product.pop('rt_return_ordered_product', None)
            if rt_return_ordered_product:
                for return_item in rt_return_ordered_product:
                    if return_item['status'] == 'created':
                        product['return_qty'] = return_item['return_qty']
                    else:
                        product['already_returned_qty'] = product['already_returned_qty'] + return_item[
                            'return_qty'] if 'return_qty' in product else return_item['return_qty']
                    if 'new_sp' in product:
                        if return_item['new_sp'] < product['new_sp']:
                            product['new_sp'] = return_item['new_sp']
                    else:
                        product['new_sp'] = return_item['new_sp']
            # map purchased product with free product
            if product['retailer_product']['id'] in product_offer_map:
                offer = product_offer_map[product['retailer_product']['id']]
                free_product = {
                    'id': offer['free_item_id'],
                    'mrp': offer['free_item_mrp'],
                    'name': offer['free_item_name'],
                    'qty': offer['free_item_qty_added'],
                    'already_returned_qty': return_item_map[offer['item_id']] if offer[
                                                                                     'item_id'] in return_item_map else 0,
                    'return_qty': return_item_ongoing[offer['item_id']] if offer[
                                                                               'item_id'] in return_item_ongoing else 0,
                    'coupon_code': offer['coupon_code']
                }
                product['free_product'] = free_product

        if cart_free_product:
            cart_free_product['already_returned_qty'] = return_item_map[
                'free_product'] if 'free_product' in return_item_map else 0
            cart_free_product['return_qty'] = return_item_ongoing[
                'free_product'] if 'free_product' in return_item_ongoing else 0
            products.append(cart_free_product)
        return products

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

    def invoice_dt(self, obj):
        return get_invoice_and_link(OrderedProduct.objects.get(order=obj), self.context.get("current_url", None))

    class Meta:
        model = Order
        # fields = ('id', 'order_no', 'order_status', 'order_amount', 'total_discount_amount', 'refunded_amount', 'buyer',
        #           'products', 'invoice', 'created_at', 'modified_at', 'ongoing_return')
        fields = ('id', 'order_no', 'products', 'ongoing_return')


class OrderReturnCheckoutSerializer(serializers.ModelSerializer):
    """
        Get refund amount on checkout
    """
    order_total = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    received_amount = serializers.SerializerMethodField()
    refunded_amount = serializers.SerializerMethodField()
    current_amount = serializers.SerializerMethodField()
    refund_amount = serializers.SerializerMethodField()
    buyer = PosUserSerializer()

    def get_order_total(self, obj):
        return round(obj.order_amount + self.get_discount_amount(obj), 2)

    def get_discount_amount(self, obj):
        discount = 0
        offers = self.get_cart_offers(obj)
        for offer in offers:
            discount += float(offer['discount_value'])
        return round(discount, 2)

    def get_current_amount(self, obj):
        return round(obj.order_amount - self.get_refunded_amount(obj) - self.get_refund_amount(obj), 2)

    def get_refunded_amount(self, obj):
        amt = obj.rt_return_order.filter(status='completed').aggregate(amt=Sum('refund_amount'))
        return round(amt['amt'], 2) if amt['amt'] else 0

    def get_cart_offers(self, obj):
        """
            Get offers applied on cart
        """
        offers = obj.ordered_cart.offers
        cart_offers = []
        for offer in offers:
            if offer['coupon_type'] == 'cart' and offer['type'] == 'discount':
                cart_offers.append(offer)
        return cart_offers

    def get_received_amount(self, obj):
        """
            order amount
        """
        return round(obj.order_amount, 2)

    def get_refund_amount(self, obj):
        """
            refund amount
        """
        ongoing_return = obj.rt_return_order.filter(status='created').last()
        return round(ongoing_return.refund_amount, 2) if ongoing_return else 0

    class Meta:
        model = Order
        fields = ('id', 'order_total', 'discount_amount', 'received_amount', 'refunded_amount',
                  'current_amount', 'refund_amount', 'buyer', 'order_status')


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
