from django.db import transaction
from django.utils.text import slugify

from rest_framework import serializers
from categories.models import Category,CategoryPosation,CategoryData
from brand.models import Brand
from categories.models import Category
from products.models import CentralLog
from products.api.v1.serializers import UserSerializers, LogSerializers
from categories.common_function import CategoryCls
from categories.common_validators import get_validate_category


class SubCategorySerializer(serializers.Serializer):

    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class CategorySerializer(serializers.ModelSerializer):
    category_product_log = LogSerializers(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'category_name', 'category_desc', 'category_slug', 'category_sku_part', 'category_image',
                  'status', 'category_product_log')


class CategoryPosSerializer(serializers.ModelSerializer):

    class Meta:
        model = CategoryPosation
        fields = '__all__'


class CategoryDataSerializer(serializers.ModelSerializer):
    category_pos = CategoryPosSerializer()
    category_data = CategorySerializer()

    class Meta:
        model = CategoryData
        fields = ('id', 'category_pos', 'category_data', 'category_data_order')


class BrandSerializer(serializers.ModelSerializer):

    class Meta:
        model = Brand
        fields = '__all__'


class AllCategorySerializer(serializers.ModelSerializer):
    sub_category = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'category_name', 'sub_category', 'category_image', 'category_desc')


class SubbCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ('id', 'category_name', 'category_desc', 'status')


class ParentCategorySerializers(serializers.ModelSerializer):
    class Meta:
        model = Category

        fields = ('id', 'category_name',)


class SubCategorySerializers(serializers.ModelSerializer):

    class Meta:
        model = Category

        fields = ('id', 'category_name', 'category_name', 'category_desc', 'category_slug',
                  'category_sku_part', 'category_image', 'status',)


class CategoryCrudSerializers(serializers.ModelSerializer):
    sub_category = SubCategorySerializers(many=True, read_only=True)
    category_parent = ParentCategorySerializers(read_only=True)
    category_slug = serializers.SlugField(required=False, allow_null=True, allow_blank=True)
    updated_by = UserSerializers(write_only=True, required=False)
    category_product_log = LogSerializers(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'category_name', 'category_desc', 'category_slug', 'category_sku_part', 'category_image',
                  'updated_by', 'status', 'category_parent', 'category_product_log', 'sub_category')

    def validate(self, data):
        """
            category_slug validation.
        """
        if not 'category_slug' in self.initial_data or not self.initial_data['category_slug']:
            data['category_slug'] = slugify(data.get('category_name'))

        if 'category_parent' in self.initial_data and self.initial_data['category_parent'] is not None:
            cat_val = get_validate_category(self.initial_data['category_parent'])
            if 'error' in cat_val:
                raise serializers.ValidationError(cat_val['error'])
            data['category_parent'] = cat_val['category']

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            category = Category.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return category

    @transaction.atomic
    def update(self, instance, validated_data):
        category = super().update(instance, validated_data)
        CategoryCls.create_category_log(category)

        return category


