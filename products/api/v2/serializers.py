import codecs
import csv
import logging
import re
import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from brand.models import Brand
from categories.common_validators import get_validate_category
from categories.models import Category
from products.api.v1.serializers import UserSerializers
from products.bulk_common_function import download_sample_file_update_master_data, create_update_master_data
from products.common_validators import read_file, get_validate_vendor
from products.master_data import create_product_vendor_mapping_sample_file, create_bulk_product_vendor_mapping, \
    create_bulk_product_slab_price
from products.models import Product, ProductImage, ParentProduct, ParentProductImage, BulkUploadForProductAttributes, \
    ProductVendorMapping, ProductPrice
from shops.models import Shop
from retailer_backend.utils import isDateValid, getStrToDate, isBlankRow
from retailer_backend.validators import *

logger = logging.getLogger(__name__)

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class CategoryListSerializers(serializers.ModelSerializer):
    class Meta:
        model = Category

        fields = ('id', 'category_name',)


DATA_TYPE_CHOICES = (
    # ('product_status_update_inactive', 'product_status_update_inactive'),
    # ('sub_brand_with_brand_mapping', 'sub_brand_with_brand_mapping'),
    # ('sub_category_with_category_mapping', 'sub_category_with_category_mapping'),
    # ('child_parent_product_update', 'child_parent_product_update'),
    # ('product_tax_update', 'product_tax_update'),

    ('create_data', (
        ('create_child_product', 'Create Child Product'),
        ('create_parent_product', 'Create Parent Product'),
        ('create_category', 'Create Category'),
        ('create_brand', 'Create Brand'),
        ('create_product_vendor_mapping', 'Create Product Vendor Mapping')
    )
     ),
    ('update_data', (
        ('child_product_update', 'Update Child Product'),
        ('parent_product_update', 'Update Parent Product'),
        ('category_update', 'Update Category'),
        ('brand_update', 'Update Brand'),
    )
     ),
    ('upload_bulk_images', (
        ('child_product_image_update', 'Update Child Product Images'),
        ('parent_product_image_update', 'Update Parent Product Images'),
        ('category_image_update', 'Update Category Images'),
        ('brand_image_update', 'Update Brand Images'),
    )
     ),
)


class ChoiceField(serializers.ChoiceField):
    def to_internal_value(self, data):
        for key, val in self._choices.items():
            if key == data:
                return key
        self.fail('invalid_choice', input=data)
        # if not (any(data in i for i in DATA_TYPE_CHOICES)):
        #     raise serializers.ValidationError(_('Sorry! Not a Valid Option.'))


