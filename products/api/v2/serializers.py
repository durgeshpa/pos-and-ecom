import re
import json
import logging
import codecs
import csv
import datetime
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from collections import OrderedDict
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES

from products.models import Product, ProductCategory, ProductImage, ProductHSN, ParentProduct, ParentProductCategory, \
    Tax, ParentProductImage, BulkUploadForProductAttributes, ParentProductTaxMapping, ProductSourceMapping, \
    DestinationRepackagingCostMapping, ProductPackingMapping, ParentProductTaxMapping, BulkProductTaxUpdate
from categories.models import Category
from brand.models import Brand, Vendor

from products.common_validators import read_file
from categories.common_validators import get_validate_category, product_category
from products.common_function import download_sample_file_master_data, create_master_data
from products.api.v1.serializers import UserSerializers
from products.upload_file import upload_file_to_s3


logger = logging.getLogger(__name__)

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')

DATA_TYPE_CHOICES = (
    ('inactive_status', 'inactive_status'),
    ('sub_brand_with_brand', 'sub_brand_with_brand'),
    ('sub_category_with_category', 'sub_category_with_category'),
    ('child_parent', 'child_parent'),
    ('child_data', 'child_data'),
    ('parent_data', 'parent_data'),
)


class ChoiceField(serializers.ChoiceField):
    def to_internal_value(self, data):
        for key, val in self._choices.items():
            if val == data:
                return key
        self.fail('invalid_choice', input=data)


