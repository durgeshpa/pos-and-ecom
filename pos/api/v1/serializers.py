from decimal import Decimal
import datetime
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from django.db.models import Q
from django.urls import reverse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Sum

from products.models import Product, ProductImage
from pos.models import RetailerProduct, RetailerProductImage
from retailer_to_sp.models import CartProductMapping, Cart, Order, OrderedProduct, OrderReturn, ReturnItems, OrderedProductMapping
from accounts.api.v1.serializers import UserSerializer, UserPhoneSerializer
from products.models import Product
from retailer_backend.validators import ProductNameValidator
from shops.models import Shop
from coupon.models import Coupon, CouponRuleSet, RuleSetProductMapping, DiscountValue


class RetailerProductImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(
        max_length=None, use_url=True,
    )
    class Meta:
        model = RetailerProductImage
        fields = ('image_name', 'image')


class RetailerProductCreateSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField(required=False)
    status = serializers.CharField(required=False)
    linked_product_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    product_name = serializers.CharField(required=True, validators=[ProductNameValidator])
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False)
    product_ean_code = serializers.CharField(required=True)
    images = RetailerProductImageSerializer(many=True, required=True)

    def validate(self, attrs):
        serializer_list = ['shop_id', "linked_product_id", "product_name", "mrp", "selling_price",
                           "product_ean_code", "description", "status", "images"]

        for key in self.initial_data.keys():
            if key not in serializer_list:
                raise serializers.ValidationError(_(f"{key} is not allowed"))

        # Check, shop_id exists or not
        shop_id = attrs.get('shop_id')
        if shop_id:
            # If user provide shop_id
            if not Shop.objects.filter(id=shop_id).exists():
                raise serializers.ValidationError(_("Shop ID not found! Please enter a valid Shop ID!"))

        selling_price = attrs.get('selling_price')
        mrp = attrs.get('mrp')
        if selling_price and mrp:
            # If user provide selling_price and mrp
            if selling_price > mrp:
                raise serializers.ValidationError(_("Selling Price cannot be greater than MRP"))

        linked_product_id = attrs.get('linked_product_id')
        if linked_product_id:
            # If user provides linked_product_id
            if not Product.objects.filter(id=linked_product_id).exists():
                raise serializers.ValidationError(_("Linked Product ID not found! Please enter a valid Product ID"))

        return attrs


class RetailerProductResponseSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    shop = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    sku = serializers.SerializerMethodField()
    mrp = serializers.SerializerMethodField()
    selling_price = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    sku_type = serializers.SerializerMethodField()
    linked_product = serializers.SerializerMethodField()
    product_ean_code = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    modified_at = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj['id']

    def get_status(self, obj):
        return obj['status']

    def get_shop(self, obj):
        return obj['shop__shop_name']

    def get_name(self, obj):
        return obj['name']

    def get_sku(self, obj):
        return obj['sku']

    def get_mrp(self, obj):
        return obj['mrp']

    def get_selling_price(self, obj):
        return obj['selling_price']

    def get_description(self, obj):
        return obj['description']

    def get_sku_type(self, obj):
        if obj['sku_type'] == 1:
            return 'CREATED'
        if obj['sku_type'] == 2:
            return 'LINKED'
        if obj['sku_type'] == 3:
            return 'LINKED_EDITED'

    def get_linked_product(self, obj):
        if obj['linked_product__product_name']:
            return obj['linked_product__product_name']
        return ''

    def get_images(self, obj):

        queryset = RetailerProductImage.objects.filter(product_id=obj['id'])
        return RetailerProductImageSerializer(queryset, many=True).data

    def get_created_at(self, obj):
        return obj['created_at']

    def get_product_ean_code(self, obj):
        return obj['product_ean_code']

    def get_modified_at(self, obj):
        return obj['modified_at']