class UploadMasterDataSerializers(serializers.ModelSerializer):
    file = serializers.FileField(label='Upload Master Data', required=True)
    updated_by = UserSerializers(read_only=True)
    upload_type = ChoiceField(choices=DATA_TYPE_CHOICES, required=True)

    class Meta:
        model = BulkUploadForProductAttributes
        fields = ('id', 'file', 'upload_type', 'updated_by', 'created_at', 'updated_at')

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError(_('Sorry! Only csv file accepted.'))

        if data['upload_type'] == "product_status_update_inactive" or data['upload_type'] == \
                "child_parent_product_update" or data['upload_type'] == "parent_product_update" \
                or data['upload_type'] == "child_product_update":

            if not 'category_id' in self.initial_data:
                raise serializers.ValidationError(_('Please Select One Category!'))

            elif 'category_id' in self.initial_data and self.initial_data['category_id']:
                category_val = get_validate_category(self.initial_data['category_id'])
                if 'error' in category_val:
                    raise serializers.ValidationError(_(category_val["error"]))
                self.initial_data['category_id'] = category_val['category']
        else:
            self.initial_data['category_id'] = None

        csv_file_data = csv.reader(codecs.iterdecode(data['file'], 'utf-8', errors='ignore'))
        # Checking, whether csv file is empty or not!
        if csv_file_data:
            read_file(csv_file_data, self.initial_data['upload_type'], self.initial_data['category_id'])
        else:
            raise serializers.ValidationError("CSV File cannot be empty.Please add some data to upload it!")
        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            create_update_master_data(validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        attribute_id = BulkUploadForProductAttributes.objects.values('id').last()
        if attribute_id:
            validated_data['file'].name = validated_data['upload_type'] + '-' + \
                                          str(attribute_id['id'] + 1) + '.csv '
        else:
            validated_data['file'].name = validated_data['upload_type'] + '-' + str(1) + '.csv'
        product_attribute = BulkUploadForProductAttributes.objects.create(file=validated_data['file'],
                                                                          updated_by=validated_data['updated_by'],
                                                                          upload_type=validated_data['upload_type'])

        return product_attribute

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%b %d %Y %I:%M%p")
        representation['updated_at'] = instance.updated_at.strftime("%b %d %Y %I:%M%p")
        return representation


class DownloadMasterDataSerializers(serializers.ModelSerializer):
    upload_type = ChoiceField(choices=DATA_TYPE_CHOICES, required=True, write_only=True)

    class Meta:
        model = BulkUploadForProductAttributes
        fields = ('upload_type',)

    def validate(self, data):

        if data['upload_type'] == "product_status_update_inactive" or data['upload_type'] == "parent_product_update" \
                or data['upload_type'] == "child_parent_product_update" or data[
            'upload_type'] == "child_product_update":

            if not 'category_id' in self.initial_data:
                raise serializers.ValidationError(_('Please Select One Category!'))

            elif 'category_id' in self.initial_data and self.initial_data['category_id']:
                category_val = get_validate_category(self.initial_data['category_id'])
                if 'error' in category_val:
                    raise serializers.ValidationError(_(category_val["error"]))
                data['category_id'] = category_val['category']
        else:
            self.initial_data['category_id'] = None

        return data

    def create(self, validated_data):
        response = download_sample_file_update_master_data(validated_data)
        return response


class ParentProductImageSerializers(serializers.ModelSerializer):
    """Handles creating, reading and updating parent product images."""

    image = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False, use_url=True, ), write_only=True)

    class Meta:
        model = ParentProductImage
        fields = ('image',)

    def create(self, validated_data):
        images_data = validated_data['image']

        data = []
        aborted_count = 0
        upload_count = 0

        for img in images_data:
            file_name = img.name
            parent_id = file_name.rsplit(".", 1)[0]
            try:
                parent_pro = ParentProduct.objects.get(parent_id=parent_id)
            except:
                val_data = {
                    'is_valid': False,
                    'error': True,
                    'name': 'No Parent Product found with Parent ID {}'.format(parent_id),
                    'url': '#'
                }
                aborted_count += 1
            else:
                img_instance = ParentProductImage.objects.create(parent_product=parent_pro,
                                                                 image_name=parent_id, image=img)
                val_data = {
                    'is_valid': True,
                    'url': img_instance.image.url,
                    'product_sku': parent_pro.parent_id,
                    'product_name': parent_pro.name
                }
                upload_count += 1

            total_count = upload_count + aborted_count
            data.append(val_data)

        data_value = {
            'total_count': total_count,
            'upload_count': upload_count,
            'aborted_count': aborted_count,
            'uploaded_data': data
        }
        return data_value

    def to_representation(self, instance):
        return instance


class ChildProductImageSerializers(serializers.ModelSerializer):
    """Handles creating, reading and updating child product images."""

    image = serializers.ListField(
        child=serializers.FileField(max_length=100000,
                                    allow_empty_file=False,
                                    use_url=True, ), write_only=True)

    class Meta:
        model = ProductImage
        fields = ('image',)

    def create(self, validated_data):
        images_data = validated_data['image']

        data = []
        aborted_count = 0
        upload_count = 0

        for img in images_data:
            file_name = img.name
            product_sku = file_name.rsplit(".", 1)[0]
            try:
                child_product = Product.objects.get(product_sku=product_sku)
            except:
                val_data = {
                    'is_valid': False,
                    'error': True,
                    'name': 'No Product found with SKU ID {}'.format(product_sku),
                    'url': '#'
                }
                aborted_count += 1
            else:
                img_instance = ProductImage.objects.create(product=child_product, image_name=product_sku, image=img)
                val_data = {
                    'is_valid': True,
                    'url': img_instance.image.url,
                    'product_sku': child_product.product_sku,
                    'product_name': child_product.product_name
                }
                upload_count += 1

            total_count = upload_count + aborted_count
            data.append(val_data)

        data_value = {
            'total_count': total_count,
            'upload_count': upload_count,
            'aborted_count': aborted_count,
            'uploaded_data': data
        }
        return data_value

    def to_representation(self, instance):
        return instance


