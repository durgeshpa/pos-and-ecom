from django import forms
from .models import Vendor
from django.urls import reverse
import datetime, csv, codecs, re
from django.core.exceptions import ValidationError
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from products.models import Product

class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(VendorForm, self).__init__(*args, **kwargs)
        self.fields['vendor_products_csv'].help_text = self.instance.products_sample_file
        
    def clean_vendor_products_csv(self):
        if not self.cleaned_data['vendor_products_csv'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['vendor_products_csv'], 'utf-8'))
        first_row = next(reader)
        for id,row in enumerate(reader):
            try:
                Product.objects.get(pk=row[0])
            except:
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | Product does not exist with this ID")
            if not row[0]:
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | Product ID cannot be empty")
            if row[2] and not re.match("^\d{0,8}(\.\d{1,4})?$", row[2]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[2]+":"+row[2]+" | "+VALIDATION_ERROR_MESSAGES['INVALID_PRICE'])
        return self.cleaned_data['vendor_products_csv']
