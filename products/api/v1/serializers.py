from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers
from products.models import Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, ParentProductImage
from categories.models import Category



VALID_IMAGE_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
]


def valid_image_extension(image, extension_list=VALID_IMAGE_EXTENSIONS):
    return any([image.endswith(e) for e in extension_list])


class ParentProductCategorySerializers(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = ParentProductCategory
        fields = ('id', 'parent_product', 'category', 'category_name')

    def get_category_name(self, obj):
        return obj.category.category_name


class ParentProductImageSerializers(serializers.ModelSerializer):
    image = serializers.ImageField(
        max_length=None, use_url=True,
    )

    class Meta:
        model = ParentProductImage
        fields = ('id', 'image_name', 'image',)


class ParentProductTaxMappingSerializers(serializers.ModelSerializer):
    tax_name = serializers.SerializerMethodField()
    tax_type = serializers.SerializerMethodField()
    tax_percentage = serializers.SerializerMethodField()

    class Meta:
        model = ParentProductTaxMapping
        fields = ('id', 'parent_product', 'tax', 'tax_name', 'tax_type', 'tax_percentage')

    def get_tax_name(self, obj):
        return obj.tax.tax_name

    def get_tax_type(self, obj):
        return obj.tax.tax_type

    def get_tax_percentage(self, obj):
        return obj.tax.tax_percentage


class ParentProductSerializers(serializers.ModelSerializer):
    parent_product_pro_image = ParentProductImageSerializers(many=True, required=False)
    parent_product_pro_category = ParentProductCategorySerializers(many=True, required=False)
    parent_product_pro_tax = ParentProductTaxMappingSerializers(many=True, required=False)
    parent_brand_name = serializers.SerializerMethodField()
    product_hsn_code = serializers.SerializerMethodField()
    parent_id = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    parent_image_id = serializers.ListField(required=False)
    parent_category_id = serializers.ListField(required=False)
    parent_tax_id = serializers.ListField(required=False)

    def clear_existing_images(self, instance):
        for post_image in instance.parent_product_pro_image.all():
            post_image.delete()

    def get_id(self, obj):
        return obj.id

    def get_parent_id(self, obj):
        return obj.parent_id

    def get_parent_brand_name(self, obj):
        return obj.parent_brand.brand_name

    def get_product_hsn_code(self, obj):
        return obj.product_hsn.product_hsn_code

    def validate(self, data):
        """
            is_ptr_applicable validation.
        """
        if data.get('is_ptr_applicable'):
            if not data.get('ptr_type'):
                raise serializers.ValidationError(_('Invalid PTR Type'))
            elif not data.get('ptr_percent'):
                raise serializers.ValidationError(_('Invalid PTR Percentage'))

        if self.initial_data.getlist('parent_product_pro_image'):
            for image in self.initial_data.getlist('parent_product_pro_image'):
                if not valid_image_extension(image.name):
                    raise serializers.ValidationError(_("Not a valid Image. "
                                                        "The URL must have an image extensions (.jpg/.jpeg/.png)"))

        if self.instance is None:
            if len(self.initial_data.getlist('parent_product_pro_image')) == 0:
                raise serializers.ValidationError(_('parent_product_image is required'))

            if len(self.initial_data.getlist('parent_product_pro_category')) == 0:
                raise serializers.ValidationError(_('parent_product_category is required'))

            cat_list = []
            for cat_data in self.initial_data['parent_product_pro_category']:
                try:
                    category = Category.objects.get(id=cat_data['category'])
                except ObjectDoesNotExist:
                    raise serializers.ValidationError('{} category not found'.format(cat_data['category']))
                if category in cat_list:
                    raise serializers.ValidationError(
                        '{} do not repeat same category for one product'.format(category))
                cat_list.append(category)

            if self.initial_data.getlist('parent_product_pro_tax'):
                tax_list_type = []
                for tax_data in self.initial_data['parent_product_pro_tax']:
                    try:
                        tax = Tax.objects.get(id=tax_data['tax'])
                    except ObjectDoesNotExist:
                        raise serializers.ValidationError('tax not found')

                    if tax.tax_type in tax_list_type:
                        raise serializers.ValidationError(
                            '{} type tax can be filled only once'.format(tax.tax_type))
                    tax_list_type.append(tax.tax_type)
                if 'gst' not in tax_list_type:
                    raise serializers.ValidationError('Please fill the GST tax value')

        if self.instance:
            with transaction.atomic():
                if self.initial_data.getlist('parent_product_pro_image'):
                    if self.initial_data['parent_image_id'] and self.initial_data['id']:
                        for img_data in self.initial_data['parent_image_id']:
                            image = ParentProductImage.objects.filter(id=img_data,
                                                                      parent_product_id=self.initial_data['id']).last()
                            if image is None:
                                raise serializers.ValidationError('please provide valid parent_image id')
                            image.delete()

                if self.initial_data['parent_product_pro_category']:
                    if self.initial_data['parent_category_id'] and self.initial_data['id']:
                        for cat_data in self.initial_data['parent_category_id']:
                            parent_cat = ParentProductCategory.objects.filter(id=cat_data,
                                                                              parent_product_id=self.initial_data[
                                                                                  'id']).last()
                            if parent_cat is None:
                                raise serializers.ValidationError('please provide valid parent_category id')
                            parent_cat.delete()
                        cat_list = []
                        mapped_cat = ParentProductCategory.objects.filter(parent_product=self.instance.id)
                        for cat in mapped_cat:
                            cat_list.append(cat.category.category_name)
                        for cat_data in self.initial_data['parent_product_pro_category']:
                            try:
                                category = Category.objects.get(id=cat_data['category'])
                            except ObjectDoesNotExist:
                                raise serializers.ValidationError('{} category not found'.format(cat_data['category']))
                            if category.category_name in cat_list:
                                raise serializers.ValidationError(
                                    '{} do not repeat same category for one product'.format(category))
                            cat_list.append(category.category_name)

                if self.initial_data.get('parent_product_pro_tax'):
                    if self.initial_data['parent_tax_id'] and self.initial_data['id']:
                        for tax in self.initial_data['parent_tax_id']:
                            parent_tax = ParentProductTaxMapping.objects.filter(id=tax,
                                                                                parent_product_id=self.initial_data['id']).last()
                            if parent_tax is None:
                                raise serializers.ValidationError('please provide valid parent_tax id')
                            parent_tax.delete()

                        tax_list_type = []
                        mapped_tax = ParentProductTaxMapping.objects.filter(parent_product=self.instance.id)
                        for tax in mapped_tax:
                            tax_list_type.append(tax.tax.tax_type)
                        for tax_data in self.initial_data['parent_product_pro_tax']:
                            try:
                                tax = Tax.objects.get(id=tax_data['tax'])
                            except ObjectDoesNotExist:
                                raise serializers.ValidationError('tax not found')

                            if tax.tax_type in tax_list_type:
                                raise serializers.ValidationError(
                                    '{} type tax can be filled only once'.format(tax.tax_type))
                            tax_list_type.append(tax.tax_type)
                        if 'gst' not in tax_list_type:
                            raise serializers.ValidationError('Please fill the GST tax value')
        return data

    class Meta:
        model = ParentProduct
        fields = ('id', 'parent_id',  'parent_brand', 'parent_brand_name', 'name', 'product_hsn', 'product_hsn_code', 'brand_case_size',
                  'inner_case_size', 'product_type', 'is_ptr_applicable', 'ptr_percent',
                  'ptr_type', 'status', 'parent_product_pro_image', 'parent_product_pro_category',
                  'parent_product_pro_tax', 'parent_image_id', 'parent_category_id', 'parent_tax_id')

    @transaction.atomic
    def create(self, validated_data):
        """create a new Parent Product with image category & tax"""

        validated_data.pop('parent_product_pro_image')
        validated_data.pop('parent_product_pro_category')
        validated_data.pop('parent_product_pro_tax')
        validated_data.pop('parent_image_id', None)
        validated_data.pop('parent_category_id', None)
        validated_data.pop('parent_tax_id', None)

        try:
            parentproduct = ParentProduct.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        for image_data in self.initial_data.getlist('parent_product_pro_image'):
            ParentProductImage.objects.create(image=image_data, image_name=image_data.name.rsplit(".", 1)[0],
                                              parent_product=parentproduct)
        for product_category in self.initial_data['parent_product_pro_category']:
            category = Category.objects.filter(id=product_category['category']).last()
            ParentProductCategory.objects.create(parent_product=parentproduct, category=category)
        for tax_data in self.initial_data['parent_product_pro_tax']:
            tax = Tax.objects.filter(id=tax_data['tax']).last()
            ParentProductTaxMapping.objects.create(parent_product=parentproduct, tax=tax)

        return parentproduct

    @transaction.atomic
    def update(self, instance, validated_data):
        """update a Parent Product with image category & tax using parent product id"""

        validated_data.pop('parent_product_pro_image', None)
        validated_data.pop('parent_product_pro_category', None)
        validated_data.pop('parent_product_pro_tax', None)
        validated_data.pop('parent_image_id', None)
        validated_data.pop('parent_category_id', None)
        validated_data.pop('parent_tax_id', None)

        if self.initial_data.getlist('parent_product_pro_image'):
            # self.clear_existing_images(instance)  # uncomment this if you want to clear existing images.
            for image_data in self.initial_data.getlist('parent_product_pro_image'):
                ParentProductImage.objects.create(image=image_data, image_name=image_data.name.rsplit(".", 1)[0],
                                                  parent_product=instance)
        for product_category in self.initial_data['parent_product_pro_category']:
            category = Category.objects.filter(id=product_category['category']).last()
            ParentProductCategory.objects.create(parent_product=instance, category=category)
        for tax_data in self.initial_data['parent_product_pro_tax']:
            tax = Tax.objects.filter(id=tax_data['tax']).last()
            ParentProductTaxMapping.objects.create(parent_product=instance, tax=tax)

        instance = super().update(instance, validated_data)
        instance.save()
        return instance



