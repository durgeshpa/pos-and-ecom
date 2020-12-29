from django.db.models import Q
from django import forms
from dal import autocomplete

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