from django import forms
from .models import Address, City, State
from django.urls import reverse

class AddressForm(forms.ModelForm):
    state = forms.ModelChoiceField(queryset=State.objects.order_by('state_name'))
    city = forms.ModelChoiceField(queryset=City.objects.all())

    class Media:
        js = ('https://code.jquery.com/jquery-3.2.1.js','admin/js/vendor/vendor_form.js',
                'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.6-rc.0/js/select2.min.js')
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.6-rc.0/css/select2.min.css',)
            }

    class Meta:
        model = Address
        fields = '__all__'

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
