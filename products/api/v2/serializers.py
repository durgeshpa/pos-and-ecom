import re
import logging
import codecs
import csv
import datetime
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from collections import OrderedDict

from rest_framework import serializers
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES

from products.models import Product, ProductCategory, ProductImage, ProductHSN, ParentProduct, ParentProductCategory, \
    Tax, ParentProductImage, BulkUploadForProductAttributes, ParentProductTaxMapping, ProductSourceMapping, \
    DestinationRepackagingCostMapping, ProductPackingMapping, ParentProductTaxMapping, BulkProductTaxUpdate
from categories.models import Category
from brand.models import Brand, Vendor

from products.common_validators import read_file
from categories.common_validators import get_validate_category
from products.common_function import download_sample_file_update_master_data, update_master_data
from products.api.v1.serializers import UserSerializers
from products.upload_file import upload_file_to_s3

logger = logging.getLogger(__name__)

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')

DATA_TYPE_CHOICES = (
    ('product_status_update_inactive', 'product_status_update_inactive'),
    ('sub_brand_with_brand_mapping', 'sub_brand_with_brand_mapping'),
    ('sub_category_with_category_mapping', 'sub_category_with_category_mapping'),
    ('child_parent_product_update', 'child_parent_product_update'),
    ('child_product_update', 'child_product_update'),
    ('parent_product_update', 'parent_product_update'),
    ('product_tax_update', 'product_tax_update'),
    ('create_child_product', 'create_child_product'),
    ('create_parent_product', 'create_parent_product'),
    ('create_category', 'create_category'),
    ('create_brand', 'create_brand'),

)


class ChoiceField(serializers.ChoiceField):
    def to_internal_value(self, data):
        for key, val in self._choices.items():
            if val == data:
                return key
        self.fail('invalid_choice', input=data)


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

        if data['upload_type'] == "product_status_update_inactive" or data['upload_type'] == "parent_product_update" \
                or data['upload_type'] == "child_parent_product_update" or data['upload_type'] == "child_product_update":

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
            update_master_data(validated_data)
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
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

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
                or data['upload_type'] == "child_parent_product_update" or data['upload_type'] == "child_product_update":

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
        response, csv_filename = download_sample_file_update_master_data(validated_data)
        object_url = upload_file_to_s3(response, csv_filename)
        return object_url


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
        result = OrderedDict()
        result['data'] = str(instance)
        return result


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
        result = OrderedDict()
        result['data'] = str(instance)
        return result
