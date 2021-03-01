import codecs
import re

from dal import autocomplete
from django import forms
import csv

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


from pos.models import RetailerProduct
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

    def validate_data(self, uploaded_data_by_user_list):
        row_num = 1
        for row in uploaded_data_by_user_list:
            row_num += 1
            if 'product_mrp' in row.keys():
                if not re.match("^\d+[.]?[\d]{0,2}$", str(row['product_mrp'])):
                    raise ValidationError(_(f"Row {row_num} | 'Product MRP' can only be a numeric value."))

            if 'selling_price' in row.keys():
                if not re.match("^\d+[.]?[\d]{0,2}$", str(row['selling_price'])):
                    raise ValidationError(_(f"Row {row_num} | 'Selling Price' can only be a numeric value."))

            if 'product_mrp' and 'selling_price' in row.keys():
                if int(row['selling_price']) > int(row['product_mrp']):
                    raise ValidationError(_(f"Selling Price cannot be greater than product mrp"))




    def read_file(self, headers, reader):
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
        self.validate_data(uploaded_data_by_user_list)

    def clean_file(self):
        if self.cleaned_data.get('file'):
            if not self.cleaned_data['file'].name[-4:] in ('.csv'):
                raise forms.ValidationError("Please upload only CSV File")
            else:
                reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
                headers = next(reader, None)
                self.read_file(headers, reader)
        return self.cleaned_data['file']