import codecs
import csv
import re
import datetime

from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers
from products.models import Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory,\
    ParentProductImage, ProductHSN
from categories.models import Category
from brand.models import Brand


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
    """Handles creating, reading and updating parent product items."""
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

    def clear_existing_parent_cat(self, parent_product):
        for pro_image in parent_product.parent_product_pro_image.all():
            pro_image.delete()

    def clear_existing_parent_tax(self, parent_product):
        for pro_cat in parent_product.parent_product_pro_category.all():
            pro_cat.delete()

    def clear_existing_images(self, parent_product):
        for pro_tax in parent_product.parent_product_pro_tax.all():
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
            parent_product = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.clear_existing_images(parent_product)
        self.clear_existing_parent_cat(parent_product)
        self.clear_existing_parent_tax(parent_product)

        for image_data in self.initial_data.getlist('parent_product_pro_image'):
            ParentProductImage.objects.create(image=image_data, image_name=image_data.name.rsplit(".", 1)[0],
                                              parent_product=parent_product)

        for product_category in self.initial_data['parent_product_pro_category']:
            category = Category.objects.filter(id=product_category['category']).last()
            ParentProductCategory.objects.create(parent_product=parent_product, category=category)

        for tax_data in self.initial_data['parent_product_pro_tax']:
            tax = Tax.objects.filter(id=tax_data['tax']).last()
            ParentProductTaxMapping.objects.create(parent_product=parent_product, tax=tax)

        return parent_product


class ParentProductBulkUploadSerializers(serializers.ModelSerializer):
    file = serializers.FileField(label='Upload Parent Product list')

    class Meta:
        model = ParentProduct
        fields = ('file', )

    def validate(self, data):
        if not data['file'].name[-4:] in ('.csv'):
            raise serializers.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(data['file'], 'utf-8', errors='ignore'))
        next(reader)
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if '' in row:
                if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and
                        row[5] == '' and row[6] == '' and row[7] == '' and row[8] == '' and row[9] == ''):
                    continue
            if not row[0]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Parent Name' can not be empty."))
            elif not re.match("^[ \w\$\_\,\%\@\.\/\#\&\+\-\(\)\*\!\:]*$", row[0]):
                raise serializers.ValidationError(_(f"Row {row_id + 2} | {VALIDATION_ERROR_MESSAGES['INVALID_PRODUCT_NAME']}."))
            if not row[1]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Brand' can not be empty."))
            elif not Brand.objects.filter(brand_name=row[1].strip()).exists():
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Brand' doesn't exist in the system."))
            if not row[2]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Category' can not be empty."))
            else:
                if not Category.objects.filter(category_name=row[2].strip()).exists():
                    categories = row[2].split(',')
                    for cat in categories:
                        cat = cat.strip().replace("'", '')
                        if not Category.objects.filter(category_name=cat).exists():
                            raise serializers.ValidationError(
                                _(f"Row {row_id + 2} | 'Category' {cat.strip()} doesn't exist in the system."))
            if not row[3]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'HSN' can not be empty."))
            elif not ProductHSN.objects.filter(product_hsn_code=row[3].replace("'", '')).exists():
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'HSN' doesn't exist in the system."))
            if not row[4]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'GST' can not be empty."))
            elif not re.match("^([0]|[5]|[1][2]|[1][8]|[2][8])(\s+)?(%)?$", row[4]):
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'GST' can only be 0, 5, 12, 18, 28."))
            if row[5] and not re.match("^([0]|[1][2])(\s+)?%?$", row[5]):
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'CESS' can only be 0, 12."))
            if row[6] and not re.match("^[0-9]\d*(\.\d{1,2})?(\s+)?%?$", row[6]):
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Surcharge' can only be a numeric value."))
            if not row[7]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Brand Case Size' can not be empty."))
            elif not re.match("^\d+$", row[7]):
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Brand Case Size' can only be a numeric value."))
            if not row[8]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Inner Case Size' can not be empty."))
            elif not re.match("^\d+$", row[8]):
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Inner Case Size' can only be a numeric value."))
            if not row[9]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Product Type' can not be empty."))
            elif row[9].lower() not in ['b2b', 'b2c', 'both', 'both b2b and b2c']:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Product Type' can only be 'B2B', 'B2C', 'Both B2B and B2C'."))

        return data

    def create(self, validated_data):
        reader = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        next(reader)
        parent_product_list = []
        try:
            for row in reader:
                parent_product = ParentProduct.objects.create(
                    name=row[0].strip(),
                    parent_brand=Brand.objects.filter(brand_name=row[1].strip()).last(),
                    product_hsn=ProductHSN.objects.filter(product_hsn_code=row[3].replace("'", '')).last(),
                    brand_case_size=int(row[7]),
                    inner_case_size=int(row[8]),
                    product_type=row[9]
                )
                parent_product.save()

                parent_gst = int(row[4])
                ParentProductTaxMapping.objects.create(
                    parent_product=parent_product,
                    tax=Tax.objects.filter(tax_type='gst', tax_percentage=parent_gst).last()
                ).save()

                parent_cess = int(row[5]) if row[5] else 0
                ParentProductTaxMapping.objects.create(
                    parent_product=parent_product,
                    tax=Tax.objects.filter(tax_type='cess', tax_percentage=parent_cess).last()
                ).save()

                parent_surcharge = float(row[6]) if row[6] else 0
                if Tax.objects.filter(
                        tax_type='surcharge',
                        tax_percentage=parent_surcharge
                ).exists():
                    ParentProductTaxMapping.objects.create(
                        parent_product=parent_product,
                        tax=Tax.objects.filter(tax_type='surcharge', tax_percentage=parent_surcharge).last()
                    ).save()
                else:
                    new_surcharge_tax = Tax.objects.create(
                        tax_name='Surcharge - {}'.format(parent_surcharge),
                        tax_type='surcharge',
                        tax_percentage=parent_surcharge,
                        tax_start_at=datetime.datetime.now()
                    )
                    new_surcharge_tax.save()
                    ParentProductTaxMapping.objects.create(
                        parent_product=parent_product,
                        tax=new_surcharge_tax
                    ).save()
                if Category.objects.filter(category_name=row[2].strip()).exists():
                    parent_product_category = ParentProductCategory.objects.create(
                        parent_product=parent_product,
                        category=Category.objects.filter(category_name=row[2].strip()).last()
                    )
                    parent_product_category.save()
                else:
                    categories = row[2].split(',')
                    for cat in categories:
                        cat = cat.strip().replace("'", '')
                        parent_product_category = ParentProductCategory.objects.create(
                            parent_product=parent_product,
                            category=Category.objects.filter(category_name=cat).last()
                        )
                        parent_product_category.save()
                parent_product_list.append(parent_product)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return parent_product_list