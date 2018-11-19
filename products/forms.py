from django import forms
from addresses.models import City, State
from shops.models import Shop, ShopType
from tempus_dominus.widgets import DatePicker, TimePicker, DateTimePicker
import datetime, csv, codecs, re
from retailer_backend.validators import *
from django.core.exceptions import ValidationError
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES

class ProductPriceForm(forms.Form):
    state = forms.ModelChoiceField(queryset=State.objects.order_by('state_name'))
    city = forms.ModelChoiceField(queryset=City.objects.all())
    sp_sr_choice = forms.ModelChoiceField(queryset=ShopType.objects.filter(shop_type__in=['sp','sr']))
    sp_sr_list = forms.ModelMultipleChoiceField(queryset=Shop.objects.all())
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

        self.fields['sp_sr_choice'].label = 'Select SP/SR'
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
            'class':'form-control',
            'required':None,
            }

        self.fields['end_date_time'].label = 'Ends at'
        self.fields['end_date_time'].widget.attrs={
            'class':'form-control',
            'required':None,

            }

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        first_row = next(reader)
        for id,row in enumerate(reader):
            if not row[0] or not re.match("^[\d]*$", row[0]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | "+VALIDATION_ERROR_MESSAGES['INVALID_ID'])
            if not row[1] or not re.match("^[ \w\$\_\,\@\.\/\#\&\+\-\(\)]*$", row[1]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[1]+":"+row[1]+" | "+VALIDATION_ERROR_MESSAGES['INVALID_PRODUCT_NAME'])
            if not row[2] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[2]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[2]+":"+row[2]+" | "+VALIDATION_ERROR_MESSAGES['INVALID_PRICE'])
            if not row[3] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[3]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[3]+":"+row[3]+" | "+VALIDATION_ERROR_MESSAGES['INVALID_PRICE'])
            if not row[4] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[4]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[4]+":"+row[4]+" | "+VALIDATION_ERROR_MESSAGES['INVALID_PRICE'])
            if not row[5] or not re.match("^\d{0,8}(\.\d{1,4})?$", row[5]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[5]+":"+row[5]+" | "+VALIDATION_ERROR_MESSAGES['INVALID_PRICE'])
        return self.cleaned_data['file']

    def read_csv(self):
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        id = "jaggi"
        IDValidator(id)
