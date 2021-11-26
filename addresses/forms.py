from django import forms

from shops.models import Shop
from .models import Address, City, State, Pincode, DispatchCenterCityMapping, DispatchCenterPincodeMapping
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from dal import autocomplete

from retailer_backend.validators import PinCodeValidator


class AddressForm(forms.ModelForm):
    state = forms.ModelChoiceField(
        queryset=State.objects.all(),
        widget=autocomplete.ModelSelect2(url='state-autocomplete',)
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        widget=autocomplete.ModelSelect2(url='admin:city_autocomplete',
                                         forward=('state',)),
        required=True
    )
    pincode_link = forms.ModelChoiceField(
        queryset=Pincode.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:pincode_autocomplete',
            forward=('city',)),
        required=True
    )

    class Meta:
        model = Address
        fields = ('nick_name', 'address_contact_name',
                  'address_contact_number', 'address_type', 'address_line1',
                  'state', 'city', 'pincode_link')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nick_name'].required = True
        self.fields['address_contact_name'].required = True
        self.fields['address_contact_number'].required = True


class DispatchCenterCityMappingForm(forms.ModelForm):
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        widget=autocomplete.ModelSelect2(url='dispatch-center-cities-autocomplete'),
        required=True
    )

    class Meta:
        model = DispatchCenterCityMapping
        fields = ('city', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DispatchCenterPincodeMappingForm(forms.ModelForm):
    pincode = forms.ModelChoiceField(
        queryset=Pincode.objects.all(),
        widget=autocomplete.ModelSelect2(url='dispatch-center-pincodes-autocomplete'),
        required=True
    )

    class Meta:
        model = DispatchCenterPincodeMapping
        fields = ('pincode', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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
