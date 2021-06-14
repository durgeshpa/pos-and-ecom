from django.db import transaction
from django.utils.text import slugify

from rest_framework import serializers
from categories.models import Category
from products.api.v1.serializers import UserSerializers
from categories.common_function import CategoryCls
from categories.common_validators import get_validate_category


class ParentCategorySerializers(serializers.ModelSerializer):
    class Meta:
        model = Category

        fields = ('id', 'category_name',)


class CategoryCrudSerializers(serializers.ModelSerializer):
    cat_parent = ParentCategorySerializers(many=True, read_only=True)
    category_slug = serializers.SlugField(required=False, allow_null=True, allow_blank=True)
    updated_by = UserSerializers(write_only=True, required=False)

    class Meta:
        model = Category
        prepopulated_fields = {'category_slug': ('category_name',)}
        fields = ('id', 'category_name', 'category_desc', 'cat_parent', 'category_slug',
                  'category_sku_part', 'category_image', 'updated_by', 'status',)

    def validate(self, data):
        """
            category_slug validation.
        """
        if not 'category_slug' in self.initial_data or not self.initial_data['category_slug']:
            data['category_slug'] = slugify(data.get('category_name'))

        if 'category_parent' in self.initial_data or self.initial_data['category_parent']:
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