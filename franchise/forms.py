from django.db.models import Q
from django import forms

from accounts.middlewares import get_current_user
from wms.forms import BinForm
from audit.forms import AuditCreationForm
from shops.models import Shop


class FranchiseBinForm(BinForm):

    def __init__(self, *args, **kwargs):
        super(FranchiseBinForm, self).__init__(*args, **kwargs)

        if 'warehouse' in self.fields:
            franchise_shop = Shop.objects.filter(shop_type__shop_type__in=['f'])
            user = get_current_user()
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
            franchise_shop = Shop.objects.filter(shop_type__shop_type__in=['f'])
            user = get_current_user()
            if not user.is_superuser:
                franchise_shop = franchise_shop.filter(Q(related_users=user) | Q(shop_owner=user))

            self.fields['warehouse'].queryset = franchise_shop
            self.fields['warehouse'].empty_label = None

        if 'audit_level' in self.fields:
            self.fields['audit_level'].choices = [c for c in self.fields['audit_level'].choices if c[0] == 1]

        if 'audit_run_type' in self.fields:
            self.fields['audit_run_type'].choices = [c for c in self.fields['audit_run_type'].choices if c[0] == 0]