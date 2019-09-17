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
            queryset=Shop.objects.filter(shop_type__shop_type__in=['sp']),
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

    def __init__(self, user, *args, **kwargs):
        super(SalesReportForm, self).__init__(*args, **kwargs)
        if user:
            queryset = Shop.objects.filter(shop_type__shop_type__in=['sp'])
            queryset = queryset.filter(Q(related_users=user) | Q(shop_owner=user))
            self.fields['shop'].queryset = queryset

class OrderReportForm(forms.Form):
    shop = forms.ModelChoiceField(
            queryset=Shop.objects.filter(shop_type__shop_type__in=['sp']),
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

    def __init__(self, user, *args, **kwargs):
        super(OrderReportForm, self).__init__(*args, **kwargs)
        if user:
            queryset = Shop.objects.filter(shop_type__shop_type__in=['sp'])
            queryset = queryset.filter(Q(related_users=user) | Q(shop_owner=user))
            self.fields['shop'].queryset = queryset


class GRNReportForm(forms.Form):
    shop = forms.ModelChoiceField(
            queryset=Shop.objects.filter(shop_type__shop_type__in=['gf']),
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

    def __init__(self, user, *args, **kwargs):
        super(GRNReportForm, self).__init__(*args, **kwargs)
        if user:
            queryset = Shop.objects.filter(shop_type__shop_type__in=['gf'])
            queryset = queryset.filter(Q(related_users=user) | Q(shop_owner=user))
            self.fields['shop'].queryset = queryset

class MasterReportForm(forms.Form):
    shop = forms.ModelChoiceField(
            queryset=Shop.objects.filter(shop_type__shop_type__in=['sp']),
        )

    def __init__(self, user, *args, **kwargs):
        super(MasterReportForm, self).__init__(*args, **kwargs)
        if user:
            queryset = Shop.objects.filter(shop_type__shop_type__in=['sp'])
            queryset = queryset.filter(Q(related_users=user) | Q(shop_owner=user))
        self.fields['shop'].queryset = queryset

class OrderGrnForm(forms.Form):
    shop = forms.ModelChoiceField(
            queryset=Shop.objects.filter(shop_type__shop_type__in=['sp']),
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

    def __init__(self, user, *args, **kwargs):
        super(OrderGrnForm, self).__init__(*args, **kwargs)
        if user:
            queryset = Shop.objects.filter(shop_type__shop_type__in=['sp'])
            queryset = queryset.filter(Q(related_users=user) | Q(shop_owner=user))
            self.fields['shop'].queryset = queryset

class CategoryProductReportForm(forms.Form):
    created_at = forms.DateTimeField(
        widget=DateTimePicker(
            options={
            'format': 'YYYY-MM-DD H:mm:ss',
            }
        ),
    )

