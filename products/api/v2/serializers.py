import logging
import codecs
import csv

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from products.models import Product, ProductCategory, ProductImage, ProductHSN, ParentProduct, ParentProductCategory, \
    Tax, ParentProductImage, BulkUploadForProductAttributes, ParentProductTaxMapping, ProductSourceMapping, \
    DestinationRepackagingCostMapping, ProductPackingMapping, ParentProductTaxMapping, BulkProductTaxUpdate
from categories.models import Category
from brand.models import Brand
from products.common_validators import read_file
from categories.common_validators import get_validate_category
from products.bulk_common_function import download_sample_file_update_master_data, create_update_master_data
from products.api.v1.serializers import UserSerializers


logger = logging.getLogger(__name__)

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')

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
    )
    ),
    ('update_data', (
        ('child_product_update', 'Update Child Product'),
        ('parent_product_update', 'Update Parent Product'),
        ('category_update', 'Update Category'),
        ('brand_update', 'Update Brand'),
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
                "child_parent_product_update" or data['upload_type'] == "parent_product_update"\
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
                Brand.objects.get(id=int(brand_id))
            except:
                val_data = {
                    'is_valid': False,
                    'error': True,
                    'name': 'No Brand found with Brand ID {}'.format(brand_id),
                    'url': '#'
                }
                aborted_count += 1

            else:
                brand_obj = Brand.objects.filter(id=int(brand_id))
                brand_obj.update(id=brand_obj.last().id, brand_logo=img, updated_by=validated_data['updated_by'])
                val_data = {
                    'is_valid': True,
                    'url': brand_obj.last().brand_logo.url,
                    'brand_id': brand_id,
                    'brand_name': brand_obj.last().brand_name,
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
                Category.objects.get(id=int(cat_id))
            except:
                val_data = {
                    'is_valid': False,
                    'error': True,
                    'name': 'No Category found with Category ID {}'.format(cat_id),
                    'url': '#'
                }
                aborted_count += 1
            else:
                cat_obj = Category.objects.filter(id=int(cat_id))
                cat_obj.update(id=cat_obj.last().id, category_image=img, updated_by=validated_data['updated_by'])
                val_data = {
                    'is_valid': True,
                    'url': cat_obj.last().category_image.url,
                    'category_id': cat_id,
                    'category_name': cat_obj.last().category_name
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
