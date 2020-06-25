from django import forms
from .models import Bin, In, Putaway, PutawayBinInventory, BinInventory, Out, Pickup
from shops.models import Shop


warehouse_choices = Shop.objects.filter(shop_type__shop_type='sp')


class BulkBinUpdation(forms.Form):
    file = forms.FileField(label='Select a file')

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name[-5:] == '.xlsx':
            raise forms.ValidationError("Sorry! Only Excel file accepted")
        return file


class BinForm(forms.ModelForm):
    bin_id = forms.CharField(required=True, max_length=20)
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    class Meta:
        model = Bin
        fields = ['warehouse', 'bin_id', 'bin_type', 'is_active', ]


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






