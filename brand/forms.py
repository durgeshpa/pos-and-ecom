from django import forms
from .models import Vendor, Brand, BrandPosition
from django.urls import reverse
import datetime, csv, codecs, re
from django.core.exceptions import ValidationError
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from products.models import Product
from addresses.models import City, State
from dal import autocomplete
from shops.models import Shop

class VendorForm(forms.ModelForm):
    state = forms.ModelChoiceField(queryset=State.objects.order_by('state_name'))
    city = forms.ModelChoiceField(queryset=City.objects.all())

    class Media:
        js = ('https://code.jquery.com/jquery-3.2.1.js','admin/js/vendor/vendor_form.js',
                'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.6-rc.0/js/select2.min.js')
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.6-rc.0/css/select2.min.css',)
            }

    class Meta:
        model = Vendor
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(VendorForm, self).__init__(*args, **kwargs)
        self.fields['state'].widget.attrs={
            'class':'js-example-basic-single',
            'style':'width: 25%'
            }

        self.fields['city'].widget.attrs={
            'class':'js-example-basic-single',
            'data-cities-url': reverse('admin:ajax_load_cities'),
            'style':'width: 25%'
            }

        self.fields['vendor_products_csv'].help_text = """<h3><a href="%s" target="_blank">Download Products List</a></h3>""" % (reverse('admin:products_export_for_vendor'))

    def clean_vendor_products_csv(self):
        if self.cleaned_data['vendor_products_csv']:
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
                if row[3] and not re.match("^\d{0,8}(\.\d{1,4})?$", row[3]):
                    raise ValidationError("Row["+str(id+1)+"] | "+first_row[3]+":"+row[3]+" | "+VALIDATION_ERROR_MESSAGES['INVALID_PRICE'])
            return self.cleaned_data['vendor_products_csv']


class BrandForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp',]),
        widget=autocomplete.ModelSelect2(url='shop-autocomplete', ),
        required=False
    )

    class Meta:
        Model = BrandPosition
        fields = '__all__'
