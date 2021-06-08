from django import forms
from django.core.validators import EMPTY_VALUES, validate_email
from django.utils.translation import ugettext_lazy as _

from .models import Vendor, BrandPosition
from django.urls import reverse
from addresses.models import City, State
from dal import autocomplete
from shops.models import Shop


class VendorForm(forms.ModelForm):
    state = forms.ModelChoiceField(queryset=State.objects.order_by('state_name'))
    city = forms.ModelChoiceField(queryset=City.objects.all())
    email_id = forms.CharField(max_length=255,
                               widget= forms.Textarea(attrs={'placeholder': 'Enter comma separated email ids'}))

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

    def to_list(self, value):

        """
        normalizes the data to a list of the email strings.
        """
        if value in EMPTY_VALUES:
            return []

        value = [item.strip() for item in value.split(',') if item.strip()]

        return list(set(value))

    def clean(self):
        cleaned_data = super(VendorForm, self).clean()
        email_filed_value = cleaned_data.get('email_id')
        email_list = self.to_list(email_filed_value)
        if email_list in EMPTY_VALUES :
            raise forms.ValidationError('This field is required.')
        for email in email_list:
            try:
                validate_email(email)
            except forms.ValidationError:
                raise forms.ValidationError(_("'%s' is not a valid email address.") % email)
        return cleaned_data


class BrandForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp',]),
        widget=autocomplete.ModelSelect2(url='shop-autocomplete', ),
        required=False
    )

    class Meta:
        Model = BrandPosition
        fields = '__all__'
