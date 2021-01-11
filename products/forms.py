import codecs
import csv
import datetime
import re
from django.urls import reverse

from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.db.models import Value, Case, When, F
from django.db import transaction
from model_utils import Choices

from tempus_dominus.widgets import DatePicker, DateTimePicker, TimePicker

from addresses.models import City, Pincode, State
from brand.models import Brand, Vendor
from categories.models import Category
from products.models import (Color, Flavor, Fragrance, PackageSize, Product,
                             ProductCategory, ProductImage, ProductPrice,
                             ProductVendorMapping, Size, Tax, Weight,
                             BulkProductTaxUpdate, ProductTaxMapping, BulkUploadForGSTChange,
                             Repackaging, ParentProduct, ProductHSN, ProductSourceMapping,
                             DestinationRepackagingCostMapping, ParentProductImage, ProductCapping)
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from retailer_backend.validators import *
from shops.models import Shop, ShopType
from wms.models import InventoryType, WarehouseInventory, InventoryState


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ('image', )


class ProductImageFormSet(forms.models.BaseInlineFormSet):

    def clean(self):
        super(ProductImageFormSet, self).clean()
        count = 0
        delete_count = 0
        valid = True
        for form in self:
            if form.is_valid():
                if form.cleaned_data:
                    count += 1
                if 'DELETE' in form.cleaned_data and form.cleaned_data['DELETE'] is True:
                    delete_count += 1
            else:
                valid = False
        if valid:
            if self.instance.use_parent_image:
                if self.instance.parent_product and not self.instance.parent_product.parent_product_pro_image.exists():
                    raise ValidationError(_(f"Parent Product Image Not Available. Please Upload Child Product Image(s)."))
            elif count < 1 or count == delete_count:
                if self.instance.parent_product and self.instance.parent_product.parent_product_pro_image.exists():
                    self.instance.use_parent_image = True
                else:
                    raise ValidationError(
                        _(f"Parent Product Image Not Available. Please Upload Child Product Image(s)."))
            return self.cleaned_data

    class Meta:
        model = ProductImage


class ParentProductImageForm(forms.ModelForm):
    class Meta:
        model = ParentProductImage
        fields = ('image', )

class ProductPriceForm(forms.Form):
    state = forms.ModelChoiceField(queryset=State.objects.order_by('state_name'))
    city = forms.ModelChoiceField(queryset=City.objects.all())
    sp_sr_choice = forms.ModelChoiceField(
        queryset=ShopType.objects.filter(
            shop_type__in=['sp', 'sr', 'gf']
        )
    )
    sp_sr_list = forms.ModelMultipleChoiceField(queryset=Shop.objects.none())
    start_date_time = forms.DateTimeField(
    widget=DateTimePicker(
        options={
            'minDate': datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            'defaultDate': datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            'format': 'YYYY-MM-DD H:mm:ss',
            }
        ),
    )
    end_date_time = forms.DateTimeField(
        widget=DateTimePicker(
            options={
            'defaultDate': (datetime.datetime.today() + datetime.timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'),
            'format': 'YYYY-MM-DD H:mm:ss',
            }
        ),
    )
    file = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['state'].label = 'Select State'
        self.fields['state'].widget.attrs={
            'class':'custom-select custom-select-lg mb-3',
            }

        self.fields['city'].label = 'Select City'
        self.fields['city'].widget.attrs={
            'class':'custom-select custom-select-lg mb-3',
            }

        self.fields['sp_sr_choice'].label = 'Select SP/SR/GF'
        self.fields['sp_sr_choice'].widget.attrs={
            'class':'custom-select custom-select-lg mb-3',
            }
        self.fields['sp_sr_list'].widget.attrs={
            'class':'form-control',
            'size':15,
            }

        self.fields['file'].label = 'Choose File'
        self.fields['file'].widget.attrs={
            'class':'custom-file-input',
            }

        self.fields['start_date_time'].label = 'Starts at'
        self.fields['start_date_time'].widget.attrs={
            'class':'form-control datetimepicker-input',
            'required':None,
            }

        self.fields['end_date_time'].label = 'Ends at'
        self.fields['end_date_time'].widget.attrs={
            'class':'form-control datetimepicker-input',
            'required':None,

            }

        if 'state' and 'city' in self.data:
            try:
                state_id = int(self.data.get('state'))
                city_id = int(self.data.get('city'))
                self.fields['sp_sr_list'].queryset = Shop.objects.filter(
                    id__in=self.data.get('sp_sr_list').split(','))
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        return self.cleaned_data['file']

class GFProductPriceForm(forms.Form):
    state = forms.ModelChoiceField(queryset=State.objects.order_by('state_name'))
    city = forms.ModelChoiceField(queryset=City.objects.all())
    gf_list = forms.ModelMultipleChoiceField(queryset=Shop.objects.none())
    start_date_time = forms.DateTimeField(
    widget=DateTimePicker(
        options={
            'minDate': datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            'defaultDate': datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            'format': 'YYYY-MM-DD H:mm:ss',
            }
        ),
    )
    end_date_time = forms.DateTimeField(
        widget=DateTimePicker(
            options={
            'defaultDate': (datetime.datetime.today() + datetime.timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'),
            'format': 'YYYY-MM-DD H:mm:ss',
            }
        ),
    )
    file = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['state'].label = 'Select State'
        self.fields['state'].widget.attrs={
            'class':'custom-select custom-select-lg mb-3',
            }

        self.fields['city'].label = 'Select City'
        self.fields['city'].widget.attrs={
            'class':'custom-select custom-select-lg mb-3',
            }

        self.fields['gf_list'].widget.attrs={
            'class':'form-control',
            'size':15,
            }

        self.fields['file'].label = 'Choose File'
        self.fields['file'].widget.attrs={
            'class':'custom-file-input',
            }

        self.fields['start_date_time'].label = 'Starts at'
        self.fields['start_date_time'].widget.attrs={
            'class':'form-control datetimepicker-input',
            'required':None,
            }

        self.fields['end_date_time'].label = 'Ends at'
        self.fields['end_date_time'].widget.attrs={
            'class':'form-control datetimepicker-input',
            'required':None,

            }

        if 'state' and 'city' in self.data:
            try:
                state_id = int(self.data.get('state'))
                city_id = int(self.data.get('city'))
                self.fields['gf_list'].queryset = Shop.objects.all()
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        first_row = next(reader)
        for id,row in enumerate(reader):
            if not row[0] or not re.match("^[\d]*$", row[0]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | "+VALIDATION_ERROR_MESSAGES['INVALID_ID'])
            if not row[1]:
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[
                    1]+":"+row[1]+" | Product Name required")
            if not row[4] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[4]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[
                    4]+":"+row[4]+" | "+VALIDATION_ERROR_MESSAGES[
                    'INVALID_PRICE'])
            if not row[5] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[5]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[
                    5]+":"+row[5]+" | "+VALIDATION_ERROR_MESSAGES[
                    'INVALID_PRICE'])
            if not row[6] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[6]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[
                    6]+":"+row[6]+" | "+VALIDATION_ERROR_MESSAGES[
                    'INVALID_PRICE'])
            if not row[7] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[7]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[
                    7]+":"+row[7]+" | "+VALIDATION_ERROR_MESSAGES[
                    'INVALID_PRICE'])
            if not row[8] or not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[8]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[
                    8]+":"+row[8]+" | "+VALIDATION_ERROR_MESSAGES[
                    'INVALID_PRICE'])
            if not row[9] or not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[9]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[
                    9]+":"+row[9]+" | "+VALIDATION_ERROR_MESSAGES[
                    'INVALID_PRICE'])
        return self.cleaned_data['file']

