import codecs
import csv
import logging
import re

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from rest_framework import serializers

from products.models import Product, ParentProductTaxMapping, ParentProduct, ParentProductCategory, \
    ParentProductB2cCategory, ParentProductImage, \
    ProductTaxMapping, ProductCapping, ProductVendorMapping, \
    ProductImage, ProductPrice, ProductHSN, Tax, \
    ProductSourceMapping, ProductPackingMapping, DestinationRepackagingCostMapping, \
    Weight, CentralLog, PriceSlab, ProductHsnCess, ProductHsnGst, GST_CHOICE, SuperStoreProductPrice, \
    SuperStoreProductPriceLog
from categories.models import Category, B2cCategory
from addresses.models import Pincode, City
from brand.models import Brand, Vendor
from products.utils import send_mail_on_product_tax_declined
from shops.models import Shop
from accounts.models import User

from products.common_validators import get_validate_parent_brand, get_validate_product_hsn, get_validate_parent_product, \
    get_validate_images, get_validate_categories, get_validate_tax, is_ptr_applicable_validation, get_validate_product, \
    get_validate_seller_shop, check_active_capping, get_validate_packing_material, get_source_product, product_category, \
    product_gst, product_cess, product_surcharge, product_image, get_validate_vendor, get_validate_buyer_shop, \
    get_validate_parent_product_image_ids, get_validate_child_product_image_ids, validate_parent_product_name, \
    validate_child_product_name, validate_tax_name, get_validate_slab_price, b2b_category, b2c_category, \
    get_validate_hsn_gsts, get_validate_gsts_mandatory_fields, get_validate_hsn_cess, \
    get_validate_cess_mandatory_fields, \
    read_product_hsn_file, read_super_store_product_price_file, validate_superstore_product, validate_retailer_price_exist
from products.common_function import ParentProductCls, ProductCls, ProductHSNCommonFunction, \
    SuperStoreProductPriceCommonFunction
from shops.common_validators import get_validate_city_id, get_validate_pin_code

info_logger = logging.getLogger('file-info')


class ChoiceField(serializers.ChoiceField):

    def to_representation(self, obj):
        if obj == '' and self.allow_blank:
            return obj
        return {'id': obj, 'value': self._choices[obj]}


class ProductSerializers(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'product_mrp',)


class GetParentProductSerializers(serializers.ModelSerializer):
    class Meta:
        model = ParentProduct
        fields = ('id', 'name')


