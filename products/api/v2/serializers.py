import re
import json
import logging
import codecs
import csv
import datetime
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from pyexcel_xlsx import get_data as xlsx_get
from collections import OrderedDict

from rest_framework import serializers
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES

from products.models import Product, ProductCategory, ProductImage, ProductHSN, ParentProduct, ParentProductCategory,\
    Tax, ParentProductImage, BulkUploadForProductAttributes, ParentProductTaxMapping, ProductSourceMapping, \
    DestinationRepackagingCostMapping, ProductPackingMapping
from categories.models import Category
from brand.models import Brand, Vendor

from categories.common_validators import get_validate_category
from products.common_function import get_excel_file_data, download_sample_file_master_data, create_master_data
from products.api.v1.serializers import UserSerializers


logger = logging.getLogger(__name__)

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')

DATA_TYPE_CHOICES = (
    ('master_data', 'master_data'),
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
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Inner Case Size' can not be empty."))
            elif not re.match("^\d+$", row[7]):
                raise serializers.ValidationError(
                    _(f"Row {row_id + 2} | 'Inner Case Size' can only be a numeric value."))

            if not row[8]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Product Type' can not be empty."))
            elif row[8].lower() not in ['b2b', 'b2c', 'both', 'both b2b and b2c']:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Product Type' can only be 'B2B', 'B2C', "
                                                    f"'Both B2B and B2C'."))

            if not row[9]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'is_ptr_applicable' can not be empty."))

            if str(row[9]).lower() not in ['yes', 'no']:
                raise serializers.ValidationError(_(f"Row {row_id + 2} |  {row['is_ptr_applicable']} | "
                                                    f"'is_ptr_applicable' can only be 'Yes' or 'No' "))

            elif row[9].lower() == 'yes' and (not row[10] or row[10] == '' or row[10].lower() not in [
                        'mark up', 'mark down']):
                raise serializers.ValidationError(_(f"Row {row_id + 2} | "
                                                    f"'ptr_type' can either be 'Mark Up' or 'Mark Down' "))

            elif row[9].lower() == 'yes' and (not row[11] or row[11] == '' or 100 < int(row[11]) or int(row[11]) < 0):
                raise serializers.ValidationError(_(f"Row {row_id + 2} | "
                                                    f"'ptr_percent' is invalid"))

            if not row[12]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'is_ars_applicable' can not be empty."))

            if str(row[12]).lower() not in ['yes', 'no']:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | {row[12]} |" 
                                                    f"'is_ars_applicable' can only be 'Yes' or 'No' "))

            if not row[13]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'max_inventory_in_days' can not be empty."))

            if not re.match("^\d+$", str(row[13])) or int(row[13]) < 1 or int(row[13]) > 999:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | {row[13]} "
                                                    f"|'Max Inventory In Days' is invalid."))

            if not row[14]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'is_lead_time_applicable' can not be empty."))

            if str(row[14]).lower() not in ['yes', 'no']:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | {row[15]} |"
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
                    inner_case_size=int(row[7]),product_type=row[8], is_ptr_applicable=(True if row[9].lower() == 'yes' else False),
                    ptr_type=(None if not row[9].lower() == 'yes' else ParentProduct.PTR_TYPE_CHOICES.MARK_UP
                              if row[10].lower() == 'mark up' else ParentProduct.PTR_TYPE_CHOICES.MARK_DOWN),
                    ptr_percent=(None if not row[9].lower() == 'yes' else row[11]),
                    is_ars_applicable=True if row[12].lower() == 'yes' else False,
                    max_inventory=row[13].lower(), is_lead_time_applicable=(True if row[14].lower() == 'yes' else False),
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
                child_product = Product.objects.create(parent_product=ParentProduct.objects.filter(parent_id=row[0]).last(),
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
                        ProductSourceMapping.objects.create(destination_sku=child_product, source_sku=pro_sku, status=True)
                    DestinationRepackagingCostMapping.objects.create(destination=child_product, raw_material=float(row[9]),
                                                                     wastage=float(row[10]), fumigation=float(row[11]),
                                                                     label_printing=float(row[12]), packing_labour=float(row[13]),
                                                                     primary_pm_cost=float(row[14]), secondary_pm_cost=float(row[15]))
                    ProductPackingMapping.objects.create(sku=child_product, packing_sku=Product.objects.get(product_sku=row[16]),
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
        fields = ('file', 'upload_type', 'updated_by', 'created_at', 'updated_at')

    def validate(self, data):
        if not data['file'].name[-5:] in '.xlsx':
            raise serializers.ValidationError(_('Sorry! Only excel(xlsx) file accepted.'))
        excel_file_data = xlsx_get(self.initial_data['file'])['Users']

        if data['upload_type'] == "master_data" or data['upload_type'] == "inactive_status" or \
                data['upload_type'] == "child_parent" or data['upload_type'] == "child_data" or \
                data['upload_type'] == "parent_data":

            if not 'category_id' in self.initial_data:
                raise serializers.ValidationError(_('Please Select One Category!'))

            elif 'category_id' in self.initial_data and self.initial_data['category_id']:
                category_val = get_validate_category(self.initial_data['category_id'])
                if 'error' in category_val:
                    raise serializers.ValidationError(_(category_val["error"]))
                self.initial_data['category_id'] = category_val['category']
        else:
            self.initial_data['category_id'] = None

        # Checking, whether excel file is empty or not!
        if excel_file_data:
            self.read_file(excel_file_data, self.initial_data['upload_type'], self.initial_data['category_id'])
        else:
            raise serializers.ValidationError("Excel File cannot be empty.Please add some data to upload it!")

        return data

    def validate_row(self, uploaded_data_list, header_list, category):
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
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['sku_id']} | 'SKU ID' doesn't exist."))
                    product = Product.objects.filter(product_sku=row['sku_id'])
                    if not Product.objects.filter(id=product[0].id, parent_product__parent_product_pro_category__category__category_name__icontains=
                                                  category.category_name).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | Please upload Products of Category "
                                                            f"({category.category_name}) that you have "
                                                            f"selected in Dropdown Only! "))

                if 'sku_name' in header_list and 'sku_name' in row.keys() and row['sku_name'] != '':
                    if not Product.objects.filter(product_name=row['sku_name']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['sku_name']} |"
                                                            f"'SKU Name' doesn't exist in the system."))

                if 'product_type' in header_list and 'product_type' in row.keys() and row['product_type'] != '':
                    product_type_list = ['b2b', 'b2c', 'both']
                    if row['product_type'] not in product_type_list:
                        raise serializers.ValidationError(
                            _(f"Row {row_num} | {row['product_type']} | 'Product Type can either be 'b2b',"
                              f"'b2c' or 'both'!"))

                if 'parent_id' in header_list and 'parent_id' in row.keys():
                    if row['parent_id'] != '':
                        if not ParentProduct.objects.filter(parent_id=row['parent_id']).exists():
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['parent_id']} | 'Parent ID' doesn't exist."))
                    parent_product = ParentProduct.objects.filter(parent_id=row['parent_id'])
                    if 'sku_id' not in row.keys():
                        if not ParentProductCategory.objects.filter(category=category.id, parent_product=parent_product[0].id).exists():
                            category = Category.objects.values('category_name').filter(id=category.category_name)
                            raise serializers.ValidationError(_(f"Row {row_num} | Please upload Products of Category "
                                                                f"({category.category_name}) that you have "
                                                                f"selected in Dropdown Only! "))

                if 'parent_name' in header_list and 'parent_name' in row.keys() and row['parent_name'] != '':
                    if not ParentProduct.objects.filter(name=row['parent_name']).exists():
                        raise serializers.ValidationError(
                            _(f"Row {row_num} | {row['parent_name']} | 'Parent Name' doesn't "
                              f"exist."))

                if 'status' in header_list and 'status' in row.keys() and row['status'] != '':
                    status_list = ['active', 'deactivated', 'pending_approval']
                    if row['status'] not in status_list:
                        raise serializers.ValidationError(
                            _(f"Row {row_num} | {row['status']} | 'Status can either be 'Active',"
                              f"'Pending Approval' or 'Deactivated'!"))

                if 'mrp' in header_list and 'mrp' in row.keys() and row['mrp'] != '':
                    if not re.match("^\d+[.]?[\d]{0,2}$", str(row['mrp'])):
                        raise serializers.ValidationError(
                            _(f"Row {row_num} | 'Product MRP' can only be a numeric value."))

                if 'weight_unit' in header_list and 'weight_unit' in row.keys() and row['weight_unit'] != '':
                    if str(row['weight_unit']).lower() not in ['gm']:
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Weight Unit' can only be 'gm'."))

                if 'weight_value' in header_list and 'weight_value' in row.keys() and row['weight_value'] != '':
                    if not re.match("^\d+[.]?[\d]{0,2}$", str(row['weight_value'])):
                        raise serializers.ValidationError(_(f"Row {row_num} |' "
                                                            f"Weight Value' can only be a numeric value."))

                if 'hsn' in header_list and 'hsn' in row.keys() and row['hsn'] != '':
                    if not ProductHSN.objects.filter(
                            product_hsn_code=row['hsn']).exists() and not ProductHSN.objects.filter(
                            product_hsn_code='0' + str(row['hsn'])).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['hsn']} |"
                                                            f"'HSN' doesn't exist in the system."))

                if 'tax_1(gst)' in header_list and 'tax_1(gst)' in row.keys() and row['tax_1(gst)'] != '':
                    if not Tax.objects.filter(tax_name=row['tax_1(gst)']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['tax_1(gst)']} | Invalid Tax(GST)!"))

                if 'tax_2(cess)' in header_list and 'tax_2(cess)' in row.keys() and row['tax_2(cess)'] != '':
                    if not Tax.objects.filter(tax_name=row['tax_2(cess)']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['tax_2(cess)']} "
                                                            f"| Invalid Tax(CESS)!"))

                if 'tax_3(surcharge)' in header_list and 'tax_3(surcharge)' in row.keys() and row['tax_3(surcharge)'] != '':
                    if not Tax.objects.filter(tax_name=row['tax_3(surcharge)']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['tax_3(surcharge)']} "
                                                            f"| Invalid Tax(Surcharge)!"))

                if 'inner_case_size' in header_list and 'inner_case_size' in row.keys() and row['inner_case_size'] != '':
                    if not re.match("^\d+$", str(row['inner_case_size'])):
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['inner_case_size']} "
                                                            f"| 'Inner Case Size' can only be a numeric value."))

                if 'brand_id' in header_list and 'brand_id' in row.keys() and row['brand_id'] != '':
                    if not Brand.objects.filter(id=row['brand_id']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['brand_id']} | "
                                                            f"'Brand_ID' doesn't exist in the system "))

                if 'brand_name' in header_list and 'brand_name' in row.keys() and row['brand_name'] != '':
                    if not Brand.objects.filter(brand_name=row['brand_name']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['brand_name']} | "
                                                            f"'Brand_Name' doesn't exist in the system "))

                if 'sub_brand_id' in header_list and 'sub_brand_id' in row.keys() and row['sub_brand_id'] != '':
                    if not Brand.objects.filter(id=row['sub_brand_id']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['sub_brand_id']} | "
                                                            f"'Sub_Brand_ID' doesn't exist in the system "))

                if 'sub_brand_name' in header_list and 'sub_brand_id' in row.keys() and row['sub_brand_name'] != '':
                    if not Brand.objects.filter(brand_name=row['sub_brand_name']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['sub_brand_name']} | "
                                                            f"'Sub_Brand_Name' doesn't exist in the system "))

                if 'category_id' in header_list and 'category_id' in row.keys() and row['category_id'] != '':
                    if not Category.objects.filter(id=row['category_id']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['category_id']} | "
                                                            f"'Category_ID' doesn't exist in the system "))

                if 'category_name' in header_list and 'category_name' in row.keys() and row['category_name'] != '':
                    if not Category.objects.filter(category_name=row['category_name']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['category_name']} | "
                                                            f"'Category_Name' doesn't exist in the system "))

                if 'sub_category_id' in header_list and 'sub_category_id' in row.keys() and row['sub_category_id'] != '':
                    if not Category.objects.filter(id=row['sub_category_id']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['sub_category_id']} | "
                                                            f"'Sub_Category_ID' doesn't exist in the system "))

                if 'sub_category_name' in header_list and 'sub_category_name' in row.keys() and row['sub_category_name'] != '':
                    if not Category.objects.filter(category_name=row['sub_category_name']).exists():
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['sub_category_name']} | "
                                                            f"'Sub_Category_Name' doesn't exist in the system "))

                if 'max_inventory_in_days' in header_list and 'max_inventory_in_days' in row.keys() \
                        and row['max_inventory_in_days'] != '':
                    if not re.match("^\d+$", str(row['max_inventory_in_days'])) or row['max_inventory_in_days'] < 1 \
                            or row['max_inventory_in_days'] > 999:
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['max_inventory_in_days']} |'Max Inventory In Days' is invalid."))

                if 'is_ars_applicable' in header_list and 'is_ars_applicable' in row.keys() and row['is_ars_applicable'] != '':
                    if str(row['is_ars_applicable']).lower() not in ['yes', 'no']:
                        raise serializers.ValidationError(
                            _(f"Row {row_num} | {row['is_ars_applicable']} |"
                              f"'is_ars_applicable' can only be 'Yes' or 'No' "))

                if 'is_lead_time_applicable' in header_list and 'is_lead_time_applicable' in row.keys() and \
                        row['is_lead_time_applicable'] != '':
                    if str(row['is_lead_time_applicable']).lower() not in ['yes', 'no']:
                        raise serializers.ValidationError(
                            _(f"Row {row_num} | {row['is_lead_time_applicable']} |"
                              f"'is_lead_time_applicable' can only be 'Yes' or 'No' "))

                if 'is_ptr_applicable' in header_list and 'is_ptr_applicable' in row.keys():
                    if row['is_ptr_applicable'] != '' and str(row['is_ptr_applicable']).lower() not in ['yes', 'no']:
                        raise serializers.ValidationError(_(f"Row {row_num} | {row['is_ptr_applicable']} | "
                                                            f"'is_ptr_applicable' can only be 'Yes' or 'No' "))
                    elif row['is_ptr_applicable'].lower() == 'yes' and \
                            ('ptr_type' not in row.keys() or row['ptr_type'] == '' or row['ptr_type'].lower() not in [
                                'mark up', 'mark down']):
                        raise serializers.ValidationError(_(f"Row {row_num} | "
                                                            f"'ptr_type' can either be 'Mark Up' or 'Mark Down' "))
                    elif row['is_ptr_applicable'].lower() == 'yes' \
                            and ('ptr_percent' not in row.keys() or row['ptr_percent'] == '' or 100 < row['ptr_percent']
                                 or row['ptr_percent'] < 0):
                        raise serializers.ValidationError(_(f"Row {row_num} | "
                                                            f"'ptr_percent' is invalid"))

                if 'repackaging_type' in header_list and 'repackaging_type' in row.keys() and row['repackaging_type'] != '':
                    repack_type = ['none', 'source', 'destination', 'packing_material']
                    if row['repackaging_type'] not in repack_type:
                        raise serializers.ValidationError(
                            _(f"Row {row_num} | {row['repackaging_type']} | 'Repackaging Type can either be 'none',"
                              f"'source', 'destination' or 'packing_material'!"))

                if 'repackaging_type' in header_list and 'repackaging_type' in row.keys() and row['repackaging_type'] == 'destination':
                    mandatory_fields = ['raw_material', 'wastage', 'fumigation', 'label_printing',
                                        'packing_labour', 'primary_pm_cost', 'secondary_pm_cost', 'final_fg_cost',
                                        'conversion_cost']
                    if 'source_sku_id' not in row.keys():
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Source_SKU_ID' can't be empty "
                                                            f"when repackaging_type is destination"))
                    if 'source_sku_id' in row.keys() and row['source_sku_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Source_SKU_ID' can't be empty "
                                                            f"when repackaging_type is destination"))
                    if 'source_sku_name' not in row.keys():
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Source_SKU_Name' can't be empty "
                                                            f"when repackaging_type is destination"))
                    if 'source_sku_name' in row.keys() and row['source_sku_name'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Source_SKU_Name' can't be empty "
                                                            f"when repackaging_type is destination"))
                    for field in mandatory_fields:
                        if field not in header_list:
                            raise serializers.ValidationError(
                                _(f"{mandatory_fields} are the essential headers and cannot be empty "
                                  f"when repackaging_type is destination"))
                        if row[field] == '':
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row[field]} | {field} cannot be empty"
                                  f"| {mandatory_fields} are the essential fields when "
                                  f"repackaging_type is destination"))
                        if not re.match("^\d+[.]?[\d]{0,2}$", str(row[field])):
                            raise serializers.ValidationError(_(f"Row {row_num} | {row[field]} | "
                                                                f"{field} can only be a numeric or decimal value."))

                    if 'source_sku_id' in header_list and 'source_sku_id' in row.keys() and row['source_sku_id'] != '':
                        p = re.compile('\'')
                        skuIDs = p.sub('\"', row['source_sku_id'])
                        SKU_IDS = json.loads(skuIDs)
                        for sk in SKU_IDS:
                            if not Product.objects.filter(product_sku=sk).exists():
                                raise serializers.ValidationError(
                                    _(f"Row {row_num} | {sk} | 'Source SKU ID' doesn't exist."))
                    if 'source_sku_name' in header_list and 'source_sku_name' in row.keys() and row['source_sku_name'] != '':
                        q = re.compile('\'')
                        source_sku_name = q.sub('\"', row['source_sku_name'])
                        sku_names = json.loads(source_sku_name)
                        for sk in sku_names:
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
        if upload_master_data == "master_data":
            row_num = 1
            required_columns = ['sku_id', 'sku_name', 'parent_id', 'parent_name', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(
                        _(f"{required_columns} are mandatory columns for 'Upload Master Data'"))
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
                    raise serializers.ValidationError(
                        _(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'! | "
                          f"Status cannot be empty"))
                if 'status' in row.keys():
                    if row['sku_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))
        if upload_master_data == "inactive_status":
            row_num = 1
            required_columns = ['sku_id', 'sku_name', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(
                        _(f"{required_columns} are mandatory columns for 'Set Inactive Status'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'status' not in row.keys():
                    raise serializers.ValidationError(
                        _(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
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
        if upload_master_data == "sub_brand_with_brand":
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
        if upload_master_data == "sub_category_with_category":
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
        if upload_master_data == "child_parent":
            row_num = 1
            required_columns = ['sku_id', 'parent_id', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(
                        _(f"{required_columns} are mandatory column for 'Child and Parent Mapping'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'sku_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_id' in row.keys() and row['sku_id'] == '':
                    raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'parent_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'parent_id' in row.keys() and row['parent_id'] == '':
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'status' not in row.keys():
                    raise serializers.ValidationError(
                        _(f"Row {row_num} | 'Status can either be 'Active', 'Pending Approval' "
                          f"or 'Deactivated'!" |
                          'Status cannot be empty'))
                if 'status' in row.keys() and row['status'] == '':
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))
        if upload_master_data == "child_data":
            required_columns = ['sku_id', 'sku_name', 'status']
            row_num = 1
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(
                        _(f"{required_columns} are mandatory columns for 'Set Child Data'"))
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
        if upload_master_data == "parent_data":
            row_num = 1
            required_columns = ['parent_id', 'parent_name', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise serializers.ValidationError(
                        _(f"{required_columns} are mandatory columns for 'Set Parent Data'"))
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
                    raise serializers.ValidationError(
                        _(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                          'Status cannot be empty'))
                if 'status' in row.keys():
                    if row['status'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))

        self.validate_row(uploaded_data_list, header_list, category)

    def check_headers(self, excel_file_headers, required_header_list):
        for head in excel_file_headers:
            if not head in required_header_list:
                raise serializers.ValidationError(_(f"Invalid Header | {head} | Allowable headers for the upload "
                                                    f"are: {required_header_list}"))

    def read_file(self, excel_file, upload_master_data, category):
        """
        Template Validation (Checking, whether the excel file uploaded by user is correct or not!)
        """
        # Checking the headers of the excel file
        if upload_master_data == "master_data":
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

        if upload_master_data == "inactive_status":
            required_header_list = ['sku_id', 'sku_name', 'mrp', 'status']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        if upload_master_data == "sub_brand_with_brand":
            required_header_list = ['brand_id', 'brand_name', 'sub_brand_id', 'sub_brand_name']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        if upload_master_data == "sub_category_with_category":
            required_header_list = ['category_id', 'category_name', 'sub_category_id', 'sub_category_name']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        if upload_master_data == "child_parent":
            required_header_list = ['sku_id', 'sku_name', 'parent_id', 'parent_name', 'status']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        if upload_master_data == "child_data":
            required_header_list = ['sku_id', 'sku_name', 'ean', 'mrp', 'weight_unit', 'weight_value',
                                    'status', 'repackaging_type', 'source_sku_id', 'source_sku_name',
                                    'raw_material', 'wastage', 'fumigation', 'label_printing', 'packing_labour',
                                    'primary_pm_cost', 'secondary_pm_cost', 'final_fg_cost', 'conversion_cost']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        if upload_master_data == "parent_data":
            required_header_list = ['parent_id', 'parent_name', 'product_type', 'hsn', 'tax_1(gst)', 'tax_2(cess)',
                                    'tax_3(surcharge)', 'inner_case_size', 'brand_id', 'brand_name', 'sub_brand_id',
                                    'sub_brand_name', 'category_id', 'category_name', 'sub_category_id',
                                    'sub_category_name', 'status', 'is_ptr_applicable', 'ptr_type', 'ptr_percent',
                                    'is_ars_applicable', 'max_inventory_in_days', 'is_lead_time_applicable']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        # Checking, whether the user uploaded the data below the headings or not!
        if len(excel_file) > 0:
            uploaded_data_by_user_list, excelFile_headers = get_excel_file_data(excel_file)
            self.check_mandatory_columns(uploaded_data_by_user_list, excelFile_headers, upload_master_data, category)
        else:
            raise serializers.ValidationError("Please add some data below the headers to upload it!")

    @transaction.atomic
    def create(self, validated_data):
        try:
            create_master_data(validated_data)
            attribute_id = BulkUploadForProductAttributes.objects.values('id').last()
            if attribute_id:
                validated_data['file'].name = validated_data['upload_type'] + '-' + str(
                    attribute_id['id'] + 1) + '.xlsx '
            else:
                validated_data['file'].name = validated_data['upload_type'] + '-' + str(1) + '.xlsx'
            product_attribute = BulkUploadForProductAttributes.objects.create(file=validated_data['file'],
                                updated_by=validated_data['updated_by'], upload_type=validated_data['upload_type'])
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
        response = download_sample_file_master_data(validated_data)
        return response


class ProductCategoryMappingSerializers(serializers.Serializer):
    file = serializers.FileField(label='Upload ProductCategoryMapping Data', required=True)
    updated_by = UserSerializers(read_only=True)

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError(_("Sorry! Only csv file accepted"))
        self.validate_row(data['file'])
        return data['file']

    def validate_row(self, data):
        reader = csv.reader(codecs.iterdecode(data, 'utf-8', errors='ignore'))
        next(reader)
        for row_id, row in enumerate(reader):
            if not row[0]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'gf_code' can not be empty."))
            if not row[1]:
                raise serializers.ValidationError(_(f"Row {row_id + 1} | 'category_id' can not be empty."))

    def create(self, validated_data):
        pass


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








