from django import forms
from shops.models import Shop, ShopType
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from dal import autocomplete
import csv
import codecs
from products.models import Product, ProductPrice
import datetime, csv, codecs, re
from tempus_dominus.widgets import DatePicker, TimePicker, DateTimePicker
from django.db.models import Q

class SalesReportForm(forms.Form):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp', ]),
        widget=autocomplete.ModelSelect2(url='banner-shop-autocomplete', ),
    )
    start_date = forms.DateTimeField(
    widget=DateTimePicker(
        options={
            'format': 'YYYY-MM-DD H:mm:ss',
            }
        ),
    )
    end_date = forms.DateTimeField(
        widget=DateTimePicker(
            options={
            'format': 'YYYY-MM-DD H:mm:ss',
            }
        ),
    )

    def __init__(self, request, *args, **kwargs):
        super(SalesReportForm, self).__init__(*args, **kwargs)
        if request.user:
            queryset = Shop.objects.filter(shop_type__shop_type__in=['sp'])
            queryset = queryset.filter(Q(related_users=request.user) | Q(shop_owner=request.user))
        # latest = queryset.latest('id')
        self.fields['shop'].queryset = queryset
