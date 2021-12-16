import csv
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse

from rest_framework import serializers
from categories.models import Category, CategoryPosation, CategoryData
from brand.models import Brand
from categories.models import Category
from products.api.v1.serializers import UserSerializers, LogSerializers
from categories.common_function import CategoryCls
from categories.common_validators import get_validate_category, validate_category_name, validate_category_sku_part, \
    validate_category_slug


class SubCategorySerializer(serializers.Serializer):

    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class CategorySerializer(serializers.ModelSerializer):
    category_product_log = LogSerializers(many=True, read_only=True)

    class Meta:
        model = Category
        ref_name = "Category v1"
        fields = ('id', 'category_name', 'category_desc', 'category_slug', 'category_sku_part', 'category_image',
                  'status', 'category_product_log')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['category_image']:
            representation['category_image_png'] = representation['category_image']
        return representation


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
    cat_parent = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'category_name', 'cat_parent', 'category_image', 'category_desc')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['category_image']:
            representation['category_image_png'] = representation['category_image']
        return representation


class SubCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ('id', 'category_name', 'category_desc', 'status', 'category_image')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['category_image']:
            representation['category_image_png'] = representation['category_image']
        return representation


class ParentCategorySerializers(serializers.ModelSerializer):
    class Meta:
        model = Category

        fields = ('id', 'category_name', 'category_image')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['category_image']:
            representation['category_image_png'] = representation['category_image']
        return representation


class SubCategorySerializers(serializers.ModelSerializer):

    class Meta:
        model = Category

        fields = ('id', 'category_name', 'category_name', 'category_desc', 'category_slug',
                  'category_sku_part', 'category_image', 'status',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['category_name']:
            representation['category_name'] = representation['category_name'].title()
        if representation['category_image']:
            representation['category_image_png'] = representation['category_image']
        return representation


class CategoryCrudSerializers(serializers.ModelSerializer):
    cat_parent = SubCategorySerializers(many=True, read_only=True)
    category_parent = ParentCategorySerializers(read_only=True)
    category_slug = serializers.SlugField(required=False, allow_null=True, allow_blank=True)
    updated_by = UserSerializers(write_only=True, required=False)
    category_log = LogSerializers(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'category_name', 'category_desc', 'category_slug', 'category_sku_part', 'category_image',
                  'updated_by', 'status', 'category_parent', 'category_log', 'cat_parent')

    def validate(self, data):
        """ category_slug validation."""
        if not 'category_slug' in self.initial_data or not self.initial_data['category_slug']:
            data['category_slug'] = slugify(data.get('category_name'))

        if 'category_parent' in self.initial_data and self.initial_data['category_parent'] is not None:
            cat_val = get_validate_category(self.initial_data['category_parent'])
            if 'error' in cat_val:
                raise serializers.ValidationError(cat_val['error'])
            data['category_parent'] = cat_val['category']

        cat_id = self.instance.id if self.instance else None
        if 'category_name' in self.initial_data and self.initial_data['category_name'] is not None:
            cat_obj = validate_category_name(self.initial_data['category_name'], cat_id)
            if cat_obj is not None and 'error' in cat_obj:
                raise serializers.ValidationError(cat_obj['error'])

        if 'category_sku_part' in self.initial_data and self.initial_data['category_sku_part'] is not None:
            cat_obj = validate_category_sku_part(self.initial_data['category_sku_part'], cat_id)
            if cat_obj is not None and 'error' in cat_obj:
                raise serializers.ValidationError(cat_obj['error'])

        if 'category_slug' in self.initial_data and self.initial_data['category_slug'] is not None:
            cat_obj = validate_category_slug(self.initial_data['category_slug'], cat_id)
            if cat_obj is not None and 'error' in cat_obj:
                raise serializers.ValidationError(cat_obj['error'])

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            category = Category.objects.create(**validated_data)
            CategoryCls.create_category_log(category, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return category

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            category = super().update(instance, validated_data)
            CategoryCls.create_category_log(category, "updated")
        except Exception as e:
            error = {'message': e.args[0] if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return category

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['category_name']:
            representation['category_name'] = representation['category_name'].title()
        return representation


class CategoryExportAsCSVSerializers(serializers.ModelSerializer):
    category_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = Category
        fields = ('category_id_list',)

    def validate(self, data):

        if len(data.get('category_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one category id must be selected '))

        for c_id in data.get('category_id_list'):
            try:
                Category.objects.get(id=c_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'category not found for id {c_id}')

        return data

    def create(self, validated_data):
        meta = Category._meta
        exclude_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        queryset = Category.objects.filter(id__in=validated_data['category_id_list'])
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response

