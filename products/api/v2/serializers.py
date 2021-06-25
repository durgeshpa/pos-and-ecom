import re
import json

from pyexcel_xlsx import get_data as xlsx_get
from django.db import transaction

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from products.models import Product, ParentProductTaxMapping, ParentProduct, ParentProductCategory, ParentProductImage, \
    ProductHSN, ProductCapping, ProductVendorMapping, ProductImage, ProductPrice, ProductHSN, Tax, ProductSourceMapping, \
    ProductPackingMapping, DestinationRepackagingCostMapping, CentralLog, BulkUploadForProductAttributes
from categories.models import Category
from brand.models import Brand, Vendor
from categories.common_validators import get_validate_category
from products.common_function import get_excel_file_data, create_master_data


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


class UploadMasterDataSerializers(serializers.ModelSerializer):
    file = serializers.FileField(label='Upload Master Data', required=True)
    select_an_option = ChoiceField(choices=DATA_TYPE_CHOICES, required=True, write_only=True)

    class Meta:
        model = BulkUploadForProductAttributes
        fields = ('file', 'select_an_option',)

    def validate(self, data):
        if not data['file'].name[-5:] in '.xlsx':
            raise serializers.ValidationError(_('Sorry! Only excel(xlsx) file accepted.'))
        excel_file_data = xlsx_get(self.initial_data['file'])['Users']

        if data['select_an_option'] == "master_data" or data['select_an_option'] == "inactive_status" or \
                data['select_an_option'] == "child_parent" or data['select_an_option'] == "child_data" or \
                data['select_an_option'] == "parent_data":
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
            self.read_file(excel_file_data, self.initial_data['select_an_option'], self.initial_data['category_id'])
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
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['parent_id']} | 'Parent ID' doesn't exist."))
                    parent_product = ParentProduct.objects.filter(parent_id=row['parent_id'])
                    if 'sku_id' not in row.keys():
                        if not ParentProductCategory.objects.filter(category=int(category),
                                                                    parent_product=parent_product[0].id).exists():
                            categry = Category.objects.values('category_name').filter(id=int(category))
                            raise serializers.ValidationError(_(f"Row {row_num} | Please upload Products of Category "
                                                                f"({categry[0]['category_name']}) that you have "
                                                                f"selected in Dropdown Only! "))
                if 'parent_name' in header_list and 'parent_name' in row.keys():
                    if row['parent_name'] != '':
                        if not ParentProduct.objects.filter(name=row['parent_name']).exists():
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['parent_name']} | 'Parent Name' doesn't "
                                  f"exist."))
                if 'status' in header_list and 'status' in row.keys():
                    if row['status'] != '':
                        status_list = ['active', 'deactivated', 'pending_approval']
                        if row['status'] not in status_list:
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['status']} | 'Status can either be 'Active',"
                                  f"'Pending Approval' or 'Deactivated'!"))
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
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | 'Weight Value' can only be a numeric value."))
                if 'hsn' in header_list and 'hsn' in row.keys():
                    if row['hsn'] != '':
                        if not ProductHSN.objects.filter(
                                product_hsn_code=row['hsn']).exists() and not ProductHSN.objects.filter(
                                product_hsn_code='0' + str(row['hsn'])).exists():
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['hsn']} |'HSN' doesn't exist in the system."))
                if 'tax_1(gst)' in header_list and 'tax_1(gst)' in row.keys():
                    if row['tax_1(gst)'] != '':
                        if not Tax.objects.filter(tax_name=row['tax_1(gst)']).exists():
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['tax_1(gst)']} | Invalid Tax(GST)!"))
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
                        if not re.match("^\d+$", str(row['max_inventory_in_days'])) or row['max_inventory_in_days'] < 1 \
                                or row['max_inventory_in_days'] > 999:
                            raise serializers.ValidationError(
                                _(f"Row {row_num} | {row['max_inventory_in_days']} |'Max Inventory In Days' is invalid."))

                if 'is_ars_applicable' in header_list and 'is_ars_applicable' in row.keys():
                    if row['is_ars_applicable'] != '':
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
                    elif row['is_ptr_applicable'].lower() == 'yes' and \
                            ('ptr_type' not in row.keys() or row['ptr_type'] == '' or row['ptr_type'].lower() not in [
                                'mark up', 'mark down']):
                        raise serializers.ValidationError(_(f"Row {row_num} | "
                                                            f"'ptr_type' can either be 'Mark Up' or 'Mark Down' "))
                    elif row['is_ptr_applicable'].lower() == 'yes' \
                            and (
                            'ptr_percent' not in row.keys() or row['ptr_percent'] == '' or 100 < row['ptr_percent'] or
                            row['ptr_percent'] < 0):
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
                if 'sku_id' in row.keys():
                    if row['sku_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'parent_id' not in row.keys():
                    raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'parent_id' in row.keys():
                    if row['parent_id'] == '':
                        raise serializers.ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'status' not in row.keys():
                    raise serializers.ValidationError(
                        _(f"Row {row_num} | 'Status can either be 'Active', 'Pending Approval' "
                          f"or 'Deactivated'!" |
                          'Status cannot be empty'))
                if 'status' in row.keys():
                    if row['sku_id'] == '':
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
        create_master_data(validated_data)
        attribute_id = BulkUploadForProductAttributes.objects.values('id').last()
        if attribute_id:
            validated_data['file'].name = validated_data['select_an_option'] + '-' + str(
                attribute_id['id'] + 1) + '.xlsx '
        else:
            validated_data['file'].name = validated_data['select_an_option'] + '-' + str(1) + '.xlsx'
        product_attribute = BulkUploadForProductAttributes.objects.create(file=validated_data['file'],
                                                                          updated_by=validated_data['updated_by'])

        return product_attribute
