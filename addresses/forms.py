from django import forms
from .models import Address, City, State, Pincode
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from dal import autocomplete

from retailer_backend.validators import PinCodeValidator


class AddressForm(forms.ModelForm):
    state = forms.ModelChoiceField(queryset=State.objects.order_by('state_name'))
    city = forms.ModelChoiceField(queryset=City.objects.all())
    pincode_link = forms.ModelChoiceField(
        queryset=Pincode.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:pincode_autocomplete',
            forward=('city',)),
        required=False
    )
    class Media:
        js = ('https://code.jquery.com/jquery-3.2.1.js','admin/js/vendor/vendor_form.js',
                'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.6-rc.0/js/select2.min.js')
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.6-rc.0/css/select2.min.css',)
            }

    class Meta:
        model = Address
        fields = ('nick_name', 'address_contact_name', 'address_contact_number',
                  'address_type', 'address_line1', 'state', 'city', 'pincode',
                  'pincode_link')

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        self.fields['state'].widget.attrs={
            'class':'js-example-basic-single',
            'style':'width: 25%'
            }

        self.fields['city'].widget.attrs={
            'class':'js-example-basic-single',
            'data-cities-url': reverse('admin:ajax_load_cities'),
            'style':'width: 25%'
            }


class StateForm(forms.ModelForm):
    state_code = forms.CharField(max_length=2, min_length=1,
                                 required=True,
                                 validators=[RegexValidator(
                                             regex='^[0-9]*$',
                                             message=("State Code should"
                                                      " be numeric"),
                                             code='invalid_code_code'), ])

    class Meta:
        Model = State
        fields = ('country', 'state_name', 'state_code', 'status',)


class PincodeForm(forms.ModelForm):
    pincode = forms.CharField(max_length=6, min_length=6,
                              validators=[PinCodeValidator])

    class Meta:
        Model = Pincode
        fields = ('city', 'pincode')
