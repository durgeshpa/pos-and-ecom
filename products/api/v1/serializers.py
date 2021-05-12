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
    parent_product_pro_image = ParentProductImageSerializers(many=True)
    parent_product_pro_category = ParentProductCategorySerializers(many=True)
    parent_product_pro_tax = ParentProductTaxMappingSerializers(many=True)
    parent_brand_name = serializers.SerializerMethodField()
    product_hsn_code = serializers.SerializerMethodField()
    parent_id = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

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

        if len(self.initial_data.getlist('parent_product_pro_image')) == 0:
            raise serializers.ValidationError(_('parent_product_image is required'))

        if len(self.initial_data.getlist('parent_product_pro_category')) == 0:
            raise serializers.ValidationError(_('parent_product_category is required'))

        for image in self.initial_data.getlist('parent_product_pro_image'):
            if not valid_image_extension(image.name):
                raise serializers.ValidationError(_("Not a valid Image. "
                                                    "The URL must have an image extensions (.jpg/.jpeg/.png)"))

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

        return data

    class Meta:
        model = ParentProduct
        fields = ('id', 'parent_id',  'parent_brand', 'parent_brand_name', 'name', 'product_hsn', 'product_hsn_code', 'brand_case_size',
                  'inner_case_size', 'product_type', 'is_ptr_applicable', 'ptr_percent',
                  'ptr_type', 'status', 'parent_product_pro_image', 'parent_product_pro_category',
                  'parent_product_pro_tax')

    def clear_existing_parent_cat(self, parentproduct):
        for pro_image in parentproduct.parent_product_pro_image.all():
            pro_image.delete()

    def clear_existing_parent_tax(self, parentproduct):
        for pro_cat in parentproduct.parent_product_pro_category.all():
            pro_cat.delete()

    def clear_existing_images(self, parentproduct):
        for pro_tax in parentproduct.parent_product_pro_tax.all():
            pro_tax.delete()

    @transaction.atomic
    def create(self, validated_data):
        """create a new Parent Product with image category & tax"""

        validated_data.pop('parent_product_pro_image')
        validated_data.pop('parent_product_pro_category')
        validated_data.pop('parent_product_pro_tax')

        try:
            parentproduct = ParentProduct.objects.update_or_create(**validated_data)
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
        try:
            parentproduct = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.clear_existing_images(parentproduct)
        self.clear_existing_parent_cat(parentproduct)
        self.clear_existing_parent_tax(parentproduct)

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





