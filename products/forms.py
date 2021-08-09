import codecs
import csv
import datetime
import json
import re
import collections, decimal
from django.db.models.query import InstanceCheckMeta

from django.forms import BaseInlineFormSet
from django.urls import reverse

from dal import autocomplete, forward
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.db.models import Value, Case, When, F, Q, fields
from django.db import transaction
from model_utils import Choices
from django.db.models.functions import Length

from tempus_dominus.widgets import DatePicker, DateTimePicker, TimePicker

from addresses.models import City, Pincode, State
from brand.models import Brand, Vendor
from categories.models import Category
from global_config.views import get_config
from products.models import (Color, Flavor, Fragrance, PackageSize, Product,
                             ProductCategory, ProductImage, ProductPrice,
                             ProductVendorMapping, Size, Tax, Weight,
                             BulkProductTaxUpdate, ProductTaxMapping, BulkUploadForGSTChange,
                             Repackaging, ParentProduct, ProductHSN, ProductSourceMapping,
                             DestinationRepackagingCostMapping, ParentProductImage, ProductCapping,
                             ParentProductCategory, PriceSlab, SlabProductPrice, ProductPackingMapping, DiscountedProductPrice)
from retailer_backend.utils import isDateValid, getStrToDate, isBlankRow
from retailer_backend.validators import *
from shops.models import Shop, ShopType
from wms.models import InventoryType, WarehouseInventory, InventoryState, Bin, BinInventory
from wms.common_functions import get_stock, create_batch_id
from accounts.middlewares import get_current_user
from global_config.models import GlobalConfig


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ('image',)


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
                    raise ValidationError(
                        _(f"Parent Product Image Not Available. Please Upload Child Product Image(s)."))
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
        fields = ('image',)


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
        self.fields['state'].widget.attrs = {
            'class': 'custom-select custom-select-lg mb-3',
        }

        self.fields['city'].label = 'Select City'
        self.fields['city'].widget.attrs = {
            'class': 'custom-select custom-select-lg mb-3',
        }

        self.fields['sp_sr_choice'].label = 'Select SP/SR/GF'
        self.fields['sp_sr_choice'].widget.attrs = {
            'class': 'custom-select custom-select-lg mb-3',
        }
        self.fields['sp_sr_list'].widget.attrs = {
            'class': 'form-control',
            'size': 15,
        }

        self.fields['file'].label = 'Choose File'
        self.fields['file'].widget.attrs = {
            'class': 'custom-file-input',
        }

        self.fields['start_date_time'].label = 'Starts at'
        self.fields['start_date_time'].widget.attrs = {
            'class': 'form-control datetimepicker-input',
            'required': None,
        }

        self.fields['end_date_time'].label = 'Ends at'
        self.fields['end_date_time'].widget.attrs = {
            'class': 'form-control datetimepicker-input',
            'required': None,

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
        self.fields['state'].widget.attrs = {
            'class': 'custom-select custom-select-lg mb-3',
        }

        self.fields['city'].label = 'Select City'
        self.fields['city'].widget.attrs = {
            'class': 'custom-select custom-select-lg mb-3',
        }

        self.fields['gf_list'].widget.attrs = {
            'class': 'form-control',
            'size': 15,
        }

        self.fields['file'].label = 'Choose File'
        self.fields['file'].widget.attrs = {
            'class': 'custom-file-input',
        }

        self.fields['start_date_time'].label = 'Starts at'
        self.fields['start_date_time'].widget.attrs = {
            'class': 'form-control datetimepicker-input',
            'required': None,
        }

        self.fields['end_date_time'].label = 'Ends at'
        self.fields['end_date_time'].widget.attrs = {
            'class': 'form-control datetimepicker-input',
            'required': None,

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
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        for id, row in enumerate(reader):
            if not row[0] or not re.match("^[\d]*$", row[0]):
                raise ValidationError(
                    "Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | " + VALIDATION_ERROR_MESSAGES[
                        'INVALID_ID'])
            if not row[1]:
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    1] + ":" + row[1] + " | Product Name required")
            if not row[4] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[4]):
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    4] + ":" + row[4] + " | " + VALIDATION_ERROR_MESSAGES[
                                          'INVALID_PRICE'])
            if not row[5] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[5]):
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    5] + ":" + row[5] + " | " + VALIDATION_ERROR_MESSAGES[
                                          'INVALID_PRICE'])
            if not row[6] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[6]):
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    6] + ":" + row[6] + " | " + VALIDATION_ERROR_MESSAGES[
                                          'INVALID_PRICE'])
            if not row[7] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[7]):
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    7] + ":" + row[7] + " | " + VALIDATION_ERROR_MESSAGES[
                                          'INVALID_PRICE'])
            if not row[8] or not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[8]):
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    8] + ":" + row[8] + " | " + VALIDATION_ERROR_MESSAGES[
                                          'INVALID_PRICE'])
            if not row[9] or not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[9]):
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    9] + ":" + row[9] + " | " + VALIDATION_ERROR_MESSAGES[
                                          'INVALID_PRICE'])
        return self.cleaned_data['file']


