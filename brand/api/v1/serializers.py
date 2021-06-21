from django.db import transaction
from django.utils.text import slugify

from rest_framework import serializers
from brand.models import Brand, BrandPosition, BrandData, Vendor
from products.api.v1.serializers import UserSerializers, LogSerializers
from products.common_validators import get_validate_parent_brand
from brand.common_function import BrandCls
from products.models import ProductVendorMapping, Product, ParentProduct


class RecursiveSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class BrandSerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = Brand
        fields = '__all__'


class BrandPositionSerializer(serializers.ModelSerializer):

    class Meta:
        model = BrandPosition
        fields = '__all__'


class BrandDataSerializer(serializers.ModelSerializer):
    brand_data = BrandSerializer(read_only=True)
    slot = BrandPositionSerializer(read_only=True)

    class Meta:
        model = BrandData
        fields = ('id', 'slot', 'brand_data', 'brand_data_order')


class BrandSlotSerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = BrandPosition
        fields = '__all__'


class SubBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', "brand_name", "brand_logo", "brand_code")


class ParentBrandSerializers(serializers.ModelSerializer):
    class Meta:
        model = Brand

        fields = ('id', 'brand_name')


class VendorSerializers(serializers.ModelSerializer):

    class Meta:
        model = Vendor

        fields = ('id', 'vendor_name', 'mobile')


class BrandVendorMappingSerializers(serializers.ModelSerializer):
    vendor = VendorSerializers(read_only=True)

    class Meta:
        model = ProductVendorMapping

        fields = ('vendor',)


class ChildProductSerializers(serializers.ModelSerializer):
    product_vendor_mapping = BrandVendorMappingSerializers(read_only=True, many=True)

    class Meta:
        model = Product

        fields = ('product_name', 'product_vendor_mapping', )


class BrandCrudSerializers(serializers.ModelSerializer):
    brand_parent = ParentBrandSerializers(read_only=True)
    brand_child = SubBrandSerializer(many=True, read_only=True)
    brand_slug = serializers.SlugField(required=False, allow_null=True, allow_blank=True)
    brand_log = LogSerializers(many=True, read_only=True)
    brand_logo = serializers.ImageField(required=True)

    class Meta:
        model = Brand
        fields = ('id', 'brand_name', 'brand_code', 'brand_parent', 'brand_description', 'brand_slug',
                  'brand_logo', 'status', 'brand_child', 'brand_log',)

    def validate(self, data):
        """
            brand_slug validation.
        """
        if not 'brand_slug' in self.initial_data or not self.initial_data['brand_slug']:
            data['brand_slug'] = slugify(data.get('brand_slug'))

        if 'brand_parent' in self.initial_data and self.initial_data['brand_parent'] is not None:
            brand_val = get_validate_parent_brand(self.initial_data['brand_parent'])
            if 'error' in brand_val:
                raise serializers.ValidationError(brand_val['error'])
            data['brand_parent'] = brand_val['parent_brand']

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            brand = Brand.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return brand

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            brand = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': e.args[0] if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        BrandCls.create_brand_log(brand)

        return brand


class ProductVendorMapSerializers(serializers.ModelSerializer):
    product_parent_product = ChildProductSerializers(read_only=True, many=True)

    class Meta:
        model = ParentProduct
        fields = ('parent_brand', 'product_parent_product',)