class RetailerProductImageDeleteSerializers(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    image_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        serializer_list = ['product_id', "image_id"]

        for key in self.initial_data.keys():
            if key not in serializer_list:
                raise serializers.ValidationError(_(f"{key} is not allowed"))

        product_id = attrs.get('product_id')
        if product_id:
            # If user provides product_id
            if not RetailerProduct.objects.filter(id=product_id).exists():
                raise serializers.ValidationError(_("Product ID not found! Please enter a valid Product ID"))

        image_id = attrs.get('image_id')
        if image_id:
            # If user provides image_id
            if not RetailerProductImage.objects.filter(id=image_id).exists():
                raise serializers.ValidationError(_("Image ID not found! Please enter a valid Product ID"))

        return attrs


class RetailerProductUpdateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    shop_id = serializers.IntegerField(required=False)
    product_ean_code = serializers.CharField(required=False)
    product_name = serializers.CharField(required=False, validators=[ProductNameValidator])
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False)
    status = serializers.CharField(required=False)
    images = serializers.FileField(required=False)
    linked_product_id = serializers.IntegerField(required=False)
    image_id = serializers.ListField(required=False)

    def validate(self, attrs):
        serializer_list = ['shop_id', 'product_id', 'product_ean_code', 'product_name',
                           'mrp', 'selling_price', 'description', 'status', 'images',
                           'linked_product_id', 'image_id']

        for key in self.initial_data.keys():
            if key not in serializer_list:
                raise serializers.ValidationError(_(f"{key} is not allowed"))

        product_id = attrs.get('product_id')
        if product_id:
            if not RetailerProduct.objects.filter(id=product_id).exists():
                raise serializers.ValidationError(_("Please enter a valid product_id"))

            selling_price = attrs.get('selling_price')
            mrp = attrs.get('mrp')
            if selling_price and mrp:
                if selling_price > mrp:
                    raise serializers.ValidationError(_("Selling Price cannot be greater than MRP"))

        shop_id = attrs.get('shop_id')
        if shop_id:
            # If user provide shop_id
            if not Shop.objects.filter(id=shop_id).exists():
                raise serializers.ValidationError(_("Shop ID not found! Please enter a valid Shop ID!"))
        return attrs


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('image_name', 'image_alt_text', 'image')


class RetailerProductImageSerializer(serializers.ModelSerializer):
    """
        Images for RetailerProduct
    """

    class Meta:
        model = RetailerProductImage
        fields = ('image_name', 'image_alt_text', 'image')


class ProductDetailSerializer(serializers.ModelSerializer):
    """
        Product Detail For GramFactory products
    """
    product_pro_image = ProductImageSerializer(many=True)

    class Meta:
        model = Product
        fields = ('product_name', 'product_short_description', 'product_mrp', 'product_pro_image')


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
    margin = serializers.SerializerMethodField('margin_dt')
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

    def margin_dt(self, obj):
        """
            Mrp, cart product price margin
        """
        return ((float(obj.retailer_product.mrp) - float(obj.item_effective_prices)) / float(
            obj.retailer_product.mrp)) * 100

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
        fields = ('id', 'retailer_product', 'qty', 'product_price', 'margin', 'product_sub_total', 'display_text')


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
    buyer = UserSerializer()

    class Meta:
        model = Cart
        fields = ('id', 'cart_status', 'rt_cart_list', 'items_count', 'total_quantity', 'total_amount', 'offers',
                  'total_discount', 'sub_total', 'buyer', 'created_at', 'modified_at')

    def rt_cart_list_dt(self, obj):
        """
         Search and pagination on cart
        """
        qs = CartProductMapping.objects.filter(cart=obj, product_type=1)
        search_text = self.context.get('search_text')
        # Search on name, ean and sku
        if search_text:
            qs = qs.filter(Q(retailer_product__sku__icontains=search_text)
                           | Q(retailer_product__name__icontains=search_text)
                           | Q(retailer_product__product_ean_code__icontains=search_text))

        if qs.exists():
            # Pagination
            records_per_page = 10
            per_page_products = self.context.get('records_per_page') if self.context.get(
                'records_per_page') else records_per_page
            paginator = Paginator(qs, int(per_page_products))
            page_number = self.context.get('page_number')
            try:
                qs = paginator.get_page(page_number)
            except PageNotAnInteger:
                qs = paginator.get_page(1)
            except EmptyPage:
                qs = paginator.get_page(paginator.num_pages)

        # Order Cart In Purchased And Free Products
        cart_products = BasicCartProductMappingSerializer(qs, many=True, context=self.context).data
        product_offer_map = {}

        for offer in obj.offers:
            if offer['coupon_type'] == 'catalog' and offer['type'] == 'combo':
                product_offer_map[offer['item_id']] = offer

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