class ProductsPriceFilterForm(forms.Form):
    state = forms.ModelChoiceField(queryset=State.objects.order_by('state_name'))
    city = forms.ModelChoiceField(queryset=City.objects.all())
    sp_sr_choice = forms.ModelChoiceField(queryset=ShopType.objects.filter(shop_type__in=['sp', 'sr', 'gf']))
    sp_sr_list = forms.ModelMultipleChoiceField(queryset=Shop.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['state'].label = 'Select State'
        self.fields['state'].widget.attrs = {
            'class': 'custom-select custom-select-lg mb-3',
        }

        self.fields['city'].label = 'Select City'
        self.fields['city'].widget.attrs = {
            'class': 'custom-select custom-select-lg mb-3',
        }

        self.fields['sp_sr_choice'].label = 'Select SP/SR/GF'
        self.fields['sp_sr_choice'].widget.attrs = {
            'class': 'custom-select custom-select-lg mb-3',
        }
        self.fields['sp_sr_list'].widget.attrs = {
            'class': 'form-control',
            'size': 15,
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
            attrs={"onChange": 'getProductDetails()'}
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
        # else:
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


# query set from Product HSN which length is gte 6 and lte 8
hsn_choices = ProductHSN.objects.annotate(text_len=Length('product_hsn_code')).filter(text_len__gte=6, text_len__lte=8)


class ParentProductForm(forms.ModelForm):
    """
    Parent Product Form
    """
    product_hsn = forms.ModelChoiceField(queryset=hsn_choices,
                                         widget=autocomplete.ModelSelect2(url='admin:hsn-autocomplete',))

    class Meta:
        model = ParentProduct
        fields = ('parent_brand', 'name', 'product_hsn',
                  'brand_case_size', 'inner_case_size',
                  'product_type', 'is_ptr_applicable', 'ptr_percent', 'ptr_type', 'is_ars_applicable', 'max_inventory',
                  'is_lead_time_applicable', 'discounted_life_percent')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['max_inventory'].initial =  get_config('max_quantity_in_days', 10)

    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data.get('is_ptr_applicable') :
            if not cleaned_data.get('ptr_type'):
                raise ValidationError(_('Invalid PTR Type'))
            elif not cleaned_data.get('ptr_percent'):
                raise ValidationError(_('Invalid PTR Percentage'))

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

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if '' in row:
                if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and
                        row[5] == '' and row[6] == '' and row[7] == '' and row[8] == '' and row[9] == ''):
                    continue
            if not row[0]:
                raise ValidationError(_(f"Row {row_id + 2} | 'Parent Name' can not be empty."))
            elif not re.match("^[ \w\$\_\,\%\@\.\/\#\&\+\-\(\)\*\!\:]*$", row[0]):
                raise ValidationError(_(f"Row {row_id + 2} | {VALIDATION_ERROR_MESSAGES['INVALID_PRODUCT_NAME']}."))
            if not row[1]:
                raise ValidationError(_(f"Row {row_id + 2} | 'Brand' can not be empty."))
            elif not Brand.objects.filter(brand_name=row[1].strip()).exists():
                raise ValidationError(_(f"Row {row_id + 2} | 'Brand' doesn't exist in the system."))
            if not row[2]:
                raise ValidationError(_(f"Row {row_id + 2} | 'Category' can not be empty."))
            else:
                if not Category.objects.filter(category_name=row[2].strip()).exists():
                    categories = row[2].split(',')
                    for cat in categories:
                        cat = cat.strip().replace("'", '')
                        if not Category.objects.filter(category_name=cat).exists():
                            raise ValidationError(
                                _(f"Row {row_id + 2} | 'Category' {cat.strip()} doesn't exist in the system."))
            if not row[3]:
                raise ValidationError(_(f"Row {row_id + 2} | 'HSN' can not be empty."))
            elif not ProductHSN.objects.filter(product_hsn_code=row[3].replace("'", '')).exists():
                raise ValidationError(_(f"Row {row_id + 2} | 'HSN' doesn't exist in the system."))
            if not row[4]:
                raise ValidationError(_(f"Row {row_id + 2} | 'GST' can not be empty."))
            elif not re.match("^([0]|[5]|[1][2]|[1][8]|[2][8])(\s+)?(%)?$", row[4]):
                raise ValidationError(_(f"Row {row_id + 2} | 'GST' can only be 0, 5, 12, 18, 28."))
            if row[5] and not re.match("^([0]|[1][2])(\s+)?%?$", row[5]):
                raise ValidationError(_(f"Row {row_id + 2} | 'CESS' can only be 0, 12."))
            if row[6] and not re.match("^[0-9]\d*(\.\d{1,2})?(\s+)?%?$", row[6]):
                raise ValidationError(_(f"Row {row_id + 2} | 'Surcharge' can only be a numeric value."))
            if not row[7]:
                raise ValidationError(_(f"Row {row_id + 2} | 'Brand Case Size' can not be empty."))
            elif not re.match("^\d+$", row[7]):
                raise ValidationError(_(f"Row {row_id + 2} | 'Brand Case Size' can only be a numeric value."))
            if not row[8]:
                raise ValidationError(_(f"Row {row_id + 2} | 'Inner Case Size' can not be empty."))
            elif not re.match("^\d+$", row[8]):
                raise ValidationError(_(f"Row {row_id + 2} | 'Inner Case Size' can only be a numeric value."))
            if not row[9]:
                raise ValidationError(_(f"Row {row_id + 2} | 'Product Type' can not be empty."))
            elif row[9].lower() not in ['b2b', 'b2c', 'both', 'both b2b and b2c']:
                raise ValidationError(_(f"Row {row_id + 2} | 'GST' can only be 'B2B', 'B2C', 'Both B2B and B2C'."))
        return self.cleaned_data['file']


class ProductForm(forms.ModelForm):
    product_name = forms.CharField(required=True)
    product_ean_code = forms.CharField(required=True)
    parent_product = forms.ModelChoiceField(
        queryset=ParentProduct.objects.all(),
        empty_label='Not Specified',
        widget=autocomplete.ModelSelect2(
            url='admin:parent-product-autocomplete',
            attrs={"onChange": 'getDefaultChildDetails()'}
        )
    )
    weight_value = forms.DecimalField(min_value=0.01)
    product_special_cess = forms.FloatField(required=False, min_value=0)

    class Meta:
        model = Product
        fields = (
        'parent_product', 'reason_for_child_sku', 'product_name', 'product_ean_code', 'product_mrp', 'weight_value',
        'weight_unit', 'use_parent_image', 'status', 'repackaging_type',
        'product_special_cess',)

    def clean(self):
        if 'status' in self.cleaned_data and self.cleaned_data['status'] == 'active':
            if 'repackaging_type' in self.cleaned_data and self.cleaned_data['repackaging_type'] == 'packing_material':
                return self.cleaned_data
            error = True
            if self.instance.id and ProductPrice.objects.filter(approval_status=ProductPrice.APPROVED,
                                                                product_id=self.instance.id).exists():
                error = False
            if error:
                raise forms.ValidationError("Product cannot be made active until an active Product Price exists")
        return self.cleaned_data


class DiscountedProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('product_sku', 'product_name', 'parent_product', 'reason_for_child_sku', 'product_name',
                  'product_ean_code', 'product_mrp', 'status')


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

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if '' in row:
                if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and row[
                    5] == '' and row[6] == ''):
                    continue
            if not row[0]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Parent Product ID' can not be empty."))
            elif not ParentProduct.objects.filter(parent_id=row[0]).exists():
                raise ValidationError(_(f"Row {row_id + 1} | 'Parent Product' doesn't exist in the system."))
            if not row[1]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Reason for Child SKU' can not be empty."))
            elif row[1].lower() not in ['default', 'different mrp', 'different weight', 'different ean', 'offer']:
                raise ValidationError(_(
                    f"Row {row_id + 1} | 'Reason for Child SKU' can only be 'Default', 'Different MRP', 'Different Weight', 'Different EAN', 'Offer'."))
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
            elif row[7] not in [lis[0] for lis in Product.REPACKAGING_TYPES]:
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

                if not row[16]:
                    raise ValidationError(_(f"Row {row_id + 1} | 'Packing SKU' is required for Repackaging"
                                            f" Type 'destination'."))
                elif not Product.objects.filter(product_sku=row[16], repackaging_type='packing_material').exists():
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid Packing Sku"))

                if not row[17]:
                    raise ValidationError(_(f"Row {row_id + 1} | 'Packing Material Weight (gm) per unit (Qty) Of "
                                            f"Destination Sku' is required for Repackaging Type 'destination'."))
                elif not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[17]):
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Packing Material Weight (gm) per unit (Qty)"
                                            f" Of Destination Sku'"))

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

    def validate_row(self, uploaded_data_list, header_list, upload_master_data, category):
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
                            raise ValidationError(_(f"Row {row_num} | {row['sku_id']} | 'SKU ID' doesn't exist."))
                    product = Product.objects.filter(product_sku=row['sku_id'])
                    categry = Category.objects.values('category_name').filter(id=int(category))
                    if not Product.objects.filter(id=product[0].id,
                                                  parent_product__parent_product_pro_category__category__category_name__icontains=categry[0]['category_name']).exists():
                        raise ValidationError(_(f"Row {row_num} | Please upload Products of Category "
                                                f"({categry[0]['category_name']}) that you have "
                                                f"selected in Dropdown Only! "))
                if 'sku_name' in header_list and 'sku_name' in row.keys():
                    if row['sku_name'] != '':
                        if not Product.objects.filter(product_name=row['sku_name']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['sku_name']} |"
                                                    f"'SKU Name' doesn't exist in the system."))
                if 'product_type' in header_list and 'product_type' in row.keys():
                    if row['product_type'] != '':
                        product_type_list = ['b2b', 'b2c', 'both']
                        if row['product_type'] not in product_type_list:
                            raise ValidationError(
                                _(f"Row {row_num} | {row['product_type']} | 'Product Type can either be 'b2b',"
                                  f"'b2c' or 'both'!"))
                if 'parent_id' in header_list and 'parent_id' in row.keys():
                    if row['parent_id'] != '':
                        if not ParentProduct.objects.filter(parent_id=row['parent_id']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['parent_id']} | 'Parent ID' doesn't exist."))
                    parent_product = ParentProduct.objects.filter(parent_id=row['parent_id'])
                    if 'sku_id' not in row.keys():
                        if not ParentProductCategory.objects.filter(category=int(category), parent_product=parent_product[0].id).exists():
                            categry = Category.objects.values('category_name').filter(id=int(category))
                            raise ValidationError(_(f"Row {row_num} | Please upload Products of Category "
                                                    f"({categry[0]['category_name']}) that you have "
                                                    f"selected in Dropdown Only! "))
                if 'parent_name' in header_list and 'parent_name' in row.keys():
                    if row['parent_name'] != '':
                        if not ParentProduct.objects.filter(name=row['parent_name']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['parent_name']} | 'Parent Name' doesn't "
                                                    f"exist."))
                if 'status' in header_list and 'status' in row.keys():
                    if row['status'] != '':
                        status_list = ['active', 'deactivated', 'pending_approval']
                        if row['status'] not in status_list:
                            raise ValidationError(
                                _(f"Row {row_num} | {row['status']} | 'Status can either be 'Active',"
                                  f"'Pending Approval' or 'Deactivated'!"))
                # if 'ean' in header_list and 'ean' in row.keys():
                #     if row['ean'] != '':
                #         if not re.match('^\d{13}$', str(row['ean'])):
                #             raise ValidationError(_(f"Row {row_num} | {row['ean']} | Please Provide valid EAN code."))
                if 'mrp' in header_list and 'mrp' in row.keys():
                    if row['mrp'] != '':
                        if not re.match("^\d+[.]?[\d]{0,2}$", str(row['mrp'])):
                            raise ValidationError(
                                _(f"Row {row_num} | 'Product MRP' can only be a numeric value."))
                if 'weight_unit' in header_list and 'weight_unit' in row.keys():
                    if row['weight_unit'] != '':
                        if str(row['weight_unit']).lower() not in ['gm']:
                            raise ValidationError(_(f"Row {row_num} | 'Weight Unit' can only be 'gm'."))
                if 'weight_value' in header_list and 'weight_value' in row.keys():
                    if row['weight_value'] != '':
                        if not re.match("^\d+[.]?[\d]{0,2}$", str(row['weight_value'])):
                            raise ValidationError(_(f"Row {row_num} | 'Weight Value' can only be a numeric value."))
                if 'hsn' in header_list and 'hsn' in row.keys():
                    if row['hsn'] != '':
                        if not ProductHSN.objects.filter(
                                product_hsn_code=row['hsn']).exists() and not ProductHSN.objects.filter(
                                product_hsn_code='0' + str(row['hsn'])).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['hsn']} |'HSN' doesn't exist in the system."))
                        if len(str(row['hsn'])) < 6 or len(str(row['hsn'])) > 8:
                            raise ValidationError(
                                _(f"Row {row_num} | {row['hsn']} |'HSN' code should be min 6 char and max 8 char."))
                if 'tax_1(gst)' in header_list and 'tax_1(gst)' in row.keys():
                    if row['tax_1(gst)'] != '':
                        if not Tax.objects.filter(tax_name=row['tax_1(gst)']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['tax_1(gst)']} | Invalid Tax(GST)!"))
                if 'tax_2(cess)' in header_list and 'tax_2(cess)' in row.keys():
                    if row['tax_2(cess)'] != '':
                        if not Tax.objects.filter(tax_name=row['tax_2(cess)']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['tax_2(cess)']} "
                                                    f"| Invalid Tax(CESS)!"))
                if 'tax_3(surcharge)' in header_list and 'tax_3(surcharge)' in row.keys():
                    if row['tax_3(surcharge)'] != '':
                        if not Tax.objects.filter(tax_name=row['tax_3(surcharge)']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['tax_3(surcharge)']} "
                                                    f"| Invalid Tax(Surcharge)!"))
                if 'brand_case_size' in header_list and 'brand_case_size' in row.keys():
                        if row['brand_case_size'] != '':
                            if not re.match("^\d+$", str(row['brand_case_size'])):
                                raise ValidationError(
                                    _(
                                        f"Row {row_num} | {row['brand_case_size']} |'Brand Case Size' can only be a numeric value."))
                if 'inner_case_size' in header_list and 'inner_case_size' in row.keys():
                    if row['inner_case_size'] != '':
                        if not re.match("^\d+$", str(row['inner_case_size'])):
                            raise ValidationError(
                                _(
                                    f"Row {row_num} | {row['inner_case_size']} |'Inner Case Size' can only be a numeric value."))
                if 'brand_id' in header_list and 'brand_id' in row.keys():
                    if row['brand_id'] != '':
                        if not Brand.objects.filter(id=row['brand_id']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['brand_id']} | "
                                                    f"'Brand_ID' doesn't exist in the system "))
                if 'brand_name' in header_list and 'brand_name' in row.keys():
                    if row['brand_name'] != '':
                        if not Brand.objects.filter(brand_name=row['brand_name']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['brand_name']} | "
                                                    f"'Brand_Name' doesn't exist in the system "))
                if 'sub_brand_id' in header_list and 'sub_brand_id' in row.keys():
                    if row['sub_brand_id'] != '':
                        if not Brand.objects.filter(id=row['sub_brand_id']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['sub_brand_id']} | "
                                                    f"'Sub_Brand_ID' doesn't exist in the system "))
                if 'sub_brand_name' in header_list and 'sub_brand_id' in row.keys():
                    if row['sub_brand_name'] != '':
                        if not Brand.objects.filter(brand_name=row['sub_brand_name']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['sub_brand_name']} | "
                                                    f"'Sub_Brand_Name' doesn't exist in the system "))
                if 'category_id' in header_list and 'category_id' in row.keys():
                    if row['category_id'] != '':
                        if not Category.objects.filter(id=row['category_id']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['category_id']} | "
                                                    f"'Category_ID' doesn't exist in the system "))
                if 'category_name' in header_list and 'category_name' in row.keys():
                    if row['category_name'] != '':
                        if not Category.objects.filter(category_name=row['category_name']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['category_name']} | "
                                                    f"'Category_Name' doesn't exist in the system "))
                if 'sub_category_id' in header_list and 'sub_category_id' in row.keys():
                    if row['sub_category_id'] != '':
                        if not Category.objects.filter(id=row['sub_category_id']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['sub_category_id']} | "
                                                    f"'Sub_Category_ID' doesn't exist in the system "))
                if 'sub_category_name' in header_list and 'sub_category_name' in row.keys():
                    if row['sub_category_name'] != '':
                        if not Category.objects.filter(category_name=row['sub_category_name']).exists():
                            raise ValidationError(_(f"Row {row_num} | {row['sub_category_name']} | "
                                                    f"'Sub_Category_Name' doesn't exist in the system "))
                if 'max_inventory_in_days' in header_list and 'max_inventory_in_days' in row.keys():
                    if row['max_inventory_in_days'] != '':
                        if not re.match("^\d+$", str(row['max_inventory_in_days'])) or  row['max_inventory_in_days'] < 1\
                                or  row['max_inventory_in_days'] > 999:
                            raise ValidationError(
                                _(f"Row {row_num} | {row['max_inventory_in_days']} |'Max Inventory In Days' is invalid."))

                if 'is_ars_applicable' in header_list and 'is_ars_applicable' in row.keys():
                    if row['is_ars_applicable'] != '' :
                        if str(row['is_ars_applicable']).lower() not in ['yes', 'no']:
                            raise ValidationError(
                                _(f"Row {row_num} | {row['is_ars_applicable']} |"
                                                    f"'is_ars_applicable' can only be 'Yes' or 'No' "))
                if 'is_lead_time_applicable' in header_list and 'is_lead_time_applicable' in row.keys():
                    if row['is_lead_time_applicable'] != '':
                        if str(row['is_lead_time_applicable']).lower() not in ['yes', 'no']:
                            raise ValidationError(
                                _(f"Row {row_num} | {row['is_lead_time_applicable']} |"
                                                    f"'is_lead_time_applicable' can only be 'Yes' or 'No' "))
                if 'is_ptr_applicable' in header_list and 'is_ptr_applicable' in row.keys():
                    if row['is_ptr_applicable'] != '' and str(row['is_ptr_applicable']).lower() not in ['yes', 'no']:
                            raise ValidationError(_(f"Row {row_num} | {row['is_ptr_applicable']} | "
                                                    f"'is_ptr_applicable' can only be 'Yes' or 'No' "))
                    elif row['is_ptr_applicable'].lower()=='yes' and \
                        ('ptr_type' not in row.keys() or row['ptr_type'] == '' or row['ptr_type'].lower() not in ['mark up', 'mark down']):
                        raise ValidationError(_(f"Row {row_num} | "
                                                    f"'ptr_type' can either be 'Mark Up' or 'Mark Down' "))
                    elif row['is_ptr_applicable'].lower() == 'yes' \
                        and ('ptr_percent' not in row.keys() or row['ptr_percent'] == '' or 100 < row['ptr_percent'] or  row['ptr_percent'] < 0) :
                        raise ValidationError(_(f"Row {row_num} | "
                                                    f"'ptr_percent' is invalid"))
                if 'discounted_life_percent' in row.keys() \
                        and (row['discounted_life_percent'] == '' or 100 < row['discounted_life_percent']
                             or  row['discounted_life_percent'] < 0) :
                        raise ValidationError(_(f"Row {row_num} | "
                                                    f"'discounted_life_percent' is invalid"))
                if 'repackaging_type' in header_list and 'repackaging_type' in row.keys():
                    if row['repackaging_type'] != '':
                        if not row['repackaging_type'].lower() in ['none', 'source', 'destination', 'packing_material']:
                            raise ValidationError(
                                _(f"Row {row_num} | {row['repackaging_type']} | 'Repackaging Type can either be 'none',"
                                  f"'source', 'destination' or 'packing_material'!"))
                if 'repackaging_type' in header_list and 'repackaging_type' in row.keys():
                    if row['repackaging_type'] == 'destination':
                        mandatory_fields = ['raw_material', 'wastage', 'fumigation', 'label_printing',
                                            'packing_labour', 'primary_pm_cost', 'secondary_pm_cost', 'final_fg_cost',
                                            'conversion_cost']
                        if 'source_sku_id' not in row.keys():
                            raise ValidationError(_(f"Row {row_num} | 'Source_SKU_ID' can't be empty "
                                                    f"when repackaging_type is destination"))
                        if 'source_sku_id' in row.keys():
                            if row['source_sku_id'] == '':
                                raise ValidationError(_(f"Row {row_num} | 'Source_SKU_ID' can't be empty "
                                                        f"when repackaging_type is destination"))
                        if 'source_sku_name' not in row.keys():
                            raise ValidationError(_(f"Row {row_num} | 'Source_SKU_Name' can't be empty "
                                                    f"when repackaging_type is destination"))
                        if 'source_sku_name' in row.keys():
                            if row['source_sku_name'] == '':
                                raise ValidationError(_(f"Row {row_num} | 'Source_SKU_Name' can't be empty "
                                                        f"when repackaging_type is destination"))
                        for field in mandatory_fields:
                            if field not in header_list:
                                raise ValidationError(_(f"{mandatory_fields} are the essential headers and cannot be empty "
                                                        f"when repackaging_type is destination"))
                            if row[field]=='':
                                raise ValidationError(_(f"Row {row_num} | {row[field]} | {field} cannot be empty"
                                                        f"| {mandatory_fields} are the essential fields when "
                                                        f"repackaging_type is destination"))
                            if not re.match("^\d+[.]?[\d]{0,2}$", str(row[field])):
                                raise ValidationError(_(f"Row {row_num} | {row[field]} | "
                                                        f"{field} can only be a numeric or decimal value."))

                        if 'source_sku_id' in header_list and 'source_sku_id' in row.keys():
                            if row['source_sku_id'] != '':
                                p = re.compile('\'')
                                skuIDs = p.sub('\"', row['source_sku_id'])
                                SKU_IDS = json.loads(skuIDs)
                                for sk in SKU_IDS:
                                    if not Product.objects.filter(product_sku=sk).exists():
                                        raise ValidationError(
                                            _(f"Row {row_num} | {sk} | 'Source SKU ID' doesn't exist."))
                        if 'source_sku_name' in header_list and 'source_sku_name' in row.keys():
                            if row['source_sku_name'] != '':
                                q = re.compile('\'')
                                skuNames = q.sub('\"', row['source_sku_name'])
                                SKU_Names = json.loads(skuNames)
                                for sk in SKU_Names:
                                    if not Product.objects.filter(product_name=sk).exists():
                                        raise ValidationError(_(f"Row {row_num} | {sk} |"
                                                                f"'Source SKU Name' doesn't exist in the system."))

        except ValueError as e:
            raise ValidationError(_(f"Row {row_num} | ValueError : {e} | Please Enter valid Data"))
        except KeyError as e:
            raise ValidationError(_(f"Row {row_num} | KeyError : {e} | Something went wrong while"
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
                    raise ValidationError(_(f"{required_columns} are mandatory columns for 'Upload Master Data'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'sku_id' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_id' in row.keys():
                    if row['sku_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_name' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))
                if 'sku_name' in row.keys():
                    if row['sku_name'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))
                if 'parent_id' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'parent_id' in row.keys():
                    if row['parent_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'parent_name' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Parent_Name' can't be empty"))
                if 'parent_name' in row.keys():
                    if row['parent_name'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Parent_Name' can't be empty"))
                if 'status' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'! | "
                                            f"Status cannot be empty"))
                if 'status' in row.keys():
                    if row['sku_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))

        if upload_master_data == "inactive_status":
            row_num = 1
            required_columns = ['sku_id', 'sku_name', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory columns for 'Set Inactive Status'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'status' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                                            'Status cannot be empty'))
                if 'status' in row.keys():
                    if row['sku_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))
                if 'sku_id' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_id' in row.keys():
                    if row['sku_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_name' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))
                if 'sku_name' in row.keys():
                    if row['sku_name'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))

        if upload_master_data == "sub_brand_with_brand":
            row_num = 1
            required_columns = ['brand_id', 'brand_name']
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(
                        _(f"{required_columns} are mandatory columns for 'Sub Brand and Brand Mapping'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'brand_id' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Brand_ID can't be empty"))
                if 'brand_id' in row.keys():
                    if row['brand_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Brand_ID' can't be empty"))
                if 'brand_name' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Brand_Name' can't be empty"))
                if 'brand_name' in row.keys():
                    if row['brand_name'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Brand_Name' can't be empty"))
        if upload_master_data == "sub_category_with_category":
            row_num = 1
            required_columns = ['category_id', 'category_name']
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory columns"
                                            f" for 'Sub Category and Category Mapping'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'category_id' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Sub_Category_ID' can't be empty"))
                if 'category_id' in row.keys():
                    if row['category_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Category_ID' can't be empty"))
                if 'category_name' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Category_Name' can't be empty"))
                if 'category_name' in row.keys():
                    if row['category_name'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Category_Name' can't be empty"))
        if upload_master_data == "child_parent":
            row_num = 1
            required_columns = ['sku_id', 'parent_id', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory column for 'Child and Parent Mapping'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'sku_id' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_id' in row.keys():
                    if row['sku_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'parent_id' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'parent_id' in row.keys():
                    if row['parent_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'status' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Status can either be 'Active', 'Pending Approval' "
                                            f"or 'Deactivated'!" |
                                            'Status cannot be empty'))
                if 'status' in row.keys():
                    if row['sku_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))
        if upload_master_data == "child_data":
            required_columns = ['sku_id', 'sku_name', 'status']
            row_num = 1
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory columns for 'Set Child Data'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'status' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                                            'Status cannot be empty'))
                if 'status' in row.keys():
                    if row['sku_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))
                if 'sku_id' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_id' in row.keys():
                    if row['sku_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'SKU_ID' can't be empty"))
                if 'sku_name' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))
                if 'sku_name' in row.keys():
                    if row['sku_name'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'SKU_Name' can't be empty"))
        if upload_master_data == "parent_data":
            row_num = 1
            required_columns = ['parent_id', 'parent_name', 'status']
            for ele in required_columns:
                if ele not in header_list:
                    raise ValidationError(_(f"{required_columns} are mandatory columns for 'Set Parent Data'"))
            for row in uploaded_data_list:
                row_num += 1
                if 'parent_id' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Parent_ID' is a mandatory field"))
                if 'parent_id' in row.keys():
                    if row['parent_id'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Parent_ID' can't be empty"))
                if 'parent_name' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Parent_Name' is a mandatory field"))
                if 'parent_name' in row.keys():
                    if row['parent_name'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Parent_Name' can't be empty"))
                if 'status' not in row.keys():
                    raise ValidationError(_(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                                            'Status cannot be empty'))
                if 'status' in row.keys():
                    if row['status'] == '':
                        raise ValidationError(_(f"Row {row_num} | 'Status' can't be empty"))

        self.validate_row(uploaded_data_list, header_list, upload_master_data, category)

    def check_headers(self, excel_file_headers, required_header_list):
        for head in excel_file_headers:
            if head in required_header_list:
                pass
            else:
                raise ValidationError(_(f"Invalid Header | {head} | Allowable headers for the upload are: "
                                        f"{required_header_list}"))

    def read_file(self, excel_file, upload_master_data, category):
        """
        Template Validation (Checking, whether the excel file uploaded by user is correct or not!)
        """
        # Checking the headers of the excel file
        if upload_master_data == "master_data":
            required_header_list = ['sku_id', 'sku_name', 'parent_id', 'parent_name', 'ean', 'mrp', 'hsn',
                                    'weight_unit', 'weight_value','tax_1(gst)', 'tax_2(cess)', 'tax_3(surcharge)',
                                    'brand_case_size', 'inner_case_size',  'brand_id', 'brand_name', 'sub_brand_id',
                                    'sub_brand_name','category_id', 'category_name', 'sub_category_id', 'sub_category_name',
                                    'status', 'repackaging_type', 'source_sku_id', 'source_sku_name', 'raw_material',
                                    'wastage', 'fumigation', 'label_printing', 'packing_labour', 'primary_pm_cost',
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
            required_header_list = ['parent_id', 'parent_name', 'product_type', 'hsn', 'tax_1(gst)', 'tax_2(cess)', 'tax_3(surcharge)', 'brand_case_size',
                                    'inner_case_size', 'brand_id', 'brand_name', 'sub_brand_id', 'sub_brand_name',
                                    'category_id', 'category_name', 'sub_category_id', 'sub_category_name',
                                    'status', 'is_ptr_applicable', 'ptr_type', 'ptr_percent', 'is_ars_applicable',
                                    'max_inventory_in_days', 'is_lead_time_applicable', 'discounted_life_percent']
            excel_file_header_list = excel_file[0]  # headers of the uploaded excel file
            excel_file_headers = [str(ele).lower() for ele in
                                  excel_file_header_list]  # Converting headers into lowercase
            self.check_headers(excel_file_headers, required_header_list)

        headers = excel_file.pop(0)  # headers of the uploaded excel file
        excelFile_headers = [str(ele).lower() for ele in headers]  # Converting headers into lowercase

        # Checking, whether the user uploaded the data below the headings or not!
        if len(excel_file) > 0:
            uploaded_data_by_user_list = []
            excel_dict = {}
            count = 0
            for row in excel_file:
                for ele in row:
                    excel_dict[excelFile_headers[count]] = ele
                    count += 1
                uploaded_data_by_user_list.append(excel_dict)
                excel_dict = {}
                count = 0
            self.check_mandatory_columns(uploaded_data_by_user_list, excelFile_headers, upload_master_data, category)
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
                    self.read_file(excel_file_data, self.data['upload_master_data'], self.data['category'])
                else:
                    raise ValidationError("Excel File cannot be empty.Please add some data to upload it!")

                return self.cleaned_data['file']
            else:
                raise ValidationError("Excel File is required!")
        except Exception as e:
            raise ValidationError(str(e))


class ProductsFilterForm(forms.Form):
    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.order_by('category_name'),
    )

    brand = forms.ModelMultipleChoiceField(queryset=Brand.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.fields['category1'].widget.attrs['class'] = 'test'
        self.fields['category'].widget.attrs = {
            'class': 'select2-filter',
            # 'size':15,
        }
        self.fields['brand'].widget.attrs = {
            'class': 'form-control',
            'size': 15,
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
        self.fields['file'].widget.attrs = {
            'class': 'custom-file-input',
        }

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        for id, row in enumerate(reader):
            if not row[0] or row[0].isspace():
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    0] + ":" + row[0] + " | Product Name required")
            if not row[1] or row[1].isspace():
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    1] + ":" + row[1] + " | Product short description required")
            if not row[2] or row[2].isspace():
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    2] + ":" + row[2] + " | Product long description required")
            if not row[3] or row[3].isspace():
                raise ValidationError(_("PRODUCT_GF_CODE required at Row[%(value)s]."), params={'value': id + 1}, )
            if not row[12] or row[12].isspace():
                raise ValidationError(_("Product weight in gram required at Row[%(value)s]."),
                                      params={'value': id + 1}, )
            #            if row[3]:
            #                product_gf = Product.objects.filter(product_gf_code=row[3])
            #                if product_gf:
            #                    raise ValidationError(_("PRODUCT_GF_CODE should be
            #                    unique at Row[%(value)s]."), params={'value': id+1},)
            # if not row[4] or not re.match("^\d{13}$", row[4]):
            #     raise ValidationError(_("INVALID_PRODUCT_EAN_CODE at Row[%(value)s]. Exactly 13 numbers required"), params={'value': id+1},)

            if not row[5] or not re.match("^[\d]*$", row[5]):
                raise ValidationError(_('INVALID_BRAND_ID at Row[%(value)s]. It should be numeric'),
                                      params={'value': id + 1}, )
            if row[5]:
                try:
                    Brand.objects.get(pk=row[5])
                except:
                    raise ValidationError(_('No brand found with given BRAND_ID at Row[%(value)s]'),
                                          params={'value': id + 1}, )

            if not row[6] or not re.match("^[\d\,]*$", row[6]):
                raise ValidationError(_('INVALID_CATEGORY_ID/IDs at Row[%(value)s]. It should be numeric'),
                                      params={'value': id + 1}, )
            if row[6]:
                try:
                    for c in row[6].split(','):
                        if c is not '':
                            Category.objects.get(pk=c.strip())
                except:
                    raise ValidationError(_('No category found with given CATEGORY_ID/IDs at Row[%(value)s]'),
                                          params={'value': id + 1}, )

            if not row[7] or not re.match("^[\d\,]*$", row[7]):
                raise ValidationError(_('INVALID_TAX_ID/IDs at Row[%(value)s]. It should be numeric'),
                                      params={'value': id + 1}, )
            if row[7]:
                try:
                    for t in row[7].split(','):
                        if t is not '':
                            Tax.objects.get(pk=t.strip())
                except:
                    raise ValidationError(_('No tax found with given TAX_ID/IDs at Row[%(value)s]'),
                                          params={'value': id + 1}, )

            if row[8] and not re.match("^[\d\,]*$", row[8]):
                raise ValidationError(_('INVALID_SIZE_ID at Row[%(value)s]. It should be numeric'),
                                      params={'value': id + 1}, )
            if row[8]:
                try:
                    Size.objects.get(pk=row[8])
                except:
                    raise ValidationError(_('No size found with given SIZE_ID at Row[%(value)s]'),
                                          params={'value': id + 1}, )

            if row[9] and not re.match("^[\d\,]*$", row[9]):
                raise ValidationError(_('INVALID_COLOR_ID at Row[%(value)s]. It should be numeric'),
                                      params={'value': id + 1}, )
            if row[9]:
                try:
                    Color.objects.get(pk=row[9])
                except:
                    raise ValidationError(_('No color found with given COLOR_ID at Row[%(value)s]'),
                                          params={'value': id + 1}, )

            if row[10] and not re.match("^[\d\,]*$", row[10]):
                raise ValidationError(_('INVALID_FRAGRANCE_ID at Row[%(value)s]. It should be numeric'),
                                      params={'value': id + 1}, )
            if row[10]:
                try:
                    Fragrance.objects.get(pk=row[10])
                except:
                    raise ValidationError(_('No fragrance found with given FRAGRANCE_ID at Row[%(value)s]'),
                                          params={'value': id + 1}, )

            if row[11] and not re.match("^[\d\,]*$", row[11]):
                raise ValidationError(_('INVALID_FLAVOR_ID at Row[%(value)s]. It should be numeric'),
                                      params={'value': id + 1}, )
            if row[11]:
                try:
                    Flavor.objects.get(pk=row[11])
                except:
                    raise ValidationError(_('No flavor found with given FLAVOR_ID at Row[%(value)s]'),
                                          params={'value': id + 1}, )

            if row[12] and not re.match("^[\d+\.?\d]*$", row[12]):  # "^[\d\,]*$",
                raise ValidationError(_('INVALID WEIGHT at Row[%(value)s]. It should be numeric'),
                                      params={'value': id + 1}, )
            # if row[12]:
            #     try:
            #         Weight.objects.get(pk=row[12])
            #     except:
            #         raise ValidationError(_('No weight found with given WEIGHT_ID at Row[%(value)s]'), params={'value': id+1},)

            if row[13] and not re.match("^[\d\,]*$", row[13]):
                raise ValidationError(_('INVALID_PACKAGE_SIZE_ID at Row[%(value)s]. It should be numeric'),
                                      params={'value': id + 1}, )
            if row[13]:
                try:
                    PackageSize.objects.get(pk=row[13])
                except:
                    raise ValidationError(_('No package size found with given PACKAGE_SIZE_ID at Row[%(value)s]'),
                                          params={'value': id + 1}, )
            if not row[14] or not re.match("^[\d]*$", row[14]):
                raise ValidationError(_('INVALID_INNER_CASE_SIZE at Row[%(value)s]. It should be numeric'),
                                      params={'value': id + 1}, )
            if not row[15] or not re.match("^[\d]*$", row[15]):
                raise ValidationError(_('INVALID_CASE_SIZE at Row[%(value)s]. It should be numeric'),
                                      params={'value': id + 1}, )
            if not row[16]:
                raise ValidationError(_('HSN_CODE_REQUIRED at Row[%(value)s].'), params={'value': id + 1}, )
        return self.cleaned_data['file']


class ProductPriceAddPerm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:product-price-autocomplete', )
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
            url='admin:product-price-autocomplete', )
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
        # self.fields['start_date'].required = True
        # self.fields['end_date'].required = True
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
            url='admin:vendor-autocomplete')
    )

    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:product-price-autocomplete',
            attrs={
                "onChange": 'getProductMRP(this)'
            },
        )
    )

    def __init__(self, *args, **kwargs):
        super(ProductVendorMappingForm, self).__init__(*args, **kwargs)
        self.fields['product_mrp'].widget.attrs['readonly'] = True

    class Meta:
        model = ProductVendorMapping
        fields = ['vendor', 'product', 'product_price', 'product_price_pack', 'product_mrp', 'case_size']

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
            url='admin:product-price-autocomplete', )
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
                csv_reader = csv.reader(codecs.iterdecode(file, 'utf-8', errors='ignore'))
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
                    gst_tax = Tax.objects.values('id') \
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
                    cess_tax = Tax.objects.values('id') \
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
        reader = csv.reader(codecs.iterdecode(file, 'utf-8', errors='ignore'))
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
        fields = ('file',)

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
                csv_reader = csv.reader(codecs.iterdecode(file, 'utf-8', errors='ignore'))
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
                    gst_tax = Tax.objects.values('id') \
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
                    cess_tax = Tax.objects.values('id') \
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
        reader = csv.reader(codecs.iterdecode(file, 'utf-8', errors='ignore'))
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

    available_packing_material_weight = forms.CharField(label='Available Packing Material Weight (Kg)', required=False)
    available_packing_material_weight_initial = forms.CharField(widget=forms.HiddenInput(), required=False)
    packing_sku_weight_per_unit_sku = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Repackaging
        fields = ('seller_shop', 'source_sku', 'destination_sku', 'source_repackage_quantity', 'status',
                  "available_source_weight", "available_source_quantity", "destination_sku_quantity", "remarks",
                  "expiry_date", "source_picking_status", 'available_packing_material_weight',
                  'available_packing_material_weight_initial', 'packing_sku_weight_per_unit_sku')
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        if 'expiry_date' in self.cleaned_data:
            today_date = datetime.date.today()
            if self.cleaned_data['expiry_date'] < today_date:
                raise forms.ValidationError("Expiry Date should be greater than or equal to {}".format(today_date))
        if 'source_sku' in self.cleaned_data:
            try:
                normal_type = InventoryType.objects.filter(inventory_type='normal').last()
                product_id = self.cleaned_data['source_sku'].id
                product_inv = get_stock(self.cleaned_data['seller_shop'], normal_type, [int(product_id)])
                if product_inv and int(product_id) in product_inv:
                    source_quantity = product_inv[int(product_id)]
                else:
                    raise forms.ValidationError("Warehouse Inventory Does Not Exist")
            except Exception as e:
                raise forms.ValidationError("Warehouse Inventory Could not be fetched")
            if self.cleaned_data['source_repackage_quantity'] + self.cleaned_data['available_source_quantity'] != \
                    source_quantity:
                raise forms.ValidationError("Source Quantity Changed! Please Input Again")
            try:
                ProductPackingMapping.objects.get(sku=self.cleaned_data['destination_sku'])
            except:
                raise forms.ValidationError("Please Map A Packing Material To The Selected Destination Product First")
        if 'destination_sku_quantity' in self.cleaned_data:
            try:
                ppm = ProductPackingMapping.objects.get(sku=self.instance.destination_sku)
            except:
                raise forms.ValidationError("Please Map A Packing Material To The Selected Destination Product First")
            try:
                inv = WarehouseInventory.objects.get(inventory_type__inventory_type='normal', sku=ppm.packing_sku,
                                                     inventory_state__inventory_state='total_available',
                                                     warehouse=self.instance.seller_shop)
            except:
                raise forms.ValidationError("Packing Material Warehouse Inventory Not Found")
            if inv.weight < self.cleaned_data['destination_sku_quantity'] * ppm.packing_sku_weight_per_unit_sku:
                raise forms.ValidationError("Packing Material Inventory Not Sufficient")
        if self.instance.source_picking_status in ['pickup_created', 'picking_assigned']:
            raise forms.ValidationError("Source pickup is still not complete.")
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super(RepackagingForm, self).__init__(*args, **kwargs)
        if self.instance.pk and 'expiry_date' in self.fields:
            self.fields['expiry_date'].required = True
        readonly = ['available_source_weight', 'available_source_quantity', 'available_packing_material_weight']
        for key in readonly:
            if key in self.fields:
                self.fields[key].widget.attrs['readonly'] = True
        if self.instance.pk and 'available_packing_material_weight' in self.fields:
            self.fields['available_packing_material_weight'].initial = 0
            self.fields['available_packing_material_weight_initial'].initial = 0
            self.fields['packing_sku_weight_per_unit_sku'].initial = 0
            repack_obj = Repackaging.objects.get(pk=self.instance.pk)
            ppm = ProductPackingMapping.objects.filter(sku=repack_obj.destination_sku).last()
            if ppm:
                inventory = WarehouseInventory.objects.filter(inventory_type__inventory_type='normal',
                                                              inventory_state__inventory_state='total_available',
                                                              sku=ppm.packing_sku, warehouse=repack_obj.seller_shop).last()
                self.fields['available_packing_material_weight'].initial = (inventory.weight - repack_obj.destination_sku_quantity * ppm.packing_sku_weight_per_unit_sku)/1000 if inventory else 0
                self.fields['available_packing_material_weight_initial'].initial = inventory.weight if inventory else 0
                self.fields['packing_sku_weight_per_unit_sku'].initial = ppm.packing_sku_weight_per_unit_sku


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
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        for id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if '' in row:
                if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and row[
                    5] == '' and row[6] == ''):
                    continue
            if not row[0]:
                raise ValidationError(
                    "Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | Product ID cannot be empty")
            try:
                Product.objects.get(pk=row[0])
            except:
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[
                    0] + " | Product does not exist with this ID")

            if not row[3] or not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[3]):
                raise ValidationError(
                    "Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | " + VALIDATION_ERROR_MESSAGES[
                        'EMPTY_OR_NOT_VALID'] % ("MRP"))

            if not (row[4].title() == "Per Piece" or row[4].title() == "Per Pack"):
                raise ValidationError(
                    "Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | " + VALIDATION_ERROR_MESSAGES[
                        'EMPTY_OR_NOT_VALID_STRING'] % ("Gram_to_brand_Price_Unit"))

            if not row[5] or not re.match("^[0-9]{0,}(\.\d{0,2})?$", row[5]):
                raise ValidationError(
                    "Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | " + VALIDATION_ERROR_MESSAGES[
                        'INVALID_PRICE'])

            if not row[6] or not re.match("^[\d\,]*$", row[6]):
                raise ValidationError(
                    "Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | " + VALIDATION_ERROR_MESSAGES[
                        'EMPTY_OR_NOT_VALID'] % ("Case_size"))

        return self.cleaned_data['file']