class ParentProductBulkUploadSerializers(serializers.ModelSerializer):
    file = serializers.FileField(label='Upload Parent Product list', write_only=True, required=True)

    class Meta:
        model = ParentProduct
        fields = ('file',)

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(data['file'], 'utf-8', errors='ignore'))
        next(reader)
        for row_id, row in enumerate(reader):
            if not row[0]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Parent Name' can not be empty."))
            elif not re.match("^[ \w\$\_\,\%\@\.\/\#\&\+\-\(\)\*\!\:]*$", row[0]):
                raise serializers.ValidationError(
                    _(f"Row {row_id + 1} | {VALIDATION_ERROR_MESSAGES['INVALID_PRODUCT_NAME']}."))

            if not row[1]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Brand' can not be empty."))
            elif not Brand.objects.filter(brand_name=row[1].strip()).exists():
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Brand' doesn't exist in the system."))

            if not row[2]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Category' can not be empty."))
            else:
                if not Category.objects.filter(category_name=row[2].strip()).exists():
                    categories = row[2].split(',')
                    for cat in categories:
                        cat = cat.strip().replace("'", '')
                        if not Category.objects.filter(category_name=cat).exists():
                            raise serializers.ValidationError(
                                _(f"Row {row_id + 1} | 'Category' {cat.strip()} doesn't exist in the system."))
            if not row[3]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'HSN' can not be empty."))
            elif not ProductHSN.objects.filter(product_hsn_code=row[3].replace("'", '')).exists():
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'HSN' doesn't exist in the system."))

            if not row[4]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'GST' can not be empty."))
            elif not re.match("^([0]|[5]|[1][2]|[1][8]|[2][8])(\s+)?(%)?$", row[4]):
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'GST' can only be 0, 5, 12, 18, 28."))

            if row[5] and not re.match("^([0]|[1][2])(\s+)?%?$", row[5]):
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'CESS' can only be 0, 12."))

            if row[6] and not re.match("^[0-9]\d*(\.\d{1,2})?(\s+)?%?$", row[6]):
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Surcharge' can only be a numeric value."))

            if not row[7]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Inner Case Size' can not be empty."))
            elif not re.match("^\d+$", row[7]):
                raise serializers.ValidationError(
                    _(f"Row {row_id + 1} | 'Inner Case Size' can only be a numeric value."))

            if not row[8]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Product Type' can not be empty."))
            elif row[8].lower() not in ['b2b', 'b2c', 'both', 'both b2b and b2c']:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Product Type' can only be 'B2B', 'B2C', "
                                                    f"'Both B2B and B2C'."))

            if not row[9]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'is_ptr_applicable' can not be empty."))

            if str(row[9]).lower() not in ['yes', 'no']:
                raise serializers.ValidationError(_(f"Row {row_id + 1} |  {row['is_ptr_applicable']} | "
                                                    f"'is_ptr_applicable' can only be 'Yes' or 'No' "))

            elif row[9].lower() == 'yes' and (not row[10] or row[10] == '' or row[10].lower() not in [
                'mark up', 'mark down']):
                raise serializers.ValidationError(_(f"Row {row_id + 1} | "
                                                    f"'ptr_type' can either be 'Mark Up' or 'Mark Down' "))

            elif row[9].lower() == 'yes' and (not row[11] or row[11] == '' or 100 < int(row[11]) or int(row[11]) < 0):
                raise serializers.ValidationError(_(f"Row {row_id + 1} | "
                                                    f"'ptr_percent' is invalid"))

            if not row[12]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'is_ars_applicable' can not be empty."))

            if str(row[12]).lower() not in ['yes', 'no']:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | {row[12]} |"
                                                    f"'is_ars_applicable' can only be 'Yes' or 'No' "))

            if not row[13]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'max_inventory_in_days' can not be empty."))

            if not re.match("^\d+$", str(row[13])) or int(row[13]) < 1 or int(row[13]) > 999:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | {row[13]} "
                                                    f"|'Max Inventory In Days' is invalid."))

            if not row[14]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'is_lead_time_applicable' can not be empty."))

            if str(row[14]).lower() not in ['yes', 'no']:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | {row[15]} |"
                                                    f"'is_lead_time_applicable' can only be 'Yes' or 'No' "))

        return data

    @transaction.atomic
    def create(self, validated_data):
        reader = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        next(reader)
        parent_product_list = []
        try:
            for row in reader:
                parent_product = ParentProduct.objects.create(
                    name=row[0].strip(), parent_brand=Brand.objects.filter(brand_name=row[1].strip()).last(),
                    product_hsn=ProductHSN.objects.filter(product_hsn_code=row[3].replace("'", '')).last(),
                    inner_case_size=int(row[7]), product_type=row[8],
                    is_ptr_applicable=(True if row[9].lower() == 'yes' else False),
                    ptr_type=(None if not row[9].lower() == 'yes' else ParentProduct.PTR_TYPE_CHOICES.MARK_UP
                    if row[10].lower() == 'mark up' else ParentProduct.PTR_TYPE_CHOICES.MARK_DOWN),
                    ptr_percent=(None if not row[9].lower() == 'yes' else row[11]),
                    is_ars_applicable=True if row[12].lower() == 'yes' else False,
                    max_inventory=row[13].lower(),
                    is_lead_time_applicable=(True if row[14].lower() == 'yes' else False),
                    created_by=validated_data['created_by']
                )

                parent_gst = int(row[4])
                ParentProductTaxMapping.objects.create(
                    parent_product=parent_product,
                    tax=Tax.objects.filter(tax_type='gst', tax_percentage=parent_gst).last())

                parent_cess = int(row[5]) if row[5] else 0
                ParentProductTaxMapping.objects.create(
                    parent_product=parent_product,
                    tax=Tax.objects.filter(tax_type='cess', tax_percentage=parent_cess).last())

                parent_surcharge = float(row[6]) if row[6] else 0
                if Tax.objects.filter(tax_type='surcharge', tax_percentage=parent_surcharge).exists():
                    ParentProductTaxMapping.objects.create(
                        parent_product=parent_product,
                        tax=Tax.objects.filter(tax_type='surcharge', tax_percentage=parent_surcharge).last())
                else:
                    new_surcharge_tax = Tax.objects.create(tax_name='Surcharge - {}'.format(parent_surcharge),
                                                           tax_type='surcharge', tax_percentage=parent_surcharge,
                                                           tax_start_at=datetime.datetime.now())

                    ParentProductTaxMapping.objects.create(parent_product=parent_product, tax=new_surcharge_tax)

                if Category.objects.filter(category_name=row[2].strip()).exists():
                    ParentProductCategory.objects.create(
                        parent_product=parent_product,
                        category=Category.objects.filter(category_name=row[2].strip()).last())

                else:
                    categories = row[2].split(',')
                    for cat in categories:
                        cat = cat.strip().replace("'", '')
                        ParentProductCategory.objects.create(parent_product=parent_product,
                                                             category=Category.objects.filter(category_name=cat).last())

                parent_product_list.append(parent_product)

        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return parent_product_list


