import codecs
import csv
import re
import datetime
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from django.http import HttpResponse
from rest_framework import serializers
from products.models import Product, Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, \
    ParentProductImage, ProductHSN, ProductCapping, ProductVendorMapping
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
        fields = ('id', 'parent_id', 'parent_brand', 'parent_brand_name', 'name', 'product_hsn', 'product_hsn_code',
                  'brand_case_size',
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
        fields = ('file',)

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
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
                raise serializers.ValidationError(
                    _(f"Row {row_id + 2} | {VALIDATION_ERROR_MESSAGES['INVALID_PRODUCT_NAME']}."))
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
                raise serializers.ValidationError(
                    _(f"Row {row_id + 2} | 'Brand Case Size' can only be a numeric value."))
            if not row[8]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Inner Case Size' can not be empty."))
            elif not re.match("^\d+$", row[8]):
                raise serializers.ValidationError(
                    _(f"Row {row_id + 2} | 'Inner Case Size' can only be a numeric value."))
            if not row[9]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Product Type' can not be empty."))
            elif row[9].lower() not in ['b2b', 'b2c', 'both', 'both b2b and b2c']:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Product Type' can only be 'B2B', 'B2C', "
                                                    f"'Both B2B and B2C'."))

        return data

    def create(self, validated_data):
        reader = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        next(reader)
        parent_product_list = []
        try:
            for row in reader:
                if len(row) == 0:
                    continue
                if '' in row:
                    if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and
                            row[5] == '' and row[6] == '' and row[7] == '' and row[8] == '' and row[9] == ''):
                        continue
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


class ParentProductExportAsCSVSerializers(serializers.ModelSerializer):
    parent_product_id_list = serializers.ListField(
        child=serializers.IntegerField()
    )

    class Meta:
        model = ParentProduct
        fields = ('parent_product_id_list',)

    def validate(self, data):

        if len(data.get('parent_product_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one parent_product id must be selected '))

        for id in data.get('parent_product_id_list'):
            try:
                ParentProduct.objects.get(id=id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'parent_product not found for id {id}')

        return data

    def product_gst(self, obj):
        if ParentProductTaxMapping.objects.filter(parent_product=obj, tax__tax_type='gst').exists():
            return "{} %".format(ParentProductTaxMapping.objects.filter(parent_product=obj,
                                                                        tax__tax_type='gst').last().tax.tax_percentage)
        return ''

    def product_cess(self, obj):
        if ParentProductTaxMapping.objects.filter(parent_product=obj, tax__tax_type='cess').exists():
            return "{} %".format(ParentProductTaxMapping.objects.filter(parent_product=obj,
                                                                        tax__tax_type='cess').last().tax.tax_percentage)
        return ''

    def product_surcharge(self, obj):
        if ParentProductTaxMapping.objects.filter(parent_product=obj, tax__tax_type='surcharge').exists():
            return "{} %".format(ParentProductTaxMapping.objects.filter(parent_product=obj,
                                                                        tax__tax_type='surcharge').last().tax.tax_percentage)
        return ''

    def product_category(self, obj):
        try:
            if obj.parent_product_pro_category.exists():
                cats = [str(c.category) for c in obj.parent_product_pro_category.filter(status=True)]
                return "\n".join(cats)
            return ''
        except:
            return ''

    def product_image(self, obj):
        if obj.parent_product_pro_image.exists():
            return "{}".format(obj.parent_product_pro_image.last().image.url)
        else:
            return '-'

    def create(self, validated_data):
        meta = ParentProduct._meta
        field_names = [
            'parent_id', 'name', 'parent_brand', 'product_category', 'product_hsn',
            'product_gst', 'product_cess', 'product_surcharge', 'product_image', 'status',
            'product_type', 'is_ptr_applicable', 'ptr_type', 'ptr_percent'
        ]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        for id in validated_data['parent_product_id_list']:
            obj = ParentProduct.objects.filter(id=id).last()
            row = []
            for field in field_names:
                try:
                    val = getattr(obj, field)
                    if field == 'ptr_type':
                        val = getattr(obj, 'ptr_type_text')
                except:
                    val = eval("self.{}(obj)".format(field))
                finally:
                    row.append(val)
            writer.writerow(row)
        return response


