from django.db import transaction
from django.utils.text import slugify

from rest_framework import serializers
from brand.models import Brand, BrandPosition, BrandData
from products.api.v1.serializers import UserSerializers, LogSerializers
from products.common_validators import get_validate_parent_brand
from brand.common_function import BrandCls


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

        fields = ('id', 'brand_name',)


class BrandCrudSerializers(serializers.ModelSerializer):
    brand_child = SubBrandSerializer(many=True, read_only=True)
    brand_parent = ParentBrandSerializers(read_only=True)
    brand_slug = serializers.SlugField(required=False, allow_null=True, allow_blank=True)
    updated_by = UserSerializers(write_only=True, required=False)
    brand_log = LogSerializers(many=True, read_only=True)

    class Meta:
        model = Brand
        fields = ('id', 'brand_name', 'brand_code', 'brand_parent', 'brand_description', 'updated_by', 'brand_slug',
                  'brand_logo', 'status', 'brand_child', 'brand_log')

    def validate(self, data):
        """
            category_slug validation.
        """
        if not 'category_slug' in self.initial_data or not self.initial_data['category_slug']:
            data['category_slug'] = slugify(data.get('category_name'))

        if 'brand_parent' in self.initial_data and self.initial_data['brand_parent'] is not None:
            brand_val = get_validate_parent_brand(self.initial_data['brand_parent'])
            if 'error' in brand_val:
                raise serializers.ValidationError(brand_val['error'])
            data['brand_parent'] = brand_val['parent_brand']

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            category = Brand.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return category

    @transaction.atomic
    def update(self, instance, validated_data):
        brand = super().update(instance, validated_data)
        BrandCls.create_brand_log(brand)

        return brand

