from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

import codecs
import re
import decimal
from dal import autocomplete
from django import forms
import csv

from pos.models import RetailerProduct, RetailerProductImage
from products.models import Product
from shops.models import Shop
from wms.models import PosInventory, PosInventoryState


class RetailerProductsForm(forms.ModelForm):
    linked_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:product-price-autocomplete', ),
        required=False
    )


class DiscountedRetailerProductsForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset = Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(
            url='retailer-product-autocomplete'
        )
    )
    product_ref = forms.ModelChoiceField(
        queryset=RetailerProduct.objects.filter(~Q(sku_type=4)),
        widget=autocomplete.ModelSelect2(
            url='discounted-product-autocomplete',
            forward=('shop',),
            attrs={"onChange": 'getProductDetails()'},
        )
    )
    product_ean_code = forms.CharField(required=False)
    mrp = forms.DecimalField(required=False)
    selling_price = forms.DecimalField(min_value=0, decimal_places=2, required=False)
    discounted_price = forms.DecimalField(min_value=0, decimal_places=2)
    discounted_stock = forms.IntegerField(initial=0)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.id:
            discounted_stock = PosInventory.objects.filter(product=self.instance,
                                                                inventory_state__inventory_state=PosInventoryState.AVAILABLE).last().quantity

            initial_arguments = {'discounted_stock': discounted_stock, 'discounted_price': self.instance.selling_price}
            kwargs.update(initial=initial_arguments)
            super().__init__(*args, **kwargs)
            self.fields['shop'].disabled = True
            self.fields['product_ref'].disabled = True
        self.fields['mrp'].disabled = True
        self.fields['selling_price'].disabled = True
        self.fields['product_ean_code'].disabled = True


    def clean(self):
        data = self.cleaned_data
        if not data.get('product_ref'):
            raise ValidationError(_('Invalid Product.'))
        product_ref = data.get('product_ref')
        if data.get('discounted_price') is None or data.get('discounted_price') <= 0 \
                or data.get('discounted_price') >= product_ref.selling_price:
            raise ValidationError(_('Invalid discounted price.'))
        return data



class RetailerProductsCSVDownloadForm(forms.Form):
    """
        Select shop for downloading Retailer Products
    """
    shop = forms.ModelChoiceField(
        label='Select Shop',
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(url='retailer-product-autocomplete',)
    )