class ProductsPriceFilterForm(forms.Form):
    state = forms.ModelChoiceField(queryset=State.objects.order_by('state_name'))
    city = forms.ModelChoiceField(queryset=City.objects.all())
    sp_sr_choice = forms.ModelChoiceField(queryset=ShopType.objects.filter(shop_type__in=['sp','sr','gf']))
    sp_sr_list = forms.ModelMultipleChoiceField(queryset=Shop.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['state'].label = 'Select State'
        self.fields['state'].widget.attrs={
            'class':'custom-select custom-select-lg mb-3',
            }

        self.fields['city'].label = 'Select City'
        self.fields['city'].widget.attrs={
            'class':'custom-select custom-select-lg mb-3',
            }

        self.fields['sp_sr_choice'].label = 'Select SP/SR/GF'
        self.fields['sp_sr_choice'].widget.attrs={
            'class':'custom-select custom-select-lg mb-3',
            }
        self.fields['sp_sr_list'].widget.attrs={
            'class':'form-control',
            'size':15,
            }

        if 'state' and 'city' in self.data:
            try:
                state_id = int(self.data.get('state'))
                city_id = int(self.data.get('city'))
                self.fields['sp_sr_list'].queryset = Shop.objects.all()
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset


class ProductPriceNewForm(forms.ModelForm):
    seller_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='sp'),
        widget=autocomplete.ModelSelect2(url='admin:seller_shop_autocomplete')
    )
    buyer_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(url='admin:retailer_autocomplete'),
        required=False
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:city_autocomplete',
            forward=('buyer_shop',)),
        required=False
    )
    pincode = forms.ModelChoiceField(
        queryset=Pincode.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:pincode_autocomplete',
            forward=('city', 'buyer_shop')),
        required=False
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        empty_label='Not Specified',
        widget=autocomplete.ModelSelect2(
            url='product-autocomplete',
            attrs={"onChange":'getProductDetails()'}
        )
    )
    mrp = forms.DecimalField(required=False)

    class Meta:
        model = ProductPrice
        fields = ('product', 'mrp', 'selling_price', 'seller_shop',
                  'buyer_shop', 'city', 'pincode',
                  'start_date', 'approval_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.fields['start_date'].required = True
        # self.fields['end_date'].required = True
        self.fields['mrp'].disabled = True
        if 'approval_status' in self.fields:
            self.fields['approval_status'].choices = ProductPrice.APPROVAL_CHOICES[:1]

    def clean(self):
        cleaned_data = self.cleaned_data
        # mrp = int(self.cleaned_data.get('mrp', '0'))
        if self.cleaned_data['product'].product_mrp:
            self.cleaned_data['mrp'] = self.cleaned_data['product'].product_mrp
        selling_price = int(self.cleaned_data.get('selling_price', '0'))
        # if not mrp:
        #     raise forms.ValidationError(
        #         _('Please enter valid value for mrp'),
        #     )
        # if not selling_price:
        #     raise forms.ValidationError(
        #         _('Please enter valid value for Selling Price'),
        #     )
        #else:
        return cleaned_data


class DestinationRepackagingCostMappingForm(forms.ModelForm):

    class Meta:
        model = DestinationRepackagingCostMapping
        fields = ('raw_material', 'wastage', 'fumigation',
                    'label_printing', 'packing_labour', \
                    'primary_pm_cost', 'secondary_pm_cost', \
                    'final_fg_cost', 'conversion_cost')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['final_fg_cost'].disabled = True
        self.fields['final_fg_cost'].required = False
        self.fields['conversion_cost'].disabled = True
        self.fields['conversion_cost'].required = False
        self.fields['raw_material'].widget.attrs = {
            'onChange': 'calc_final_fg_and_conversion_cost(this)'
        }
        self.fields['wastage'].widget.attrs = {
            'onChange': 'calc_final_fg_and_conversion_cost(this)'
        }
        self.fields['fumigation'].widget.attrs = {
            'onChange': 'calc_final_fg_and_conversion_cost(this)'
        }
        self.fields['label_printing'].widget.attrs = {
            'onChange': 'calc_final_fg_and_conversion_cost(this)'
        }
        self.fields['packing_labour'].widget.attrs = {
            'onChange': 'calc_final_fg_and_conversion_cost(this)'
        }
        self.fields['primary_pm_cost'].widget.attrs = {
            'onChange': 'calc_final_fg_and_conversion_cost(this)'
        }
        self.fields['secondary_pm_cost'].widget.attrs = {
            'onChange': 'calc_final_fg_and_conversion_cost(this)'
        }


class ParentProductForm(forms.ModelForm):

    class Meta:
        model = ParentProduct
        # fields = ('parent_brand', 'name', 'product_hsn', 'gst', 'cess',
        #           'surcharge', 'brand_case_size', 'inner_case_size',
        #           'product_type',)
        fields = ('parent_brand', 'name', 'product_hsn',
                    'brand_case_size', 'inner_case_size',
                    'product_type',)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        return cleaned_data


class UploadParentProductAdminForm(forms.Form):
    """
      Upload Parent Product Form
    """
    file = forms.FileField(label='Upload Parent Product list')

    class Meta:
        model = ParentProduct

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        first_row = next(reader)
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if '' in row:
                if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and
                    row[5] == '' and row[6] == '' and row[7] == '' and row[8] == '' and row[9] == ''):
                    continue
            if not row[0]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Parent Name' can not be empty."))
            elif not re.match("^[ \w\$\_\,\%\@\.\/\#\&\+\-\(\)\*\!\:]*$", row[0]):
                raise ValidationError(_(f"Row {row_id + 1} | {VALIDATION_ERROR_MESSAGES['INVALID_PRODUCT_NAME']}."))
            if not row[1]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Brand' can not be empty."))
            elif not Brand.objects.filter(brand_name=row[1].strip()).exists():
                raise ValidationError(_(f"Row {row_id + 1} | 'Brand' doesn't exist in the system."))
            if not row[2]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Category' can not be empty."))
            else:
                if not Category.objects.filter(category_name=row[2].strip()).exists():
                    categories = row[2].split(',')
                    for cat in categories:
                        cat = cat.strip().replace("'", '')
                        if not Category.objects.filter(category_name=cat).exists():
                            raise ValidationError(_(f"Row {row_id + 1} | 'Category' {cat.strip()} doesn't exist in the system."))
            if not row[3]:
                raise ValidationError(_(f"Row {row_id + 1} | 'HSN' can not be empty."))
            elif not ProductHSN.objects.filter(product_hsn_code=row[3].replace("'", '')).exists():
                raise ValidationError(_(f"Row {row_id + 1} | 'HSN' doesn't exist in the system."))
            if not row[4]:
                raise ValidationError(_(f"Row {row_id + 1} | 'GST' can not be empty."))
            elif not re.match("^([0]|[5]|[1][2]|[1][8]|[2][8])(\s+)?(%)?$", row[4]):
                raise ValidationError(_(f"Row {row_id + 1} | 'GST' can only be 0, 5, 12, 18, 28."))
            if row[5] and not re.match("^([0]|[1][2])(\s+)?%?$", row[5]):
                raise ValidationError(_(f"Row {row_id + 1} | 'CESS' can only be 0, 12."))
            if row[6] and not re.match("^[0-9]\d*(\.\d{1,2})?(\s+)?%?$", row[6]):
                raise ValidationError(_(f"Row {row_id + 1} | 'Surcharge' can only be a numeric value."))
            if not row[7]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Brand Case Size' can not be empty."))
            elif not re.match("^\d+$", row[7]):
                raise ValidationError(_(f"Row {row_id + 1} | 'Brand Case Size' can only be a numeric value."))
            if not row[8]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Inner Case Size' can not be empty."))
            elif not re.match("^\d+$", row[8]):
                raise ValidationError(_(f"Row {row_id + 1} | 'Inner Case Size' can only be a numeric value."))
            if not row[9]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Product Type' can not be empty."))
            elif row[9].lower() not in ['b2b', 'b2c', 'both', 'both b2b and b2c']:
                raise ValidationError(_(f"Row {row_id + 1} | 'GST' can only be 'B2B', 'B2C', 'Both B2B and B2C'."))
        return self.cleaned_data['file']