class CategorySerializers(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField('get_category_parent_category_name')

    def get_category_parent_category_name(self, obj):
        full_path = [obj.category_name]
        parent_category_obj = obj.category_parent

        while parent_category_obj is not None:
            full_path.append(parent_category_obj.category_name)
            parent_category_obj = parent_category_obj.category_parent

        return ' -> '.join(full_path[::-1])

    class Meta:
        model = Category
        fields = ('id', 'category_name',)


class B2cCategorySerializers(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField('get_category_parent_category_name')

    def get_category_parent_category_name(self, obj):
        full_path = [obj.category_name]
        parent_category_obj = obj.category_parent

        while parent_category_obj is not None:
            full_path.append(parent_category_obj.category_name)
            parent_category_obj = parent_category_obj.category_parent

        return ' -> '.join(full_path[::-1])

    class Meta:
        model = B2cCategory
        fields = ('id', 'category_name',)


class BrandSerializers(serializers.ModelSerializer):
    brand_name = serializers.SerializerMethodField('get_brand_parent_brand_name')

    def get_brand_parent_brand_name(self, obj):
        full_path = [obj.brand_name]
        brand_obj = obj.brand_parent

        while brand_obj is not None:
            full_path.append(brand_obj.brand_name)
            brand_obj = brand_obj.brand_parent

        return ' -> '.join(full_path[::-1])

    class Meta:
        model = Brand
        fields = ('id', 'brand_name',)


class VendorSerializers(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ('id', 'vendor_name', 'mobile')


def only_int(value):
    if value.isdigit() is False:
        raise serializers.ValidationError('HSN can only be a numeric value.')


class ProductHSNSerializers(serializers.ModelSerializer):
    """ Handles Get & creating """

    class Meta:
        model = ProductHSN
        fields = ('id', 'product_hsn_code')


class ParentProductCategorySerializers(serializers.ModelSerializer):
    category = CategorySerializers(read_only=True)

    class Meta:
        model = ParentProductCategory
        fields = ('id', 'category',)


class ParentProductB2cCategorySerializers(serializers.ModelSerializer):
    category = B2cCategorySerializers(read_only=True)

    class Meta:
        model = ParentProductB2cCategory
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


class ProductTaxMappingSerializers(serializers.ModelSerializer):
    tax = TaxSerializers(read_only=True)

    class Meta:
        model = ProductTaxMapping
        fields = ('id', 'tax')


class ChildProductVendorMappingSerializers(serializers.ModelSerializer):
    vendor = VendorSerializers(read_only=True)

    class Meta:
        model = ProductVendorMapping
        fields = ('id', 'vendor',)


class ChildProductVendorSerializers(serializers.ModelSerializer):
    product_pro_image = ProductImageSerializers(many=True, read_only=True)
    product_vendor_mapping = ChildProductVendorMappingSerializers(many=True)

    class Meta:
        model = Product
        fields = ('id', 'product_name', 'product_sku', 'repackaging_type', 'status', 'product_pro_image',
                  'product_vendor_mapping')


class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        ref_name = "UserSerializers v1"
        fields = ('id', 'first_name', 'last_name', 'phone_number',)


class LogSerializers(serializers.ModelSerializer):
    updated_by = UserSerializers(read_only=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['update_at'] = instance.update_at.strftime("%b %d %Y %I:%M%p")
        return representation

    class Meta:
        model = CentralLog
        fields = ('update_at', 'updated_by')


class ParentProductSerializers(serializers.ModelSerializer):
    """Handles creating, reading and updating parent product items."""
    parent_brand = BrandSerializers(read_only=True)
    parent_product_log = LogSerializers(many=True, read_only=True)
    product_hsn = ProductHSNSerializers(read_only=True)
    parent_product_pro_image = ParentProductImageSerializers(many=True, read_only=True)
    parent_product_pro_category = ParentProductCategorySerializers(many=True, read_only=True)
    parent_product_pro_b2c_category = ParentProductB2cCategorySerializers(many=True, read_only=True)
    parent_product_pro_tax = ParentProductTaxMappingSerializers(many=True, read_only=True)
    product_parent_product = ChildProductVendorSerializers(many=True, required=False, read_only=True)
    parent_id = serializers.CharField(read_only=True)
    product_type = serializers.CharField(read_only=True)
    description = serializers.SerializerMethodField()
    max_inventory = serializers.IntegerField(allow_null=True, max_value=999)
    product_images = serializers.ListField(required=False, default=None, child=serializers.ImageField(),
                                           write_only=True)

    def validate(self, data):
        """
            is_ptr_applicable validation.
        """
        if self.initial_data.get('product_type') == '':
            raise serializers.ValidationError(_('Product type is required'))

        if not 'parent_product_pro_image' in self.initial_data or not self.initial_data['parent_product_pro_image']:
            if not 'product_images' in self.initial_data or not self.initial_data['product_images']:
                raise serializers.ValidationError(_('product image is required'))

        if 'parent_product_pro_image' in self.initial_data and self.initial_data['parent_product_pro_image']:
            image_val = get_validate_parent_product_image_ids(self.initial_data['id'],
                                                              self.initial_data['parent_product_pro_image'])
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

        # if self.initial_data.get('product_type') == 'b2c' and \
        #         (not 'parent_product_pro_b2c_category' in self.initial_data or not \
        #         self.initial_data['parent_product_pro_b2c_category']):
        #     raise serializers.ValidationError(_('parent product b2c category is required'))
        # elif self.initial_data.get('product_type') == 'b2b' and \
        #         (not 'parent_product_pro_category' in self.initial_data or not \
        #         self.initial_data['parent_product_pro_category']):
        #     raise serializers.ValidationError(_('parent product category is required'))
        if not 'parent_product_pro_category' in self.initial_data or not self.initial_data['parent_product_pro_category']:
            raise serializers.ValidationError(_('parent product category is required'))

        if self.initial_data.get('product_type') == 'grocery':
            if not 'parent_product_pro_b2c_category' in self.initial_data or not self.initial_data['parent_product_pro_b2c_category']:
                raise serializers.ValidationError(_('parent product b2c category is required'))


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
        b2b_category_val = None
        b2c_category_val = None
        if 'parent_product_pro_category' in self.initial_data and self.initial_data['parent_product_pro_category']:
            b2b_category_val = get_validate_categories(self.initial_data['parent_product_pro_category'])
            if 'error' in b2b_category_val:
                raise serializers.ValidationError(_(b2b_category_val["error"]))
        if self.initial_data.get('product_type') == 'grocery':
            if 'parent_product_pro_b2c_category' in self.initial_data and \
                    self.initial_data['parent_product_pro_b2c_category']:
                b2c_category_val = get_validate_categories(self.initial_data['parent_product_pro_b2c_category'], True)
                if 'error' in b2c_category_val:
                    raise serializers.ValidationError(_(b2c_category_val["error"]))
        tax_val = get_validate_tax(self.initial_data['parent_product_pro_tax'])
        if 'error' in tax_val:
            raise serializers.ValidationError(_(tax_val["error"]))

        parent_pro_id = self.instance.id if self.instance else None
        if 'name' in self.initial_data and self.initial_data['name'] is not None:
            pro_obj = validate_parent_product_name(self.initial_data['name'], parent_pro_id)
            if pro_obj is not None and 'error' in pro_obj:
                raise serializers.ValidationError(pro_obj['error'])
        data["product_type"] = self.initial_data.get('product_type')
        data["product_discription"] = self.initial_data.get("description")

        return data

    class Meta:
        model = ParentProduct
        fields = ('id', 'parent_id', 'name', 'inner_case_size', 'brand_case_size', 'status', 'product_type', 'description',
                  'product_hsn', 'parent_brand', 'parent_product_pro_tax', 'parent_product_pro_category',
                  'parent_product_pro_b2c_category', 'is_ptr_applicable', 'ptr_percent', 'ptr_type',
                  'is_ars_applicable', 'max_inventory', 'is_lead_time_applicable', 'discounted_life_percent',
                  'product_images', 'parent_product_pro_image', 'product_parent_product', 'parent_product_log',
                  'tax_status', 'tax_remark', 'is_kvi')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if not representation['is_ptr_applicable']:
            representation['ptr_type'] = representation['ptr_percent'] = None
        if representation['name']:
            representation['name'] = representation['name'].title()
        return representation

    def get_description(self, obj):
        return obj.product_discription

    @transaction.atomic
    def create(self, validated_data):
        """create a new Parent Product with image category & tax"""

        validated_data.pop('product_images', None)
        validated_data.pop('parent_product_pro_category', None)
        validated_data.pop('parent_product_pro_b2c_category', None)
        validated_data.pop('parent_product_pro_tax', None)
        validated_data.pop('product_parent_product', None)

        try:
            parent_product = ParentProduct.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.create_parent_tax_image_cat(parent_product)
        ParentProductCls.update_tax_status_and_remark(parent_product)
        ParentProductCls.create_parent_product_log(parent_product, "created")

        return parent_product

    @transaction.atomic
    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Parent Product's attribute. """
        validated_data.pop('parent_product_pro_image', None)
        validated_data.pop('product_images', None)
        validated_data.pop('parent_product_pro_category', None)
        validated_data.pop('preant_product_pro_b2c_category', None)
        validated_data.pop('parent_product_pro_tax', None)
        validated_data.pop('product_parent_product', None)

        try:
            # call super to save modified instance along with the validated data
            parent_product = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.create_parent_tax_image_cat(parent_product)
        ParentProductCls.update_tax_status_and_remark(parent_product)
        ParentProductCls.create_parent_product_log(parent_product, "updated")

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
        if 'parent_product_pro_category' in self.initial_data and self.initial_data['parent_product_pro_category']:
            ParentProductCls.create_parent_product_category(parent_product,
                                                            self.initial_data['parent_product_pro_category'])
        if 'parent_product_pro_b2c_category' in self.initial_data and \
                self.initial_data['parent_product_pro_b2c_category']:
            ParentProductCls.create_parent_product_b2c_category(parent_product,
                                                                self.initial_data['parent_product_pro_b2c_category'])
        ParentProductCls.create_parent_product_tax(parent_product, self.initial_data['parent_product_pro_tax'])


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
            'parent_id', 'name', 'parent_brand', 'b2b_category', 'b2c_category', 'product_hsn', 'product_gst', 'product_cess',
            'product_surcharge', 'inner_case_size', 'product_image', 'status', 'product_type', 'is_ptr_applicable',
            'ptr_type',
            'ptr_percent', 'is_ars_applicable', 'is_lead_time_applicable', 'max_inventory', 'is_kvi'
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


class ProductSourceSerializers(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'product_name', 'product_sku')


class ProductSourceMappingSerializers(serializers.ModelSerializer):
    source_sku = ProductSourceSerializers(read_only=True)

    class Meta:
        model = ProductSourceMapping
        fields = ('source_sku',)


class ProductPackingMappingSerializers(serializers.ModelSerializer):
    packing_sku = ProductSourceSerializers(read_only=True)

    class Meta:
        model = ProductPackingMapping
        fields = ('packing_sku', 'packing_sku_weight_per_unit_sku',)


class DestinationRepackagingCostMappingSerializers(serializers.ModelSerializer):
    class Meta:
        model = DestinationRepackagingCostMapping
        fields = ('raw_material', 'wastage', 'fumigation', 'label_printing', 'packing_labour', 'primary_pm_cost',
                  'secondary_pm_cost')


class SuperStorePriceSerializers(serializers.ModelSerializer):
    class Meta:
        model = SuperStoreProductPrice
        fields = ('id', 'product', 'seller_shop', 'selling_price',)


class ChildProductSerializers(serializers.ModelSerializer):
    """ Handles creating, reading and updating child product items."""
    parent_product = ParentProductSerializers(read_only=True)
    product_pro_tax = ProductTaxMappingSerializers(many=True, read_only=True)
    child_product_log = LogSerializers(many=True, read_only=True)
    # super_store_product_price = SuperStorePriceSerializers(many=True, read_only=True)
    super_store_product_price = serializers.SerializerMethodField()
    product_vendor_mapping = ChildProductVendorMappingSerializers(many=True, required=False)
    product_sku = serializers.CharField(required=False)
    product_pro_image = serializers.SerializerMethodField()
    product_images = serializers.ListField(required=False, default=None, child=serializers.ImageField(),
                                           write_only=True)
    destination_product_pro = ProductSourceMappingSerializers(many=True, required=False)
    packing_product_rt = ProductPackingMappingSerializers(many=True, required=False)
    destination_product_repackaging = DestinationRepackagingCostMappingSerializers(many=True,
                                                                                   required=False)
    off_percentage = serializers.SerializerMethodField()
    parent_product_discription = serializers.SerializerMethodField()

    class Meta:
        model = Product
        ref_name = "ChildProduct v1"
        fields = ('id', 'product_sku', 'product_name', 'product_ean_code', 'status', 'product_mrp', 'weight_value',
                  'weight_unit', 'reason_for_child_sku', 'use_parent_image', 'product_special_cess', 'product_type',
                  'is_manual_price_update', 'repackaging_type', 'product_pro_image', 'parent_product', 'super_store_product_price',
                  'product_pro_tax', 'destination_product_pro', 'product_images', 'destination_product_repackaging',
                  'packing_product_rt', 'product_vendor_mapping', 'child_product_log','parent_product_discription',
                  'off_percentage')

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

            if self.initial_data['packing_product_rt']:
                mandatory_fields = ['packing_sku', 'packing_sku_weight_per_unit_sku']
                for field in mandatory_fields:
                    if field not in self.initial_data['packing_product_rt'][0]:
                        raise serializers.ValidationError(f"{mandatory_fields} are mandatory fields")
            packing_product = get_validate_packing_material(self.initial_data['packing_product_rt'])
            if 'error' in packing_product:
                raise serializers.ValidationError(_(packing_product["error"]))

        child_pro_id = self.instance.id if self.instance else None
        if 'product_name' in self.initial_data and self.initial_data['product_name'] is not None:
            pro_obj = validate_child_product_name(self.initial_data['product_name'], child_pro_id)
            if pro_obj is not None and 'error' in pro_obj:
                raise serializers.ValidationError(pro_obj['error'])

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new Child Product with image category & tax"""
        validated_data.pop('product_images', None)
        validated_data.pop('destination_product_pro', None)
        validated_data.pop('packing_product_rt', None)
        destination_product_repack = validated_data.pop('destination_product_repackaging', None)

        try:
            child_product = ProductCls.create_child_product(self.initial_data['parent_product'], **validated_data)
            ProductCls.create_child_product_log(child_product, "created")
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
            ProductCls.create_child_product_log(child_product, "updated")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        if 'product_pro_image' in self.initial_data or 'product_images' in self.initial_data:
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

        return child_product

    def get_super_store_product_price(self, instance):
        parent_shop_id = self.context.get('parent_shop_id')
        if parent_shop_id:
            return SuperStorePriceSerializers(instance.super_store_product_price.filter(seller_shop_id=parent_shop_id), many=True).data
        else:
            return None
    
    def get_off_percentage(self,obj):
        parent_shop_id = self.context.get('parent_shop_id')
        price = obj.get_superstore_price_by_shop(parent_shop_id) if parent_shop_id else None
        return round(100-((price.selling_price*100)/obj.product_mrp)) if price else None

    def get_parent_product_discription(self, obj):
        """Return Parent product discription ...."""
        if obj:
            return obj.parent_product.product_discription

    def create_source_packing_material_destination_product(self, child_product, destination_product_repack):
        ProductCls.create_source_product_mapping(child_product, self.initial_data['destination_product_pro'])
        ProductCls.packing_material_product_mapping(child_product, self.initial_data['packing_product_rt'])
        ProductCls.create_destination_product_mapping(child_product, destination_product_repack)

    def get_product_pro_image(self, instance):
        if instance.use_parent_image and not instance.product_pro_image.filter(status=True).exists():
            return ParentProductImageSerializers(instance.parent_product.parent_product_pro_image.all(), many=True).data
        else:
            return ProductImageSerializers(instance.product_pro_image.filter(status=True), many=True).data
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['product_name']:
            representation['product_name'] = representation['product_name'].title()
        return representation


class ChildProductExportAsCSVSerializers(serializers.ModelSerializer):
    child_product_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )
    product_type = serializers.IntegerField(required=True)

    class Meta:
        model = Product
        fields = ('child_product_id_list', 'product_type')

    def validate(self, data):

        if self.initial_data['product_type'] not in [0, 1]:
            raise serializers.ValidationError("incorrect product_type")

        if len(data.get('child_product_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one child_product id must be selected '))

        for id in data.get('child_product_id_list'):
            try:
                Product.objects.get(id=id, product_type=data.get('product_type'))
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'child_product not found for id {id}')

        return data

    def create(self, validated_data):
        meta = Product._meta
        exclude_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]
        field_names.extend(['is_ptr_applicable', 'ptr_type', 'ptr_percent'])

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        field_names_dest = field_names.copy()
        cost_params = ['raw_material', 'wastage', 'fumigation', 'label_printing', 'packing_labour',
                       'primary_pm_cost', 'secondary_pm_cost', 'final_fg_cost', 'conversion_cost']
        add_fields = ['product_brand',  'b2b_category', 'b2c_category', 'image', 'source skus', 'packing_sku',
                      'packing_sku_weight_per_unit_sku'] + cost_params

        for field_name in add_fields:
            field_names_dest.append(field_name)

        writer.writerow(field_names_dest)

        for id in validated_data['child_product_id_list']:
            obj = Product.objects.filter(id=id).last()
            items = [getattr(obj, field) for field in field_names]
            items.append(obj.product_brand)
            items.append(b2b_category(obj.parent_product))
            items.append(b2c_category(obj.parent_product))

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
                if cost_obj:
                    for param in cost_params:
                        items.append(str(getattr(cost_obj, param)))
            writer.writerow(items)
        return response


class ProductHSNGstSerializers(serializers.ModelSerializer):
    gst = ChoiceField(choices=GST_CHOICE, required=False)

    class Meta:
        model = ProductHsnGst
        fields = ('id', 'gst')


class ProductHSNCessSerializers(serializers.ModelSerializer):

    class Meta:
        model = ProductHsnCess
        fields = ('id', 'cess')


class ProductHSNCrudSerializers(serializers.ModelSerializer):
    """ Handles Get & creating """
    product_hsn_code = serializers.CharField(max_length=8, min_length=6, validators=[only_int])
    hsn_gst = ProductHSNGstSerializers(many=True, read_only=True)
    hsn_cess = ProductHSNCessSerializers(many=True, read_only=True)
    hsn_log = LogSerializers(many=True, read_only=True)

    class Meta:
        model = ProductHSN
        fields = ('id', 'product_hsn_code', 'hsn_gst', 'hsn_cess', 'hsn_log')

    def validate(self, data):
        hsn_id = self.instance.id if self.instance else None
        if 'product_hsn_code' in self.initial_data and data['product_hsn_code']:
            if ProductHSN.objects.filter(product_hsn_code__iexact=data['product_hsn_code'], status=True) \
                    .exclude(id=hsn_id).exists():
                raise serializers.ValidationError("hsn code already exists.")
            if not re.match("^\d+$", str(self.initial_data['product_hsn_code'])):
                raise serializers.ValidationError(f"{self.initial_data['product_hsn_code']} "
                                                  f"'Product HSN Code' can only be a numeric value.")
            if len(self.initial_data['product_hsn_code']) < 6:
                raise serializers.ValidationError(f"'Product HSN Code' must be of minimum 6 digits.")

        if 'hsn_gst' in self.initial_data:
            if self.instance:
                hsn_gsts = get_validate_hsn_gsts(self.initial_data['hsn_gst'], self.instance)
            else:
                hsn_gsts = get_validate_gsts_mandatory_fields(self.initial_data['hsn_gst'])
            if 'error' in hsn_gsts:
                raise serializers.ValidationError(hsn_gsts['error'])
            data['gsts'] = hsn_gsts['data']['gsts']
            data['gst_update_ids'] = hsn_gsts['data'].get('gst_update_ids', [])

        if 'hsn_cess' in self.initial_data and self.initial_data['hsn_cess']:
            if self.instance:
                hsn_cess = get_validate_hsn_cess(self.initial_data['hsn_cess'], self.instance)
            else:
                hsn_cess = get_validate_cess_mandatory_fields(self.initial_data['hsn_cess'])
            if 'error' in hsn_cess:
                raise serializers.ValidationError(hsn_cess['error'])
            data['cess'] = hsn_cess['data']['cess']
            data['cess_update_ids'] = hsn_cess['data'].get('cess_update_ids', [])

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new HSN"""
        gsts = validated_data.pop("gsts", [])
        gst_update_ids = validated_data.pop("gst_update_ids", [])
        cess = validated_data.pop("cess", [])
        cess_update_ids = validated_data.pop("cess_update_ids", [])
        try:
            hsn = ProductHSN.objects.create(**validated_data)
            ProductCls.create_hsn_log(hsn, "created")
            self.post_product_hsn_save(gsts, gst_update_ids, cess, cess_update_ids, hsn)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return hsn

    @transaction.atomic
    def update(self, instance, validated_data):
        """update hsn"""
        gsts = validated_data.pop("gsts", [])
        gst_update_ids = validated_data.pop("gst_update_ids", [])
        cess = validated_data.pop("cess", [])
        cess_update_ids = validated_data.pop("cess_update_ids", [])
        try:
            instance = super().update(instance, validated_data)
            ProductCls.create_hsn_log(instance, "updated")
            self.post_product_hsn_save(gsts, gst_update_ids, cess, cess_update_ids, instance)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return instance

    def post_product_hsn_save(self, gsts, gst_update_ids, cess, cess_update_ids, product_hsn_instance):
        self.remove_non_exist_product_hsn_gsts(gst_update_ids, product_hsn_instance)
        if gsts:
            self.create_update_product_hsn_gsts(gsts, product_hsn_instance)
        self.remove_non_exist_product_hsn_cess(cess_update_ids, product_hsn_instance)
        if cess:
            self.create_update_product_hsn_cess(cess, product_hsn_instance)

    def remove_non_exist_product_hsn_gsts(self, gst_ids, product_hsn_instance):
        gsts_to_be_deleted = ProductHsnGst.objects.filter(
            ~Q(id__in=gst_ids), product_hsn=product_hsn_instance)
        gsts_to_be_deleted.delete()

    def create_update_product_hsn_gsts(self, data_list, product_hsn_instance):
        for data in data_list:
            if 'id' in data and data['id']:
                ProductHsnGst.objects.filter(id=data['id'], product_hsn=product_hsn_instance).update(gst=data['gst'])
            else:
                ProductHsnGst.objects.create(
                    product_hsn=product_hsn_instance, gst=data['gst'], created_by=self.context['request'].user)

    def remove_non_exist_product_hsn_cess(self, cess_ids, product_hsn_instance):
        cess_to_be_deleted = ProductHsnCess.objects.filter(
            ~Q(id__in=cess_ids), product_hsn=product_hsn_instance)
        cess_to_be_deleted.delete()

    def create_update_product_hsn_cess(self, data_list, product_hsn_instance):
        for data in data_list:
            if 'id' in data and data['id']:
                ProductHsnCess.objects.filter(id=data['id'], product_hsn=product_hsn_instance).update(cess=data['cess'])
            else:
                ProductHsnCess.objects.create(
                    product_hsn=product_hsn_instance, cess=data['cess'], created_by=self.context['request'].user)


class TaxCrudSerializers(serializers.ModelSerializer):
    tax_log = LogSerializers(many=True, read_only=True)

    class Meta:
        model = Tax
        fields = ('id', 'tax_name', 'tax_type', 'tax_percentage', 'tax_start_at',
                  'tax_end_at', 'tax_log', 'status')

    def validate(self, data):
        if 'tax_start_at' in self.initial_data and 'tax_end_at' in self.initial_data:
            if data['tax_start_at'] and data['tax_end_at']:
                if data['tax_end_at'] < data['tax_start_at']:
                    raise serializers.ValidationError("End date should be greater than start date.")

        tax_id = self.instance.id if self.instance else None
        if 'tax_name' in self.initial_data and self.initial_data['tax_name'] is not None:
            tax_obj = validate_tax_name(self.initial_data['tax_name'], tax_id)
            if tax_obj is not None and 'error' in tax_obj:
                raise serializers.ValidationError(tax_obj['error'])
        if 'tax_type' in self.initial_data and 'tax_percentage' in self.initial_data:
            if data['tax_type'] and data['tax_percentage'] and \
                    Tax.objects.filter(tax_type=data['tax_type'], tax_percentage=data['tax_percentage']).exclude(
                        id=tax_id).exists():
                raise serializers.ValidationError("tax with this tax type & tax percentage already exists .")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new tax"""
        try:
            tax = Tax.objects.create(**validated_data)
            ProductCls.create_tax_log(tax, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return tax

    def update(self, instance, validated_data):
        """update tax"""
        instance = super().update(instance, validated_data)
        ProductCls.create_tax_log(instance, "updated")
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # if instance.tax_start_at:
        #     representation['tax_start_at'] = instance.tax_start_at.strftime("%b %d %Y %I:%M%p")
        # if instance.tax_end_at:
        #     representation['tax_end_at'] = instance.tax_end_at.strftime("%b %d %Y %I:%M%p")
        if representation['tax_name']:
            representation['tax_name'] = representation['tax_name'].title()
        return representation


class WeightSerializers(serializers.ModelSerializer):
    weight_log = LogSerializers(many=True, read_only=True)

    class Meta:
        model = Weight
        fields = ('id', 'weight_name', 'weight_value', 'weight_unit', 'status', 'weight_log')

    @transaction.atomic
    def create(self, validated_data):
        """create a new weight"""
        try:
            weight = Weight.objects.create(**validated_data)
            ProductCls.create_weight_log(weight, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return weight

    @transaction.atomic
    def update(self, instance, validated_data):
        """update weight"""
        try:
            instance = super().update(instance, validated_data)
            ProductCls.create_weight_log(instance, "updated")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['weight_name']:
            representation['weight_name'] = representation['weight_name'].title()
        return representation


class TaxExportAsCSVSerializers(serializers.ModelSerializer):
    tax_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = Tax
        fields = ('tax_id_list',)

    def validate(self, data):

        if len(data.get('tax_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one tax id must be selected '))

        for t_id in data.get('tax_id_list'):
            try:
                Tax.objects.get(id=t_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'tax not found for id {t_id}')

        return data

    def create(self, validated_data):
        meta = Tax._meta
        exclude_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        queryset = Tax.objects.filter(id__in=validated_data['tax_id_list'])
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response


class WeightExportAsCSVSerializers(serializers.ModelSerializer):
    weight_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = Weight
        fields = ('weight_id_list',)

    def validate(self, data):

        if len(data.get('weight_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one weight id must be selected '))

        for w_id in data.get('weight_id_list'):
            try:
                Weight.objects.get(id=w_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'weight not found for id {w_id}')

        return data

    def create(self, validated_data):
        meta = Weight._meta
        exclude_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        queryset = Weight.objects.filter(id__in=validated_data['weight_id_list'])
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response


class HSNExportAsCSVSerializers(serializers.ModelSerializer):
    hsn_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = ProductHSN
        fields = ('hsn_id_list',)

    def validate(self, data):

        if len(data.get('hsn_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one hsn id must be selected '))

        for h_id in data.get('hsn_id_list'):
            try:
                ProductHSN.objects.get(id=h_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'hsn not found for id {h_id}')

        return data

    def create(self, validated_data):
        meta = ProductHSN._meta
        exclude_fields = ['created_at', 'updated_at', 'created_by', 'updated_by', 'status']
        model_field_names = [field.name for field in meta.fields if field.name not in exclude_fields]
        gst_cess_field_names = ["gst_rate_1", "gst_rate_2", "gst_rate_3", "cess_rate_1", "cess_rate_2", "cess_rate_3"]
        field_names = model_field_names + gst_cess_field_names

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        queryset = ProductHSN.objects.filter(id__in=validated_data['hsn_id_list'])
        for obj in queryset:
            hsn_gsts = obj.hsn_gst.values_list('gst', flat=True)[:3]
            hsn_cess = obj.hsn_cess.values_list('cess', flat=True)[:3]
            writer.writerow([getattr(obj, field) for field in model_field_names] +
                            list(hsn_gsts) + ([None] * (3 - len(hsn_gsts))) +
                            list(hsn_cess) + ([None] * (3 - len(hsn_cess))))
        return response


class HSNExportAsCSVUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(
        label='Upload Shop Route', required=True, write_only=True)

    def __init__(self, *args, **kwargs):
        super(HSNExportAsCSVUploadSerializer, self).__init__(*args, **kwargs)  # call the super()

    class Meta:
        model = ProductHSN
        fields = ('file',)

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError(
                _('Sorry! Only csv file accepted.'))
        csv_file_data = csv.reader(codecs.iterdecode(data['file'], 'utf-8', errors='ignore'))
        # Checking, whether csv file is empty or not!
        if csv_file_data:
            read_product_hsn_file(csv_file_data)
        else:
            raise serializers.ValidationError(
                "CSV File cannot be empty.Please add some data to upload it!")

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            ProductHSNCommonFunction.create_product_hsn(validated_data, self.context['request'].user)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return validated_data


class ChildProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'status')


class ProductVendorMappingSerializers(serializers.ModelSerializer):
    product = ChildProductSerializer(read_only=True)
    vendor = VendorSerializers(read_only=True)

    def validate(self, data):
        if data.get('product_price') is None and data.get('product_price_pack') is None:
            raise serializers.ValidationError("please enter one Brand to Gram Price")

        if data.get('case_size') is None:
            raise serializers.ValidationError("please enter case_size")
        if data.get('case_size') <= 0:
            raise serializers.ValidationError(" 'case_size' Ensure this value is greater than 0")
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
        fields = ('id', 'product_price', 'product_price_pack', 'product_mrp', 'case_size', 'status', 'is_default',
                  'vendor', 'product', 'created_at')

    @transaction.atomic
    def create(self, validated_data):
        """ create vendor product mapping """
        try:
            product_vendor_map = ProductCls.create_product_vendor_mapping(self.initial_data['product'],
                                                                          self.initial_data['vendor'], **validated_data)
            ProductCls.create_product_vendor_map_log(product_vendor_map, "created")
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
            ProductCls.create_product_vendor_map_log(instance, "updated")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return product_vendor_map


class ProductVendorMappingExportAsCSVSerializers(serializers.ModelSerializer):
    product_vendor_mapping_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = ProductVendorMapping
        fields = ('product_vendor_mapping_id_list',)

    def validate(self, data):

        if len(data.get('product_vendor_mapping_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one product vendor mapping id must be selected '))

        for pv_id in data.get('product_vendor_mapping_id_list'):
            try:
                ProductVendorMapping.objects.get(id=pv_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'product vendor mapping not found for id {pv_id}')

        return data

    def create(self, validated_data):
        meta = ProductVendorMapping._meta
        exclude_fields = ['id', 'product_price_pack', 'brand_to_gram_price_unit', 'updated_at', 'created_by',
                          'updated_by', 'is_default']
        #  list_display = ('vendor', 'product', 'product_price', 'product_mrp', 'case_size', 'created_at', 'status')
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        queryset = ProductVendorMapping.objects.filter(id__in=validated_data['product_vendor_mapping_id_list'])
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        ref_name = 'Shop City v1'
        fields = ('id', 'city_name',)


class PinCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pincode
        ref_name = 'Pin Code Serializer v1'
        fields = ('id', 'pincode',)


class ShopsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', '__str__')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['service_partner'] = {
            'id': representation['id'],
            'shop': representation['__str__']
        }
        return representation['service_partner']


class DiscountedProductsSerializers(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name',)


class ProductsSerializers(serializers.ModelSerializer):
    product_ref = DiscountedProductsSerializers(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'is_ptr_applicable', 'ptr_type', 'ptr_percent', 'product_ref')


class PriceSlabSerializersData(serializers.ModelSerializer):
    class Meta:
        model = PriceSlab
        fields = ('id', 'start_value', 'end_value', 'selling_price', 'offer_price', 'offer_price_start_date',
                  'offer_price_end_date', '__str__')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        obj = representation.copy()
        obj.pop('__str__')
        obj['price_slab'] = representation['__str__']
        return obj


class ImageProductSerializers(serializers.ModelSerializer):
    product_pro_image = ProductImageSerializers(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'product_mrp', 'product_pro_image')


class ProductPriceSerializers(serializers.ModelSerializer):
    price_slabs = PriceSlabSerializersData(read_only=True, many=True)
    product = ProductsSerializers(read_only=True)
    seller_shop = ShopsSerializer(read_only=True)
    buyer_shop = ShopsSerializer(read_only=True)
    city = CitySerializer(read_only=True)
    pincode = PinCodeSerializer(read_only=True)
    approval_status = ChoiceField(choices=ProductPrice.APPROVAL_CHOICES, required=True)
    slab_price_applicable = serializers.BooleanField(required=False, read_only=True)

    def validate(self, data):
        if not 'product_type' in self.initial_data or self.initial_data['product_type'] not in [0, 1]:
            raise serializers.ValidationError("product_type is mandatory")

        if self.initial_data['product'] is None:
            raise serializers.ValidationError("please select product")
        product_val = get_validate_product(self.initial_data['product'])
        if 'error' in product_val:
            raise serializers.ValidationError(product_val['error'])
        data['product'] = product_val['product']

        if not int(data['product'].product_type) == int(self.initial_data['product_type']):
            raise serializers.ValidationError("product_type is mismatch")

        if product_val['product'] and product_val['product'].product_mrp:
            data['mrp'] = product_val['product'].product_mrp

        if self.initial_data['seller_shop'] is None:
            raise serializers.ValidationError("please select seller shop")
        seller_shop_val = get_validate_seller_shop(self.initial_data['seller_shop'])
        if 'error' in seller_shop_val:
            raise serializers.ValidationError(seller_shop_val['error'])
        data['seller_shop'] = seller_shop_val['seller_shop']

        if self.initial_data['buyer_shop']:
            buyer_shop_val = get_validate_buyer_shop(self.initial_data['buyer_shop'])
            if 'error' in buyer_shop_val:
                raise serializers.ValidationError(buyer_shop_val['error'])
            data['buyer_shop'] = buyer_shop_val['buyer_shop']
            if not data['buyer_shop'].shop_name_address_mapping.exists():
                raise serializers.ValidationError("address is missing for selected buyer shop")

        if self.initial_data['city']:
            city_val = get_validate_city_id(self.initial_data['city'])
            if 'error' in city_val:
                raise serializers.ValidationError(city_val['error'])
            data['city'] = city_val['data']

        if self.initial_data['pincode']:
            pincode_val = get_validate_pin_code(self.initial_data['pincode'])
            if 'error' in pincode_val:
                raise serializers.ValidationError(pincode_val['error'])
            data['pincode'] = pincode_val['data']

        if not 'price_slabs' in self.initial_data or not self.initial_data['price_slabs']:
            raise serializers.ValidationError(_('price_slabs is required'))
        get_validate_slab_price(self.initial_data['price_slabs'], self.initial_data['product_type'],
                                self.initial_data['slab_price_applicable'], data)
        data['price_slabs'] = self.initial_data['price_slabs']

        return data

    class Meta:
        model = ProductPrice
        fields = ('id', 'product', 'mrp', 'seller_shop', 'buyer_shop', 'city', 'pincode', 'approval_status',
                  'price_slabs', 'slab_price_applicable')

    @transaction.atomic
    def create(self, validated_data):
        """ create product price mapping """
        price_slabs = validated_data.pop('price_slabs', None)
        try:
            product_price = ProductPrice.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        if price_slabs:
            self.create_price_slabs(product_price, price_slabs)

        return product_price

    def create_price_slabs(self, product_price, price_slabs):
        for price_slab in price_slabs:
            if 'start_value' not in price_slab:
                price_slab['start_value'] = 0
            if 'end_value' not in price_slab:
                price_slab['end_value'] = 0
            PriceSlab.objects.create(product_price=product_price, **price_slab)


class DisapproveSelectedProductPriceSerializers(serializers.ModelSerializer):
    approval_status = serializers.BooleanField(required=True)
    product_price_id_list = serializers.ListField(child=serializers.IntegerField(min_value=1))

    class Meta:
        model = ProductPrice
        fields = ('approval_status', 'product_price_id_list',)

    def validate(self, data):

        if data.get('approval_status') is None:
            raise serializers.ValidationError('approval_status field is required')

        if not int(data.get('approval_status')) == 0:
            raise serializers.ValidationError('invalid approval_status')

        if 'product_price_id_list' not in data or not data['product_price_id_list']:
            raise serializers.ValidationError(_('atleast one product price id must be selected '))

        for p_id in data.get('product_price_id_list'):
            try:
                ProductPrice.objects.get(id=p_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'product price not found for id {p_id}')

        return data

    @transaction.atomic
    def update(self, instance, validated_data):

        try:
            product_prices = ProductPrice.objects.filter(
                id__in=validated_data['product_price_id_list'])
            product_prices.update(approval_status=int(validated_data['approval_status']), modified_at=timezone.now())
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return validated_data


class ProductSlabPriceExportAsCSVSerializers(serializers.ModelSerializer):
    product_price_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = ProductPrice
        fields = ('product_price_list',)

    def validate(self, data):

        if len(data.get('product_price_list')) == 0:
            raise serializers.ValidationError(_('Atleast one product slab price id must be selected '))

        for psp_id in data.get('product_price_list'):
            try:
                ProductPrice.objects.get(id=psp_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'product slab price not found for id {psp_id}')

        return data

    def create(self, validated_data):
        meta = ProductPrice._meta

        field_names = ["SKU", "Product Name", "Shop Id", "Shop Name", "MRP", "is_ptr_applicable", "ptr_type",
                       "ptr_percent", "Slab 1 Qty", "Selling Price 1", "Offer Price 1", "Offer Price 1 Start Date",
                       "Offer Price 1 End Date", "Slab 2 Qty", "Selling Price 2", "Offer Price 2",
                       "Offer Price 2 Start Date", "Offer Price 2 End Date"]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)

        queryset = ProductPrice.objects.filter(id__in=validated_data['product_price_list'])
        for obj in queryset:
            obj = ProductPrice.objects.get(id=obj.id)
            try:
                row = [obj.product.product_sku, obj.product.product_name, obj.seller_shop.id, obj.seller_shop.shop_name,
                       obj.mrp, obj.product.is_ptr_applicable, obj.product.ptr_type, obj.product.ptr_percent]
                first_slab = True
                for slab in obj.price_slabs.all().order_by('start_value'):
                    if first_slab:
                        row.append(slab.end_value)
                    else:
                        row.append(slab.start_value)
                    row.append(slab.selling_price)
                    row.append(slab.offer_price)
                    row.append(slab.offer_price_start_date)
                    row.append(slab.offer_price_end_date)
                    first_slab = False
                writer.writerow(row)

            except Exception as exc:
                info_logger.error(exc)
        return response


class DiscountChildProductSerializers(serializers.ModelSerializer):
    """ Handles creating, reading and updating child product items."""
    parent_product = ParentProductSerializers(read_only=True)
    child_product_logs = LogSerializers(many=True, read_only=True)
    product_pro_image = ProductImageSerializers(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'product_ean_code', 'status', 'product_mrp', 'weight_value',
                  'weight_unit', 'reason_for_child_sku', 'use_parent_image', 'product_type', 'is_manual_price_update',
                  'product_pro_image', 'parent_product', 'child_product_logs')

    @transaction.atomic
    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Child Product's attribute."""
        try:
            # call super to save modified instance along with the validated data
            child_product = super().update(instance, validated_data)
            ProductCls.create_child_product_log(child_product, "updated")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return child_product


class ProductHSNApprovalSerializers(serializers.ModelSerializer):
    hsn_gst = ProductHSNGstSerializers(many=True, read_only=True)
    hsn_cess = ProductHSNCessSerializers(many=True, read_only=True)

    class Meta:
        model = ProductHSN
        fields = ('id', 'product_hsn_code', 'hsn_gst', 'hsn_cess')


class ParentProductApprovalSerializers(serializers.ModelSerializer):
    """Handles creating, reading and updating parent product items."""
    parent_brand = BrandSerializers(read_only=True)
    product_hsn = ProductHSNApprovalSerializers(read_only=True)
    parent_product_pro_category = ParentProductCategorySerializers(many=True, read_only=True)
    parent_product_pro_tax = ParentProductTaxMappingSerializers(many=True, read_only=True)
    parent_id = serializers.CharField(read_only=True)
    name = serializers.CharField(required=False)
    product_type = serializers.CharField(required=False)

    def validate(self, data):
        """
            tax_status & tax_remark validation.
        """
        if not self.instance:
            raise serializers.ValidationError("Only update allowed.")

        # if 'name' in self.initial_data and self.initial_data['name'] is not None:
        #     pro_obj = validate_parent_product_name(self.initial_data['name'], self.instance.id)
        #     if pro_obj is not None and 'error' in pro_obj:
        #         raise serializers.ValidationError(pro_obj['error'])

        if self.instance.tax_status == ParentProduct.APPROVED:
            raise serializers.ValidationError("Product Tax is already approved.")

        if 'tax_status' not in self.initial_data or not self.initial_data['tax_status']:
            raise serializers.ValidationError(_('tax_status is required'))
        if self.initial_data['tax_status'] not in [ParentProduct.APPROVED, ParentProduct.DECLINED]:
            raise serializers.ValidationError(_('Invalid tax_status.'))

        if self.instance.tax_status == self.initial_data['tax_status']:
            raise serializers.ValidationError(f"Product Tax is already {self.instance.get_tax_status_display()}.")

        tax_remark = None
        if self.initial_data['tax_status'] == ParentProduct.DECLINED:
            # Validate tax_remark if the tax_status is DECLINED
            if 'tax_remark' not in self.initial_data or not self.initial_data['tax_remark']:
                raise serializers.ValidationError(_('tax_remark is required'))
            if len(str(self.initial_data['tax_remark']).strip()) > 50:
                raise serializers.ValidationError(_("'tax_remark' | Max length exceeded, only 50 characters allowed."))
            tax_remark = str(self.initial_data['tax_remark']).strip()
        elif self.initial_data['tax_status'] == ParentProduct.APPROVED:
            # Validate GST from HSN
            product_gst_tax = self.instance.parent_product_pro_tax.filter(tax__tax_type='gst').last()
            if product_gst_tax and product_gst_tax.tax.tax_percentage not in \
                    self.instance.product_hsn.hsn_gst.values_list('gst', flat=True):
                raise serializers.ValidationError("Please map GST in HSN to approve product.")
            # Validate Cess from HSN
            product_cess_tax = self.instance.parent_product_pro_tax.filter(tax__tax_type='cess').last()
            if product_cess_tax and product_cess_tax.tax.tax_percentage not in \
                    self.instance.product_hsn.hsn_cess.values_list('cess', flat=True):
                raise serializers.ValidationError("Please map CESS in HSN to approve product.")

        data['name'] = self.instance.name
        data['parent_id'] = self.instance.parent_id
        data['product_type'] = self.instance.product_type

        data['tax_status'] = self.initial_data['tax_status']
        data['tax_remark'] = tax_remark

        return data

    class Meta:
        model = ParentProduct
        fields = ('id', 'parent_id', 'name', 'product_type', 'status', 'product_hsn', 'parent_brand',
                  'parent_product_pro_tax', 'parent_product_pro_category', 'tax_status', 'tax_remark',
                  'created_at', 'updated_at', 'created_by', 'updated_by')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['name']:
            representation['name'] = representation['name'].title()
        return representation

    @transaction.atomic
    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Parent Product's attribute. """
        try:
            # call super to save modified instance along with the validated data
            parent_product = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        ParentProductCls.update_tax_status_and_remark_in_log(
            parent_product, validated_data['tax_status'], validated_data['tax_remark'], validated_data['updated_by'])
        ParentProductCls.create_parent_product_log(parent_product, "updated")
        if parent_product.tax_status == ParentProduct.DECLINED:
            send_mail_on_product_tax_declined(parent_product)

        return parent_product


class CategoryBasicSerializers(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'category_name',)


class B2BCategoryBasicSerializer(serializers.ModelSerializer):
    category = CategoryBasicSerializers(read_only=True)

    class Meta:
        model = ParentProductCategory
        fields = ('id', 'category',)


class B2CCategoryBasicSerializers(serializers.ModelSerializer):
    class Meta:
        model = B2cCategory
        fields = ('id', 'category_name',)


class B2CCategoryBasicSerializer(serializers.ModelSerializer):
    category = CategoryBasicSerializers(read_only=True)

    class Meta:
        model = ParentProductB2cCategory
        fields = ('id', 'category',)


class ParentProductBasicSerializer(serializers.ModelSerializer):
    parent_product_pro_category = B2BCategoryBasicSerializer(many=True, read_only=True)
    parent_product_pro_b2c_category = B2CCategoryBasicSerializer(many=True, read_only=True)

    class Meta:
        model = ParentProduct
        fields = ('id', 'parent_id', 'name', 'parent_product_pro_category', 'parent_product_pro_b2c_category')


class ChildProductsSerializers(serializers.ModelSerializer):
    parent_product = ParentProductBasicSerializer(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'product_mrp', 'parent_product')


class SuperStoreProductPriceLogSerializer(serializers.ModelSerializer):
    updated_by = UserSerializers(read_only=True)

    class Meta:
        model = SuperStoreProductPriceLog
        fields = ('updated_by', 'update_at', 'old_selling_price', 'new_selling_price',)


class SuperStoreProductPriceSerializers(serializers.ModelSerializer):
    product = ChildProductsSerializers(read_only=True)
    seller_shop = ShopsSerializer(read_only=True)
    selling_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=True, min_value=0.01)
    product_price_change_log = SuperStoreProductPriceLogSerializer(read_only=True, many=True)

    def validate(self, data):

        if self.initial_data['product'] is None:
            raise serializers.ValidationError("please select product")
        product_val = validate_superstore_product(self.initial_data['product'])
        if 'error' in product_val:
            raise serializers.ValidationError(product_val['error'])
        product_price = validate_retailer_price_exist(self.initial_data['product'], self.initial_data['seller_shop'])
        if 'error' in product_price:
            raise serializers.ValidationError(product_price['error'])
        data['product'] = product_val['product']

        # if product_val['product'] and product_val['product'].product_mrp:
        #     data['mrp'] = product_val['product'].product_mrp

        if data['selling_price'] > product_val['product'].product_mrp:
            raise serializers.ValidationError("selling price can not be greater than product mrp")

        if self.initial_data['seller_shop'] is None:
            raise serializers.ValidationError("please select seller shop")
        seller_shop_val = get_validate_seller_shop(self.initial_data['seller_shop'])
        if 'error' in seller_shop_val:
            raise serializers.ValidationError(seller_shop_val['error'])
        data['seller_shop'] = seller_shop_val['seller_shop']

        if not 'id' in self.initial_data or not self.initial_data['id']:
            if SuperStoreProductPrice.objects.filter(seller_shop=data['seller_shop'],
                                                     product=data['product']).exists():
                raise serializers.ValidationError("You have already created price for this product!!!")

        if 'id' in self.initial_data and self.initial_data['id']:
            if not SuperStoreProductPrice.objects.filter(seller_shop=data['seller_shop'],
                                                         product=data['product'], id=self.initial_data['id']):
                raise serializers.ValidationError("You can't change product or seller shop!!!")

        return data

    class Meta:
        model = SuperStoreProductPrice
        fields = ('id', 'product', 'seller_shop', 'selling_price', 'product_price_change_log')

    @transaction.atomic
    def create(self, validated_data):
        """ create product price mapping """
        try:
            product_price = SuperStoreProductPrice.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return product_price

    @transaction.atomic
    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Child Product's price attribute."""
        try:
            # call super to save modified instance along with the validated data
            product_price = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return product_price


class SuperStoreProductPriceAsCSVUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(
        label='Upload Product Price', required=True, write_only=True)

    def __init__(self, *args, **kwargs):
        super(SuperStoreProductPriceAsCSVUploadSerializer, self).__init__(*args, **kwargs)  # call the super()

    class Meta:
        model = SuperStoreProductPrice
        fields = ('file',)

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError(
                _('Sorry! Only csv file accepted.'))
        csv_file_data = csv.reader(codecs.iterdecode(data['file'], 'utf-8', errors='ignore'))
        # Checking, whether csv file is empty or not!
        if csv_file_data:
            errorlist, validated_data = read_super_store_product_price_file(csv_file_data)
        else:
            raise serializers.ValidationError(
                "CSV File cannot be empty.Please add some data to upload it!")

        return {"ErrorData": errorlist, "SuccessData": validated_data}

    @transaction.atomic
    def create(self, validated_data):
        try:
            # Store valid data in model
            SuperStoreProductPriceCommonFunction.create_product_price(validated_data["SuccessData"], self.context['request'].user)

            # Write error list into csv file
            filename = f"super_store_product_price-upload.csv"
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            writer = csv.writer(response)
            total_data = len(validated_data["ErrorData"]) + len(validated_data["SuccessData"])
            fail_data = len(validated_data["ErrorData"])
            pass_data = len(validated_data["SuccessData"])
            if len(validated_data["ErrorData"]):
                writer.writerow(['Total Data:', total_data])
                writer.writerow(['Pass Data:', pass_data])
                writer.writerow(['Fail Data:', fail_data])
                writer.writerow([])
                writer.writerow(
                    ['seller_shop_id', 'seller_shop', 'parent_product_id', 'product_id', 'product_sku', 'product_name',
                     'b2b_category', 'b2c_category', 'mrp', 'selling_price', 'upload_status'])
                for row in validated_data["ErrorData"]:
                    writer.writerow(row)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return response


class SuperStoreProductPriceDownloadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperStoreProductPrice
        fields = ('seller_shop_id',)

    def validate(self, data):

        if not 'seller_shop_id' in self.initial_data:
            raise serializers.ValidationError(_('Please Select One seller shop id!'))

        elif 'seller_shop_id' in self.initial_data and self.initial_data['seller_shop_id']:
            seller_shop_val = get_validate_seller_shop(self.initial_data['seller_shop_id'])
            if 'error' in seller_shop_val:
                raise serializers.ValidationError(_(seller_shop_val["error"]))
            data['seller_shop_id'] = seller_shop_val['seller_shop']

        return data

    def create(self, validated_data):
        shop = validated_data['seller_shop_id']
        filename = f"super_store_product_price-{shop.id}.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(
            ['seller_shop_id', 'seller_shop', 'parent_product_id', 'product_id', 'product_sku', 'product_name',
             'b2b_category', 'b2c_category', 'mrp', 'selling_price'])

        price_product_qs = SuperStoreProductPrice.objects.filter(seller_shop=shop).\
            select_related('product', 'seller_shop', 'product__parent_product').\
            prefetch_related('product__parent_product', 'seller_shop__shop_type', 'seller_shop__shop_owner',
                             'product__parent_product__parent_product_pro_category',
                             'product__parent_product__parent_product_pro_b2c_category').order_by('-updated_at')
        if price_product_qs.exists():
            for obj in price_product_qs:
                b2b = obj.product.parent_product.parent_product_pro_category.last()
                b2c = obj.product.parent_product.parent_product_pro_b2c_category.last()
                writer.writerow(
                    [obj.seller_shop.pk, obj.seller_shop.shop_name, obj.product.parent_product.parent_id,
                     obj.product.id, obj.product.product_sku, obj.product.product_name,
                     b2b.category.category_name if b2b else b2b, b2c.category.category_name if b2c else b2c,
                     obj.product.product_mrp, obj.selling_price])
        else:
            writer.writerow(
                [600, 'GFDN', 'PCBDPCO0074', '544', 'BEVBEVNIM00000001', 'maggie', 'Liquid Drinks', 'Liquid Drinks', 233, 200])
        return response