class ProductPriceSlabForm(forms.ModelForm):
    """
    This class is used to create Slab Product Price for a particular product
    """

    class Meta:
        model = ProductPrice
        fields = ('product', 'mrp', 'seller_shop', 'buyer_shop', 'city', 'pincode', 'approval_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'approval_status' in self.fields:
            self.fields['approval_status'].choices = ProductPrice.APPROVAL_CHOICES[:1]

class ProductPriceSlabCreationForm(forms.ModelForm):
    """
        This class is used to create Slab Product Price for a particular product
        """
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
        queryset=Product.objects.filter(repackaging_type__in=['none', 'source', 'destination']),
        empty_label='Not Specified',
        widget=autocomplete.ModelSelect2(
            url='product-autocomplete',
            attrs={"onChange": 'getProductDetails()'},
            forward=(forward.Const(1, 'price-slab'), )
        )
    )
    mrp = forms.DecimalField(required=False)
    slab_price_applicable = forms.BooleanField(required=False)
    selling_price = forms.DecimalField(min_value=0, decimal_places=2, required=False)
    offer_price = forms.DecimalField(min_value=0, decimal_places=2, required=False)
    offer_price_start_date = forms.DateField(required=False, widget=forms.widgets.DateInput(attrs={'type': 'date'}))
    offer_price_end_date = forms.DateField(required=False, widget=forms.widgets.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = ProductPrice
        fields = ('product', 'mrp', 'seller_shop', 'buyer_shop', 'city', 'pincode', 'approval_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mrp'].disabled = True
        if 'approval_status' in self.fields:
            self.fields['approval_status'].choices = ProductPrice.APPROVAL_CHOICES[:1]

    def clean(self):
        data = self.cleaned_data
        if not data.get('product'):
            raise ValidationError(_('Invalid Product.'))
        if data.get('product') and data['product'].product_mrp:
            data['mrp'] = data['product'].product_mrp
        if not data.get('slab_price_applicable'):
            if data.get('selling_price') is None or data.get('selling_price') == 0 \
                    or data.get('selling_price') > data['mrp']*data['product'].product_inner_case_size:
                raise ValidationError('Invalid Selling Price')
            elif data.get('offer_price') is not None:
                if data.get('selling_price') <= data.get('offer_price'):
                    raise ValidationError('Invalid Offer Price')
                elif data.get('offer_price_start_date') is None or data.get(
                        'offer_price_start_date') < datetime.datetime.today().date():
                    raise ValidationError('Offer Price Start Date is invalid')
                elif data.get('offer_price_end_date') is None \
                        or data.get('offer_price_end_date') < data.get('offer_price_start_date'):
                    raise ValidationError('Offer Price End Date is invalid')
        return data


class PriceSlabForm(forms.ModelForm):
    """
    This class is used to create the Price Slabs
    """

    class Meta:
        model = PriceSlab
        fields = ('start_value', 'end_value', 'selling_price', 'offer_price', 'offer_price_start_date', 'offer_price_end_date')

    def __init__(self, *args, **kwargs):
        super(PriceSlabForm, self).__init__(*args, **kwargs)
        if self.instance.pk is not None:
            return

        if self.prefix == 'price_slabs-0':
            self.fields['start_value'].widget.attrs['readonly'] = True
            self.fields['end_value'].widget.attrs['readonly'] = True
        elif self.prefix == 'price_slabs-1' and self.fields.get('end_value') is not None:
            self.fields['end_value'].widget.attrs['readonly'] = True


class SlabInlineFormSet(BaseInlineFormSet):

    """
        This class is used to check for PriceSlab form validations
    """

    def clean(self):
        if self.data.get('slab_price_applicable') is None:
            return
        super(SlabInlineFormSet, self).clean()
        last_slab_end_value = 0
        last_slab_selling_price = 0
        for form in self.forms:
            slab_data = form.cleaned_data

            if slab_data.get('start_value') is None or slab_data.get('start_value') < 0:
                raise ValidationError("Slab Start Value is Invalid")
            elif slab_data.get('end_value') is None or slab_data.get('end_value') < 0:
                raise ValidationError("Slab End Value is Invalid")
            elif slab_data.get('selling_price') is None or slab_data.get('selling_price') == 0:
                raise ValidationError('Invalid Selling Price')
            elif form.prefix != 'price_slabs-0' and slab_data['start_value'] <= last_slab_end_value:
                raise ValidationError("Quantity should be greater than earlier slabs quantity")
            elif form.prefix != 'price_slabs-0' and slab_data.get('selling_price') and (slab_data.get('selling_price') >= last_slab_selling_price \
                    or (last_slab_offer_price and slab_data.get('selling_price') >= last_slab_offer_price)) :
                raise ValidationError("Selling price should be less than earlier slabs selling price/offer price.")
            elif slab_data.get('offer_price') is not None:
                if slab_data.get('selling_price') <= slab_data.get('offer_price'):
                    raise ValidationError('Invalid Offer Price')
                elif slab_data.get('offer_price_start_date') is None or slab_data.get('offer_price_start_date') < datetime.datetime.today().date():
                    raise ValidationError('Offer Price Start Date is invalid')
                elif slab_data.get('offer_price_end_date') is None or slab_data.get('offer_price_end_date') < slab_data.get('offer_price_start_date'):
                    raise ValidationError('Offer Price End Date is invalid')
            last_slab_end_value = slab_data['end_value']
            last_slab_selling_price = slab_data.get('selling_price')
            last_slab_offer_price = slab_data.get('offer_price')


class UploadSlabProductPriceForm(forms.Form):
    """
    Upload SLab Product Prices Form
    """
    file = forms.FileField(label='Upload Slab Product Prices')

    class Meta:
        model = SlabProductPrice

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if isBlankRow(row, len(first_row)):
                continue
            product = Product.objects.filter(product_sku=row[0]).last()
            if not row[0] or product is None:
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'SKU'"))
            is_ptr_applicable = product.parent_product.is_ptr_applicable
            case_size = product.parent_product.inner_case_size
            selling_price = float(row[6])
            selling_price_per_saleable_unit = selling_price
            if is_ptr_applicable:
                ptr_percent = product.parent_product.ptr_percent
                ptr_type = product.parent_product.ptr_type
                if ptr_type == ParentProduct.PTR_TYPE_CHOICES.MARK_UP:
                    selling_price = product.product_mrp / (1 + (ptr_percent / 100))
                elif ptr_type == ParentProduct.PTR_TYPE_CHOICES.MARK_DOWN:
                    selling_price = product.product_mrp*(1 - (ptr_percent / 100))
                selling_price_per_saleable_unit = float(round(selling_price, 2))


            if not row[2] or not Shop.objects.filter(id=row[2], shop_type__shop_type__in=['sp']).exists():
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Shop Id'"))
            elif not row[5]:
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Quantity'"))
            if not row[6] or float(row[6]) <= 0:
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Selling price'"))
            elif selling_price_per_saleable_unit != float(row[6]):
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Selling Price', PTR {selling_price_per_saleable_unit} != Slab1 SP {row[6]}"))
            elif float(row[6]) > float(product.product_mrp):
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Selling Price', Slab1 SP {row[6]} > MRP {product.product_mrp}"))
            elif row[7] and float(row[7]) >= float(row[6]):
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Offer Price'"))
            elif row[7] and (not isDateValid(row[8], "%d-%m-%y") or not isDateValid(row[9], "%d-%m-%y")
                             or getStrToDate(row[8], "%d-%m-%y") < datetime.datetime.today().date()
                             or getStrToDate(row[9], "%d-%m-%y") < datetime.datetime.today().date()
                             or getStrToDate(row[8], "%d-%m-%y") > getStrToDate(row[9], "%d-%m-%y")):
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 1 Offer Start/End Date'"))
            elif int(row[5]) > 0 :
                if not row[10] or int(row[10]) != int(row[5])+1:
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Quantity'"))
                elif not row[11] or float(row[11]) <= 0:
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Selling Price'"))
                elif float(row[11]) >= float(row[6]):
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Selling Price', Slab2 SP {row[11]} >= Slab1 SP {row[6]}"))
                elif (row[7] and float(row[11]) >= float(row[7])):
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Selling Price', Slab2 SP {row[11]} >= Slab 1 Offer Price {row[7]}"))
                elif row[12] and float(row[12]) >= float(row[11]):
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Offer Price'"))
                elif row[12] and (not isDateValid(row[13], "%d-%m-%y") or not isDateValid(row[14], "%d-%m-%y")
                                  or getStrToDate(row[13], "%d-%m-%y") < datetime.datetime.today().date()
                                  or getStrToDate(row[14], "%d-%m-%y") < datetime.datetime.today().date()
                                  or getStrToDate(row[13], "%d-%m-%y") > getStrToDate(row[14], "%d-%m-%y")):
                    raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Slab 2 Offer Start/End Date'"))
        return self.cleaned_data['file']

class UploadDiscountedProductPriceForm(forms.Form):
    """
    Upload SLab Product Prices Form
    """
    file = forms.FileField(label='Upload Discounted Product Prices')

    class Meta:
        model = DiscountedProductPrice

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if isBlankRow(row, len(first_row)):
                continue
            product = Product.objects.filter(product_sku=row[0]).last()
            if not row[0] or product is None:
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'SKU'"))
            if int(product.product_type) != 1:
                raise ValidationError(_(f"Row {row_id + 1} | Product 'SKU' is not discounted"))
            if not row[2] or not Shop.objects.filter(id=row[2], shop_type__shop_type__in=['sp']).exists():
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Shop Id'"))
            seller_shop = Shop.objects.filter(pk = int(row[2])).last()
            manual_price_update = int(row[4])
            selling_price = float(row[5])
            if not manual_price_update:
                original_product = product.product_ref
                product_price = original_product.product_pro_price.all()
                shops = Shop.objects.filter(shop_product_price__in = product_price).distinct()
                if seller_shop not in shops:
                    raise ValidationError(_(f"Row {row_id + 1} | No original product exist for this shop and no selling price is provided."))
            if manual_price_update and not selling_price:
                raise ValidationError(_(f"Row {row_id + 1} | No 'Selling Price' in case of manual price update"))
            if manual_price_update and selling_price:
                if selling_price == 0 \
                        or selling_price > product.product_mrp:
                    raise ValidationError('Invalid Selling Price')
        return self.cleaned_data['file']
    
def only_int(value):
    if value.isdigit() is False:
        raise ValidationError('HSN can only be a numeric value.')


class ProductHSNForm(forms.ModelForm):
    product_hsn_code = forms.CharField(max_length=8, min_length=6, validators=[only_int])


    class Meta:
        model = ProductHSN
        fields = ['product_hsn_code']

    # this function will be used for the validation
    def clean(self):

        # data from the form is fetched using super function
        super(ProductHSNForm, self).clean()


class ProductPackingMappingFormSet(forms.models.BaseInlineFormSet):

    def clean(self):
        super(ProductPackingMappingFormSet, self).clean()
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
                raise ValidationError("At least one packing material mapping is required")
        if valid:
            return self.cleaned_data

    class Meta:
        model = ProductPackingMapping


class ProductPackingMappingForm(forms.ModelForm):
    packing_sku = forms.ModelChoiceField(
        queryset=Product.objects.filter(repackaging_type='packing_material'),
        empty_label='Not Specified',
        widget=autocomplete.ModelSelect2(
            url='packing-product-autocomplete'
        )
    )
    packing_sku_weight_per_unit_sku = forms.CharField(required=True)

    class Meta:
        model = ProductPackingMapping
        fields = ('packing_sku', 'packing_sku_weight_per_unit_sku')


class UploadPackingSkuInventoryAdminForm(forms.Form):
    file = forms.FileField(label='Upload csv', required=False)
    inventory_threshold = forms.FloatField(label='Inventory Threshold (Kg)')

    class Meta:
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        threshold, created = GlobalConfig.objects.get_or_create(key='packing_sku_inventory_threshold_kg')
        if created:
            threshold.value = 50
            threshold.save()
        self.fields['inventory_threshold'].initial = threshold.value

    def clean_file(self):
        if not self.cleaned_data['file']:
            return self.cleaned_data['file']
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)

        unique_data_list = []
        form_data_list = []
        user = get_current_user()
        for row_id, row in enumerate(reader):
            row = [str(i).strip() for i in row]
            if '' in row:
                if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and
                        row[5] == '' and row[6] == '' and row[7] == '' and row[8] == ''):
                    continue
            # validation for shop id, it should be numeric.
            if not row[0] or not re.match("^[\d]*$", row[0]):
                raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s]. It should be numeric.'),
                                      params={'value': row_id + 2}, )

            # validation for shop
            check_shop = Shop.objects.filter(pk=row[0]).last()
            if not check_shop:
                raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s].'
                                        'Warehouse Id does not exists in the system.'),
                                      params={'value': row_id + 2}, )
            elif check_shop.shop_type.shop_type == 'f' and not user.is_superuser:
                """
                    Single virtual bin present for all products in a franchise shop. This stock correction does not
                     apply to Franchise shops.
                """
                raise ValidationError(_('The warehouse/shop is of type Franchise. Stock changes not allowed'),
                                      params={'value': row_id + 1}, )

            # validate for product name
            if not row[1]:
                raise ValidationError(_('Product Name can not be blank at Row number [%(value)s].'),
                                      params={'value': row_id + 2}, )

            # validate for product sku
            if not row[2]:
                raise ValidationError(_('Product SKU can not be blank at Row number [%(value)s].'),
                                      params={'value': row_id + 2}, )

            # validate for product
            if not Product.objects.filter(product_sku=row[2], repackaging_type='packing_material').exists():
                raise ValidationError(_('Invalid Product SKU at Row number [%(value)s].'
                                        'Product SKU does not exists in the system / Not a packing material'),
                                      params={'value': row_id + 2}, )

            # validate for expiry_date
            if not row[3]:
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Expiry date can not be empty."))

            try:
                # if expiry date is "dd/mm/yy"
                if datetime.datetime.strptime(row[3], '%d/%m/%y'):
                    pass
            except:
                try:
                    # if expiry date is "dd/mm/yyyy"
                    if datetime.datetime.strptime(row[3], '%d/%m/%Y'):
                        pass
                    else:
                        raise ValidationError(_(
                            "Issue in Row" + " " + str(
                                row_id + 2) + "," + "Expiry date format is not correct, It should be"
                                                    " DD/MM/YYYY, DD/MM/YY, DD-MM-YYYY and DD-MM-YY"
                                                    " format, Example:-11/07/2020, 11/07/20,"
                                                    "11-07-2020 and 11-07-20."))
                except:
                    try:
                        # if expiry date is "dd-mm-yy"
                        if datetime.datetime.strptime(row[3], '%d-%m-%y'):
                            pass
                    except:
                        try:
                            # if expiry date is "dd-mm-yyyy"
                            if datetime.datetime.strptime(row[3], '%d-%m-%Y'):
                                pass
                        except:
                            # raise validation error
                            raise ValidationError(_(
                                "Issue in Row" + " " + str(row_id + 2) + "," + "Expiry date format is not correct, It"
                                                                               " should be DD/MM/YYYY, DD/MM/YY, DD-MM-YYYY"
                                                                               " and DD-MM-YY format, Example:-11/07/2020,"
                                                                               " 11/07/20, 11-07-2020 and 11-07-20."))

            # validate for bin id
            if not row[4]:
                raise ValidationError(_('Bin Id can not be blank at Row number [%(value)s].'),
                                      params={'value': row_id + 2}, )

            # validate for bin
            if not Bin.objects.filter(bin_id=row[4], is_active=True,
                                      warehouse=Shop.objects.filter(pk=row[0]).last()).exists():
                raise ValidationError(_('Invalid Bin Id at Row number [%(value)s]. '
                                        'Bin Id is not associated with Warehouse.'),
                                      params={'value': row_id + 2}, )

            # validation for weight
            if not row[5] or not re.match("^[\d+\.?\d]*$", row[5]):
                raise ValidationError(_('Invalid Normal Weight at Row number [%(value)s].'),
                                      params={'value': row_id + 2}, )

            if not row[6] or not re.match("^[\d+\.?\d]*$", row[6]):
                raise ValidationError(_('Invalid Damaged Weight at Row number [%(value)s].'),
                                      params={'value': row_id + 2}, )

            if not row[7] or not re.match("^[\d+\.?\d]*$", row[7]):
                raise ValidationError(_('Invalid Expired Weight at Row number [%(value)s].'),
                                      params={'value': row_id + 2}, )

            if not row[8] or not re.match("^[\d+\.?\d]*$", row[8]):
                raise ValidationError(_('Invalid Missing Weight at Row number [%(value)s].'),
                                      params={'value': row_id + 2}, )

            if float(row[5]) < 0:
                raise ValidationError(
                    _('Invalid Normal Weight at Row number [%(value)s]. It should be greater than or equal to 0.'),
                    params={'value': row_id + 2}, )
            if float(row[6]) < 0:
                raise ValidationError(
                    _('Invalid Damaged Weight at Row number [%(value)s]. It should be greater than or equal to 0.'),
                    params={'value': row_id + 2}, )
            if float(row[7]) < 0:
                raise ValidationError(
                    _('Invalid Expired Weight at Row number [%(value)s]. It should be greater than or equal to 0.'),
                    params={'value': row_id + 2}, )
            if float(row[8]) < 0:
                raise ValidationError(
                    _('Invalid Missing Weight at Row number [%(value)s]. It should be greater than or equal to 0.'),
                    params={'value': row_id + 2}, )

            # to get the date format
            try:
                expiry_date = datetime.datetime.strptime(row[3], '%d/%m/%Y').strftime('%Y-%m-%d')
            except:
                try:
                    expiry_date = datetime.datetime.strptime(row[3], '%d-%m-%Y').strftime('%Y-%m-%d')
                except:
                    try:
                        expiry_date = datetime.datetime.strptime(row[3], '%d-%m-%y').strftime('%Y-%m-%d')
                    except:
                        expiry_date = datetime.datetime.strptime(row[3], '%d/%m/%y').strftime('%Y-%m-%d')

            # to validate normal weight for past expired date
            if expiry_date < datetime.datetime.today().strftime("%Y-%m-%d"):
                if float(row[5]) > 0:
                    raise ValidationError(_(
                        "Issue in Row" + " " + str(
                            row_id + 2) + "," + "For Past expiry date, the normal weight (final)"
                                                " should be 0."))

            # to validate damaged weight for past expired date
            if expiry_date < datetime.datetime.today().strftime("%Y-%m-%d"):
                if float(row[6]) > 0:
                    raise ValidationError(_(
                        "Issue in Row" + " " + str(
                            row_id + 2) + "," + "For Past expiry date, the damaged weight (final)"
                                                " should be 0."))

            # to validate expired weight for future expired date
            if expiry_date > datetime.datetime.today().strftime("%Y-%m-%d"):
                if float(row[7]) > 0:
                    raise ValidationError(_(
                        "Issue in Row" + " " + str(row_id + 2) + "," + "For Future expiry date, the expired weight "
                                                                       " should be 0."))

            # to get object from GRN Order Product Mapping
            sku = row[2]
            # create batch id
            batch_id = create_batch_id(sku, row[3])
            bin_exp_obj = BinInventory.objects.filter(warehouse=row[0],
                                                      bin=Bin.objects.filter(bin_id=row[4], warehouse=row[0]).last(),
                                                      sku=Product.objects.filter(
                                                          product_sku=row[2]).last(),
                                                      batch_id=batch_id)
            # if combination of expiry date and sku is not exist in GRN Order Product Mapping
            if not bin_exp_obj.exists() and check_shop.shop_type.shop_type != 'f':
                bin_in_obj = BinInventory.objects.filter(
                    warehouse=row[0], sku=Product.objects.filter(product_sku=row[2]).last())
                for bin_in in bin_in_obj:
                    sku = row[1]
                    # create batch id
                    if not (bin_in.batch_id == create_batch_id(sku, row[3])):
                        if bin_in.bin.bin_id == row[4] and bin_in.weight != 0:
                            raise ValidationError(_(
                                "Issue in Row" + " " + str(row_id + 2) + "," + "Non zero weight of 2 Different"
                                                                               " Batch ID/Expiry date for same SKU"
                                                                               " can’t be in the same Bin."))
            unique_data_list.append(row[0] + row[2] + row[3] + row[4])
            form_data_list.append(row)
        duplicate_data_list = ([item for item, count in collections.Counter(unique_data_list).items() if count > 1])
        if len(duplicate_data_list) > 0:
            raise ValidationError(_(
                "Alert ! Duplicate Data. Same SKU, Expiry Date, Bin ID exists in the csv,"
                " please re-verify at your end."))

        return form_data_list