class BasicOrderedProductSerializer(serializers.ModelSerializer):
    invoice_link = serializers.SerializerMethodField('invoice_link_id')

    def invoice_link_id(self, obj):
        current_url = self.context.get("current_url", None)
        return "{0}{1}".format(current_url, reverse('download_invoice_sp', args=[obj.pk]))

    class Meta:
        model = OrderedProduct
        fields = ('order', 'invoice_no', 'invoice_link')


class CheckoutSerializer(serializers.ModelSerializer):
    """
        Checkout Serializer - After products are added
    """
    total_discount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    amount_payable = serializers.SerializerMethodField()
    buyer = UserSerializer()

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
    ordered_by = UserPhoneSerializer()
    order_status = serializers.CharField(source='get_order_status_display')
    order_no = serializers.CharField()
    total_final_amount = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = ('id', 'order_status', 'total_final_amount', 'order_no', 'ordered_by',)


class BasicCartListSerializer(serializers.ModelSerializer):
    """
        List of active/pending carts
    """
    buyer = UserPhoneSerializer()
    cart_status = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField('total_amount_dt')
    total_discount = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField('sub_total_dt')
    order_id = serializers.SerializerMethodField()

    def get_cart_status(self, obj):
        if obj.cart_status in ['active', 'pending']:
            return 'open'
        return obj.cart_status

    def get_order_id(self, obj):
        return obj.order_id

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
        fields = ('id', 'cart_status', 'total_amount', 'total_discount', 'sub_total', 'created_at',
                  'modified_at', 'order_id', 'buyer')


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

    class Meta:
        model = ReturnItems
        fields = ('return_qty', )


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
    rt_return_ordered_product = ReturnItemsSerializer()

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
        fields = ('retailer_product', 'effective_price', 'selling_price', 'qty', 'product_subtotal', 'received_effective_price',
                  'rt_return_ordered_product')


class BasicOrderSerializer(serializers.ModelSerializer):
    """
        Pos Order detail
    """
    ordered_by = UserSerializer()
    total_discount_amount = serializers.SerializerMethodField('total_discount_amount_dt')
    products = serializers.SerializerMethodField()
    rt_order_order_product = BasicOrderedProductSerializer(many=True)
    rt_return_order = OrderReturnSerializer(many=True)

    def get_products(self, obj):
        """
            Get ordered products details
        """
        qs = OrderedProductMapping.objects.filter(ordered_product__order=obj, product_type=1)
        products = BasicOrderProductDetailSerializer(qs, many=True).data
        # car offers - map free product to purchased
        product_offer_map = {}
        for offer in obj.ordered_cart.offers:
            if offer['coupon_type'] == 'catalog' and offer['type'] == 'combo':
                product_offer_map[offer['item_id']] = offer
        # check if any returns
        return_item_map = {}
        return_obj = OrderReturn.objects.filter(order=obj).last()
        if return_obj:
            return_item_detail = return_obj.free_qty_map
            if return_item_detail:
                for combo in return_item_detail:
                    return_item_map[combo['item_id']] = combo['free_item_return_qty']

        for product in products:
            rt_return_ordered_product = product.pop('rt_return_ordered_product', None)
            if rt_return_ordered_product:
                product['return_qty'] = rt_return_ordered_product['return_qty']
            # map purchased product with free product
            if product['retailer_product']['id'] in product_offer_map:
                offer = product_offer_map[product['retailer_product']['id']]
                free_product = {
                    'id': offer['free_item_id'],
                    'mrp': offer['free_item_mrp'],
                    'name': offer['free_item_name'],
                    'qty': offer['free_item_qty_added'],
                    'return_qty': return_item_map[offer['item_id']] if offer['item_id'] in return_item_map else 0,
                    'coupon_code': offer['coupon_code']
                }
                product['free_product'] = free_product
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

    class Meta:
        model = Order
        fields = ('id', 'order_no', 'order_status', 'total_final_amount', 'total_discount_amount',
                  'total_tax_amount', 'total_mrp_amount', 'products', 'rt_order_order_product', 'ordered_by', 'created_at',
                  'modified_at', 'rt_return_order')


