from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from pos.models import RetailerProduct, RetailerOffer
from products.models import Product
from retailer_backend.validators import ProductNameValidator
from shops.models import Shop


class RetailerProductCreateSerializer(serializers.Serializer):

    shop_id = serializers.IntegerField(required=False)
    linked_product_id = serializers.IntegerField(required=False)
    product_name = serializers.CharField(required=True, validators=[ProductNameValidator])
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False)

    def validate(self, attrs):
        serializer_list = ['shop_id', "linked_product_id", "product_name", "mrp", "selling_price", "description"]

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
    created_at = serializers.SerializerMethodField()
    modified_at = serializers.SerializerMethodField()


    def get_id(self, obj):
        return obj['id']

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

    def get_modified_at(self, obj):
        return obj['modified_at']


class RetailerProductUpdateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    shop_id = serializers.IntegerField(required=False)
    product_name = serializers.CharField(required=False, validators=[ProductNameValidator])
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    description = serializers.CharField(allow_blank=True, validators=[ProductNameValidator], required=False)

    def validate(self, attrs):
        serializer_list = ['shop_id', 'product_id', "product_name", "mrp", "selling_price", "description"]

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


class CouponCodeSerializer(serializers.ModelSerializer):
    order_value = serializers.IntegerField(required=True)

    class Meta:
        model = RetailerOffer
        fields = ('offer_type', 'coupon_name', 'order_value', 'discount_value', 'status',
                  'offer_start_date', 'offer_end_date')


class ComboDealsSerializer(serializers.ModelSerializer):
    primary_product = serializers.IntegerField(required=True)
    primary_product_qty = serializers.IntegerField(required=True)
    free_product = serializers.IntegerField(required=True)
    free_product_qty = serializers.IntegerField(required=True)



    class Meta:
        model = RetailerOffer
        fields = ('offer_type', 'coupon_name', 'discount_value', 'status', 'primary_product', 'primary_product_qty',
                  'free_product', 'free_product_qty', 'offer_start_date', 'offer_end_date')
