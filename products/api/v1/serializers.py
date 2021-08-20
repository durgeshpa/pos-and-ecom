import csv
import logging
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from rest_framework import serializers

from products.models import Product, ParentProductTaxMapping, ParentProduct, ParentProductCategory, ParentProductImage, \
    ProductTaxMapping, ProductCapping, ProductVendorMapping, ProductImage, ProductPrice, ProductHSN, Tax, \
    ProductSourceMapping, ProductPackingMapping, DestinationRepackagingCostMapping, Weight, CentralLog, PriceSlab
from categories.models import Category
from addresses.models import Pincode, City
from brand.models import Brand, Vendor
from shops.models import Shop
from accounts.models import User

from products.common_validators import get_validate_parent_brand, get_validate_product_hsn, get_validate_parent_product, \
    get_validate_images, get_validate_categories, get_validate_tax, is_ptr_applicable_validation, get_validate_product, \
    get_validate_seller_shop, check_active_capping, get_validate_packing_material, get_source_product, product_category, \
    product_gst, product_cess, product_surcharge, product_image, get_validate_vendor, get_validate_buyer_shop, \
    get_validate_parent_product_image_ids, get_validate_child_product_image_ids, validate_parent_product_name, \
    validate_child_product_name, validate_tax_name, get_validate_slab_price
from products.common_function import ParentProductCls, ProductCls
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
    parent_product_pro_category = ParentProductCategorySerializers(many=True)
    parent_product_pro_tax = ParentProductTaxMappingSerializers(many=True)
    product_parent_product = ChildProductVendorSerializers(many=True, required=False)
    parent_id = serializers.CharField(read_only=True)
    max_inventory = serializers.IntegerField(allow_null=True, max_value=999)
    product_images = serializers.ListField(required=False, default=None, child=serializers.ImageField(),
                                           write_only=True)

    def validate(self, data):
        """
            is_ptr_applicable validation.
        """
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

        category_val = get_validate_categories(self.initial_data['parent_product_pro_category'])
        if 'error' in category_val:
            raise serializers.ValidationError(_(category_val["error"]))
        # data['parent_product_pro_category'] = category_val['category']

        tax_val = get_validate_tax(self.initial_data['parent_product_pro_tax'])
        if 'error' in tax_val:
            raise serializers.ValidationError(_(tax_val["error"]))
        # data['parent_product_pro_tax'] = tax_val['tax']

        parent_pro_id = self.instance.id if self.instance else None
        if 'name' in self.initial_data and self.initial_data['name'] is not None:
            pro_obj = validate_parent_product_name(self.initial_data['name'], parent_pro_id)
            if pro_obj is not None and 'error' in pro_obj:
                raise serializers.ValidationError(pro_obj['error'])

        return data

    class Meta:
        model = ParentProduct
        fields = ('id', 'parent_id', 'name', 'inner_case_size', 'brand_case_size', 'product_type', 'status',
                  'product_hsn', 'parent_brand', 'parent_product_pro_tax', 'parent_product_pro_category',
                  'is_ptr_applicable', 'ptr_percent', 'ptr_type', 'is_ars_applicable', 'max_inventory',
                  'is_lead_time_applicable', 'discounted_life_percent', 'product_images', 'parent_product_pro_image',
                  'product_parent_product', 'parent_product_log',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if not representation['is_ptr_applicable']:
            representation['ptr_type'] = representation['ptr_percent'] = None
        if representation['name']:
            representation['name'] = representation['name'].title()
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
        ParentProductCls.create_parent_product_log(parent_product, "created")

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
        ParentProductCls.create_parent_product_category(parent_product,
                                                        self.initial_data['parent_product_pro_category'])
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
            'parent_id', 'name', 'parent_brand', 'product_category', 'product_hsn', 'product_gst', 'product_cess',
            'product_surcharge', 'inner_case_size', 'product_image', 'status', 'product_type', 'is_ptr_applicable',
            'ptr_type',
            'ptr_percent', 'is_ars_applicable', 'is_lead_time_applicable', 'max_inventory',
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


class ChildProductSerializers(serializers.ModelSerializer):
    """ Handles creating, reading and updating child product items."""
    parent_product = ParentProductSerializers(read_only=True)
    product_pro_tax = ProductTaxMappingSerializers(many=True, read_only=True)
    child_product_logs = LogSerializers(many=True, read_only=True)
    product_vendor_mapping = ChildProductVendorMappingSerializers(many=True, required=False)
    product_sku = serializers.CharField(required=False)
    product_pro_image = ProductImageSerializers(many=True, read_only=True)
    product_images = serializers.ListField(required=False, default=None, child=serializers.ImageField(),
                                           write_only=True)
    destination_product_pro = ProductSourceMappingSerializers(many=True, required=False)
    packing_product_rt = ProductPackingMappingSerializers(many=True, required=False)
    destination_product_repackaging = DestinationRepackagingCostMappingSerializers(many=True,
                                                                                   required=False)

    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'product_ean_code', 'status', 'product_mrp', 'weight_value',
                  'weight_unit', 'reason_for_child_sku', 'use_parent_image', 'product_special_cess', 'product_type',
                  'is_manual_price_update', 'repackaging_type', 'product_pro_image', 'parent_product',
                  'product_pro_tax', 'destination_product_pro', 'product_images', 'destination_product_repackaging',
                  'packing_product_rt', 'product_vendor_mapping', 'child_product_logs')

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

    def create_source_packing_material_destination_product(self, child_product, destination_product_repack):
        ProductCls.create_source_product_mapping(child_product, self.initial_data['destination_product_pro'])
        ProductCls.packing_material_product_mapping(child_product, self.initial_data['packing_product_rt'])
        ProductCls.create_destination_product_mapping(child_product, destination_product_repack)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['product_name']:
            representation['product_name'] = representation['product_name'].title()
        return representation


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
        exclude_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
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
                if cost_obj:
                    for param in cost_params:
                        items.append(str(getattr(cost_obj, param)))
            writer.writerow(items)
        return response