class OrderReturnCheckoutSerializer(serializers.ModelSerializer):
    """
        Get refund amount on checkout
    """
    received_amount = serializers.SerializerMethodField()
    current_amount = serializers.SerializerMethodField()
    refund_amount = serializers.SerializerMethodField()
    buyer = UserSerializer()

    def get_received_amount(self, obj):
        """
            order amount
        """
        return obj.total_final_amount

    def get_current_amount(self, obj):
        """
            net pay
        """
        return self.get_received_amount(obj) - self.get_refund_amount(obj)

    def get_refund_amount(self, obj):
        """
            refund amount
        """
        order_return = OrderReturn.objects.get(order=obj)
        return order_return.refund_amount

    class Meta:
        model = Order
        fields = ('id', 'received_amount',  'current_amount', 'refund_amount', 'buyer', 'order_status')


def coupon_name_validation(coupon_name):
    """
       Check that the Coupon name should be unique.
   """
    if coupon_name:
        if CouponRuleSet.objects.filter(rulename=coupon_name).exists():
            raise serializers.ValidationError(_("This Coupon name has already been registered."))


def combo_offer_name_validation(combo_offer_name):
    """
        Check that the Combo Offer name should be unique.
    """
    if combo_offer_name:
        if CouponRuleSet.objects.filter(rulename=combo_offer_name).exists():
            raise serializers.ValidationError(_("This Offer name has already been registered."))


def validate_retailer_product(retailer_product):
    """
        Check that the product is present in RetailerProduct.
    """
    if not RetailerProduct.objects.filter(id=retailer_product).exists():
        raise serializers.ValidationError(_("Please enter a valid Product"))


def discount_validation(data):
    """
         Check that the discount value should be less then discount_qty_amount.
    """
    if data['discount_value'] > data['discount_qty_amount']:
        raise serializers.ValidationError("discount value must less then order value")


def date_validation(data):
    """
        Check that the start date is before the expiry date.
    """
    if data['start_date'] > data['expiry_date']:
        raise serializers.ValidationError("expiry date must occur after start date")
    """
        Check that the expiry date is before the today.
    """
    if data['expiry_date'] < datetime.date.today():
        raise serializers.ValidationError("expiry date must be greater than today")


class CouponCodeSerializer(serializers.ModelSerializer):
    coupon_name = serializers.CharField(required=True)
    discount_qty_amount = serializers.DecimalField(required=True, max_digits=12, decimal_places=4)
    discount_value = serializers.DecimalField(required=True, max_digits=12, decimal_places=4)

    def validate(self, data):
        """
            Check start & expiry date validation,
            Coupon name should be unique,
            Discount value should be less then discount_qty_amount.
        """
        date_validation(data)
        coupon_name_validation(data.get('coupon_name'))
        discount_validation(data)
        return data

    class Meta:
        model = Coupon
        fields = ('coupon_name', 'start_date', 'expiry_date', 'discount_qty_amount', 'discount_value')


