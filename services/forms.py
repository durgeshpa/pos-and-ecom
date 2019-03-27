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