class ChildProductBulkUploadSerializers(serializers.ModelSerializer):
    file = serializers.FileField(label='Upload Child Product list', write_only=True, required=True)

    class Meta:
        model = Product
        fields = ('file',)

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(data['file'], 'utf-8', errors='ignore'))
        next(reader)
        for row_id, row in enumerate(reader):
            if not row[0]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Parent Product ID' can not be empty."))
            elif not ParentProduct.objects.filter(parent_id=row[0]).exists():
                raise serializers.ValidationError(
                    _(f"Row {row_id + 1} | 'Parent Product' doesn't exist in the system."))

            if not row[1]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Reason for Child SKU' can not be empty."))
            elif row[1].lower() not in ['default', 'different mrp', 'different weight', 'different ean', 'offer']:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Reason for Child SKU' can only be 'Default', "
                                                    f"'Different MRP', 'Different Weight', 'Different EAN', 'Offer'."))

            if not row[2]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Product Name' can not be empty."))
            elif not re.match("^[ \w\$\_\,\%\@\.\/\#\&\+\-\(\)\*\!\:]*$", row[2]):
                raise serializers.ValidationError(
                    _(f"Row {row_id + 1} | {VALIDATION_ERROR_MESSAGES['INVALID_PRODUCT_NAME']}."))

            if not row[3]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Product EAN Code' can not be empty."))
            elif not re.match("^[a-zA-Z0-9\+\.\-]*$", row[3].replace("'", '')):
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Product EAN Code' can only contain "
                                                    f"alphanumeric input."))

            if not row[4]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Product MRP' can not be empty."))
            elif not re.match("^\d+[.]?[\d]{0,2}$", row[4]):
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Product MRP' can only be a numeric value."))

            if not row[5]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Weight Value' can not be empty."))
            elif not re.match("^\d+[.]?[\d]{0,2}$", row[5]):
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Weight Value' can only be a numeric value."))

            if not row[6]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Weight Unit' can not be empty."))
            elif row[6].lower() not in ['gram']:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Weight Unit' can only be 'Gram'."))

            if not row[7]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Repackaging Type' can not be empty."))
            elif row[7] not in [lis[0] for lis in Product.REPACKAGING_TYPES]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Repackaging Type' is invalid."))
            if row[7] == 'destination':
                if not row[8]:
                    raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Source SKU Mapping' is required for "
                                                        f"Repackaging Type 'destination'."))
                else:
                    source_sku = False
                    for pro in row[8].split(','):
                        pro = pro.strip()
                        if pro is not '':
                            if Product.objects.filter(product_sku=pro, repackaging_type='source').exists():
                                source_sku = True
                            else:
                                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Source SKU Mapping' {pro} "
                                                                    f"is invalid."))
                    if not source_sku:
                        raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Source SKU Mapping' is required for "
                                                            f"Repackaging Type 'destination'."))

                if not row[16]:
                    raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Packing SKU' is required for Repackaging "
                                                        f"Type 'destination'."))
                elif not Product.objects.filter(product_sku=row[16], repackaging_type='packing_material').exists():
                    raise serializers.ValidationError(_(f"Row {row_id + 1} | Invalid Packing Sku"))

                if not row[17]:
                    raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Packing Material Weight "
                                                        f"(gm) per unit (Qty) Of Destination Sku' is required "
                                                        f"for Repackaging Type 'destination'."))
                elif not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[17]):
                    raise serializers.ValidationError(_(f"Row {row_id + 1} | Invalid 'Packing Material Weight "
                                                        f"(gm) per unit (Qty) Of Destination Sku'"))

                dest_cost_fields = ['Raw Material Cost', 'Wastage Cost', 'Fumigation Cost', 'Label Printing Cost',
                                    'Packing Labour Cost', 'Primary PM Cost', 'Secondary PM Cost']
                for i in range(0, 7):
                    if not row[i + 9]:
                        raise serializers.ValidationError(_(f"Row {row_id + 1} | {dest_cost_fields[i]} required for "
                                                            f"Repackaging Type 'destination'."))
                    elif not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[i + 9]):
                        raise serializers.ValidationError(_(f"Row {row_id + 1} | {dest_cost_fields[i]} is Invalid"))
        return data

    @transaction.atomic
    def create(self, validated_data):
        reader = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        next(reader)
        try:
            for row_id, row in enumerate(reader):
                child_product = Product.objects.create(
                    parent_product=ParentProduct.objects.filter(parent_id=row[0]).last(),
                    reason_for_child_sku=(row[1].lower()), product_name=row[2],
                    product_ean_code=row[3].replace("'", ''), product_mrp=float(row[4]),
                    weight_value=float(row[5]), weight_unit='gm' if 'gram' in row[6].lower() else 'gm',
                    repackaging_type=row[7], created_by=validated_data['created_by'])

                if row[7] == 'destination':
                    source_map = []
                    for product_skus in row[8].split(','):
                        pro = product_skus.strip()
                        if pro is not '' and pro not in source_map and \
                                Product.objects.filter(product_sku=pro, repackaging_type='source').exists():
                            source_map.append(pro)
                    for sku in source_map:
                        pro_sku = Product.objects.filter(product_sku=sku, repackaging_type='source').last()
                        ProductSourceMapping.objects.create(destination_sku=child_product, source_sku=pro_sku,
                                                            status=True)
                    DestinationRepackagingCostMapping.objects.create(destination=child_product,
                                                                     raw_material=float(row[9]),
                                                                     wastage=float(row[10]), fumigation=float(row[11]),
                                                                     label_printing=float(row[12]),
                                                                     packing_labour=float(row[13]),
                                                                     primary_pm_cost=float(row[14]),
                                                                     secondary_pm_cost=float(row[15]))
                    ProductPackingMapping.objects.create(sku=child_product,
                                                         packing_sku=Product.objects.get(product_sku=row[16]),
                                                         packing_sku_weight_per_unit_sku=float(row[17]))
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return child_product


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

        if data['upload_type'] == "inactive_status" or data['upload_type'] == "child_parent" or \
                data['upload_type'] == "child_data" or data['upload_type'] == "parent_data":

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
            create_master_data(validated_data)
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

        if data['upload_type'] == "master_data" or data['upload_type'] == "inactive_status" or \
                data['upload_type'] == "child_parent" or data['upload_type'] == "child_data" or \
                data['upload_type'] == "parent_data":
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
        response, csv_filename = download_sample_file_master_data(validated_data)
        upload_file_to_s3(response, csv_filename)
        return response