class ActiveDeactivateSelectedProductSerializers(serializers.ModelSerializer):
    is_active = serializers.BooleanField()
    parent_product_id_list = serializers.ListField(
        child=serializers.IntegerField()
    )

    class Meta:
        model = ParentProduct
        fields = ('parent_product_id_list', 'is_active',)

    def validate(self, data):

        if data.get('is_active') is None:
            raise serializers.ValidationError('This field is required')

        if len(data.get('parent_product_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one parent_product id must be selected '))

        for id in data.get('parent_product_id_list'):
            try:
                ParentProduct.objects.get(id=id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'parent_product not found for id {id}')

        return data

    def update(self, instance, validated_data):

        if validated_data['is_active']:
            parent_product_status = True
            product_status = "active"
        else:
            parent_product_status = False
            product_status = "deactivated"

        try:
            parent_products = ParentProduct.objects.filter(id__in=validated_data['parent_product_id_list'])
            parent_products.update(status=parent_product_status)
            for parent_product_obj in parent_products:
                Product.objects.filter(parent_product=parent_product_obj).update(status=product_status)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return validated_data


class ProductCappingSerializers(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    product_sku = serializers.SerializerMethodField()
    seller_shop_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductCapping
        fields = ('id', 'product', 'product_name', 'product_sku', 'seller_shop', 'seller_shop_name', 'capping_type',
                  'capping_qty', 'start_date', 'end_date', 'status')

    def get_product_name(self, obj):
        return obj.product.product_name

    def get_product_sku(self, obj):
        return obj.product.product_sku

    def get_seller_shop_name(self, obj):
        return obj.seller_shop.shop_name

    def validate(self, data):

        if not self.instance:
            if data.get('seller_shop') is None:
                raise serializers.ValidationError('seller_shop is required')

            """ check capping is active for the selected sku and warehouse """
            if ProductCapping.objects.filter(seller_shop=data.get('seller_shop'),
                                             product=data.get('product'),
                                             status=True).exists():
                raise serializers.ValidationError(
                    "Another Capping is Active for the selected SKU or selected Warehouse.")

            if data.get('capping_type') is None:
                raise serializers.ValidationError('Please select the Capping Type.')

            if data.get('start_date') is None:
                raise serializers.ValidationError('start_date is required')

            if data.get('end_date') is None:
                raise serializers.ValidationError('end_date is required')

            if data.get('start_date') > data.get('end_date'):
                raise serializers.ValidationError("Start Date should be less than End Date.")

            if data.get('capping_qty') is None:
                raise serializers.ValidationError('capping_qty is required')

        if self.instance:
            if data.get('end_date'):
                if self.instance.start_date > data.get('end_date'):
                    raise serializers.ValidationError("End Date should be greater than Start Date.")

        # check capping quantity is zero or not
        if data.get('capping_qty') == 0:
            raise serializers.ValidationError("Capping qty should be greater than 0.")

        self.capping_duration_check(data)

        return data

    def capping_duration_check(self, data):
        """ Capping Duration check according to capping type """
        if self.instance:
            # if capping type is Daily, & check this condition for Weekly & Monthly as Well
            day_difference = data.get('end_date').date() - self.instance.start_date.date()
            if day_difference.days == 0:
                raise serializers.ValidationError("Please enter valid Start Date and End Date.")

            # if capping type is Weekly
            if self.instance.capping_type == 1:
                if not day_difference.days % 7 == 0:
                    raise serializers.ValidationError("Please enter valid End Date.")

            # if capping type is Monthly
            elif self.instance.capping_type == 2:
                if not day_difference.days % 30 == 0:
                    raise serializers.ValidationError("Please enter valid End Date.")
        else:
            # if capping type is Daily, & check this condition for Weekly & Monthly as Well
            day_difference = data.get('end_date').date() - data.get('start_date').date()
            if day_difference.days == 0:
                raise serializers.ValidationError("Please enter valid Start Date and End Date.")

            # if capping type is Weekly
            if data.get('capping_type') == 1:
                if not day_difference.days % 7 == 0:
                    raise serializers.ValidationError("Please enter valid Start Date and End Date.")

            # if capping type is Monthly
            elif data.get('capping_type') == 2:
                if not day_difference.days % 30 == 0:
                    raise serializers.ValidationError("Please enter valid Start Date and End Date.")

    @transaction.atomic
    def update(self, instance, validated_data):
        """update a Product Capping """
        try:
            # non editable fields
            validated_data.pop('product', None)
            validated_data.pop('seller_shop', None)
            validated_data.pop('capping_type', None)
            validated_data.pop('start_date', None)
            product_capping = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return product_capping


class ProductVendorMappingSerializers(serializers.ModelSerializer):
    class Meta:
        model = ProductVendorMapping
        fields = ('vendor', 'product', 'product_price', 'product_price_pack',
                  'product_mrp', 'case_size', 'status')
