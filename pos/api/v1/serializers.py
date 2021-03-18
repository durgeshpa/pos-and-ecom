from decimal import Decimal

from rest_framework import serializers
from django.db.models import Q
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from global_config.models import GlobalConfig
from products.models import Product, ProductImage
from pos.models import RetailerProduct, RetailerProductImage
from retailer_to_sp.models import CartProductMapping, Cart, Order
from accounts.api.v1.serializers import UserSerializer, UserPhoneSerializer

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
        fields = ('product_name','product_short_description','product_mrp', 'product_pro_image')


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
            Mrp, selling price margin
        """
        return ((obj.retailer_product.mrp - Decimal(self.product_price_dt(obj))) / obj.retailer_product.mrp) * 100

    def display_text_dt(self, obj):
        """
            If combo offer on product, display whether offer is applied or more products should be added
        """
        display_text_applied = ''
        display_text_add = ''
        if obj.selling_price > 0:
            offers = obj.cart.offers
            for offer in offers:
                if offer['coupon_type'] == 'catalog' and offer['available_type'] != 'none' and\
                        offer['item_id'] == obj.retailer_product.id:
                    if offer['type'] == 'none':
                        display_text_add += offer['display_text']
                    else:
                        display_text_applied = offer['display_text']
        return display_text_applied + ' | ' + display_text_add if display_text_applied or display_text_add else ''

    class Meta:
        model = CartProductMapping
        fields = ('id', 'retailer_product', 'qty', 'product_price', 'margin', 'product_sub_total', 'display_text',
                  'parent_retailer_product')


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
        qs = CartProductMapping.objects.filter(cart=obj)
        search_text = self.context.get('search_text')
        # Search on name, ean and sku
        if search_text:
            qs = qs.filter(Q(retailer_product__sku__icontains=search_text)
                           | Q(retailer_product__name__icontains=search_text)
                           | Q(retailer_product__product_ean_code__icontains=search_text))

        if qs.exists():
            # Pagination
            records_per_page = 10
            per_page_products = self.context.get('records_per_page') if self.context.get('records_per_page') else records_per_page
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
        purchased_products = []
        for product in cart_products:
            if not product['parent_retailer_product']:
                purchased_products += [product]

        free_products = {}
        for product in cart_products:
            if product['parent_retailer_product']:
                free_products[product['parent_retailer_product']] = free_products[product['parent_retailer_product']] \
                                                                    + [product] if product['parent_retailer_product'] \
                                                                                   in free_products else [product]
        for product in purchased_products:
            if product['retailer_product']['id'] in free_products:
                product['free_products'] = free_products[product['retailer_product']['id']]

        return purchased_products

    def items_count_dt(self, obj):
        """
            Total Types Of Products
        """
        return obj.rt_cart_list.count()

    def total_quantity_dt(self, obj):
        """
            Total Quantity Of All Products
        """
        qty = 0
        for cart_pro in obj.rt_cart_list.all():
            qty += int(cart_pro.qty)
        return qty

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


class BasicOrderSerializer(serializers.ModelSerializer):
    """
        Order Placed Data For Basic Cart
    """
    ordered_cart = BasicCartSerializer()
    ordered_by = UserSerializer()
    order_status = serializers.CharField(source='get_order_status_display')
    total_discount_amount = serializers.SerializerMethodField('total_discount_amount_dt')

    def total_discount_amount_dt(self, obj):
        return obj.total_mrp_amount - obj.total_final_amount

    class Meta:
        model = Order
        fields = ('id', 'ordered_cart', 'order_status', 'total_final_amount', 'total_discount_amount',
                  'total_tax_amount', 'total_mrp_amount', 'ordered_by', 'created_at', 'modified_at')


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
        fields = ('id', 'total_amount', 'offers', 'total_discount', 'amount_payable', 'buyer')


class BasicOrderListSerializer(serializers.ModelSerializer):
    """
        Order List For Basic Cart
    """
    ordered_by = UserPhoneSerializer()
    order_status = serializers.CharField(source='get_order_status_display')
    total_final_amount = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = ('id', 'order_status', 'total_final_amount', 'ordered_by',)
