import re
from django import forms
from .models import Bin, In, Putaway, PutawayBinInventory, BinInventory, Out, Pickup
from shops.models import Shop
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

warehouse_choices = Shop.objects.filter(shop_type__shop_type='sp')


class BulkBinUpdation(forms.Form):
    file = forms.FileField(label='Select a file')

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name[-5:] == '.xlsx':
            raise forms.ValidationError("Sorry! Only Excel file accepted")
        return file


class BinForm(forms.ModelForm):
    bin_id = forms.CharField(required=True, max_length=14)
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    class Meta:
        model = Bin
        fields = ['warehouse', 'bin_id', 'bin_type', 'is_active', ]

    def clean_bin_id(self):
        if len(self.cleaned_data['bin_id']) < 14:
            raise forms.ValidationError(_('Bin Id min and max char limit is 14.Example:-B2BZ01SR01-001'),)
        if not self.cleaned_data['bin_id'][0:3] in ['B2B', 'B2C']:
            raise forms.ValidationError(_('First three letter should be start with either B2B and B2C.'
                                          'Example:-B2BZ01SR01-001'),)
        if not self.cleaned_data['bin_id'][3] in ['Z']:
            raise forms.ValidationError(_('Zone should be start with char Z.Example:-B2BZ01SR01-001'), )
        if not bool(re.match('^[0-9]+$', self.cleaned_data['bin_id'][4:6]
                             ) and not self.cleaned_data['bin_id'][4:6] == '00'):
            raise forms.ValidationError(_('Zone number should be start in between 01 to 99.Example:-B2BZ01SR01-001'), )
        if not self.cleaned_data['bin_id'][6:8] in ['SR', 'PA']:
            raise forms.ValidationError(_('Rack type should be start with either SR and RA char only.'
                                          'Example:-B2BZ01SR01-001'),)
        if not bool(re.match('^[0-9]+$', self.cleaned_data['bin_id'][8:10]
                             )and not self.cleaned_data['bin_id'][8:10] == '00'):
            raise forms.ValidationError(_('Rack number should be start in between 01 to 99.'
                                          'Example:- B2BZ01SR01-001'), )
        if not self.cleaned_data['bin_id'][10] in ['-']:
            raise forms.ValidationError(_('Only - allowed in between Rack number and Bin Number.'
                                          'Example:-B2BZ01SR01-001'),)
        if not bool(re.match('^[0-9]+$', self.cleaned_data['bin_id'][11:14]
                             )and not self.cleaned_data['bin_id'][11:14] == '000'):
            raise forms.ValidationError(_('Bin number should be start in between 001 to 999.Example:-B2BZ01SR01-001'), )
        return self.cleaned_data['bin_id']


class InForm(forms.ModelForm):
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    class Meta:
        model = In
        fields = '__all__'


class PutAwayForm(forms.ModelForm):
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    class Meta:
        model = Putaway
        fields = ['warehouse','putaway_type', 'putaway_type_id', 'sku', 'batch_id','quantity','putaway_quantity']

    def __init__(self, *args, **kwargs):
        super(PutAwayForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        self.fields['putaway_quantity'].initial = 0
        # self.fields['putaway_quantity'].disabled = True


class PutAwayBinInventoryForm(forms.ModelForm):
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    class Meta:
        model = PutawayBinInventory
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(PutAwayBinInventoryForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

        if instance:
            self.fields['putaway_quantity'].initial = 0
            # self.fields['putaway_quantity'].disabled = True


class BinInventoryForm(forms.ModelForm):
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    class Meta:
        model = BinInventory
        fields = '__all__'


class OutForm(forms.ModelForm):
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    class Meta:
        model = Out
        fields = '__all__'


class PickupForm(forms.ModelForm):
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)
    pickup_quantity = forms.IntegerField(initial=0)

    class Meta:
        model = Pickup
        fields = '__all__'






