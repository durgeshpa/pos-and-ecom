from django import forms
from addresses.models import City, State, Pincode
from shops.models import Shop, ShopType
from tempus_dominus.widgets import DatePicker, TimePicker, DateTimePicker
import datetime, csv, codecs, re
from retailer_backend.validators import *
from django.core.exceptions import ValidationError
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from products.models import ProductCategory, Tax, Size, Color, Fragrance, Weight, Flavor, PackageSize
from brand.models import Brand, Vendor
from categories.models import Category
from django.utils.translation import gettext_lazy as _
from products.models import Product, ProductImage, ProductPrice, ProductVendorMapping
from shops.models import Shop
from dal import autocomplete

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
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
        queryset=Shop.objects.filter(shop_type__shop_type='r'),
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

    class Meta:
        model = ProductPrice
        fields = ('product', 'mrp', 'selling_price', 'seller_shop',
                  'buyer_shop', 'city', 'pincode',
                  'start_date', 'end_date', 'approval_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.fields['start_date'].required = True
        # self.fields['end_date'].required = True
        if 'approval_status' in self.fields:
            self.fields['approval_status'].choices = ProductPrice.APPROVAL_CHOICES[:1]


class ProductForm(forms.ModelForm):
    product_name = forms.CharField(required=True)
    product_short_description = forms.CharField(required=True)
    product_slug = forms.CharField(required=True)
    product_gf_code = forms.CharField(required=True)

    class Meta:
        model = Product
        fields = ('product_name','product_slug','product_short_description', 'product_long_description',
                  'product_gf_code', 'product_ean_code', 'product_hsn','product_brand', 'product_inner_case_size',
                  'product_case_size','weight_value', 'weight_unit', 'status',)


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
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
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
        fields = ('product', 'mrp', 'selling_price', 'seller_shop',
                  'buyer_shop', 'city', 'pincode',
                  'start_date', 'end_date', 'approval_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # if 'start_date' in self.fields and 'end_date' in self.fields:
        #     self.fields['start_date'].required = True
        #     self.fields['end_date'].required = True
        if 'approval_status' in self.fields:
            self.fields['approval_status'].initial = ProductPrice.APPROVAL_PENDING
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
        fields = ('product', 'mrp', 'selling_price', 'seller_shop',
                  'buyer_shop', 'city', 'pincode',
                  'start_date', 'end_date', 'approval_status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.fields['start_date'].required = True
        #self.fields['end_date'].required = True
        # self.fields['approval_status'].choices = ProductPrice.APPROVAL_CHOICES[:-1]


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
        queryset=Shop.objects.filter(shop_type__shop_type='r'),
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
        fields = ('vendor', 'product', 'product_price', 'product_mrp', 'case_size', )
