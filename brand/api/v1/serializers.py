import csv
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse

from rest_framework import serializers
from brand.models import Brand, BrandPosition, BrandData, Vendor
from products.api.v1.serializers import LogSerializers
from brand.common_validators import validate_brand_name, validate_brand_code, validate_brand_slug
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

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['brand_name']:
            representation['brand_name'] = representation['brand_name'].title()
        return representation


class ParentBrandSerializers(serializers.ModelSerializer):
    class Meta:
        model = Brand

        fields = ('id', 'brand_name')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['brand_name']:
            representation['brand_name'] = representation['brand_name'].title()
        return representation


class VendorSerializers(serializers.ModelSerializer):
    class Meta:
        model = Vendor

        fields = ('id', 'vendor_name', 'mobile')
        distinct = ('id',)


class BrandVendorMappingSerializers(serializers.ModelSerializer):
    vendor = VendorSerializers(read_only=True)

    class Meta:
        model = ProductVendorMapping

        fields = ('vendor',)
        distinct = ('vendor',)


class ChildProductSerializers(serializers.ModelSerializer):
    product_vendor_mapping = BrandVendorMappingSerializers(read_only=True, many=True)

    class Meta:
        model = Product

        fields = ('product_vendor_mapping',)

    def to_representation(self, instance):

        representation = super().to_representation(instance)
        if representation['product_vendor_mapping']:
            representation
        else:
            pass
        return representation


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

        brand_id = self.instance.id if self.instance else None
        if 'brand_name' in self.initial_data and self.initial_data['brand_name'] is not None:
            brand_obj = validate_brand_name(self.initial_data['brand_name'], brand_id)
            if brand_obj is not None and 'error' in brand_obj:
                raise serializers.ValidationError(brand_obj['error'])

        if 'brand_code' in self.initial_data and self.initial_data['brand_code'] is not None:
            brand_obj = validate_brand_code(self.initial_data['brand_code'], brand_id)
            if brand_obj is not None and 'error' in brand_obj:
                raise serializers.ValidationError(brand_obj['error'])

        if 'brand_slug' in self.initial_data and self.initial_data['brand_slug'] is not None:
            brand_obj = validate_brand_slug(self.initial_data['brand_slug'], brand_id)
            if brand_obj is not None and 'error' in brand_obj:
                raise serializers.ValidationError(brand_obj['error'])

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            brand = Brand.objects.create(**validated_data)
            BrandCls.create_brand_log(brand, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return brand

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            brand = super().update(instance, validated_data)
            BrandCls.create_brand_log(brand, "updated")
        except Exception as e:
            error = {'message': e.args[0] if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return brand

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['brand_name']:
            representation['brand_name'] = representation['brand_name'].title()
        return representation


class ProductVendorMapSerializers(serializers.ModelSerializer):
    product_parent_product = ChildProductSerializers(read_only=True, many=True)

    class Meta:
        model = ParentProduct
        fields = ('product_parent_product',)

    def to_representation(self, data):
        result = super().to_representation(data)
        if result['product_parent_product'] is None:
            pass
        return result['product_parent_product']


class BrandExportAsCSVSerializers(serializers.ModelSerializer):
    brand_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = Brand
        fields = ('brand_id_list',)

    def validate(self, data):

        if len(data.get('brand_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one brand id must be selected '))

        for c_id in data.get('brand_id_list'):
            try:
                Brand.objects.get(id=c_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'brand not found for id {c_id}')

        return data

    def create(self, validated_data):
        meta = Brand._meta
        exclude_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        queryset = Brand.objects.filter(id__in=validated_data['brand_id_list'])
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response


class BrandListSerializers(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', 'brand_name',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['brand_name']:
            representation['brand_name'] = representation['brand_name'].title()
        return representation
