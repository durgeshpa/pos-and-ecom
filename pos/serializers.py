import datetime
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from pos.models import RetailerProduct
from products.models import Product
from retailer_backend.validators import ProductNameValidator
from shops.models import Shop
from coupon.models import Coupon, CouponRuleSet, RuleSetProductMapping, DiscountValue


class RetailerProductCreateSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField(required=False)
    status = serializers.CharField(required=False)
    linked_product_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    product_name = serializers.CharField(required=True, validators=[ProductNameValidator])
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False)
    product_ean_code = serializers.CharField(required=True)

    def validate(self, attrs):
        serializer_list = ['shop_id', "linked_product_id", "product_name", "mrp", "selling_price",
                           "product_ean_code", "description", "status"]

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

    def get_created_at(self, obj):
        return obj['created_at']

    def get_product_ean_code(self, obj):
        return obj['product_ean_code']

    def get_modified_at(self, obj):
        return obj['modified_at']


class RetailerProductUpdateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    shop_id = serializers.IntegerField(required=False)
    product_ean_code = serializers.CharField(required=False)
    product_name = serializers.CharField(required=False, validators=[ProductNameValidator])
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False)
    status = serializers.CharField(required=False)

    def validate(self, attrs):
        serializer_list = ['shop_id', 'product_id', "product_name", "mrp", "selling_price", "description", "status"]

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
