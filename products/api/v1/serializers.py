import codecs
import csv
import re
import datetime

from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from rest_framework import serializers

from products.models import Product, ParentProductTaxMapping, ParentProduct, ParentProductCategory, ParentProductImage, \
    ProductHSN, ProductCapping, ProductVendorMapping, ProductImage, ProductPrice, ProductHSN, Tax, ProductSourceMapping, \
    ProductPackingMapping, DestinationRepackagingCostMapping, CentralLog, BulkUploadForProductAttributes
from categories.models import Category
from brand.models import Brand, Vendor
from shops.models import Shop
from products.common_validators import get_validate_parent_brand, get_validate_product_hsn, get_validate_parent_product, \
    get_validate_images, get_validate_categorys, get_validate_tax, is_ptr_applicable_validation, get_validate_product, \
    get_validate_seller_shop, check_active_capping, get_validate_packing_material, get_source_product, product_category, product_gst, \
    product_cess, product_surcharge, product_image, get_validate_vendor, get_validate_parent_product_image_ids, \
    get_validate_child_product_image_ids
from products.common_function import ParentProductCls, ProductCls
from accounts.models import User
from categories.common_validators import get_validate_category


class ProductSerializers(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name')


class GetParentProductSerializers(serializers.ModelSerializer):
    class Meta:
        model = ParentProduct
        fields = ('id', 'name')


class BrandSerializers(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', 'brand_name',)


class VendorSerializers(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ('id', 'vendor_name', 'mobile')


class ProductHSNSerializers(serializers.ModelSerializer):
    class Meta:
        model = ProductHSN
        fields = ('id', 'product_hsn_code')


class CategorySerializers(serializers.ModelSerializer):
    class Meta:
        model = Category

        fields = ('id', 'category_name',)


class ParentProductCategorySerializers(serializers.ModelSerializer):
    category = CategorySerializers(read_only=True)

    class Meta:
        model = ParentProductCategory
        fields = ('id', 'category',)


class ParentProductImageSerializers(serializers.ModelSerializer):
    image = serializers.ImageField(
        max_length=None, use_url=True,
    )

    class Meta:
        model = ParentProductImage
        fields = ('id', 'image_name', 'image',)


class ProductImageSerializers(serializers.ModelSerializer):
    image = serializers.ImageField(
        max_length=None, use_url=True,
    )

    class Meta:
        model = ProductImage
        fields = ('id', 'image_name', 'image',)


class TaxSerializers(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = ('id', 'tax_type', 'tax_percentage')


class ParentProductTaxMappingSerializers(serializers.ModelSerializer):
    tax = TaxSerializers(read_only=True)

    class Meta:
        model = ParentProductTaxMapping
        fields = ('id', 'tax')


class ChildProductVendorMappingSerializers(serializers.ModelSerializer):
    vendor = VendorSerializers(read_only=True)

    class Meta:
        model = ProductVendorMapping
        fields = ('id', 'vendor',)


class ChildProductVendorSerializers(serializers.ModelSerializer):
    product_vendor_mapping = ChildProductVendorMappingSerializers(many=True)

    class Meta:
        model = Product
        fields = ('id', 'product_name', 'product_vendor_mapping')


class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'phone_number',)


class LogSerializers(serializers.ModelSerializer):
    class Meta:
        model = CentralLog

        fields = ('update_at', 'updated_by',)


class ParentProductSerializers(serializers.ModelSerializer):
    """Handles creating, reading and updating parent product items."""
    parent_brand = BrandSerializers(read_only=True)
    parent_product_log = LogSerializers(many=True, read_only=True)
    product_hsn = ProductHSNSerializers(read_only=True)
    parent_product_pro_image = ParentProductImageSerializers(many=True, read_only=True)
    product_images = serializers.ListField(required=False, default=None, child=serializers.ImageField(),
                                           write_only=True)
    parent_product_pro_category = ParentProductCategorySerializers(many=True)
    parent_product_pro_tax = ParentProductTaxMappingSerializers(many=True)
    parent_id = serializers.CharField(read_only=True)
    product_parent_product = ChildProductVendorSerializers(many=True, required=False)
    max_inventory = serializers.IntegerField(allow_null=True, max_value=999)

    def validate(self, data):
        """
            is_ptr_applicable validation.
        """
        if not 'parent_product_pro_image' in self.initial_data or not self.initial_data['parent_product_pro_image']:
            if not 'product_images' in self.initial_data or not self.initial_data['product_images']:
                raise serializers.ValidationError(_('product_images is required'))

        if 'parent_product_pro_image' in self.initial_data and self.initial_data['parent_product_pro_image']:
            image_val = get_validate_parent_product_image_ids(self.initial_data['id'], self.initial_data['parent_product_pro_image'])
            if 'error' in image_val:
                raise serializers.ValidationError(_(image_val["error"]))

        if 'product_images' in self.initial_data and self.initial_data['product_images']:
            image_val = get_validate_images(self.initial_data['product_images'])
            if 'error' in image_val:
                raise serializers.ValidationError(_(image_val["error"]))

        if not 'parent_brand' in self.initial_data or not self.initial_data['parent_brand']:
            raise serializers.ValidationError(_('parent_brand is required'))

        if not 'product_hsn' in self.initial_data or not self.initial_data['product_hsn']:
            raise serializers.ValidationError(_('product_hsn is required'))

        if not 'parent_product_pro_category' in self.initial_data or not \
                self.initial_data['parent_product_pro_category']:
            raise serializers.ValidationError(_('parent_product_category is required'))

        if not 'parent_product_pro_tax' in self.initial_data or not self.initial_data['parent_product_pro_tax']:
            raise serializers.ValidationError(_('parent_product_pro_tax is required'))

        if data.get('is_ptr_applicable'):
            is_ptr_applicable = is_ptr_applicable_validation(data)
            if 'error' in is_ptr_applicable:
                raise serializers.ValidationError(is_ptr_applicable['error'])

        parent_brand_val = get_validate_parent_brand(self.initial_data['parent_brand'])
        if 'error' in parent_brand_val:
            raise serializers.ValidationError(parent_brand_val['error'])
        data['parent_brand'] = parent_brand_val['parent_brand']

        product_hsn_val = get_validate_product_hsn(self.initial_data['product_hsn'])
        if 'error' in product_hsn_val:
            raise serializers.ValidationError(_(f'{product_hsn_val["error"]}'))
        data['product_hsn'] = product_hsn_val['product_hsn']

        category_val = get_validate_categorys(self.initial_data['parent_product_pro_category'])
        if 'error' in category_val:
            raise serializers.ValidationError(_(category_val["error"]))

        tax_val = get_validate_tax(self.initial_data['parent_product_pro_tax'])
        if 'error' in tax_val:
            raise serializers.ValidationError(_(tax_val["error"]))

        return data

    class Meta:
        model = ParentProduct
        fields = ('id', 'parent_id', 'name', 'inner_case_size', 'product_type', 'status', 'product_hsn', 'parent_brand',
                  'parent_product_pro_tax', 'parent_product_pro_category', 'is_ptr_applicable', 'ptr_percent',
                  'ptr_type', 'is_ars_applicable', 'max_inventory', 'is_lead_time_applicable', 'product_images',
                  'parent_product_pro_image', 'product_parent_product', 'parent_product_log')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if not representation['is_ptr_applicable']:
            representation['ptr_type'] = representation['ptr_percent'] = '-'
        return representation

    @transaction.atomic
    def create(self, validated_data):
        """create a new Parent Product with image category & tax"""

        validated_data.pop('product_images', None)
        validated_data.pop('parent_product_pro_category', None)
        validated_data.pop('parent_product_pro_tax', None)
        validated_data.pop('product_parent_product', None)

        try:
            parent_product = ParentProduct.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.create_parent_tax_image_cat(parent_product)

        return parent_product

    @transaction.atomic
    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Parent Product's attribute. """

        validated_data.pop('parent_product_pro_image', None)
        validated_data.pop('product_images', None)
        validated_data.pop('parent_product_pro_category', None)
        validated_data.pop('parent_product_pro_tax', None)
        validated_data.pop('product_parent_product', None)

        try:
            # call super to save modified instance along with the validated data
            parent_product = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.create_parent_tax_image_cat(parent_product)
        ParentProductCls.create_parent_product_log(parent_product)
        return parent_product

    # crete parent product image, tax & category
    def create_parent_tax_image_cat(self, parent_product):
        parent_product_pro_image = None
        product_images = None

        if 'parent_product_pro_image' in self.initial_data and self.initial_data['parent_product_pro_image']:
            parent_product_pro_image = self.initial_data['parent_product_pro_image']
        if 'product_images' in self.initial_data and self.initial_data['product_images']:
            product_images = self.initial_data['product_images']

        ParentProductCls.upload_parent_product_images(parent_product, parent_product_pro_image, product_images)
        ParentProductCls.create_parent_product_category(parent_product,
                                                        self.initial_data['parent_product_pro_category'])
        ParentProductCls.create_parent_product_tax(parent_product, self.initial_data['parent_product_pro_tax'])


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
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = ParentProduct
        fields = ('parent_product_id_list',)

    def validate(self, data):

        if len(data.get('parent_product_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one parent_product id must be selected '))

        for p_id in data.get('parent_product_id_list'):
            try:
                ParentProduct.objects.get(id=p_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'parent_product not found for id {p_id}')

        return data

    def create(self, validated_data):
        meta = ParentProduct._meta
        field_names = [
            'parent_id', 'name', 'parent_brand', 'product_category', 'product_hsn', 'product_gst', 'product_cess',
            'product_surcharge', 'product_image', 'status', 'product_type', 'is_ptr_applicable', 'ptr_type',
            'ptr_percent', 'is_ars_applicable', 'is_lead_time_applicable', 'max_inventory'
        ]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        for p_id in validated_data['parent_product_id_list']:
            obj = ParentProduct.objects.filter(id=p_id).last()
            row = []
            for field in field_names:
                try:
                    val = getattr(obj, field)
                    if field == 'ptr_type':
                        val = getattr(obj, 'ptr_type_text')
                except:
                    val = eval("{}(obj)".format(field))
                finally:
                    row.append(val)
            writer.writerow(row)
        return response


class ActiveDeactiveSelectedParentProductSerializers(serializers.ModelSerializer):
    is_active = serializers.BooleanField(required=True)
    parent_product_id_list = serializers.ListField(
        child=serializers.IntegerField(min_value=1)
    )

    class Meta:
        model = ParentProduct
        fields = ('parent_product_id_list', 'is_active',)

    def validate(self, data):

        if data.get('is_active') is None:
            raise serializers.ValidationError('is_active field is required')

        if not 'parent_product_id_list' in data or not data['parent_product_id_list']:
            raise serializers.ValidationError(_('atleast one parent_product id must be selected '))

        for p_id in data.get('parent_product_id_list'):
            try:
                ParentProduct.objects.get(id=p_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'parent_product not found for id {p_id}')

        return data

    @transaction.atomic
    def update(self, instance, validated_data):

        if validated_data['is_active']:
            parent_product_status = True
            product_status = "active"
        else:
            parent_product_status = False
            product_status = "deactivated"

        try:
            parent_products = ParentProduct.objects.filter(id__in=validated_data['parent_product_id_list'])
            parent_products.update(status=parent_product_status, updated_by=validated_data['updated_by'],
                                   updated_at=timezone.now())
            for parent_product_obj in parent_products:
                Product.objects.filter(parent_product=parent_product_obj).update(status=product_status,
                                                                                 updated_by=validated_data[
                                                                                     'updated_by'],
                                                                                 updated_at=timezone.now())
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return validated_data


class ActiveDeactiveSelectedChildProductSerializers(serializers.ModelSerializer):
    is_active = serializers.BooleanField(required=True)
    child_product_id_list = serializers.ListField(
        child=serializers.IntegerField(min_value=1)
    )

    class Meta:
        model = Product
        fields = ('child_product_id_list', 'is_active',)

    def validate(self, data):

        if data.get('is_active') is None:
            raise serializers.ValidationError('is_active field is required')

        if not 'child_product_id_list' in data or not data['child_product_id_list']:
            raise serializers.ValidationError(_('atleast one child product id must be selected '))

        for p_id in data.get('child_product_id_list'):
            try:
                Product.objects.get(id=p_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'child product not found for id {p_id}')

        return data

    # @transaction.atomic
    def update(self, instance, validated_data):

        if validated_data['is_active']:
            parent_product_status = True
            product_status = "active"
            product_price_not_approved = ''

            try:
                child_products = Product.objects.filter(id__in=validated_data['child_product_id_list'])
                for child_product_obj in child_products:
                    parent_sku = ParentProduct.objects.filter(
                        parent_id=child_product_obj.parent_product.parent_id).last()

                    if not ProductPrice.objects.filter(approval_status=ProductPrice.APPROVED,
                                                       product_id=child_product_obj.id).exists():
                        product_price_not_approved += ' ' + str(child_product_obj.product_sku) + ','
                        continue

                    if not parent_sku.status:
                        parent_sku.status = parent_product_status
                        parent_sku.updated_by = validated_data['updated_by']
                        parent_sku.save()

                    child_product_obj.status = product_status
                    child_product_obj.updated_by = validated_data['updated_by']
                    child_product_obj.save()

                if product_price_not_approved != '':
                    not_approved = product_price_not_approved.strip(',')
                    raise serializers.ValidationError("Products" + not_approved + " were not be approved due to non "
                                                                                  "existent active Product Price")

            except Exception as e:
                error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
                raise serializers.ValidationError(error)
        else:
            product_status = "deactivated"
            try:
                child_products = Product.objects.filter(id__in=validated_data['child_product_id_list'])
                child_products.update(status=product_status, updated_by=validated_data['updated_by'],
                                      updated_at=timezone.now())
            except Exception as e:
                error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
                raise serializers.ValidationError(error)

        return validated_data


class ShopSerializers(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'shop_name',)


class ProductCappingSerializers(serializers.ModelSerializer):
    product = ChildProductVendorSerializers(read_only=True)
    seller_shop = ShopSerializers(read_only=True)

    class Meta:
        model = ProductCapping
        fields = ('id', 'product', 'seller_shop', 'capping_type', 'capping_qty', 'start_date', 'end_date', 'status')

    def validate(self, data):

        if self.initial_data['product'] is None:
            raise serializers.ValidationError('product is required')

        product_val = get_validate_product(self.initial_data['product'])
        if 'error' in product_val:
            raise serializers.ValidationError(product_val['error'])

        if self.initial_data['seller_shop'] is None:
            raise serializers.ValidationError('seller_shop is required')

        seller_shop_val = get_validate_seller_shop(self.initial_data['seller_shop'])
        if 'error' in seller_shop_val:
            raise serializers.ValidationError(seller_shop_val['error'])

        """ check capping is active for the selected sku and warehouse """
        active_capping = check_active_capping(self.initial_data['seller_shop'], self.initial_data['product'])
        if 'error' in active_capping:
            raise serializers.ValidationError(active_capping['error'])

        # check capping quantity is zero or not
        if data.get('capping_qty') == 0:
            raise serializers.ValidationError("Capping qty should be greater than 0.")

        self.capping_duration_check(data)

        return data

    def capping_duration_check(self, data):
        """ Capping Duration check according to capping type """

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
    def create(self, validated_data):
        """ create product capping """
        try:
            product_capping = ProductCls.create_product_capping(self.initial_data['product'],
                                                                self.initial_data['seller_shop'], **validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return product_capping

    @transaction.atomic
    def update(self, instance, validated_data):
        """update a Product Capping """
        try:
            product_capping = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return product_capping


class ProductVendorMappingSerializers(serializers.ModelSerializer):
    product = ChildProductVendorSerializers(read_only=True)
    vendor = VendorSerializers(read_only=True)

    def validate(self, data):
        if data.get('product_price') is None and data.get('product_price_pack') is None:
            raise serializers.ValidationError("please enter one Brand to Gram Price")

        if data.get('case_size') is None:
            raise serializers.ValidationError("please enter case_size")

        if self.initial_data['vendor'] is None:
            raise serializers.ValidationError("please select vendor")

        if self.initial_data['product'] is None:
            raise serializers.ValidationError("please select product")

        if not (data.get('product_price') is None or data.get('product_price_pack') is None):
            raise serializers.ValidationError("please enter only one Brand to Gram Price")

        product_val = get_validate_product(self.initial_data['product'])
        if 'error' in product_val:
            raise serializers.ValidationError(product_val['error'])

        vendor_val = get_validate_vendor(self.initial_data['vendor'])
        if 'error' in vendor_val:
            raise serializers.ValidationError(vendor_val['error'])

        return data

    class Meta:
        model = ProductVendorMapping
        fields = ('id', 'product_price', 'product_price_pack', 'product_mrp', 'case_size', 'status', 'vendor',
                  'product')

    @transaction.atomic
    def create(self, validated_data):
        """ create vendor product mapping """
        try:
            product_vendor_map = ProductCls.create_product_vendor_mapping(self.initial_data['product'],
                                                                          self.initial_data['vendor'], **validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return product_vendor_map

    @transaction.atomic
    def update(self, instance, validated_data):
        """update vendor product mapping """
        try:
            # call super to save modified instance along with the validated data
            product_vendor_map_obj = super().update(instance, validated_data)
            product_vendor_map = ProductCls.update_product_vendor_mapping(self.initial_data['product'],
                                                                          self.initial_data['vendor'],
                                                                          product_vendor_map_obj)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return product_vendor_map


class ProductSourceSerializers(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('product_name', 'product_sku')


class ProductSourceMappingSerializers(serializers.ModelSerializer):
    source_sku = ProductSourceSerializers(read_only=True)

    class Meta:
        model = ProductSourceMapping
        fields = ('id', 'source_sku',)


class ProductPackingMappingSerializers(serializers.ModelSerializer):
    packing_sku = ProductSourceSerializers(read_only=True)

    class Meta:
        model = ProductPackingMapping
        fields = ('id', 'packing_sku', 'packing_sku_weight_per_unit_sku',)


class DestinationRepackagingCostMappingSerializers(serializers.ModelSerializer):
    class Meta:
        model = DestinationRepackagingCostMapping
        fields = ('id', 'raw_material', 'wastage', 'fumigation', 'label_printing', 'packing_labour', 'primary_pm_cost',
                  'secondary_pm_cost')


class ChildProductSerializers(serializers.ModelSerializer):
    """ Handles creating, reading and updating child product items."""
    parent_product = ParentProductSerializers(read_only=True)
    child_product_logs = LogSerializers(many=True, read_only=True)
    product_vendor_mapping = ChildProductVendorMappingSerializers(many=True, required=False)
    product_sku = serializers.CharField(required=False)
    product_pro_image = ProductImageSerializers(many=True, read_only=True)
    product_images = serializers.ListField(required=False, default=None, child=serializers.ImageField(),
                                           write_only=True)
    destination_product_pro = ProductSourceMappingSerializers(many=True, required=False)
    packing_product_rt = ProductPackingMappingSerializers(many=True, required=False)
    destination_product_repackaging = DestinationRepackagingCostMappingSerializers(many=True, required=False)

    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'product_ean_code', 'status', 'product_mrp', 'weight_value',
                  'weight_unit', 'reason_for_child_sku', 'use_parent_image', 'product_special_cess', 'repackaging_type',
                  'product_pro_image', 'parent_product', 'destination_product_pro', 'destination_product_repackaging',
                  'packing_product_rt', 'product_vendor_mapping', 'product_images', 'child_product_logs')

    def validate(self, data):
        if not 'parent_product' in self.initial_data or self.initial_data['parent_product'] is None:
            raise serializers.ValidationError('parent_product is required')

        parent_product_val = get_validate_parent_product(self.initial_data['parent_product'])
        if 'error' in parent_product_val:
            raise serializers.ValidationError(parent_product_val['error'])

        if self.initial_data['use_parent_image']:
            if parent_product_val['parent_product'] and not parent_product_val['parent_product']. \
                    parent_product_pro_image.exists():
                raise serializers.ValidationError(
                    _(f"Parent Product Image Not Available. Please Upload Child Product Image(s)."))

        elif not 'product_images' in self.initial_data or not self.initial_data['product_images']:
            if not 'product_pro_image' in self.initial_data or not self.initial_data['product_pro_image']:
                if parent_product_val['parent_product'] and parent_product_val[
                    'parent_product'].parent_product_pro_image. \
                        exists():
                    data['use_parent_image'] = True
                else:
                    raise serializers.ValidationError(
                        _(f"Parent Product Image Not Available. Please Upload Child Product Image(s)."))

        if 'product_images' in self.initial_data:
            image_val = get_validate_images(self.initial_data['product_images'])
            if 'error' in image_val:
                raise serializers.ValidationError(_(image_val["error"]))

        if 'product_pro_image' in self.initial_data and self.initial_data['product_pro_image']:
            image_val = get_validate_child_product_image_ids(self.initial_data['id'],
                                                             self.initial_data['product_pro_image'])
            if 'error' in image_val:
                raise serializers.ValidationError(_(image_val["error"]))

        if 'status' in self.initial_data and self.initial_data['status'] == 'active':
            error = True
            if 'id' in self.initial_data and ProductPrice.objects.filter(approval_status=ProductPrice.APPROVED,
                                                                         product_id=self.initial_data['id']).exists():
                error = False
            if error:
                raise serializers.ValidationError("Product cannot be made active until an active Product Price exists")

        if self.initial_data['repackaging_type'] == 'destination':
            if not self.initial_data['destination_product_pro'] or not self.initial_data['packing_product_rt'] \
                    or not self.initial_data['destination_product_repackaging']:
                raise serializers.ValidationError(
                    _(f"Product Source Mapping, Package Material SKU & Destination Product Repackaging can not be empty."))

            destination_product = get_source_product(self.initial_data['destination_product_pro'])
            if 'error' in destination_product:
                raise serializers.ValidationError(_(destination_product["error"]))

            packing_product = get_validate_packing_material(self.initial_data['packing_product_rt'])
            if 'error' in packing_product:
                raise serializers.ValidationError(_(packing_product["error"]))

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new Child Product with image category & tax"""
        validated_data.pop('product_images', None)
        source_product = validated_data.pop('destination_product_pro', None)
        packing_material = validated_data.pop('packing_product_rt', None)
        destination_product_repack = validated_data.pop('destination_product_repackaging', None)
        try:
            child_product = ProductCls.create_child_product(self.initial_data['parent_product'], **validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        if 'product_images' in self.initial_data and self.initial_data['product_images']:
            product_pro_image = None
            ProductCls.upload_child_product_images(child_product, self.initial_data['product_images'],
                                                   product_pro_image)

        if child_product.repackaging_type == 'packing_material':
            ProductCls.update_weight_inventory(child_product)

        if child_product.repackaging_type == 'destination':
            self.create_source_packing_material_destination_product(child_product,
                                                                            destination_product_repack)

        return child_product

    @transaction.atomic
    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Child Product's attribute."""
        validated_data.pop('product_images', None)
        validated_data.pop('destination_product_pro', None)
        validated_data.pop('packing_product_rt', None)
        destination_product_repack = validated_data.pop('destination_product_repackaging', None)
        try:
            # call super to save modified instance along with the validated data
            child_product_obj = super().update(instance, validated_data)
            child_product = ProductCls.update_child_product(self.initial_data['parent_product'],
                                                            child_product_obj)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        if 'product_pro_image' in self.initial_data and 'product_images' in self.initial_data:
            product_images = None
            product_pro_image = None
            if 'product_pro_image' in self.initial_data:
                product_pro_image = self.initial_data['product_pro_image']
            if 'product_images' in self.initial_data:
                product_images = self.initial_data['product_images']
            ProductCls.upload_child_product_images(child_product, product_images, product_pro_image)

        if child_product.repackaging_type == 'packing_material':
            ProductCls.update_weight_inventory(child_product)

        if child_product.repackaging_type == 'destination':
            self.create_source_packing_material_destination_product(child_product,
                                                                    destination_product_repack)
        ProductCls.create_child_product_log(child_product)
        return child_product

    def create_source_packing_material_destination_product(self, child_product, destination_product_repack):
        ProductCls.create_source_product_mapping(child_product, self.initial_data['destination_product_pro'])
        ProductCls.packing_material_product_mapping(child_product, self.initial_data['packing_product_rt'])
        ProductCls.create_destination_product_mapping(child_product, destination_product_repack)


def only_int(value):
    if value.isdigit() is False:
        raise serializers.ValidationError('HSN can only be a numeric value.')


class ProductHSNSerializers(serializers.ModelSerializer):
    """ Handles Get & creating """
    product_hsn_code = serializers.CharField(max_length=8, min_length=6, validators=[only_int])

    class Meta:
        model = ProductHSN
        fields = ['id', 'product_hsn_code', ]


class ChildProductExportAsCSVSerializers(serializers.ModelSerializer):
    child_product_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = Product
        fields = ('child_product_id_list',)

    def validate(self, data):

        if len(data.get('child_product_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one child_product id must be selected '))

        for id in data.get('child_product_id_list'):
            try:
                Product.objects.get(id=id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'child_product not found for id {id}')

        return data

    def create(self, validated_data):
        meta = Product._meta
        exclude_fields = ['created_at', 'updated_at']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]
        field_names.extend(['is_ptr_applicable', 'ptr_type', 'ptr_percent'])

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        field_names_dest = field_names.copy()
        cost_params = ['raw_material', 'wastage', 'fumigation', 'label_printing', 'packing_labour',
                       'primary_pm_cost', 'secondary_pm_cost', 'final_fg_cost', 'conversion_cost']
        add_fields = ['product_brand', 'product_category', 'image', 'source skus', 'packing_sku',
                      'packing_sku_weight_per_unit_sku'] + cost_params

        for field_name in add_fields:
            field_names_dest.append(field_name)

        writer.writerow(field_names_dest)

        for id in validated_data['child_product_id_list']:
            obj = Product.objects.filter(id=id).last()
            items = [getattr(obj, field) for field in field_names]
            items.append(obj.product_brand)
            items.append(product_category(obj))

            if obj.use_parent_image and obj.parent_product.parent_product_pro_image.last():
                items.append(obj.parent_product.parent_product_pro_image.last().image.url)
            elif obj.product_pro_image.last():
                items.append(obj.product_pro_image.last().image.url)
            else:
                items.append('-')

            if obj.repackaging_type == 'destination':
                source_skus = [str(psm.source_sku) for psm in ProductSourceMapping.objects.filter(
                    destination_sku_id=obj.id, status=True)]
                items.append("\n".join(source_skus))
                packing_sku = ProductPackingMapping.objects.filter(sku_id=obj.id).last()
                items.append(str(packing_sku) if packing_sku else '-')
                items.append(str(packing_sku.packing_sku_weight_per_unit_sku) if packing_sku else '-')
                cost_obj = DestinationRepackagingCostMapping.objects.filter(destination_id=obj.id).last()
                for param in cost_params:
                    items.append(str(getattr(cost_obj, param)))
            writer.writerow(items)
        return response


class TaxCrudSerializers(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = ('id', 'tax_name', 'tax_type', 'tax_percentage', 'tax_start_at', 'tax_end_at')

    def validate(self, data):

        if len(data.get('child_product_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one child_product id must be selected '))

        for id in data.get('child_product_id_list'):
            try:
                Product.objects.get(id=id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'child_product not found for id {id}')

        return data


class UploadMasterDataAdminSerializers(serializers.ModelSerializer):
    file = serializers.FileField(label='Upload Master Data', required=True)
    select_an_option = serializers.IntegerField(required=True)

    class Meta:
        model = BulkUploadForProductAttributes
        fields = ('file', 'select_an_option',)

    def validate(self, data):
        if not data['file'].name[-5:] in '.xlsx':
            raise serializers.ValidationError(_('Sorry! Only excel(xlsx) file accepted.'))

        if 'category_id' in self.initial_data:
            category_val = get_validate_category(self.initial_data['category_id'])
            if 'error' in category_val:
                raise serializers.ValidationError(_(category_val["error"]))
            data['category_id'] = category_val['category']

        else:
            data['category_id'] = None

        # Checking, whether excel file is empty or not!
        excel_file_data = self.auto_id['Users']
        if excel_file_data:
            self.read_file(excel_file_data, self.data['select_an_option'], data['category_id'])
        else:
            raise serializers.ValidationError("Excel File cannot be empty.Please add some data to upload it!")

        return data

    def validate_row(self, uploaded_data_list, header_list, upload_master_data, category):
        """
        This method will check that Data uploaded by user is valid or not.
        """
        try:
            row_num = 1
            for row in uploaded_data_list:
                row_num += 1
                if 'sku_id' in header_list and 'sku_id' in row.keys():
                    if row['sku_id'] != '':
                        if not Product.objects.filter(product_sku=row['sku_id']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['sku_id']} | 'SKU ID' doesn't exist."))
                    product = Product.objects.filter(product_sku=row['sku_id'])
                    categry = Category.objects.values('category_name').filter(id=int(category))
                    if not Product.objects.filter(id=product[0].id,
                                                  parent_product__parent_product_pro_category__category__category_name__icontains=categry[0]['category_name']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | Please upload Products of Category "
                                                f"({categry[0]['category_name']}) that you have "
                                                f"selected in Dropdown Only! "))
                if 'sku_name' in header_list and 'sku_name' in row.keys():
                    if row['sku_name'] != '':
                        if not Product.objects.filter(product_name=row['sku_name']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['sku_name']} |"
                                                    f"'SKU Name' doesn't exist in the system."))
                if 'product_type' in header_list and 'product_type' in row.keys():
                    if row['product_type'] != '':
                        product_type_list = ['b2b', 'b2c', 'both']
                        if row['product_type'] not in product_type_list:
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['product_type']} | 'Product Type can either be 'b2b',"
                                  f"'b2c' or 'both'!"))
                if 'parent_id' in header_list and 'parent_id' in row.keys():
                    if row['parent_id'] != '':
                        if not ParentProduct.objects.filter(parent_id=row['parent_id']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['parent_id']} | 'Parent ID' doesn't exist."))
                    parent_product = ParentProduct.objects.filter(parent_id=row['parent_id'])
                    if 'sku_id' not in row.keys():
                        if not ParentProductCategory.objects.filter(category=int(category), parent_product=parent_product[0].id).exists():
                            categry = Category.objects.values('category_name').filter(id=int(category))
                            raise serializers.ValidationError(_(f"Row {row_num} | Please upload Products of Category "
                                                    f"({categry[0]['category_name']}) that you have "
                                                    f"selected in Dropdown Only! "))
                if 'parent_name' in header_list and 'parent_name' in row.keys():
                    if row['parent_name'] != '':
                        if not ParentProduct.objects.filter(name=row['parent_name']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['parent_name']} | 'Parent Name' doesn't "
                                                    f"exist."))
                if 'status' in header_list and 'status' in row.keys():
                    if row['status'] != '':
                        status_list = ['active', 'deactivated', 'pending_approval']
                        if row['status'] not in status_list:
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['status']} | 'Status can either be 'Active',"
                                  f"'Pending Approval' or 'Deactivated'!"))
                # if 'ean' in header_list and 'ean' in row.keys():
                #     if row['ean'] != '':
                #         if not re.match('^\d{13}$', str(row['ean'])):
                #             raise ValidationError(_(f"Row {row_num} | {row['ean']} | Please Provide valid EAN code."))
                if 'mrp' in header_list and 'mrp' in row.keys():
                    if row['mrp'] != '':
                        if not re.match("^\d+[.]?[\d]{0,2}$", str(row['mrp'])):
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | 'Product MRP' can only be a numeric value."))
                if 'weight_unit' in header_list and 'weight_unit' in row.keys():
                    if row['weight_unit'] != '':
                        if str(row['weight_unit']).lower() not in ['gm']:
                            raise serializers.ValidationError(_(f"Row {row_num} | 'Weight Unit' can only be 'gm'."))
                if 'weight_value' in header_list and 'weight_value' in row.keys():
                    if row['weight_value'] != '':
                        if not re.match("^\d+[.]?[\d]{0,2}$", str(row['weight_value'])):
                            raise serializers.ValidationError(_(f"Row {row_num} | 'Weight Value' can only be a numeric value."))
                if 'hsn' in header_list and 'hsn' in row.keys():
                    if row['hsn'] != '':
                        if not ProductHSN.objects.filter(
                                product_hsn_code=row['hsn']).exists() and not ProductHSN.objects.filter(
                                product_hsn_code='0' + str(row['hsn'])).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['hsn']} |'HSN' doesn't exist in the system."))
                if 'tax_1(gst)' in header_list and 'tax_1(gst)' in row.keys():
                    if row['tax_1(gst)'] != '':
                        if not Tax.objects.filter(tax_name=row['tax_1(gst)']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['tax_1(gst)']} | Invalid Tax(GST)!"))
                if 'tax_2(cess)' in header_list and 'tax_2(cess)' in row.keys():
                    if row['tax_2(cess)'] != '':
                        if not Tax.objects.filter(tax_name=row['tax_2(cess)']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['tax_2(cess)']} "
                                                    f"| Invalid Tax(CESS)!"))
                if 'tax_3(surcharge)' in header_list and 'tax_3(surcharge)' in row.keys():
                    if row['tax_3(surcharge)'] != '':
                        if not Tax.objects.filter(tax_name=row['tax_3(surcharge)']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['tax_3(surcharge)']} "
                                                    f"| Invalid Tax(Surcharge)!"))
                # if 'brand_case_size' in header_list and 'brand_case_size' in row.keys():
                #         if row['brand_case_size'] != '':
                #             if not re.match("^\d+$", str(row['brand_case_size'])):
                #                 raise ValidationError(
                #                     _(
                #                         f"Row {row_num} | {row['brand_case_size']} |'Brand Case Size' can only be a numeric value."))
                if 'inner_case_size' in header_list and 'inner_case_size' in row.keys():
                    if row['inner_case_size'] != '':
                        if not re.match("^\d+$", str(row['inner_case_size'])):
                            raise serializers.ValidationError(
                                _(
                                    f"Row {row_num} | {row['inner_case_size']} |'Inner Case Size' can only be a numeric value."))
                if 'brand_id' in header_list and 'brand_id' in row.keys():
                    if row['brand_id'] != '':
                        if not Brand.objects.filter(id=row['brand_id']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['brand_id']} | "
                                                    f"'Brand_ID' doesn't exist in the system "))
                if 'brand_name' in header_list and 'brand_name' in row.keys():
                    if row['brand_name'] != '':
                        if not Brand.objects.filter(brand_name=row['brand_name']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['brand_name']} | "
                                                    f"'Brand_Name' doesn't exist in the system "))
                if 'sub_brand_id' in header_list and 'sub_brand_id' in row.keys():
                    if row['sub_brand_id'] != '':
                        if not Brand.objects.filter(id=row['sub_brand_id']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['sub_brand_id']} | "
                                                    f"'Sub_Brand_ID' doesn't exist in the system "))
                if 'sub_brand_name' in header_list and 'sub_brand_id' in row.keys():
                    if row['sub_brand_name'] != '':
                        if not Brand.objects.filter(brand_name=row['sub_brand_name']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['sub_brand_name']} | "
                                                    f"'Sub_Brand_Name' doesn't exist in the system "))
                if 'category_id' in header_list and 'category_id' in row.keys():
                    if row['category_id'] != '':
                        if not Category.objects.filter(id=row['category_id']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['category_id']} | "
                                                    f"'Category_ID' doesn't exist in the system "))
                if 'category_name' in header_list and 'category_name' in row.keys():
                    if row['category_name'] != '':
                        if not Category.objects.filter(category_name=row['category_name']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['category_name']} | "
                                                    f"'Category_Name' doesn't exist in the system "))
                if 'sub_category_id' in header_list and 'sub_category_id' in row.keys():
                    if row['sub_category_id'] != '':
                        if not Category.objects.filter(id=row['sub_category_id']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['sub_category_id']} | "
                                                    f"'Sub_Category_ID' doesn't exist in the system "))
                if 'sub_category_name' in header_list and 'sub_category_name' in row.keys():
                    if row['sub_category_name'] != '':
                        if not Category.objects.filter(category_name=row['sub_category_name']).exists():
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['sub_category_name']} | "
                                                    f"'Sub_Category_Name' doesn't exist in the system "))
                if 'max_inventory_in_days' in header_list and 'max_inventory_in_days' in row.keys():
                    if row['max_inventory_in_days'] != '':
                        if not re.match("^\d+$", str(row['max_inventory_in_days'])) or  row['max_inventory_in_days'] < 1\
                                or row['max_inventory_in_days'] > 999:
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['max_inventory_in_days']} |'Max Inventory In Days' is invalid."))

                if 'is_ars_applicable' in header_list and 'is_ars_applicable' in row.keys():
                    if row['is_ars_applicable'] != '' :
                        if str(row['is_ars_applicable']).lower() not in ['yes', 'no']:
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['is_ars_applicable']} |"
                                                    f"'is_ars_applicable' can only be 'Yes' or 'No' "))
                if 'is_lead_time_applicable' in header_list and 'is_lead_time_applicable' in row.keys():
                    if row['is_lead_time_applicable'] != '':
                        if str(row['is_lead_time_applicable']).lower() not in ['yes', 'no']:
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['is_lead_time_applicable']} |"
                                                    f"'is_lead_time_applicable' can only be 'Yes' or 'No' "))
                if 'is_ptr_applicable' in header_list and 'is_ptr_applicable' in row.keys():
                    if row['is_ptr_applicable'] != '' and str(row['is_ptr_applicable']).lower() not in ['yes', 'no']:
                            raise serializers.ValidationError(_(f"Row {row_num} | {row['is_ptr_applicable']} | "
                                                    f"'is_ptr_applicable' can only be 'Yes' or 'No' "))
                    elif row['is_ptr_applicable'].lower()=='yes' and \
                        ('ptr_type' not in row.keys() or row['ptr_type'] == '' or row['ptr_type'].lower() not in ['mark up', 'mark down']):
                        raise serializers.ValidationError(_(f"Row {row_num} | "
                                                    f"'ptr_type' can either be 'Mark Up' or 'Mark Down' "))
                    elif row['is_ptr_applicable'].lower() == 'yes' \
                        and ('ptr_percent' not in row.keys() or row['ptr_percent'] == '' or 100 < row['ptr_percent'] or  row['ptr_percent'] < 0) :
                        raise serializers.ValidationError(_(f"Row {row_num} | "
                                                    f"'ptr_percent' is invalid"))

                if 'repackaging_type' in header_list and 'repackaging_type' in row.keys():
                    if row['repackaging_type'] != '':
                        if row['repackaging_type'] not in Product.REPACKAGING_TYPES:
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['repackaging_type']} | 'Repackaging Type can either be 'none',"
                                  f"'source', 'destination' or 'packing_material'!"))
                if 'repackaging_type' in header_list and 'repackaging_type' in row.keys():
                    if row['repackaging_type'] == 'destination':
                        mandatory_fields = ['raw_material', 'wastage', 'fumigation', 'label_printing',
                                            'packing_labour', 'primary_pm_cost', 'secondary_pm_cost', 'final_fg_cost',
                                            'conversion_cost']
                        if 'source_sku_id' not in row.keys():
                            raise serializers.ValidationError(_(f"Row {row_num} | 'Source_SKU_ID' can't be empty "
                                                    f"when repackaging_type is destination"))
                        if 'source_sku_id' in row.keys():
                            if row['source_sku_id'] == '':
                                raise serializers.ValidationError(_(f"Row {row_num} | 'Source_SKU_ID' can't be empty "
                                                        f"when repackaging_type is destination"))
                        if 'source_sku_name' not in row.keys():
                            raise serializers.ValidationError(_(f"Row {row_num} | 'Source_SKU_Name' can't be empty "
                                                    f"when repackaging_type is destination"))
                        if 'source_sku_name' in row.keys():
                            if row['source_sku_name'] == '':
                                raise serializers.ValidationError(_(f"Row {row_num} | 'Source_SKU_Name' can't be empty "
                                                        f"when repackaging_type is destination"))
                        for field in mandatory_fields:
                            if field not in header_list:
                                raise serializers.ValidationError(_(f"{mandatory_fields} are the essential headers and cannot be empty "
                                                        f"when repackaging_type is destination"))
                            if row[field]=='':
                                raise serializers.ValidationError(_(f"Row {row_num} | {row[field]} | {field} cannot be empty"
                                                        f"| {mandatory_fields} are the essential fields when "
                                                        f"repackaging_type is destination"))
                            if not re.match("^\d+[.]?[\d]{0,2}$", str(row[field])):
                                raise serializers.ValidationError(_(f"Row {row_num} | {row[field]} | "
                                                        f"{field} can only be a numeric or decimal value."))

                        if 'source_sku_id' in header_list and 'source_sku_id' in row.keys():
                            if row['source_sku_id'] != '':
                                p = re.compile('\'')
                                skuIDs = p.sub('\"', row['source_sku_id'])
                                SKU_IDS = json.loads(skuIDs)
                                for sk in SKU_IDS:
                                    if not Product.objects.filter(product_sku=sk).exists():
                                        raise serializers.ValidationError(
                                            _(f"Row {row_num} | {sk} | 'Source SKU ID' doesn't exist."))
                        if 'source_sku_name' in header_list and 'source_sku_name' in row.keys():
                            if row['source_sku_name'] != '':
                                q = re.compile('\'')
                                skuNames = q.sub('\"', row['source_sku_name'])
                                SKU_Names = json.loads(skuNames)
                                for sk in SKU_Names:
                                    if not Product.objects.filter(product_name=sk).exists():
                                        raise serializers.ValidationError(_(f"Row {row_num} | {sk} |"
                                                                f"'Source SKU Name' doesn't exist in the system."))

        except ValueError as e:
            raise serializers.ValidationError(_(f"Row {row_num} | ValueError : {e} | Please Enter valid Data"))
        except KeyError as e:
            raise serializers.ValidationError(_(f"Row {row_num} | KeyError : {e} | Something went wrong while"
                                    f" checking excel data from dictionary"))

    def check_mandatory_columns(self, uploaded_data_list, header_list, upload_master_data, category):
        """
        Mandatory Columns Check as per condition of  "upload_master_data"
        """
        if upload_master_data == 0:
            row_num = 1
            required_columns = ['sku_id', 'sku_name', 'parent_id', 'parent_name', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(_(f"{required_columns} are mandatory columns for 'Upload Master Data'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'sku_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_id' in row.keys():
                    if row['sku_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_name' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))
                if 'sku_name' in row.keys():
                    if row['sku_name'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))
                if 'parent_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'parent_id' in row.keys():
                    if row['parent_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'parent_name' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_Name' can't be empty"))
                if 'parent_name' in row.keys():
                    if row['parent_name'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_Name' can't be empty"))
                if 'status' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'! | "
                                            f"Status cannot be empty"))
                if 'status' in row.keys():
                    if row['sku_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))

        if upload_master_data == 1:
            row_num = 1
            required_columns = ['sku_id', 'sku_name', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(_(f"{required_columns} are mandatory columns for 'Set Inactive Status'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'status' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                                            'Status cannot be empty'))
                if 'status' in row.keys():
                    if row['sku_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))
                if 'sku_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_id' in row.keys():
                    if row['sku_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_name' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))
                if 'sku_name' in row.keys():
                    if row['sku_name'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))

        if upload_master_data == 2:
            row_num = 1
            required_columns = ['brand_id', 'brand_name']
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(
                        _(f"{required_columns} are mandatory columns for 'Sub Brand and Brand Mapping'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'brand_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Brand_ID can't be empty"))
                if 'brand_id' in row.keys():
                    if row['brand_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Brand_ID' can't be empty"))
                if 'brand_name' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Brand_Name' can't be empty"))
                if 'brand_name' in row.keys():
                    if row['brand_name'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Brand_Name' can't be empty"))
        if upload_master_data == 3:
            row_num = 1
            required_columns = ['category_id', 'category_name']
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(_(f"{required_columns} are mandatory columns"
                                            f" for 'Sub Category and Category Mapping'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'category_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Sub_Category_ID' can't be empty"))
                if 'category_id' in row.keys():
                    if row['category_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Category_ID' can't be empty"))
                if 'category_name' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Category_Name' can't be empty"))
                if 'category_name' in row.keys():
                    if row['category_name'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Category_Name' can't be empty"))
        if upload_master_data == 4:
            row_num = 1
            required_columns = ['sku_id', 'parent_id', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(_(f"{required_columns} are mandatory column for 'Child and Parent Mapping'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'sku_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_id' in row.keys():
                    if row['sku_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'parent_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'parent_id' in row.keys():
                    if row['parent_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'status' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Status can either be 'Active', 'Pending Approval' "
                                            f"or 'Deactivated'!" |
                                            'Status cannot be empty'))
                if 'status' in row.keys():
                    if row['sku_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))
        if upload_master_data == 5:
            required_columns = ['sku_id', 'sku_name', 'status']
            row_num = 1
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(_(f"{required_columns} are mandatory columns for 'Set Child Data'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'status' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Status can either be 'Active' or "
                                                        f"'Deactivated'!" | 'Status cannot be empty'))
                if 'status' in row.keys():
                    if row['sku_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))
                if 'sku_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_id' in row.keys():
                    if row['sku_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_name' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))
                if 'sku_name' in row.keys():
                    if row['sku_name'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))
        if upload_master_data == 6:
            row_num = 1
            required_columns = ['parent_id', 'parent_name', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(_(f"{required_columns} are mandatory columns for 'Set Parent Data'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'parent_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_ID' is a mandatory field"))
                if 'parent_id' in row.keys():
                    if row['parent_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'parent_name' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_Name' is a mandatory field"))
                if 'parent_name' in row.keys():
                    if row['parent_name'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_Name' can't be empty"))
                if 'status' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                                            'Status cannot be empty'))
                if 'status' in row.keys():
                    if row['status'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))

        self.validate_row(uploaded_data_list, header_list, upload_master_data, category)

    def check_headers(self, excel_file_headers, required_header_list):
        for head in excel_file_headers:
            if head in required_header_list:
                pass
            else:
                raise serializers.ValidationError(_(f"Invalid Header | {head} | Allowable headers for the upload "
                                                    f"are: {required_header_list}"))

    def read_file(self, excel_file, upload_master_data, category):
        """
        Template Validation (Checking, whether the excel file uploaded by user is correct or not!)
        """
        # Checking the headers of the excel file
        if upload_master_data == 0:
            required_header_list = ['sku_id', 'sku_name', 'parent_id', 'parent_name', 'ean', 'mrp', 'hsn',
                                    'weight_unit', 'weight_value', 'tax_1(gst)', 'tax_2(cess)', 'tax_3(surcharge)',
                                    'inner_case_size', 'brand_id', 'brand_name', 'sub_brand_id', 'sub_brand_name',
                                    'category_id', 'category_name', 'sub_category_id', 'sub_category_name', 'status',
                                    'repackaging_type', 'source_sku_id', 'source_sku_name', 'raw_material', 'wastage',
                                    'fumigation', 'label_printing', 'packing_labour', 'primary_pm_cost',
                                    'secondary_pm_cost', 'final_fg_cost', 'conversion_cost']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        if upload_master_data == 1:
            required_header_list = ['sku_id', 'sku_name', 'mrp', 'status']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        if upload_master_data == 2:
            required_header_list = ['brand_id', 'brand_name', 'sub_brand_id', 'sub_brand_name']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        if upload_master_data == 3:
            required_header_list = ['category_id', 'category_name', 'sub_category_id', 'sub_category_name']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        if upload_master_data == 4:
            required_header_list = ['sku_id', 'sku_name', 'parent_id', 'parent_name', 'status']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        if upload_master_data == 5:
            required_header_list = ['sku_id', 'sku_name', 'ean', 'mrp', 'weight_unit', 'weight_value',
                                    'status', 'repackaging_type', 'source_sku_id', 'source_sku_name',
                                    'raw_material', 'wastage', 'fumigation', 'label_printing', 'packing_labour',
                                    'primary_pm_cost', 'secondary_pm_cost', 'final_fg_cost', 'conversion_cost']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        if upload_master_data == 6:
            required_header_list = ['parent_id', 'parent_name', 'product_type', 'hsn', 'tax_1(gst)', 'tax_2(cess)',
                                    'tax_3(surcharge)', 'inner_case_size', 'brand_id', 'brand_name', 'sub_brand_id',
                                    'sub_brand_name', 'category_id', 'category_name', 'sub_category_id',
                                    'sub_category_name', 'status', 'is_ptr_applicable', 'ptr_type', 'ptr_percent',
                                    'is_ars_applicable', 'max_inventory_in_days', 'is_lead_time_applicable']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        headers = excel_file.pop(0)  # headers of the uploaded excel file
        excelFile_headers = [str(ele).lower() for ele in headers]  # Converting headers into lowercase

        # Checking, whether the user uploaded the data below the headings or not!
        if len(excel_file) > 0:
            uploaded_data_by_user_list = []
            excel_dict = {}
            count = 0
            for row in excel_file:
                for ele in row:
                    excel_dict[excelFile_headers[count]] = ele
                    count += 1
                uploaded_data_by_user_list.append(excel_dict)
                excel_dict = {}
                count = 0
            self.check_mandatory_columns(uploaded_data_by_user_list, excelFile_headers, upload_master_data, category)
        else:
            raise serializers.ValidationError("Please add some data below the headers to upload it!")

    def create(self, validated_data):

        return validated_data