class ComboDealsSerializer(serializers.ModelSerializer):
    combo_offer_name = serializers.CharField(required=True)
    retailer_primary_product = serializers.IntegerField(required=True)
    purchased_product_qty = serializers.IntegerField(required=True)
    retailer_free_product = serializers.IntegerField(required=True)
    free_product_qty = serializers.IntegerField(required=True)

    def validate(self, data):
        """
            start & expiry date, combo_offer_name & product validation.
        """
        date_validation(data)
        validate_retailer_product(data.get('retailer_primary_product'))
        validate_retailer_product(data.get('retailer_free_product'))
        combo_offer_name_validation(data.get('combo_offer_name'))
        return data

    class Meta:
        model = RuleSetProductMapping
        fields = ('combo_offer_name', 'retailer_primary_product', 'retailer_free_product',
                  'purchased_product_qty', 'free_product_qty', 'start_date', 'expiry_date')


class CouponCodeUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True)
    coupon_name = serializers.CharField(required=False)
    discount_qty_amount = serializers.DecimalField(required=False, max_digits=12, decimal_places=4)
    discount_value = serializers.DecimalField(required=False, max_digits=12, decimal_places=4)
    start_date = serializers.DateField(required=False)
    expiry_date = serializers.DateField(required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, data):
        """
            Check start & expiry date validation,
            Coupon name should be unique,
            Discount value should be less then discount_qty_amount.
        """
        if data.get('start_date') and data.get('expiry_date'):
            date_validation(data)
        if data.get('discount_value') and data.get('discount_qty_amount'):
            discount_validation(data)
        if data.get('coupon_name'):
            coupon_name_validation(data.get('coupon_name'))
        return data

    class Meta:
        model = Coupon
        fields = (
        'id', 'coupon_name', 'start_date', 'expiry_date', 'discount_qty_amount', 'discount_value', 'is_active')


class ComboDealsUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True)
    combo_offer_name = serializers.CharField(required=False)
    retailer_primary_product = serializers.IntegerField(required=False)
    purchased_product_qty = serializers.IntegerField(required=False)
    retailer_free_product = serializers.IntegerField(required=False)
    free_product_qty = serializers.IntegerField(required=False)
    start_date = serializers.DateField(required=False)
    expiry_date = serializers.DateField(required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, data):
        """
            start & expiry date, combo_offer_name & product validation.
        """
        if data.get('start_date') and data.get('expiry_date'):
            date_validation(data)
        if data.get('retailer_primary_product'):
            validate_retailer_product(data.get('retailer_primary_product'))
        if data.get('retailer_free_product'):
            validate_retailer_product(data.get('retailer_free_product'))
        if data.get('combo_offer_name'):
            combo_offer_name_validation(data.get('combo_offer_name'))
        return data

    class Meta:
        model = RuleSetProductMapping
        fields = ('id', 'combo_offer_name', 'retailer_primary_product', 'retailer_free_product',
                  'purchased_product_qty', 'free_product_qty', 'start_date', 'expiry_date', 'is_active')


class DiscountSerializer(serializers.ModelSerializer):
    discount_value = serializers.DecimalField(required=False, max_digits=12, decimal_places=4)

    class Meta:
        model = DiscountValue
        fields = ('discount_value', 'is_percentage', 'max_discount')


class CouponGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ('id', 'coupon_code', 'is_active', 'coupon_type')


class ComboGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleSetProductMapping
        fields = ('retailer_primary_product', 'retailer_free_product',
                  'purchased_product_qty', 'free_product_qty', 'is_active')


class CouponRuleSetSerializers(serializers.ModelSerializer):
    coupon_ruleset = CouponGetSerializer(many=True)
    product_ruleset = ComboGetSerializer(many=True)
    discount = DiscountSerializer()

    class Meta:
        model = CouponRuleSet
        fields = ('is_active', 'cart_qualifying_min_sku_value', 'discount',
                  'product_ruleset', 'coupon_ruleset',)


class CouponRuleSetGetSerializer(serializers.ModelSerializer):
    discount = serializers.SerializerMethodField('discount_value')

    class Meta:
        model = CouponRuleSet
        fields = ('discount', 'is_active')

    def discount_value(self, obj):
        return DiscountSerializer(obj.discount, context=self.context).data


class CouponListSerializers(serializers.ModelSerializer):
    rule = CouponRuleSetGetSerializer()

    class Meta:
        model = Coupon
        fields = ('is_active', 'coupon_code', 'rule')
