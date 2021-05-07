from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import InMemoryUploadedFile

from rest_framework import serializers
from products.models import Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, ParentProductImage
from categories.models import Category


class ParentProductCategorySerializers(serializers.ModelSerializer):

    class Meta:
        model = ParentProductCategory
        fields = ('parent_product', 'category')


class ParentProductImageSerializers(serializers.ModelSerializer):
    image = serializers.ImageField(
        max_length=None, use_url=True,
    )

    class Meta:
        model = ParentProductImage
        fields = ('image_name', 'image')


class ParentProductTaxMappingSerializers(serializers.ModelSerializer):

    class Meta:
        model = ParentProductTaxMapping
        fields = ('parent_product', 'tax')


class ParentProductSerializers(serializers.ModelSerializer):
    parent_product_pro_image = ParentProductImageSerializers(many=True, required=True)
    parent_product_pro_category = ParentProductCategorySerializers(many=True, required=True)
    parent_product_pro_tax = ParentProductTaxMappingSerializers(many=True, required=True)

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

        for image in self.initial_data.getlist('parent_product_pro_image'):
            if not isinstance(image, InMemoryUploadedFile):
                raise serializers.ValidationError(_('parent_product_image should be image'))

        if len(self.initial_data.getlist('parent_product_pro_category')) == 0:
            raise serializers.ValidationError(_('parent_product_category is required'))

        if len(self.initial_data.getlist('parent_product_pro_tax')):
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
        fields = ('parent_brand', 'name', 'product_hsn', 'brand_case_size',
                  'inner_case_size', 'product_type', 'is_ptr_applicable', 'ptr_percent',
                  'ptr_type', 'status', 'parent_product_pro_image', 'parent_product_pro_category',
                  'parent_product_pro_tax')


    @transaction.atomic
    def create(self, validated_data):
        """create a new Parent Product with image category & tax"""

        validated_data.pop('parent_product_pro_image')
        validated_data.pop('parent_product_pro_category')
        validated_data.pop('parent_product_pro_tax')
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