class ParentProductImageSerializers(serializers.ModelSerializer):
    """Handles creating, reading and updating parent product images."""

    image = serializers.ListField(
        child=serializers.FileField(max_length=100000,
                                    allow_empty_file=False,
                                    use_url=True, ), write_only=True)

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


class BulkProductTaxUpdateSerializers(serializers.ModelSerializer):
    file = serializers.FileField(label='Upload ProductTaxUpdate Data', required=True)
    updated_by = UserSerializers(read_only=True)

    class Meta:
        model = BulkProductTaxUpdate
        fields = ('file', 'updated_by')

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError(_("Sorry! Only csv file accepted"))

        reader = csv.reader(codecs.iterdecode(data['file'], 'utf-8', errors='ignore'))
        next(reader)
        for row_id, row in enumerate(reader):
            if not row[0]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'parent_id.' can not be empty."))
            elif not ParentProduct.objects.filter(parent_id=row[0].strip()).exists():
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'parent_id' doesn't exist in the system."))

            if not row[1]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'GST percentage ' can not be empty."))
            elif not row[1].isdigit():
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Please enter a valid GST percentage."))
            try:
                Tax.objects.get(tax_type='gst', tax_percentage=float(row[1]))
            except:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Tax with type GST and percentage"
                                                    f" does not exists in system."))

            if row[2] and not row[2].isdigit():
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Please enter a valid CESS percentage."))
            try:
                Tax.objects.get(tax_type='cess', tax_percentage=float(row[2]))
            except:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'Tax with type CESS and percentage"
                                                    f" does not exists in system."))

        return data

    @transaction.atomic
    def create(self, validated_data):
        reader = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        next(reader)
        try:
            for row_id, row in enumerate(reader):
                parent_pro_id = ParentProduct.objects.filter(parent_id=row[0].strip()).last()
                queryset = ParentProductTaxMapping.objects.filter(parent_product=parent_pro_id)
                if queryset.exists():
                    queryset.filter(tax__tax_type='gst').update(tax_id=row[1])
                    if row[2]:
                        tax = Tax.objects.get(tax_type='cess', tax_percentage=float(row[2]))
                        product_cess_tax = queryset.filter(tax__tax_type='cess')
                        if product_cess_tax.exists():
                            queryset.filter(tax__tax_type='cess').update(tax_id=tax)
                        else:
                            ParentProductTaxMapping.objects.create(parent_product=parent_pro_id, tax_id=tax)

            tax_update_attribute = BulkProductTaxUpdate.objects.create(file=validated_data['file'],
                                                                       updated_by=validated_data['updated_by'])

        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return tax_update_attribute


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