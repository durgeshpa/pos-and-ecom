from decimal import Decimal

from rest_framework import serializers
from django.db.models import Q
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

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

    def product_price_dt(self, obj):
        """
            Product price single
        """
        return obj.selling_price if obj.selling_price else obj.retailer_product.selling_price

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

    class Meta:
        model = CartProductMapping
        fields = ('id', 'retailer_product', 'qty', 'product_price', 'margin', 'product_sub_total')


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
        fields = ('id', 'cart_status', 'rt_cart_list', 'items_count', 'total_quantity', 'total_amount',
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
        # Pagination
        if qs.exists():
            per_page_products = self.context.get('records_per_page') if self.context.get('records_per_page') else 10
            paginator = Paginator(qs, int(per_page_products))
            page_number = self.context.get('page_number')
            try:
                qs = paginator.get_page(page_number)
            except PageNotAnInteger:
                qs = paginator.get_page(1)
            except EmptyPage:
                qs = paginator.get_page(paginator.num_pages)

        return BasicCartProductMappingSerializer(qs, many=True, context=self.context).data

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
            total_amount += Decimal(cart_pro.selling_price if cart_pro.selling_price \
                                        else cart_pro.retailer_product.selling_price) * Decimal(cart_pro.qty)
        return total_amount

    def get_total_discount(self, obj):
        """
            Discount on cart
        """
        return 0

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
    total_final_amount = serializers.ReadOnlyField()
    total_mrp_amount = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = ('id', 'ordered_cart', 'order_status', 'total_final_amount', 'total_discount_amount',
                  'total_tax_amount', 'total_mrp_amount', 'ordered_by', 'created_at', 'modified_at')


class BasicOrderListSerializer(serializers.ModelSerializer):
    """
        Order Placed Data For Basic Cart
    """
    ordered_by = UserPhoneSerializer()
    order_status = serializers.CharField(source='get_order_status_display')
    total_final_amount = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = ('id', 'order_status', 'total_final_amount',
                  'ordered_by',)