class ProductForm(forms.ModelForm):
    product_name = forms.CharField(required=True)
    product_ean_code = forms.CharField(required=True)
    parent_product = forms.ModelChoiceField(
        queryset=ParentProduct.objects.all(),
        empty_label='Not Specified',
        widget=autocomplete.ModelSelect2(
            url='admin:parent-product-autocomplete',
            attrs={"onChange":'getDefaultChildDetails()'}
        )
    )
    product_special_cess = forms.FloatField(required=False, min_value=0)

    class Meta:
        model = Product
        fields = ('parent_product', 'reason_for_child_sku', 'product_name', 'product_ean_code', 'product_mrp', 'weight_value', 'weight_unit', 'use_parent_image', 'status', 'repackaging_type',
                  'product_special_cess',)

    def clean(self):
        if 'status' in self.cleaned_data and self.cleaned_data['status'] == 'active':
            error = True
            if self.instance.id and ProductPrice.objects.filter(approval_status=ProductPrice.APPROVED,
                                                                product_id=self.instance.id).exists():
                error = False
            if error:
                raise forms.ValidationError("Product cannot be made active until an active Product Price exists")
        return self.cleaned_data


class ProductSourceMappingForm(forms.ModelForm):
    source_sku = forms.ModelChoiceField(
        queryset=Product.objects.filter(repackaging_type='source'),
        empty_label='Not Specified',
        widget=autocomplete.ModelSelect2(
            url='source-product-autocomplete'
        )
    )

    class Meta:
        model = ProductSourceMapping
        fields = ('source_sku', 'status')


class ProductSourceMappingFormSet(forms.models.BaseInlineFormSet):

    def clean(self):
        super(ProductSourceMappingFormSet, self).clean()
        count = 0
        delete_count = 0
        valid = True
        for form in self:
            if form.is_valid():
                if form.cleaned_data:
                    count += 1
                if self.instance.repackaging_type != 'destination':
                    form.cleaned_data['DELETE'] = True
                if 'DELETE' in form.cleaned_data and form.cleaned_data['DELETE'] is True:
                    delete_count += 1
            else:
                valid = False

        if self.instance.repackaging_type == 'destination':
            if count < 1 or count == delete_count:
                raise ValidationError("At least one source mapping is required")

        if valid:
            return self.cleaned_data

    class Meta:
        model = ProductSourceMapping


class DestinationRepackagingCostMappingFormSet(forms.models.BaseInlineFormSet):

    def clean(self):
        super(DestinationRepackagingCostMappingFormSet, self).clean()
        count = 0
        delete_count = 0
        valid = True
        for form in self:
            if form.is_valid():
                if form.cleaned_data:
                    count += 1
                if self.instance.repackaging_type != 'destination' and form.cleaned_data:
                    form.cleaned_data['DELETE'] = True
                if 'DELETE' in form.cleaned_data and form.cleaned_data['DELETE'] is True:
                    delete_count += 1
            else:
                valid = False

        if self.instance.repackaging_type == 'destination':
            if count < 1 or count == delete_count:
                raise ValidationError("At least one cost mapping is required")
        if valid:
            return self.cleaned_data

    class Meta:
        model = DestinationRepackagingCostMapping


class UploadChildProductAdminForm(forms.Form):
    """
      Upload Child Product Form
    """
    file = forms.FileField(label='Upload Child Product list')

    class Meta:
        model = ParentProduct

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        first_row = next(reader)
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if '' in row:
                if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and row[5] == '' and row[6] == ''):
                    continue
            if not row[0]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Parent Product ID' can not be empty."))
            elif not ParentProduct.objects.filter(parent_id=row[0]).exists():
                raise ValidationError(_(f"Row {row_id + 1} | 'Parent Product' doesn't exist in the system."))
            if not row[1]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Reason for Child SKU' can not be empty."))
            elif row[1].lower() not in ['default', 'different mrp', 'different weight', 'different ean', 'offer']:
                raise ValidationError(_(f"Row {row_id + 1} | 'Reason for Child SKU' can only be 'Default', 'Different MRP', 'Different Weight', 'Different EAN', 'Offer'."))
            if not row[2]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Product Name' can not be empty."))
            elif not re.match("^[ \w\$\_\,\%\@\.\/\#\&\+\-\(\)\*\!\:]*$", row[2]):
                raise ValidationError(_(f"Row {row_id + 1} | {VALIDATION_ERROR_MESSAGES['INVALID_PRODUCT_NAME']}."))
            if not row[3]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Product EAN Code' can not be empty."))
            elif not re.match("^[a-zA-Z0-9\+\.\-]*$", row[3].replace("'", '')):
                raise ValidationError(_(f"Row {row_id + 1} | 'Product EAN Code' can only contain alphanumeric input."))
            if not row[4]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Product MRP' can not be empty."))
            elif not re.match("^\d+[.]?[\d]{0,2}$", row[4]):
                raise ValidationError(_(f"Row {row_id + 1} | 'Product MRP' can only be a numeric value."))
            if not row[5]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Weight Value' can not be empty."))
            elif not re.match("^\d+[.]?[\d]{0,2}$", row[5]):
                raise ValidationError(_(f"Row {row_id + 1} | 'Weight Value' can only be a numeric value."))
            if not row[6]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Weight Unit' can not be empty."))
            elif row[6].lower() not in ['gram']:
                raise ValidationError(_(f"Row {row_id + 1} | 'Weight Unit' can only be 'Gram'."))
            if not row[7]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Repackaging Type' can not be empty."))
            elif row[7] not in [lis[0] for lis in Product.REASON_FOR_NEW_CHILD_CHOICES]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Repackaging Type' is invalid."))
            if row[7] == 'destination':
                if not row[8]:
                    raise ValidationError(_(f"Row {row_id + 1} | 'Source SKU Mapping' is required for Repackaging"
                                            f" Type 'destination'."))
                else:
                    there = False
                    for pro in row[8].split(','):
                        pro = pro.strip()
                        if pro is not '':
                            if Product.objects.filter(product_sku=pro, repackaging_type='source').exists():
                                there = True
                            else:
                                raise ValidationError(_(f"Row {row_id + 1} | 'Source SKU Mapping' {pro} is invalid."))
                    if not there:
                        raise ValidationError(_(f"Row {row_id + 1} | 'Source SKU Mapping' is required for Repackaging"
                                                f" Type 'destination'."))

                dest_cost_fields = ['Raw Material Cost', 'Wastage Cost', 'Fumigation Cost', 'Label Printing Cost',
                                    'Packing Labour Cost', 'Primary PM Cost', 'Secondary PM Cost']
                for i in range(0, 7):
                    if not row[i + 9]:
                        raise ValidationError(_(f"Row {row_id + 1} | {dest_cost_fields[i]} required for Repackaging"
                                            f" Type 'destination'."))
                    elif not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[i + 9]):
                        raise ValidationError(_(f"Row {row_id + 1} | {dest_cost_fields[i]} is Invalid"))
        return self.cleaned_data['file']


