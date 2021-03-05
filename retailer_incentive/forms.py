import codecs
import csv
import datetime
import re

from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
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


class UploadSchemeShopMappingForm(forms.Form):
    """
    Upload Scheme SHop Mapping Form
    """
    file = forms.FileField(label='Upload Scheme Shop Mapping CSV')

    class Meta:
        model = SchemeShopMapping

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        first_row = next(reader)
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if '' in row:
                if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' ):
                    continue
            if not row[0]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Scheme ID' can not be empty."))
            elif not Scheme.objects.filter(id=row[0], is_active=True, end_date__gte=datetime.datetime.today().date()).exists():
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Scheme'"))
            if not row[1]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Scheme name' can not be empty."))
            elif not re.match("^[ \w\$\_\,\%\@\.\/\#\&\+\-\(\)\*\!\:]*$", row[1]):
                raise ValidationError(_(f"Row {row_id + 1} | {VALIDATION_ERROR_MESSAGES['INVALID_NAME']}."))
            if not row[2]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Shop Id' can not be empty."))
            elif not Shop.objects.filter(id=row[2], shop_type__shop_type__in=['f','r']).exists():
                raise ValidationError(_(f"Row {row_id + 1} | No retailer/franchise shop exists in the system with thid ID."))
            if not row[3]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Shop Name' can not be empty."))
            elif not re.match("^[ \w\$\_\,\%\@\.\/\#\&\+\-\(\)\*\!\:]*$", row[3]):
                raise ValidationError(_(f"Row {row_id + 1} | {VALIDATION_ERROR_MESSAGES['INVALID_NAME']}."))
            if not row[4]:
                raise ValidationError(_(f"Row {row_id + 1} | 'Priority' can not be empty."))
            elif row[4] not in SchemeShopMapping.PRIORITY_CHOICE._identifier_map.keys():
                raise ValidationError(_(f"Row {row_id + 1} | 'Priority' can only be P1 or P2"))

        return self.cleaned_data['file']