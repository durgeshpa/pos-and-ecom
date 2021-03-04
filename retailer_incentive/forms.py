import datetime

from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError
from tempus_dominus.widgets import DatePicker

from retailer_incentive.models import Scheme, SchemeSlab, SchemeShopMapping
from retailer_incentive.utils import get_active_mappings
from shops.models import Shop


class SchemeCreationForm(forms.ModelForm):
    """
    This class is used to create the Scheme
    """

    class Meta:
        model = Scheme
        fields = ['name', 'start_date', 'end_date', 'is_active']

    def clean(self):
        data = self.cleaned_data
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if start_date < datetime.datetime.today().date():
            raise ValidationError('Start date cannot be earlier than today')

        if end_date <= start_date:
            raise ValidationError('End Date should be later than the Start Date')

        return self.cleaned_data


class SchemeSlabCreationForm(forms.ModelForm):
    """
    This class is used to create the Scheme Slabs
    """
    class Meta:
        model = SchemeSlab
        fields = ('min_value', 'max_value', 'discount_value', 'discount_type')


class SchemeShopMappingCreationForm(forms.ModelForm):
    """
    This class is used to create the Scheme Shop Mapping
    """
    shop_choice = Shop.objects.filter(shop_type__shop_type__in=['f', 'r'])
    scheme = forms.ModelChoiceField(queryset=Scheme.objects.all())
    shop = forms.ModelChoiceField(queryset=shop_choice,
                                  widget=autocomplete.ModelSelect2(url='shop-autocomplete'))

    def clean(self):
        data = self.cleaned_data
        shop = data['shop']
        active_mappings = get_active_mappings(shop.id)
        if active_mappings.count() >= 2:
            raise ValidationError("Shop Id - {} already has 2 active mappings".format(shop.id))
        existing_active_mapping = active_mappings.last()
        if existing_active_mapping and existing_active_mapping.priority == data['priority']:
            raise ValidationError("Shop Id - {} already has an active {} mappings"
                                  .format(shop.id, SchemeShopMapping.PRIORITY_CHOICE[data['priority']]))


    class Meta:
        model = SchemeShopMapping
        fields = ('scheme', 'shop', 'priority', 'is_active')