class RetailerProductsCSVUploadForm(forms.Form):
    """
        Select shop for create or update Products
    """
    shop = forms.ModelChoiceField(
        label='Select Shop',
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(url='retailer-product-autocomplete', ),
    )
    file = forms.FileField(label='Upload Products')

    def check_mandatory_data(self, row, key_string, row_num):
        """
            Check Mandatory Fields from uploaded CSV for creating or updating Retailer Products
        """
        if key_string not in row.keys():
            raise ValidationError(_(f"Row {row_num} | Please provide {key_string}"))

        if key_string in row.keys():
            if row[key_string] == '':
                raise ValidationError(_(f"Row {row_num} | Please provide {key_string}"))

    def validate_data_for_create_products(self, uploaded_data_by_user_list):
        """
            Validation for create Products Catalogue
        """
        row_num = 1
        for row in uploaded_data_by_user_list:
            row_num += 1
            self.check_mandatory_data(row, 'product_name', row_num)
            self.check_mandatory_data(row, 'mrp', row_num)
            self.check_mandatory_data(row, 'selling_price', row_num)

            if not re.match("^\d+[.]?[\d]{0,2}$", str(row['mrp'])):
                raise ValidationError(_(f"Row {row_num} | 'Product MRP' can only be a numeric value."))

            if not re.match("^\d+[.]?[\d]{0,2}$", str(row['selling_price'])):
                raise ValidationError(_(f"Row {row_num} | 'Selling Price' can only be a numeric value."))

            if decimal.Decimal(row['selling_price']) > decimal.Decimal(row['mrp']):
                raise ValidationError(_(f"Row {row_num} | 'Selling Price' cannot be greater than 'Product Mrp'"))

            if 'linked_product_sku' in row.keys():
                if row['linked_product_sku'] !='':
                    if not Product.objects.filter(product_sku=row['linked_product_sku']).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['linked_product_sku']} | 'SKU ID' doesn't exist."))

            if RetailerProduct.objects.filter(shop=self.cleaned_data.get('shop'), name=row.get('product_name'), mrp=row.get('mrp'),
                                              selling_price=row.get('selling_price')):
                raise ValidationError(_(f"Row {row_num} | Product {row['product_name']} | with mrp  {row['mrp']} & selling_price {row['selling_price']} | already exist."))

    def validate_data_for_update_products(self, uploaded_data_by_user_list):
        """
            Validation for update Products Catalogue
        """
        row_num = 1
        for row in uploaded_data_by_user_list:
            row_num += 1
            self.check_mandatory_data(row, 'product_id', row_num)
            self.check_mandatory_data(row, 'mrp', row_num)
            self.check_mandatory_data(row, 'selling_price', row_num)

            if not RetailerProduct.objects.filter(id=row['product_id']).exists():
                raise ValidationError(_(f"Row {row_num} | {row['product_id']} | 'product_id' doesn't exist."))

            if not re.match("^\d+[.]?[\d]{0,2}$", str(row['selling_price'])):
                raise ValidationError(_(f"Row {row_num} | 'Selling Price' can only be a numeric value."))

            if decimal.Decimal(row['selling_price']) > decimal.Decimal(row['mrp']):
                raise ValidationError(_(f"Row {row_num} | 'Selling Price' cannot be greater than 'Product Mrp'"))

            product = RetailerProduct.objects.get(id=row['product_id'])
            selling_price = row['selling_price']
            mrp = row['mrp']
            if mrp and selling_price:
                # if both mrp & selling price are there in edit product request
                # checking if product already exist, through error
                if RetailerProduct.objects.filter(shop=self.cleaned_data.get('shop'), name=product.name, mrp=mrp,
                                                  selling_price=selling_price).exists():
                    raise ValidationError(_(f"Row {row_num} | Product {row['product_name']} | with mrp  "
                                            f"{row['mrp']} & selling_price {row['selling_price']} | already exist."))
            elif mrp:
                # if only mrp is there in edit product request
                # checking if product already exist, through error
                if RetailerProduct.objects.filter(shop=self.cleaned_data.get('shop'), name=product.name, mrp=mrp,
                                                  selling_price=product.selling_price).exists():
                    raise ValidationError(_(f"Row {row_num} | Product {row['product_name']} | with mrp  "
                                            f"{row['mrp']} & selling_price {row['selling_price']} | already exist."))
            elif selling_price:
                # if only selling_price is there in edit product request
                # checking if product already exist, through error
                if RetailerProduct.objects.filter(shop=self.cleaned_data.get('shop'), name=product.name, mrp=product.mrp,
                                                  selling_price=selling_price).exists():
                    raise ValidationError(_(f"Row {row_num} | Product {row['product_name']} | with mrp  "
                                            f"{row['mrp']} & selling_price {row['selling_price']} | already exist."))

    def validate_data(self, uploaded_data_by_user_list, catalogue_product_status):
        """
            Validation for create/update Products based on selected option(catalogue_product_status)
        """
        if catalogue_product_status == 'update_products':
            self.validate_data_for_update_products(uploaded_data_by_user_list)
        else:
            self.validate_data_for_create_products(uploaded_data_by_user_list)

    def read_file(self, headers, reader, catalogue_product_status):
        """
            Reading & validating File Uploaded by user
        """
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
        """
            FileField validation Check if file ends with only .csv
        """
        if self.cleaned_data.get('file'):

            if not self.cleaned_data['file'].name[-4:] in ('.csv'):
                raise forms.ValidationError("Please upload only CSV File")
            else:
                reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
                catalogue_product_status = self.data.get('catalogue_product_status')
                headers = next(reader, None)
                self.read_file(headers, reader, catalogue_product_status)
        return self.cleaned_data['file']


class RetailerProductMultiImageForm(forms.ModelForm):
    """
       Bulk Retailer Products Image Form
    """
    class Meta:
        model = RetailerProductImage
        fields = ('image',)

class PosInventoryChangeCSVDownloadForm(forms.Form):
    """
        Select sku for downloading PosInventory changes
    """
    sku = forms.ModelChoiceField(
        label='Select Product SKU',
        queryset = RetailerProduct.objects.filter(~Q(sku_type=4)),
        widget=autocomplete.ModelSelect2(url='inventory-product-autocomplete',)
    )

