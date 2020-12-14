from django.db.models import Q

from accounts.middlewares import get_current_user
from wms.forms import BinForm
from audit.forms import AuditCreationForm
from shops.models import Shop


class FranchiseBinForm(BinForm):

    def __init__(self, *args, **kwargs):
        super(FranchiseBinForm, self).__init__(*args, **kwargs)
        franchise_shop = Shop.objects.filter(shop_type__shop_type__in=['f'])
        user = get_current_user()
        if not user.is_superuser:
            franchise_shop = franchise_shop.filter(Q(related_users=user) | Q(shop_owner=user)).last()

        self.fields['warehouse'].queryset = franchise_shop
        self.fields['warehouse'].empty_label = None

    def clean(self):
        user = get_current_user()
        if not user.is_superuser:
            franchise_shop = Shop.objects.filter(shop_type__shop_type__in=['f'])
            franchise_shop = franchise_shop.filter(Q(related_users=user) | Q(shop_owner=user)).last()
            self.cleaned_data['warehouse'] = franchise_shop
        return self.cleaned_data


class FranchiseAuditCreationForm(AuditCreationForm):

    def __init__(self, *args, **kwargs):
        super(FranchiseAuditCreationForm, self).__init__(*args, **kwargs)
        franchise_shop = Shop.objects.filter(shop_type__shop_type__in=['f'])
        user = get_current_user()
        if not user.is_superuser:
            franchise_shop = franchise_shop.filter(Q(related_users=user) | Q(shop_owner=user)).last()

        self.fields['warehouse'].queryset = franchise_shop
        self.fields['warehouse'].empty_label = None

    def clean(self):
        user = get_current_user()
        if not user.is_superuser:
            franchise_shop = Shop.objects.filter(shop_type__shop_type__in=['f'])
            franchise_shop = franchise_shop.filter(Q(related_users=user) | Q(shop_owner=user)).last()
            self.cleaned_data['warehouse'] = franchise_shop
        return self.cleaned_data