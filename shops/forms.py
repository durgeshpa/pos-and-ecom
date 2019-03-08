from django import forms
from .models import ParentRetailerMapping, Shop, ShopType
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from dal import autocomplete
import csv
import codecs


class ParentRetailerMappingForm(forms.ModelForm):
    parent = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp','gf']),
        widget=autocomplete.ModelSelect2(url='shop-parent-autocomplete', )
    )
    retailer = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp', 'r']),
        widget=autocomplete.ModelSelect2(url='shop-retailer-autocomplete', )
    )

    class Meta:
        Model = ParentRetailerMapping
        fields = ('parent','retailer','status')

    def clean(self):
        cleaned_data = super().clean()
        retailer = cleaned_data.get("retailer")
        parent_mapping = ParentRetailerMapping.objects.filter(retailer=retailer, status=True)
        if parent_mapping.exists():
            for parent in parent_mapping:
                parent.status=False
                parent.save()
        return cleaned_data


class ShopParentRetailerMappingForm(forms.ModelForm):
    parent = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp','gf']),
        widget=autocomplete.ModelSelect2(url='shop-parent-autocomplete', )
    )

    class Meta:
        Model = ParentRetailerMapping


class StockAdjustmentUploadForm(forms.Form):
    shop = forms.ModelChoiceField(
            queryset=Shop.objects.filter(shop_type__shop_type__in=['sp']),
        )
    upload_file = forms.FileField()

    def clean_upload_file(self):
        if self.cleaned_data['upload_file'].name[-4:] != ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['upload_file'], 'utf-8'))
        first_row = next(reader)
        for id, row in enumerate(reader):
            if not row[0]:
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | Product Id required")
            else:
                try:
                    Product.objects.get(pk=row[1])
                except:
                    raise ValidationError(_('INVALID_PRODUCT_ID at Row[%(value)s]'), params={'value': id+1},)

            if not row[1] or not re.match("^[\d]*$", row[1]):
                raise ValidationError(_('INVALID_AVAILABLE_QTY at Row[%(value)s]. It should be numeric'),params={'value': id + 1}, )

            if not row[2] or not re.match("^[\d]*$", row[2]):
                raise ValidationError(_('INVALID_DAMAGED_QTY at Row[%(value)s]. It should be numeric'),params={'value': id + 1}, )

            if not row[3] or not re.match("^[\d]*$", row[3]):
                raise ValidationError(_('INVALID_EXPIRED_QTY at Row[%(value)s]. It should be numeric'),params={'value': id + 1}, )

        return self.cleaned_data['file']

