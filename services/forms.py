from django import forms
from shops.models import Shop
from products.models import Product
from dal import autocomplete
from tempus_dominus.widgets import DateTimePicker
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

    def __init__(self, user, *args, **kwargs):
        super(SalesReportForm, self).__init__(*args, **kwargs)
        if user:
            queryset = Shop.objects.filter(shop_type__shop_type__in=['sp'])
            queryset = queryset.filter(Q(related_users=user) | Q(shop_owner=user))
            self.fields['shop'].queryset = queryset

# class OrderReportForm(forms.Form):
#     shop = forms.ModelChoiceField(
#             queryset=Shop.objects.filter(shop_type__shop_type__in=['sp']),
#         )
#     start_date = forms.DateTimeField(
#     widget=DateTimePicker(
#         options={
#             'format': 'YYYY-MM-DD H:mm:ss',
#             }
#         ),
#     )
#     end_date = forms.DateTimeField(
#         widget=DateTimePicker(
#             options={
#             'format': 'YYYY-MM-DD H:mm:ss',
#             }
#         ),
#     )
#
#     def __init__(self, user, *args, **kwargs):
#         super(OrderReportForm, self).__init__(*args, **kwargs)
#         if user:
#             queryset = Shop.objects.filter(shop_type__shop_type__in=['sp'])
#             queryset = queryset.filter(Q(related_users=user) | Q(shop_owner=user))
#             self.fields['shop'].queryset = queryset
#
#
# class GRNReportForm(forms.Form):
#     shop = forms.ModelChoiceField(
#             queryset=Shop.objects.filter(shop_type__shop_type__in=['gf']),
#         )
#     start_date = forms.DateTimeField(
#     widget=DateTimePicker(
#         options={
#             'format': 'YYYY-MM-DD H:mm:ss',
#             }
#         ),
#     )
#     end_date = forms.DateTimeField(
#         widget=DateTimePicker(
#             options={
#             'format': 'YYYY-MM-DD H:mm:ss',
#             }
#         ),
#     )
#
#     def __init__(self, user, *args, **kwargs):
#         super(GRNReportForm, self).__init__(*args, **kwargs)
#         if user:
#             queryset = Shop.objects.filter(shop_type__shop_type__in=['gf'])
#             queryset = queryset.filter(Q(related_users=user) | Q(shop_owner=user))
#             self.fields['shop'].queryset = queryset
#             queryset = queryset.filter(Q(related_users=request.user) | Q(shop_owner=request.user))
#         # latest = queryset.latest('id')
#         self.fields['shop'].queryset = queryset
#
# class MasterReportForm(forms.Form):
#     shop = forms.ModelChoiceField(
#             queryset=Shop.objects.filter(shop_type__shop_type__in=['sp']),
#         )
#
#     def __init__(self, user, *args, **kwargs):
#         super(MasterReportForm, self).__init__(*args, **kwargs)
#         if user:
#             queryset = Shop.objects.filter(shop_type__shop_type__in=['sp'])
#             queryset = queryset.filter(Q(related_users=user) | Q(shop_owner=user))
#         self.fields['shop'].queryset = queryset
#
# class OrderGrnForm(forms.Form):
#     shop = forms.ModelChoiceField(
#             queryset=Shop.objects.filter(shop_type__shop_type__in=['sp']),
#         )
#     start_date = forms.DateTimeField(
#     widget=DateTimePicker(
#         options={
#             'format': 'YYYY-MM-DD H:mm:ss',
#             }
#         ),
#     )
#     end_date = forms.DateTimeField(
#         widget=DateTimePicker(
#             options={
#             'format': 'YYYY-MM-DD H:mm:ss',
#             }
#         ),
#     )
#
#     def __init__(self, user, *args, **kwargs):
#         super(OrderGrnForm, self).__init__(*args, **kwargs)
#         if user:
#             queryset = Shop.objects.filter(shop_type__shop_type__in=['sp'])
#             queryset = queryset.filter(Q(related_users=user) | Q(shop_owner=user))
#             self.fields['shop'].queryset = queryset
#
# class CategoryProductReportForm(forms.Form):
#     created_at = forms.DateTimeField(
#         widget=DateTimePicker(
#             options={
#             'format': 'YYYY-MM-DD H:mm:ss',
#             }
#         ),
#     )


class InOutLedgerForm(forms.Form):
    sku = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='product-sku-autocomplete', ),
    )
    warehouse = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='sp'),
        widget=autocomplete.ModelSelect2(url='warehouse-autocomplete', ),
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