class ProductHSNCrudSerializers(serializers.ModelSerializer):
    """ Handles Get & creating """
    product_hsn_code = serializers.CharField(max_length=8, min_length=6, validators=[only_int])
    hsn_log = LogSerializers(many=True, read_only=True)

    class Meta:
        model = ProductHSN
        fields = ('id', 'product_hsn_code', 'hsn_log')

    def validate(self, data):
        hsn_id = self.instance.id if self.instance else None
        if 'product_hsn_code' in self.initial_data and data['product_hsn_code']:
            if ProductHSN.objects.filter(product_hsn_code__iexact=data['product_hsn_code'], status=True) \
                    .exclude(id=hsn_id).exists():
                raise serializers.ValidationError("hsn code already exists.")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new HSN"""
        try:
            hsn = ProductHSN.objects.create(**validated_data)
            ProductCls.create_hsn_log(hsn, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return hsn

    def update(self, instance, validated_data):
        """update hsn"""
        instance = super().update(instance, validated_data)
        ProductCls.create_hsn_log(instance, "updated")
        return instance


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
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        queryset = ProductHSN.objects.filter(id__in=validated_data['hsn_id_list'])
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response


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
        fields = ('id', 'city_name',)


class PinCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pincode
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
    discounted_sku = DiscountedProductsSerializers()

    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'is_ptr_applicable', 'ptr_type', 'ptr_percent', 'discounted_sku')


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
        if product_price.product.product_type == 0:
            for price_slab in price_slabs:
                if 'start_value' not in price_slab:
                    price_slab['start_value'] = 0
                if 'end_value' not in price_slab:
                    price_slab['end_value'] = 0
                PriceSlab.objects.create(product_price=product_price, **price_slab)
        else:
            PriceSlab.objects.create(product_price=product_price, start_value=0,
                                     end_value=0, selling_price=product_price.selling_price)


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
    product_pro_tax = ProductTaxMappingSerializers(many=True, read_only=True)
    child_product_logs = LogSerializers(many=True, read_only=True)
    product_vendor_mapping = ChildProductVendorMappingSerializers(many=True, required=False)
    product_sku = serializers.CharField(required=False)
    product_pro_image = ProductImageSerializers(many=True, read_only=True)
    product_images = serializers.ListField(required=False, default=None, child=serializers.ImageField(),
                                           write_only=True)
    destination_product_pro = ProductSourceMappingSerializers(many=True, required=False)
    packing_product_rt = ProductPackingMappingSerializers(many=True, required=False)
    destination_product_repackaging = DestinationRepackagingCostMappingSerializers(many=True,
                                                                                   required=False)

    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'product_ean_code', 'status', 'product_mrp', 'weight_value',
                  'weight_unit', 'reason_for_child_sku', 'use_parent_image', 'product_special_cess', 'product_type',
                  'is_manual_price_update', 'repackaging_type', 'product_pro_image', 'parent_product',
                  'product_pro_tax', 'destination_product_pro', 'product_images', 'destination_product_repackaging',
                  'packing_product_rt', 'product_vendor_mapping', 'child_product_logs')