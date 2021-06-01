from django import forms
from django.core.validators import validate_email
from multi_email_field.forms import MultiEmailField

from .models import Vendor, Brand, BrandPosition
from django.urls import reverse
import datetime, csv, codecs, re
from django.core.exceptions import ValidationError
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from products.models import Product, ProductVendorMapping
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
        exclude = ('email_id',)

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




class BrandForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp',]),
        widget=autocomplete.ModelSelect2(url='shop-autocomplete', ),
        required=False
    )

    class Meta:
        Model = BrandPosition
        fields = '__all__'