class UploadMasterDataAdminForm(forms.Form):
    """
    This Form Class is used for checking, whether the details required for "upload_master_data" functionality are
    correct or not.
    """
    file = forms.FileField(label='Upload Master Data')

    def validate_row(self, uploaded_data_list, header_list, upload_master_data):
        """
        This method will check that Data uploaded by user is valid or not.
        """
        try:
            row_num = 1
            for row in uploaded_data_list:
                row_num += 1
                if 'sku_id' in header_list and row['sku_id'] != '':
                    if not Product.objects.filter(product_sku=str(row['sku_id']).strip()).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['sku_id']} | 'SKU ID' doesn't exist."))
                if 'parent_id' in header_list and row['parent_id'] != '':
                    if not ParentProduct.objects.filter(parent_id=str(row['parent_id']).strip()).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['parent_id']} | 'Parent ID' doesn't exist."))
                if 'status' in header_list and row['status'] != '':
                    status_list = ['Active', 'Deactivated', 'Pending Approval']
                    if row['status'] not in status_list:
                        raise ValidationError(
                            _(f"Row {row_num} | {row['status']} | 'Status can either be 'Active',"
                              f"'Pending Approval' or 'Deactivated'!"))
                if 'sku_name' in header_list and row['sku_name'] != '':
                    if not Product.objects.filter(product_name=str(row['sku_name']).strip()).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['sku_name']} |"
                                                f"'SKU Name' doesn't exist in the system."))
                if 'ean' in header_list and row['ean'] != '':
                    if not Product.objects.filter(product_ean_code=row['ean']).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['ean']} |'HSN' doesn't exist in the system."))
                if 'mrp' in header_list and row['mrp'] != '':
                    if not re.match("^\d+[.]?[\d]{0,2}$", str(row['mrp'])):
                        raise ValidationError(
                            _(f"Row {row_num} | 'Product MRP' can only be a numeric value."))
                if 'weight_unit' in header_list and row['weight_unit'] != '':
                    if str(row['weight_unit']).lower() not in ['gram']:
                        raise ValidationError(_(f"Row {row_num} | 'Weight Unit' can only be 'Gram'."))
                if 'weight_value' in header_list and row['weight_value'] != '':
                    if not re.match("^\d+[.]?[\d]{0,2}$", str(row['weight_value'])):
                        raise ValidationError(_(f"Row {row_num} | 'Weight Value' can only be a numeric value."))
                if 'hsn' in header_list and row['hsn'] != '':
                    if not ProductHSN.objects.filter(
                            product_hsn_code=str(row['hsn']).replace("'", '')).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['hsn']} |'HSN' doesn't exist in the system."))
                if 'tax_1(gst)' in header_list and row['tax_1(gst)'] != '':
                    if not Tax.objects.filter(tax_name=row['tax_1(gst)']).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['tax_1(gst)']} | Invalid Tax(GST)!"))
                if 'tax_2(cess/surcharge)' in header_list and row['tax_2(cess/surcharge)'] != '':
                    if not Tax.objects.filter(tax_name=row['tax_2(cess/surcharge)']).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['tax_2(cess/surcharge)']} "
                                                f"| Invalid Tax(CESS/SURCHARGE)!"))
                if 'brand_case_size' in header_list and row['brand_case_size'] != '':
                    if not re.match("^\d+$", str(row['brand_case_size'])):
                        raise ValidationError(
                            _(f"Row {row_num} | {row['brand_case_size']} |'Brand Case Size' can only be a numeric value."))
                if 'inner_case_size' in header_list and row['inner_case_size'] != '':
                    if not re.match("^\d+$", str(row['inner_case_size'])):
                        raise ValidationError(
                            _(f"Row {row_num} | {row['inner_case_size']} |'Inner Case Size' can only be a numeric value."))
                if 'brand_id' in header_list and row['brand_id'] != '':
                    if not Brand.objects.filter(id=row['brand_id']).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['brand_id']} | "
                                                f"'Brand_ID' doesn't exist in the system "))
                if 'sub_brand_id' in header_list and row['sub_brand_id'] != '':
                    if not Brand.objects.filter(id=row['sub_brand_id']).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['sub_brand_id']} | "
                                                f"'Sub_Brand_ID' doesn't exist in the system "))
                if 'category_id' in header_list and row['category_id'] != '':
                    if not Category.objects.filter(id=row['category_id']).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['category_id']} | "
                                                f"'Category_ID' doesn't exist in the system "))
                if 'sub_category_id' in header_list and row['sub_category_id'] != '':
                    if not Category.objects.filter(id=row['sub_category_id']).exists():
                        raise ValidationError(_(f"Row {row_num} | {row['sub_category_id']} | "
                                                f"'Sub_Category_ID' doesn't exist in the system "))
        except ValueError as e:
            raise ValidationError(_(f"Row {row_num} | ValueError : {e} | Please Enter valid Data"))
        except KeyError as e:
            raise ValidationError(_(f"Row {row_num} | KeyError : {e} | Something went wrong while"
                                    f"checking excel data from dictionary"))

    def check_mandatory_columns(self, uploaded_data_list, header_list, upload_master_data):
        """
        Mandatory Columns Check as per condition of  "upload_master_data"
        """
        if upload_master_data == "master_data":
            row_num = 1
            required_columns = ['sku_id', 'parent_id']
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory columns for 'Upload Master Data'"))
            for row in uploaded_data_list:
                row_num += 1
                if row['sku_id'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if row['parent_id'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
        if upload_master_data == "inactive_status":
            row_num = 1
            required_columns = ['status', 'sku_id']
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory columns for 'Set Inactive Status'"))
            for row in uploaded_data_list:
                row_num += 1
                if row['status'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                                            'Status cannot be empty'))
                if row['sku_id'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
        if upload_master_data == "sub_brand_with_brand":
            row_num = 1
            required_columns = ['sub_brand_id', 'brand_id']
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory columns for 'Sub Brand and Brand Mapping'"))
            for row in uploaded_data_list:
                row_num += 1
                if row['sub_brand_id'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'Sub_Brand_ID can't be empty"))
                if row['brand_id'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'Brand_ID' can't be empty"))
        if upload_master_data == "sub_category_with_category":
            row_num = 1
            required_columns = ['sub_category_id', 'category_id']
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory columns"
                                            f" for 'Sub Category and Category Mapping'"))
            for row in uploaded_data_list:
                row_num += 1
                if row['sub_category_id'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'Sub_Category_ID' can't be empty"))
                if row['category_id'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'Category_ID' can't be empty"))
        if upload_master_data == "child_parent":
            row_num = 1
            required_columns = ['sku_id', 'parent_id', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory column for 'Child and Parent Mapping'"))
            for row in uploaded_data_list:
                row_num += 1
                if row['sku_id'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if row['parent_id'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if row['status'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'Status can either be 'Active', 'Pending Approval' "
                                            f"or 'Deactivated'!" |
                                            'Status cannot be empty'))
        if upload_master_data == "child_data":
            required_columns = ['sku_id', 'sku_name', 'status', 'ean']
            # mandatory_columns = ['status', 'sku_id']
            row_num = 1
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory columns for 'Set Child Data'"))
            for row in uploaded_data_list:
                row_num += 1
                if row['status'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                                            'Status cannot be empty'))
                if row['sku_id'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if row['sku_name'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))
        if upload_master_data == "parent_data":
            row_num = 1
            required_columns = ['parent_id', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory columns for 'Set Parent Data'"))
            for row in uploaded_data_list:
                row_num += 1
                if row['parent_id'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'Parent_ID' is a mandatory field"))
                if row['status'] == '':
                    raise ValidationError(_(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                                            'Status cannot be empty'))

        self.validate_row(uploaded_data_list, header_list, upload_master_data)

    def read_file(self, excel_file, upload_master_data):
        """
        Template Validation (Checking, whether the excel file uploaded by user is correct or not!)
        """
        # Checking the headers of the excel file
        required_header_list = ['sku_id', 'sku_name', 'parent_id', 'parent_name', 'ean', 'mrp', 'weight_unit',
                                'weight_value', 'hsn', 'tax_1(gst)', 'tax_2(cess/surcharge)', 'brand_case_size',
                                'inner_case_size', 'brand_name', 'brand_id', 'sub_brand_name', 'sub_brand_id',
                                'category_name', 'category_id', 'sub_category_name', 'sub_category_id', 'status']
        excel_file_header_list = excel_file.pop(0)  # headers of the uploaded excel file
        excel_file_headers = [str(ele).lower() for ele in excel_file_header_list]  # Converting headers into lowercase
        for head in excel_file_headers:
            if head in required_header_list:
                pass
            else:
                raise ValidationError(_(f"Invalid Header | {head} | Allowable headers for the upload are: "
                                        f"{required_header_list}"))

        # Checking, whether the user uploaded the data below the headings or not!
        if len(excel_file) > 0:
            uploaded_data_by_user_list = []
            excel_dict = {}
            count = 0
            for row in excel_file:
                for ele in row:
                    excel_dict[excel_file_headers[count]] = ele
                    count += 1
                uploaded_data_by_user_list.append(excel_dict)
                excel_dict = {}
                count = 0
            self.check_mandatory_columns(uploaded_data_by_user_list, excel_file_headers, upload_master_data)
        else:
            raise ValidationError("Please add some data below the headers to upload it!")

    def clean_file(self):
        try:
            if self.cleaned_data.get('file'):
                if not self.cleaned_data['file'].name[-5:] in ('.xlsx'):
                    raise forms.ValidationError("Sorry! Only excel(xlsx) file accepted.")
                excel_file_data = self.auto_id['Users']

                # Checking, whether excel file is empty or not!
                if excel_file_data:
                    self.read_file(excel_file_data, self.data['upload_master_data'])
                else:
                    raise ValidationError("Excel File cannot be empty.Please add some data to upload it!")

                return self.cleaned_data['file']
            else:
                raise ValidationError("Excel File is required!")
        except Exception as e:
            raise ValidationError(f"Something went wrong while checking Validations + {str(e)}")


class ProductsFilterForm(forms.Form):
    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.order_by('category_name'),
        )

    brand = forms.ModelMultipleChoiceField(queryset=Brand.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.fields['category1'].widget.attrs['class'] = 'test'
        self.fields['category'].widget.attrs={
            'class':'select2-filter',
            # 'size':15,
            }
        self.fields['brand'].widget.attrs={
            'class':'form-control',
            'size':15,
            }
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['brand'].queryset = Brand.objects.all()
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset

class ProductsCSVUploadForm(forms.Form):
    file = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['file'].label = 'Choose File'
        self.fields['file'].widget.attrs={
            'class':'custom-file-input',
            }

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        for id,row in enumerate(reader):
            if not row[0] or row[0].isspace():
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[
                    0]+":"+row[0]+" | Product Name required")
            if not row[1] or row[1].isspace():
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[
                    1]+":"+row[1]+" | Product short description required")
            if not row[2] or row[2].isspace():
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[
                    2]+":"+row[2]+" | Product long description required")
            if not row[3] or row[3].isspace():
                raise ValidationError(_("PRODUCT_GF_CODE required at Row[%(value)s]."), params={'value': id+1},)
            if not row[12] or row[12].isspace():
                raise ValidationError(_("Product weight in gram required at Row[%(value)s]."), params={'value': id+1},)
#            if row[3]:
#                product_gf = Product.objects.filter(product_gf_code=row[3])
#                if product_gf:
#                    raise ValidationError(_("PRODUCT_GF_CODE should be
            #                    unique at Row[%(value)s]."), params={'value': id+1},)
            # if not row[4] or not re.match("^\d{13}$", row[4]):
            #     raise ValidationError(_("INVALID_PRODUCT_EAN_CODE at Row[%(value)s]. Exactly 13 numbers required"), params={'value': id+1},)

            if not row[5] or not re.match("^[\d]*$", row[5]):
                raise ValidationError(_('INVALID_BRAND_ID at Row[%(value)s]. It should be numeric'), params={'value': id+1},)
            if row[5]:
                try:
                    Brand.objects.get(pk=row[5])
                except:
                    raise ValidationError(_('No brand found with given BRAND_ID at Row[%(value)s]'), params={'value': id+1},)

            if not row[6] or not re.match("^[\d\,]*$", row[6]):
                raise ValidationError(_('INVALID_CATEGORY_ID/IDs at Row[%(value)s]. It should be numeric'), params={'value': id+1},)
            if row[6]:
                try:
                    for c in row[6].split(','):
                        if c is not '':
                            Category.objects.get(pk=c.strip())
                except:
                    raise ValidationError(_('No category found with given CATEGORY_ID/IDs at Row[%(value)s]'), params={'value': id+1},)

            if not row[7] or not re.match("^[\d\,]*$", row[7]):
                raise ValidationError(_('INVALID_TAX_ID/IDs at Row[%(value)s]. It should be numeric'), params={'value': id+1},)
            if row[7]:
                try:
                    for t in row[7].split(','):
                        if t is not '':
                            Tax.objects.get(pk=t.strip())
                except:
                    raise ValidationError(_('No tax found with given TAX_ID/IDs at Row[%(value)s]'), params={'value': id+1},)

            if row[8] and not re.match("^[\d\,]*$", row[8]):
                raise ValidationError(_('INVALID_SIZE_ID at Row[%(value)s]. It should be numeric'), params={'value': id+1},)
            if row[8]:
                try:
                    Size.objects.get(pk=row[8])
                except:
                    raise ValidationError(_('No size found with given SIZE_ID at Row[%(value)s]'), params={'value': id+1},)

            if row[9] and not re.match("^[\d\,]*$", row[9]):
                raise ValidationError(_('INVALID_COLOR_ID at Row[%(value)s]. It should be numeric'), params={'value': id+1},)
            if row[9]:
                try:
                    Color.objects.get(pk=row[9])
                except:
                    raise ValidationError(_('No color found with given COLOR_ID at Row[%(value)s]'), params={'value': id+1},)

            if row[10] and not re.match("^[\d\,]*$", row[10]):
                raise ValidationError(_('INVALID_FRAGRANCE_ID at Row[%(value)s]. It should be numeric'), params={'value': id+1},)
            if row[10]:
                try:
                    Fragrance.objects.get(pk=row[10])
                except:
                    raise ValidationError(_('No fragrance found with given FRAGRANCE_ID at Row[%(value)s]'), params={'value': id+1},)

            if row[11] and not re.match("^[\d\,]*$", row[11]):
                raise ValidationError(_('INVALID_FLAVOR_ID at Row[%(value)s]. It should be numeric'), params={'value': id+1},)
            if row[11]:
                try:
                    Flavor.objects.get(pk=row[11])
                except:
                    raise ValidationError(_('No flavor found with given FLAVOR_ID at Row[%(value)s]'), params={'value': id+1},)

            if row[12] and not re.match("^[\d+\.?\d]*$", row[12]): #"^[\d\,]*$",
                raise ValidationError(_('INVALID WEIGHT at Row[%(value)s]. It should be numeric'), params={'value': id+1},)
            # if row[12]:
            #     try:
            #         Weight.objects.get(pk=row[12])
            #     except:
            #         raise ValidationError(_('No weight found with given WEIGHT_ID at Row[%(value)s]'), params={'value': id+1},)

            if row[13] and not re.match("^[\d\,]*$", row[13]):
                raise ValidationError(_('INVALID_PACKAGE_SIZE_ID at Row[%(value)s]. It should be numeric'), params={'value': id+1},)
            if row[13]:
                try:
                    PackageSize.objects.get(pk=row[13])
                except:
                    raise ValidationError(_('No package size found with given PACKAGE_SIZE_ID at Row[%(value)s]'), params={'value': id+1},)
            if not row[14] or not re.match("^[\d]*$", row[14]):
                raise ValidationError(_('INVALID_INNER_CASE_SIZE at Row[%(value)s]. It should be numeric'), params={'value': id+1},)
            if not row[15] or not re.match("^[\d]*$", row[15]):
                raise ValidationError(_('INVALID_CASE_SIZE at Row[%(value)s]. It should be numeric'), params={'value': id+1},)
            if not row[16]:
                raise ValidationError(_('HSN_CODE_REQUIRED at Row[%(value)s].'), params={'value': id+1},)
        return self.cleaned_data['file']

class ProductPriceAddPerm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:product-price-autocomplete',)
    )
    seller_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['gf', 'sp']),
    )

    class Meta:
        model = ProductPrice
        fields = ('product', 'selling_price', 'seller_shop',
                  'buyer_shop', 'city', 'pincode',
                  'start_date', 'approval_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # if 'start_date' in self.fields and 'end_date' in self.fields:
        #     self.fields['start_date'].required = True
        #     self.fields['end_date'].required = True
        if 'approval_status' in self.fields:
            self.fields['approval_status'].choices = ProductPrice.APPROVAL_CHOICES[:1]
            # self.fields['approval_status'].initial = ProductPrice.APPROVAL_PENDING
            self.fields['approval_status'].widget = forms.HiddenInput()


class ProductPriceChangePerm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:product-price-autocomplete',)
    )
    seller_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['gf', 'sp']),
    )

    class Meta:
        model = ProductPrice
        fields = ('product', 'selling_price', 'seller_shop',
                  'buyer_shop', 'city', 'pincode',
                  'start_date', 'approval_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.fields['start_date'].required = True
        #self.fields['end_date'].required = True
        self.fields['approval_status'].choices = ProductPrice.APPROVAL_CHOICES[:-1]


class ProductCategoryMappingForm(forms.Form):
    file = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['file'].label = 'Choose File'
        self.fields['file'].widget.attrs = {'class': 'custom-file-input', }

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        return self.cleaned_data['file']


class NewProductPriceUpload(forms.Form):

    seller_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='sp'),
        widget=autocomplete.ModelSelect2(url='admin:seller_shop_autocomplete')
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        widget=autocomplete.ModelSelect2(url='admin:city_autocomplete'),
        required=False
    )
    buyer_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(url='admin:retailer_autocomplete'),
        required=False
    )
    pincode_from = forms.CharField(max_length=6, min_length=6, required=False,
                                   validators=[PinCodeValidator])
    pincode_to = forms.CharField(max_length=6, min_length=6, required=False,
                                 validators=[PinCodeValidator])
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(), required=False,
        widget=autocomplete.ModelSelect2(url='admin:product_autocomplete')
    )
    action = forms.ChoiceField(widget=forms.RadioSelect,
                               choices=[('1', 'Upload'), ('2', 'Download')])
    csv_file = forms.FileField(required=False)

    class Meta:
        fields = ('seller_shop', 'city', 'pincode_from', 'pincode_to',
                  'buyer_shop', 'product', 'action', 'csv_file')

    def clean_pincode_from(self):
        cleaned_data = self.cleaned_data
        data = self.data
        if (data.get('pincode_to', None) and not
                cleaned_data.get('pincode_from', None)):
            raise forms.ValidationError('This field is required')
        return cleaned_data['pincode_from']

    def clean_pincode_to(self):
        cleaned_data = self.cleaned_data
        if (cleaned_data.get('pincode_from', None) and not
                cleaned_data.get('pincode_to', None)):
            raise forms.ValidationError('This field is required')
        return cleaned_data['pincode_to']

    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if file and not file.name[-5:] in ('.xlsx'):
            raise forms.ValidationError('Only Excel(.xlsx) file accepted')
        return file


