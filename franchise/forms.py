from django.db.models import Q
from django import forms
from dal import autocomplete
import csv
import codecs
from django.core.exceptions import ValidationError

from accounts.middlewares import get_current_user
from wms.forms import BinForm
from audit.forms import AuditCreationForm
from shops.models import Shop
from franchise.models import ShopLocationMap


class FranchiseBinForm(BinForm):

    def __init__(self, *args, **kwargs):
        super(FranchiseBinForm, self).__init__(*args, **kwargs)

        if 'warehouse' in self.fields:
            # If bin creation/editing allowed, to be done only for shop type Franchise here
            franchise_shop = Shop.objects.filter(shop_type__shop_type__in=['f'])
            user = get_current_user()
            # Bins can be created/edited for the logged in user warehouse/franchise only
            if not user.is_superuser:
                franchise_shop = franchise_shop.filter(Q(related_users=user) | Q(shop_owner=user))

            self.fields['warehouse'].queryset = franchise_shop
            self.fields['warehouse'].empty_label = None


class FranchiseAuditCreationForm(AuditCreationForm):
    warehouse_choices = Shop.objects.filter(shop_type__shop_type__in=['f'])
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    def __init__(self, *args, **kwargs):
        super(FranchiseAuditCreationForm, self).__init__(*args, **kwargs)

        if 'warehouse' in  self.fields:
            # If audit creation/editing allowed, to be done only for shop type Franchise here
            franchise_shop = Shop.objects.filter(shop_type__shop_type__in=['f'])
            user = get_current_user()
            # Audits can be created/edited for the logged in user warehouse/franchise only
            if not user.is_superuser:
                franchise_shop = franchise_shop.filter(Q(related_users=user) | Q(shop_owner=user))

            self.fields['warehouse'].queryset = franchise_shop
            self.fields['warehouse'].empty_label = None

        # Audit can only be at Product level for Franchise shops. Cannot be Bin wise as single virtual bin exists
        # for all products of all batches
        if 'audit_level' in self.fields:
            self.fields['audit_level'].choices = [c for c in self.fields['audit_level'].choices if c[0] == 1]

        # Audit can only be manual for Franchise shops. Cannot be automated currently.
        if 'audit_run_type' in self.fields:
            self.fields['audit_run_type'].choices = [c for c in self.fields['audit_run_type'].choices if c[0] == 0]


class ShopLocationMapForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='f'),
        widget=autocomplete.ModelSelect2(url='admin:franchise-shop-autocomplete',)
    )

    class Meta:
        model = ShopLocationMap
        fields = ('shop', 'location_name')


class FranchiseStockForm(forms.Form):
    file = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['file'].label = 'Choose File'
        self.fields['file'].widget.attrs = {'class': 'custom-file-input', }

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        for id, row in enumerate(reader):
            if not row[0] or row[0].isspace():
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    0] + ":" + row[0] + " | ITEMCODE is required")
            if not row[2] or row[2].isspace():
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    2] + ":" + row[2] + " | WAREHOUSENAME is required")
            if not row[5] or row[5].isspace():
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    5] + ":" + row[5] + " | CURRENTSTOCK is required")
            if not row[4] or row[4].isspace():
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[
                    4] + ":" + row[4] + " | MRP is required")
        return self.cleaned_data['file']
