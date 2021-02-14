from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from pos.models import RetailerProduct
from products.models import Product
from shops.models import Shop


class RetailerProductCreateSerializer(serializers.Serializer):

    shop_id = serializers.IntegerField(required=True)
    linked_product_id = serializers.IntegerField(required=False)
    product_name = serializers.CharField(required=True)
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    description = serializers.CharField(allow_blank=True, required=False)

    def validate(self, attrs):
        if attrs.get('shop_id'):
            if not Shop.objects.filter(id=attrs.get('shop_id')).exists():
                raise serializers.ValidationError(_("Shop ID not found! Please enter a valid Shop ID!"))

        if attrs.get('selling_price') and attrs.get('mrp'):
            if attrs.get('selling_price') > attrs.get('mrp'):
                raise serializers.ValidationError(_("Selling Price cannot be greater than MRP"))

        if attrs.get('linked_product_id'):
            if not Product.objects.filter(id=attrs.get('linked_product_id')).exists():
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
    product_name = serializers.CharField(required=False)
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    description = serializers.CharField(allow_blank=True, required=False)

    def validate(self, attrs):
        if attrs.get('product_id'):
            if not RetailerProduct.objects.filter(id=attrs.get('product_id')).exists():
                raise serializers.ValidationError(_("Please enter a valid product_id"))

            if attrs.get('selling_price') and attrs.get('mrp'):
                if attrs.get('selling_price') > attrs.get('mrp'):
                    raise serializers.ValidationError(_("Selling Price cannot be greater than MRP"))

            if RetailerProduct.objects.filter(id=attrs.get('product_id')).exists():
                if attrs.get('mrp'):
                    product = RetailerProduct.objects.filter(id=attrs.get('product_id'))
                    if attrs.get('mrp') != product.values()[0].get('mrp'):
                        if not attrs.get('product_name'):
                            raise serializers.ValidationError(_({"msg": "When you are changing the mrp of the "
                                                                        "product, some fields are mandatory",
                                                                 "fields": {"product_name": "mandatory",
                                                                            "mrp": "mandatory",
                                                                            "selling_price": "mandatory",
                                                                            "description": "mandatory"}}))
                        if not attrs.get('selling_price'):
                            raise serializers.ValidationError(_({"msg": "When you are changing the mrp of the "
                                                                        "product, some fields are mandatory",
                                                                 "fields": {"product_name": "mandatory",
                                                                            "mrp": "mandatory",
                                                                            "selling_price": "mandatory",
                                                                            "description": "mandatory"}}))
                        if attrs.get('selling_price') and attrs.get('mrp'):
                            if attrs.get('selling_price') > attrs.get('mrp'):
                                raise serializers.ValidationError(_("Selling Price cannot be greater than MRP"))

        if not attrs.get('product_id'):
            raise serializers.ValidationError(_("Please enter a product_id! It is a mandatory field"))

        return attrs