class DiscountedProductPriceSlabCreationForm(forms.ModelForm):
    """
        This class is used to create Slab Product Price for a particular discounted product
        """
    seller_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='sp'),
        widget=autocomplete.ModelSelect2(
            url='admin:seller_shop_autocomplete',
            attrs={"onChange": 'getSellingPriceDetails()'},
        )
    )

    buyer_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(url='admin:retailer_autocomplete',
        ),
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
        queryset=Product.objects.filter(repackaging_type__in=['none', 'source', 'destination'], product_type=1),
        empty_label='Not Specified',
        widget=autocomplete.ModelSelect2(
            url='discounted-product-autocomplete',
            attrs={"onChange": 'getSellingPriceDetails()'},
            forward=(forward.Const(0, 'price-slab'), )
        )
    )
    mrp = forms.DecimalField(required=False)
    is_manual_price_update = forms.BooleanField(required = False)
    selling_price = forms.DecimalField(min_value=0, decimal_places=2, required=False)

    class Meta:
        model = ProductPrice
        fields = ('product', 'mrp', 'seller_shop', 'buyer_shop', 'city', 'pincode', 'approval_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mrp'].disabled = True
        if 'approval_status' in self.fields:
            self.fields['approval_status'].choices = ProductPrice.APPROVAL_CHOICES[:1]

    def clean(self):
        data = self.cleaned_data
        if not data.get('product'):
            raise ValidationError(_('Invalid Product.'))
        if data.get('product') and data['product'].product_mrp:
            data['mrp'] = data['product'].product_mrp


        if data.get('selling_price') is None or data.get('selling_price') == 0 \
                or data.get('selling_price') > data['mrp']:
            raise ValidationError('Invalid Selling Price')

        return data

