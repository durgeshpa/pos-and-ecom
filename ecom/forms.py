from django import forms
from dal import autocomplete
from django.db.models import Q

from pos.models import RetailerProduct
from shops.models import *
from ecom.models import Tag


class TagProductForm(forms.ModelForm):
    tag = forms.ModelChoiceField(
        queryset = Tag.objects.all()
    )
    shop = forms.ModelChoiceField(
        queryset = Shop.objects.filter(shop_type__shop_type__in=['f'], status=True, approval_status=2, 
                                pos_enabled=True),
        widget = autocomplete.ModelSelect2(
            url='ecom-shop-autocomplete'
        )
    )
    product = forms.ModelChoiceField(
        queryset = RetailerProduct.objects.filter(~Q(sku_type=4) & Q(online_enabled = True)),
        widget=autocomplete.ModelSelect2(
            url='ecom-tagproduct-autocomplete',
            forward=('shop',),
        )
    )