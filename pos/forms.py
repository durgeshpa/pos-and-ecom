import codecs
import re
import decimal

from dal import autocomplete
from django import forms
import csv

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


from pos.models import RetailerProduct
from products.models import Product
from shops.models import Shop


class RetailerProductsCSVDownloadForm(forms.Form):
    shop = forms.ModelChoiceField(
        label='Select Shop',
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(url='retailer-product-autocomplete',)
    )


class RetailerProductsCSVUploadForm(forms.Form):
    shop = forms.ModelChoiceField(
        label='Select Shop',
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(url='retailer-product-autocomplete', )
    )
    file = forms.FileField(label='Upload Products')

    def check_mandatory_data(self, row, key_string, row_num):
        if key_string not in row.keys():
            raise ValidationError(_(f"Row {row_num} | Please provide {key_string}"))

        if key_string in row.keys():
            if row[key_string] == '':
                raise ValidationError(_(f"Row {row_num} | Please provide {key_string}"))

    def validate_data_for_create_products(self, uploaded_data_by_user_list):
        row_num = 1
        for row in uploaded_data_by_user_list:
            row_num += 1
            self.check_mandatory_data(row, 'product_name', row_num)
            self.check_mandatory_data(row, 'product_mrp', row_num)
            self.check_mandatory_data(row, 'selling_price', row_num)

            if not re.match("^\d+[.]?[\d]{0,2}$", str(row['product_mrp'])):
                raise ValidationError(_(f"Row {row_num} | 'Product MRP' can only be a numeric value."))

            if not re.match("^\d+[.]?[\d]{0,2}$", str(row['selling_price'])):
                raise ValidationError(_(f"Row {row_num} | 'Selling Price' can only be a numeric value."))

            if decimal.Decimal(row['selling_price']) > decimal.Decimal(row['product_mrp']):
                raise ValidationError(_(f"Row {row_num} | 'Selling Price' cannot be greater than 'Product Mrp'"))

            if 'linked_product_sku' in row.keys():
                if row['linked_product_sku'] !='':
                    if not Product.objects.filter(product_sku=row['sku_id']).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['linked_product_sku']} | 'SKU ID' doesn't exist."))

    def validate_data_for_update_products(self, uploaded_data_by_user_list):
            pass

    def validate_data(self, uploaded_data_by_user_list, catalogue_product_status):
        if catalogue_product_status == 'update_products':
            self.validate_data_for_update_products(uploaded_data_by_user_list)
        else:
            self.validate_data_for_create_products(uploaded_data_by_user_list)

    def read_file(self, headers, reader, catalogue_product_status):
        uploaded_data_by_user_list = []
        csv_dict = {}
        count = 0
        for id, row in enumerate(reader):
            for ele in row:
                csv_dict[headers[count]] = ele
                count += 1
            uploaded_data_by_user_list.append(csv_dict)
            csv_dict = {}
            count = 0
        self.validate_data(uploaded_data_by_user_list, catalogue_product_status)

    def clean_file(self):
        if self.cleaned_data.get('file'):
            if not self.cleaned_data['file'].name[-4:] in ('.csv'):
                raise forms.ValidationError("Please upload only CSV File")
            else:
                reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
                catalogue_product_status = self.data.get('catalogue_product_status')
                headers = next(reader, None)
                self.read_file(headers, reader, catalogue_product_status)
        return self.cleaned_data['file']