class ProductVendorMappingForm(forms.ModelForm):
    vendor = forms.ModelChoiceField(
        queryset=Vendor.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:vendor-autocomplete', )
    )

    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:product-price-autocomplete', )
    )
   
    class Meta:
        model = ProductVendorMapping
        fields = ['vendor', 'product', 'product_price','product_price_pack', 'product_mrp', 'case_size']
    
    # this function will be used for the validation
    def clean(self):

        # data from the form is fetched using super function
        super(ProductVendorMappingForm, self).clean()
        product_price = self.cleaned_data.get('product_price')
        product_price_pack = self.cleaned_data.get('product_price_pack')


        if product_price == None and product_price_pack == None:
            raise forms.ValidationError("Please enter one Brand to Gram Price")
        
        if not (product_price == None or product_price_pack == None):
            raise forms.ValidationError("Please enter only one Brand to Gram Price")
       



CAPPING_TYPE_CHOICES = Choices((0, 'DAILY', 'Daily'), (1, 'WEEKLY', 'Weekly'),
                                   (2, 'MONTHLY', 'Monthly'))
class ProductCappingForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:product-price-autocomplete',)
    )
    seller_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='sp'),
        widget=autocomplete.ModelSelect2(url='admin:seller_shop_autocomplete')
    )

    def clean_capping_qty(self):
        """
        method to check capping quantity is zero or not
        """
        if self.instance.id is None:
            if self.data['capping_qty'] == '0':
                raise ValidationError("Capping qty should be greater than 0.")
            else:
                return self.cleaned_data['capping_qty']
        else:
            if self.cleaned_data['capping_qty'] == 0:
                raise ValidationError("Capping qty should be greater than 0.")
            else:
                return self.cleaned_data['capping_qty']

    def clean_capping_type(self):
        """
        method to check capping type is blank or not
        """
        if self.instance.id is None:
            if self.data['capping_type'] == '':
                raise ValidationError("Please select the Capping Type.")
            else:
                return self.cleaned_data['capping_type']
        else:
            return self.cleaned_data['capping_type']

    def clean_start_date(self):
        """
        method to check start date
        """
        if self.instance.id is None:
            if self.data['start_date_0'] == '':
                raise ValidationError("Please select the Start Date.")
            if self.data['end_date_0'] == '':
                pass
            else:
                if self.data['start_date_0'] > self.data['end_date_0']:
                    raise ValidationError("Start Date should be less than End Date.")
            return self.cleaned_data['start_date']
        else:
            return self.cleaned_data['start_date']

    def clean_end_date(self):
        """
        method to check end date
        """
        if self.instance.id is None:
            if self.data['end_date_0'] == '':
                raise ValidationError("Please select the End Date.")
            if self.data['start_date_0'] == '':
                pass
            else:
                if self.data['start_date_0'] > self.data['end_date_0']:
                    raise ValidationError("End Date should be greater than Start Date.")
                else:
                    if not self.data['capping_type'] is '':
                        capping_duration_check(self.cleaned_data)
            return self.cleaned_data['end_date']
        else:
            if self.cleaned_data['end_date'] is None:
                raise ValidationError("Please select the End Date.")

            if self.cleaned_data['start_date'] > self.cleaned_data['end_date']:
                raise ValidationError("End Date should be greater than Start Date.")
            else:
                if not self.cleaned_data['capping_type'] is '':
                    capping_duration_check(self.cleaned_data)
            return self.cleaned_data['end_date']

    def __init__(self, *args, **kwargs):
        """
        args:- non keyword argument
        kwargs:- keyword argument
        """
        self.request = kwargs.pop('request', None)
        super(ProductCappingForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

        if instance.id is None:
            self.fields['product'].disabled = False
            self.fields['seller_shop'].disabled = False
        else:
            self.fields['product'].disabled = True
            self.fields['seller_shop'].disabled = True
            self.fields['start_date'] = forms.DateTimeField()
            self.fields['start_date'].disabled = True
            self.fields['capping_type'].disabled = True


    def clean(self):
        """
        Method to check capping is active for the selected sku and warehouse
        """

        if not self.instance.id:
            if self.data['seller_shop'] is '':
                raise ValidationError("Seller Shop can't be Blank.")

            if self.data['product'] is '':
                raise ValidationError("Product can't be Blank.")
            if ProductCapping.objects.filter(seller_shop=self.cleaned_data['seller_shop'],
                                                                  product=self.cleaned_data['product'],
                                                                  status=True).exists():
                raise ValidationError("Another Capping is Active for the selected SKU or selected Warehouse.")
        return self.cleaned_data


def capping_duration_check(cleaned_data):
    """
    Duration check according to capping type
    """
    if cleaned_data['end_date'] is None:
        raise ValidationError("End date can't be Blank.")

    if cleaned_data['start_date'] is None:
        raise ValidationError("Start date can't be Blank.")

    # if capping type is Daily
    if cleaned_data['capping_type'] == 0:
        day_difference = cleaned_data['end_date'].date() - cleaned_data['start_date'].date()
        if day_difference.days == 0:
            raise ValidationError("Please enter valid Start Date and End Date.")
        else:
            pass

    # if capping type is Weekly
    elif cleaned_data['capping_type'] == 1:
        day_difference = cleaned_data['end_date'].date() - cleaned_data['start_date'].date()
        if day_difference.days == 0:
            raise ValidationError("Please enter valid Start Date and End Date.")
        elif day_difference.days % 7 == 0:
            pass
        else:
            raise ValidationError("Please enter valid Start Date and End Date.")

    # if capping type is Monthly
    elif cleaned_data['capping_type'] == 2:
        day_difference = cleaned_data['end_date'].date() - cleaned_data['start_date'].date()
        if day_difference.days == 0:
            raise ValidationError("Please enter valid Start Date and End Date.")
        elif day_difference.days % 30 == 0:
            pass
        else:
            raise ValidationError("Please enter valid Start Date and End Date.")


class BulkProductTaxUpdateForm(forms.ModelForm):

    class Meta:
        model = BulkProductTaxUpdate
        fields = ('file', 'updated_by')
        readonly_fields = ('updated_by',)

    def sample_file(self):
        filename = "bulk_product_tax_update_sample.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(['SKU No.', 'GST', 'Cess'])
        return response

    def validate_row(self, columns, row, row_id, file):
        row_errors = []
        # check SKU No.
        if not row[0]:
            row_errors.append(('Please enter SKU No. at row %s') % (row_id))
        else:
            try:
                product = Product.objects.values('id').get(product_sku=row[0])
            except:
                row_errors.append(('Please enter valid SKU No. at row %s') %
                                  (row_id))
            else:
                product_id = product.get('id')
                csv_reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
                csv_columns = next(csv_reader)
                for reader_id, reader_row in enumerate(csv_reader):
                    if (reader_id + 2 != row_id) and row[0] == reader_row[0]:
                        row_errors.append(
                            ('Duplicate entry for SKU %s exists at row %s') %
                            (row[0], reader_id + 2))
        # check GST
        if not row[1]:
            row_errors.append(
                ("Please enter GST percentage at row %s for SKU No. %s") %
                (row_id, row[0]))
        else:
            if row[1].isdigit() and int(row[1]) in [0, 5, 12, 18, 28]:
                try:
                    gst_tax = Tax.objects.values('id')\
                        .get(tax_type='gst', tax_percentage=float(row[1]))
                except:
                    row_errors.append(
                        ('Tax with type GST and percentage %s does not exists at row %s for SKU No. %s') %
                        (float(row[1]), row_id, row[0]))
                else:
                    gst_tax_id = gst_tax.get('id')
            else:
                row_errors.append(
                    ('Please enter a valid GST percentage at row %s for SKU No. %s') %
                    (row_id, row[0]))
        # check Cess
        if row[2]:
            if row[2].isdigit() and int(row[2]) in [0, 12]:
                try:
                    cess_tax = Tax.objects.values('id')\
                        .get(tax_type='cess', tax_percentage=float(row[2]))
                except:
                    row_errors.append(
                        ('Tax with type Cess and percentage %s does not exists at row %s for SKU No. %s') %
                        (float(row[2]), row_id, row[0]))
                else:
                    cess_tax_id = cess_tax.get('id')
            else:
                row_errors.append(('Please enter a valid Cess percentage at row %s for SKU No. %s') %
                                  (row_id, row[0]))
        else:
            cess_tax_id = None
        # if file errors
        if row_errors:
            raise ValidationError(
                [ValidationError(_(error)) for error in row_errors]
            )
        else:
            self.product_tax_details[product_id] = {'gst_tax_id': gst_tax_id,
                                                    'cess_tax_id': cess_tax_id}

    def read_file(self, file):
        reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
        columns = next(reader)
        for row_id, row in enumerate(reader):
            self.validate_row(columns, row, row_id + 2, file)

    def update_products_tax(self, file):
        for product_id, taxes in self.product_tax_details.items():
            queryset = ProductTaxMapping.objects.filter(product_id=product_id)
            if queryset.exists():
                queryset.filter(tax__tax_type='gst').update(tax_id=taxes['gst_tax_id'])
                if taxes['cess_tax_id']:
                    product_cess_tax = queryset.filter(tax__tax_type='cess')
                    if product_cess_tax.exists():
                        product_cess_tax.update(tax_id=taxes['cess_tax_id'])
                    else:
                        ProductTaxMapping.objects.create(
                            product_id=product_id, tax_id=taxes['cess_tax_id'])

    def clean(self):
        if self.cleaned_data.get('file'):
            if not self.cleaned_data.get('file').name[-4:] in ('.csv'):
                raise forms.ValidationError("Sorry! Only csv file accepted")
            self.product_tax_details = {}
            self.read_file(self.cleaned_data.get('file'))
            try:
                with transaction.atomic():
                    self.update_products_tax(self.cleaned_data.get('file'))
            except Exception as e:
                raise ValidationError(e)
            return self.cleaned_data
        else:
            raise forms.ValidationError("CSV file is required!")


class BulkUploadForGSTChangeForm(forms.ModelForm):

    class Meta:
        model = BulkUploadForGSTChange
        fields = ('file', )

    def sample_file1(self):
        filename = "bulk_upload_for_gst_change_sample.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(['SKU No.', 'GST', 'Cess'])
        return response

    def validate_row(self, columns, row, row_id, file):
        row_errors = []
        # check SKU No.
        if not row[0]:
            row_errors.append(('Please enter SKU No. at row %s') % (row_id))
        else:
            try:
                product = Product.objects.values('id').get(product_sku=row[0])
            except:
                row_errors.append(('Please enter valid SKU No. at row %s') %
                                  (row_id))
            else:
                product_id = product.get('id')
                csv_reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
                csv_columns = next(csv_reader)
                for reader_id, reader_row in enumerate(csv_reader):
                    if (reader_id + 2 != row_id) and row[0] == reader_row[0]:
                        row_errors.append(
                            ('Duplicate entry for SKU %s exists at row %s') %
                            (row[0], reader_id + 2))
        # check GST
        if not row[1]:
            row_errors.append(
                ("Please enter GST percentage at row %s for SKU No. %s") %
                (row_id, row[0]))
        else:
            if row[1].isdigit() and int(row[1]) in [0, 5, 12, 18, 28]:
                try:
                    gst_tax = Tax.objects.values('id')\
                        .get(tax_type='gst', tax_percentage=float(row[1]))
                except:
                    row_errors.append(
                        ('Tax with type GST and percentage %s does not exists at row %s for SKU No. %s') %
                        (float(row[1]), row_id, row[0]))
                else:
                    gst_tax_id = gst_tax.get('id')
            else:
                row_errors.append(
                    ('Please enter a valid GST percentage at row %s for SKU No. %s') %
                    (row_id, row[0]))
        # check Cess
        if row[2]:
            if row[2].isdigit() and int(row[2]) in [0, 12]:
                try:
                    cess_tax = Tax.objects.values('id')\
                        .get(tax_type='cess', tax_percentage=float(row[2]))
                except:
                    row_errors.append(
                        ('Tax with type Cess and percentage %s does not exists at row %s for SKU No. %s') %
                        (float(row[2]), row_id, row[0]))
                else:
                    cess_tax_id = cess_tax.get('id')
            else:
                row_errors.append(('Please enter a valid Cess percentage at row %s for SKU No. %s') %
                                  (row_id, row[0]))
        else:
            cess_tax_id = None
        # if file errors
        if row_errors:
            raise ValidationError(
                [ValidationError(_(error)) for error in row_errors]
            )
        else:
            self.product_tax_details[product_id] = {'gst_tax_id': gst_tax_id,
                                                    'cess_tax_id': cess_tax_id}

    def read_file(self, file):
        reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
        columns = next(reader)
        for row_id, row in enumerate(reader):
            self.validate_row(columns, row, row_id + 2, file)

    def update_products_tax(self, file):
        for product_id, taxes in self.product_tax_details.items():
            queryset = ProductTaxMapping.objects.filter(product_id=product_id)
            if queryset.exists():
                queryset.filter(tax__tax_type='gst').update(tax_id=taxes['gst_tax_id'])
                if taxes['cess_tax_id']:
                    product_cess_tax = queryset.filter(tax__tax_type='cess')
                    if product_cess_tax.exists():
                        product_cess_tax.update(tax_id=taxes['cess_tax_id'])
                    else:
                        ProductTaxMapping.objects.create(
                            product_id=product_id, tax_id=taxes['cess_tax_id'])

    def clean(self):
        if self.cleaned_data.get('file'):
            if not self.cleaned_data.get('file').name[-4:] in ('.csv'):
                raise forms.ValidationError("Sorry! Only csv file accepted")
            self.product_tax_details = {}
            self.read_file(self.cleaned_data.get('file'))
            try:
                with transaction.atomic():
                    self.update_products_tax(self.cleaned_data.get('file'))
            except Exception as e:
                raise ValidationError(e)
            return self.cleaned_data
        else:
            raise forms.ValidationError("CSV file is required!")

class RepackagingForm(forms.ModelForm):
    seller_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='sp'),
        widget=autocomplete.ModelSelect2(url='admin:seller_shop_autocomplete'),
    )

    source_sku = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:product-shop-autocomplete', forward=['seller_shop']),
    )

    destination_sku = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:destination-product-autocomplete', forward=['source_sku'])
    )

    class Meta:
        model = Repackaging
        fields = ('seller_shop', 'source_sku', 'destination_sku', 'source_repackage_quantity', 'status',
                  "available_source_weight", "available_source_quantity", "destination_sku_quantity", "remarks",
                  "expiry_date", "source_picking_status")
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        if 'expiry_date' in  self.cleaned_data:
            today_date = datetime.date.today()
            if self.cleaned_data['expiry_date'] < today_date:
                raise forms.ValidationError("Expiry Date should be greater than or equal to {}".format(today_date))
        if 'source_sku' in self.cleaned_data:
            try:
                warehouse_available_obj = WarehouseInventory.objects.filter(warehouse=self.cleaned_data['seller_shop'],
                                                                            sku=self.cleaned_data['source_sku'],
                                                                            inventory_type=InventoryType.objects.filter(
                                                                                inventory_type='normal').last(),
                                                                            inventory_state=InventoryState.objects.filter(
                                                                                inventory_state='available').last())
                if warehouse_available_obj.exists():
                    w_obj = warehouse_available_obj.last()
                    source_quantity = w_obj.quantity
                else:
                    raise forms.ValidationError("Warehouse Inventory Does Not Exist")
            except Exception as e:
                raise forms.ValidationError("Warehouse Inventory Could not be fetched")
            if self.cleaned_data['source_repackage_quantity'] + self.cleaned_data['available_source_quantity'] !=\
                    source_quantity:
                raise forms.ValidationError("Source Quantity Changed! Please Input Again")
        if self.instance.source_picking_status in ['pickup_created', 'picking_assigned']:
            raise forms.ValidationError("Source pickup is still not complete.")
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super(RepackagingForm, self).__init__(*args, **kwargs)
        if self.instance.pk and 'expiry_date' in self.fields:
            self.fields['expiry_date'].required = True
        readonly = ['available_source_weight', 'available_source_quantity']
        for key in readonly:
            if key in self.fields:
                self.fields[key].widget.attrs['readonly'] = True