class BrandImageSerializers(serializers.ModelSerializer):
    """Handles creating, reading and updating brand images."""
    image = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False, use_url=True, ), write_only=True)

    class Meta:
        model = Brand
        fields = ('image',)

    def create(self, validated_data):
        images_data = validated_data['image']

        data = []
        aborted_count = 0
        upload_count = 0

        for img in images_data:
            file_name = img.name
            brand_id = file_name.rsplit(".", 1)[0]
            try:
                brand_obj = Brand.objects.get(id=int(brand_id))
            except:
                val_data = {
                    'is_valid': False,
                    'error': True,
                    'name': 'No Brand found with Brand ID {}'.format(brand_id),
                    'url': '#'
                }
                aborted_count += 1

            else:
                # brand_obj.update(id=brand_obj.last().id, brand_logo=img, updated_by=validated_data['updated_by'])
                brand_obj.brand_logo = img
                brand_obj.updated_by = validated_data['updated_by']
                brand_obj.save()
                val_data = {
                    'is_valid': True,
                    'url': brand_obj.brand_logo.url,
                    'brand_id': brand_id,
                    'brand_name': brand_obj.brand_name,
                }
                upload_count += 1

            total_count = upload_count + aborted_count
            data.append(val_data)

        data_value = {
            'total_count': total_count,
            'upload_count': upload_count,
            'aborted_count': aborted_count,
            'uploaded_data': data
        }
        return data_value

    def to_representation(self, instance):
        return instance


class CategoryImageSerializers(serializers.ModelSerializer):
    """Handles creating, reading and updating category images."""
    image = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False, use_url=True, ), write_only=True)

    class Meta:
        model = Category
        fields = ('image',)

    def create(self, validated_data):
        images_data = validated_data['image']

        data = []
        aborted_count = 0
        upload_count = 0

        for img in images_data:
            file_name = img.name
            cat_id = file_name.rsplit(".", 1)[0]
            try:
                cat_obj = Category.objects.get(id=int(cat_id))
            except:
                val_data = {
                    'is_valid': False,
                    'error': True,
                    'name': 'No Category found with Category ID {}'.format(cat_id),
                    'url': '#'
                }
                aborted_count += 1
            else:
                # cat_obj.update(id=cat_obj.last().id, category_image=img, updated_by=validated_data['updated_by'])
                cat_obj.category_image = img
                cat_obj.updated_by = validated_data['updated_by']
                cat_obj.save()

                val_data = {
                    'is_valid': True,
                    'url': cat_obj.category_image.url,
                    'category_id': cat_id,
                    'category_name': cat_obj.category_name
                }
                upload_count += 1

            total_count = upload_count + aborted_count
            data.append(val_data)

        data_value = {
            'total_count': total_count,
            'upload_count': upload_count,
            'aborted_count': aborted_count,
            'uploaded_data': data,
        }
        return data_value

    def to_representation(self, instance):
        return instance


class DownloadProductVendorMappingSerializers(serializers.ModelSerializer):
    class Meta:
        model = ProductVendorMapping
        fields = ('vendor_id',)

    def validate(self, data):

        if not 'vendor_id' in self.initial_data:
            raise serializers.ValidationError(_('Please Select One vendor id!'))

        elif 'vendor_id' in self.initial_data and self.initial_data['vendor_id']:
            vendor_val = get_validate_vendor(self.initial_data['vendor_id'])
            if 'error' in vendor_val:
                raise serializers.ValidationError(_(vendor_val["error"]))
            data['vendor_id'] = vendor_val['vendor']

        if 'download_type' in self.initial_data:
            data['download_type'] = self.initial_data['download_type']
        else:
            raise serializers.ValidationError(_('Please Select a download type!'))

        return data

    def create(self, validated_data):
        response = create_product_vendor_mapping_sample_file(validated_data, validated_data["download_type"])
        return response