class BulkProductVendorMapping(forms.Form):
    """
      Bulk Product Vendor Mapping
    """

    file = forms.FileField(label='Add Bulk Product Vendor Mapping')

    class Meta:
        model = ProductVendorMapping
       
    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        first_row = next(reader)
        for id,row in enumerate(reader):
            if len(row) == 0:
                continue
            if '' in row:
                if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and row[5] == '' and row[6] == ''):
                    continue
            if not row[0]:
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | Product ID cannot be empty")
            try:
                Product.objects.get(pk=row[0])
            except:
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | Product does not exist with this ID")

            if not row[3] or not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[3]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | "+VALIDATION_ERROR_MESSAGES[
                'EMPTY_OR_NOT_VALID']%("MRP"))
      
            if not (row[4].title()  == "Per Piece" or row[4].title()  == "Per Pack"):
               
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | "+VALIDATION_ERROR_MESSAGES[
                'EMPTY_OR_NOT_VALID_STRING']%("Gram_to_brand_Price_Unit"))

            if not row[5] or not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[5]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | "+VALIDATION_ERROR_MESSAGES['INVALID_PRICE'])

            if not row[6] or not re.match("^[\d\,]*$", row[6]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | "+VALIDATION_ERROR_MESSAGES['EMPTY_OR_NOT_VALID']%("Case_size"))

        return self.cleaned_data['file']
         