class BulkProductVendorMappingSerializers(serializers.ModelSerializer):
    """
      Bulk Product Vendor Mapping
    """
    file = serializers.FileField(label='Add Bulk Product Vendor Mapping', required=True)

    class Meta:
        model = ProductVendorMapping
        fields = ('file',)

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError(_('Sorry! Only csv file accepted.'))

        if not 'vendor_id' in self.initial_data:
            raise serializers.ValidationError(_('Please Select One vendor!'))

        elif 'vendor_id' in self.initial_data and self.initial_data['vendor_id']:
            vendor_val = get_validate_vendor(int(self.initial_data['vendor_id']))
            if 'error' in vendor_val:
                raise serializers.ValidationError(_(vendor_val["error"]))
            data['vendor_id'] = vendor_val['vendor']

        reader = csv.reader(codecs.iterdecode(data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        child_product = Product.objects.all()
        for id, row in enumerate(reader):
            if not row[0]:
                raise serializers.ValidationError("Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] +
                                                  " | Product ID cannot be empty")
            try:
                child_product.get(pk=int(row[0]))
            except:
                raise serializers.ValidationError("Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] +
                                                  " | Product does not exist with this ID")

            if not (row[3].title() == "Per Piece" or row[3].title() == "Per Pack"):
                raise serializers.ValidationError("Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | " +
                                                  VALIDATION_ERROR_MESSAGES['EMPTY_OR_NOT_VALID_STRING'] %
                                                  ("Gram_to_brand_Price_Unit"))

            if not row[4] or not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[4]):
                raise serializers.ValidationError(
                    "Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | " + VALIDATION_ERROR_MESSAGES[
                        'INVALID_PRICE'])

            # if row[4] < product.product_mrp:
            #     raise serializers.ValidationError(
            #         "Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] +
            #         "brand_to_gram_price should be less than product mrp")

            if not row[5] or not re.match("^[\d\,]*$", row[5]):
                raise serializers.ValidationError(
                    "Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | " + VALIDATION_ERROR_MESSAGES[
                        'EMPTY_OR_NOT_VALID'] % "Case_size")

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            create_bulk_product_vendor_mapping(validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        attribute_id = BulkUploadForProductAttributes.objects.values('id').last()
        if attribute_id:
            validated_data['file'].name = 'create_product_vendor_mapping' + '-' + str(attribute_id['id'] + 1) + '.csv '
        else:
            validated_data['file'].name = 'create_product_vendor_mapping' + '-' + str(1) + '.csv'
        product_attribute = BulkUploadForProductAttributes.objects.create(file=validated_data['file'],
                                                                          updated_by=validated_data['updated_by'],
                                                                          upload_type='create_product_vendor_mapping')

        return product_attribute

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%b %d %Y %I:%M%p")
        representation['updated_at'] = instance.updated_at.strftime("%b %d %Y %I:%M%p")
        return representation


class DownloadProductVendorMappingSerializers(serializers.ModelSerializer):
    class Meta:
        model = ProductVendorMapping
        fields = ('vendor_id',)

    def validate(self, data):

        if not 'vendor_id' in self.initial_data:
            raise serializers.ValidationError(_('Please Select One vendor id!'))

        elif 'vendor_id' in self.initial_data and self.initial_data['vendor_id']:
            vendor_val = get_validate_vendor(self.initial_data['vendor_id'])
            if 'error' in vendor_val:
                raise serializers.ValidationError(_(vendor_val["error"]))
            data['vendor_id'] = vendor_val['vendor']

        if 'download_type' in self.initial_data:
            data['download_type'] = self.initial_data['download_type']
        else:
            raise serializers.ValidationError(_('Please Select a download type!'))

        return data

    def create(self, validated_data):
        response = create_product_vendor_mapping_sample_file(validated_data, validated_data["download_type"])
        return response


class BulkSlabProductPriceSerializers(serializers.ModelSerializer):
    """
      Bulk Product Price Creation
    """
    file = serializers.FileField(label='Upload Slab Product Prices')

    class Meta:
        model = ProductPrice
        fields = ('file',)

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError(_('Sorry! Only csv file accepted.'))

        reader = csv.reader(codecs.iterdecode(data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if isBlankRow(row, len(first_row)):
                continue

            if not str(row[0]).strip() or not Product.objects.filter(product_sku=str(row[0]).strip()).exists():
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'SKU'"))

            if not str(row[2]).strip() or not Shop.objects.filter(id=int(row[2]), shop_type__shop_type__in=['sp']). \
                    exists():
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Shop ID'"))

            if not str(row[5]).strip():
                raise ValidationError(_(f"Row {row_id + 1} | Empty 'Slab 1 Quantity'"))
            try:
                slab_1_qty = int(row[5])
            except Exception:
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Quantity'"))

            if not str(row[6]).strip():
                raise ValidationError(_(f"Row {row_id + 1} | Empty 'Slab 1 Selling price'"))
            try:
                selling_price_slab_1 = float(row[6])
            except Exception:
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Selling price'"))

            offer_price_1 = None
            if str(row[7]).strip():
                try:
                    offer_price_1 = float(row[7])
                except Exception:
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Offer Price 1'"))

                if offer_price_1 >= selling_price_slab_1:
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Offer Price'"))

                if not str(row[8]).strip() or not str(row[9]).strip() or \
                        not isDateValid(row[8], "%d-%m-%y") or not isDateValid(row[9], "%d-%m-%y") \
                        or getStrToDate(row[8], "%d-%m-%y") < datetime.datetime.today().date() \
                        or getStrToDate(row[9], "%d-%m-%y") < datetime.datetime.today().date() \
                        or getStrToDate(row[8], "%d-%m-%y") > getStrToDate(row[9], "%d-%m-%y"):
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Offer Start/End Date'"))

            product = Product.objects.get(product_sku=str(row[0]).strip())
            selling_price_per_saleable_unit = selling_price_slab_1
            if product.parent_product.is_ptr_applicable:
                ptr_percent = product.parent_product.ptr_percent
                ptr_type = product.parent_product.ptr_type
                sups = selling_price_slab_1
                if ptr_type == ParentProduct.PTR_TYPE_CHOICES.MARK_UP:
                    sups = product.product_mrp / (1 + (ptr_percent / 100))
                elif ptr_type == ParentProduct.PTR_TYPE_CHOICES.MARK_DOWN:
                    sups = product.product_mrp * (1 - (ptr_percent / 100))
                selling_price_per_saleable_unit = float(round(sups, 2))

            if selling_price_per_saleable_unit != selling_price_slab_1:
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Selling Price', PTR "
                                        f"{selling_price_per_saleable_unit} != Slab1 SP {selling_price_slab_1}"))

            if product.product_mrp and selling_price_slab_1 > float(product.product_mrp):
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Selling Price', Slab1 SP "
                                        f"{selling_price_slab_1} > MRP {product.product_mrp}"))

            if slab_1_qty > 0:
                if not str(row[10]).strip():
                    raise ValidationError(_(f"Row {row_id + 1} | Empty 'Slab 2 Quantity'"))
                try:
                    slab_2_qty = int(row[10])
                except Exception:
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Quantity'"))

                if not str(row[11]).strip():
                    raise ValidationError(_(f"Row {row_id + 1} | Empty 'Slab 2 Selling Price'"))
                try:
                    selling_price_slab_2 = float(row[11])
                except Exception:
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Selling Price'"))

                offer_price_2 = None
                if str(row[12]).strip():
                    try:
                        offer_price_2 = float(row[12])
                    except Exception:
                        raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Offer Price'"))

                if slab_2_qty != slab_1_qty + 1:
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Quantity'"))

                if selling_price_slab_2 <= 0:
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Selling Price'"))

                if selling_price_slab_2 >= selling_price_slab_1:
                    raise ValidationError(
                        _(f"Row {row_id + 1} | Invalid 'Slab 2 Selling Price', Slab2 SP {selling_price_slab_2} >= "
                          f"Slab1 SP {selling_price_slab_1}"))

                if offer_price_1 and selling_price_slab_2 >= offer_price_1:
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Selling Price', Slab2 SP "
                          f"{selling_price_slab_2} >= Slab 1 Offer Price {offer_price_1}"))

                if offer_price_2 and offer_price_2 >= selling_price_slab_2:
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Offer Price'"))

                if (not isDateValid(row[13], "%d-%m-%y") or not isDateValid(row[14], "%d-%m-%y")
                        or getStrToDate(row[13], "%d-%m-%y") < datetime.datetime.today().date()
                        or getStrToDate(row[14], "%d-%m-%y") < datetime.datetime.today().date()
                        or getStrToDate(row[13], "%d-%m-%y") > getStrToDate(row[14], "%d-%m-%y")):
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Offer Start/End Date'"))
        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            product_price = create_bulk_product_slab_price(validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        if product_price:
            raise serializers.ValidationError(_(product_price))
        return "Slab Product Prices uploaded successfully !"
