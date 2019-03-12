import datetime

from dal import autocomplete
from django_select2.forms import Select2MultipleWidget, ModelSelect2Widget

from django.contrib.auth import get_user_model
from django.contrib.admin import widgets
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from retailer_to_sp.models import (
    CustomerCare, ReturnProductMapping, OrderedProduct,
    OrderedProductMapping, Order, Dispatch, Trip, TRIP_STATUS, Shipment, ShipmentProductMapping
)
from products.models import Product
from shops.models import Shop
from accounts.models import UserWithName


class CustomerCareForm(forms.ModelForm):
    complaint_detail = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter your Message',
            'cols': 50, 'rows': 8})
    )

    class Meta:
        model = CustomerCare
        fields = '__all__'


class ReturnProductMappingForm(forms.ModelForm):
    returned_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='return-product-autocomplete',
            forward=('invoice_no',)
        )
     )

    class Meta:
        model = ReturnProductMapping
        fields = (
            'returned_product', 'total_returned_qty',
            'reusable_qty', 'damaged_qty',
            'manufacture_date', 'expiry_date'
        )


class OrderedProductForm(forms.ModelForm):
    order = forms.ModelChoiceField(queryset=Order.objects.filter(order_status__in=[Order.OPDP, 'ordered', 'PARTIALLY_SHIPPED']))

    class Meta:
        model = OrderedProduct
        fields = ['order', 'shipment_status']

    class Media:
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/select2/'
            '4.0.6-rc.0/js/select2.min.js',
            'admin/js/orderedproduct.js'
        )
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/select2/'
                '4.0.6-rc.0/css/select2.min.css',
            )
        }

    def __init__(self, *args, **kwargs):
        super(OrderedProductForm, self).__init__(*args, **kwargs)
        self.fields['order'].required = True
        SHIPMENT_STATUS = OrderedProduct.SHIPMENT_STATUS
        self.fields['shipment_status'].choices = SHIPMENT_STATUS[:2] + SHIPMENT_STATUS[-1:]
        self.fields['shipment_status'].initial = SHIPMENT_STATUS[:1]


class OrderedProductMappingForm(forms.ModelForm):
    ordered_qty = forms.CharField(required=False, label="Ordered Pieces")
    shipped_qty = forms.CharField(required=False, label="Shipped Pieces")
    gf_code = forms.CharField(required=False)

    class Meta:
        model = OrderedProductMapping
        fields = ['product', 'gf_code','ordered_qty', 'shipped_qty', 'delivered_qty', 'returned_qty', 'damaged_qty']

    def __init__(self, *args, **kwargs):
        super(OrderedProductMappingForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance:
            self.fields['ordered_qty'].initial = instance.ordered_qty
            self.fields['gf_code'].initial = instance.gf_code
        self.fields['product'].disabled = True
        self.fields['ordered_qty'].disabled = True
        self.fields['gf_code'].disabled = True
        self.fields['shipped_qty'].disabled = True
        self.fields['delivered_qty'].label = "Delivered Pieces"
        self.fields['damaged_qty'].label = "Damaged Pieces"
        self.fields['returned_qty'].label = "Returned Pieces"


class OrderedProductMappingDeliveryForm(forms.ModelForm):
    ordered_qty = forms.CharField(required=False)
    already_shipped_qty = forms.CharField(required=False)

    class Meta:
        model = OrderedProductMapping
        fields = [
            'product', 'ordered_qty', 'already_shipped_qty', 'delivered_qty',
            'returned_qty', 'damaged_qty'
        ]

    def clean(self):
        cleaned_data = self.cleaned_data
        delivered_qty = int(self.cleaned_data.get('delivered_qty', '0'))
        returned_qty = int(self.cleaned_data.get('returned_qty', '0'))
        damaged_qty = int(self.cleaned_data.get('damaged_qty', '0'))
        already_shipped_qty = int(self.cleaned_data.get('already_shipped_qty'))
        if sum([delivered_qty, returned_qty,
                damaged_qty]) != already_shipped_qty:
            raise forms.ValidationError(
                _('Sum of Delivered, Returned and Damaged Quantity should be '
                  'equals to Already Shipped Quantity for %(value)s'),
                params={'value': self.cleaned_data.get('product')},
            )
        else:
            return cleaned_data


class OrderedProductMappingShipmentForm(forms.ModelForm):
    ordered_qty = forms.CharField(required=False)
    already_shipped_qty = forms.CharField(required=False)


    class Meta:
        model = OrderedProductMapping
        fields = [
            'product', 'ordered_qty', 'already_shipped_qty',
            'shipped_qty'
        ]

    def clean_shipped_qty(self):
        ordered_qty = int(self.cleaned_data.get('ordered_qty'))
        shipped_qty = int(self.cleaned_data.get('shipped_qty'))
        already_shipped_qty = int(self.cleaned_data.get('already_shipped_qty'))
        if (ordered_qty - already_shipped_qty) < shipped_qty:
            raise forms.ValidationError(
                _('To be Ship Qty cannot be greater than difference '
                  'of Ordered Qty and Already Shipped Qty'),
                )
        else:
            return shipped_qty

    def __init__(self, *args, **kwargs):
        super(OrderedProductMappingShipmentForm, self).__init__(*args, **kwargs)
        self.fields['ordered_qty'].widget.attrs['class'] = 'hide_input_box'
        self.fields['already_shipped_qty'].widget.attrs['class'] = 'hide_input_box'
        self.fields['product'].widget.attrs = {'class': 'ui-select hide_input_box'}


class OrderedProductDispatchForm(forms.ModelForm):
    order_custom = forms.ModelChoiceField(
        # queryset=Order.objects.filter(order_status__in=[
        #     'ordered', 'PROCESSING', 'PARTIALLY_COMPLETED'
        # ])
        queryset=Order.objects.all()
    )

    invoice_no_custom = forms.ModelChoiceField(
        queryset=OrderedProduct.objects.all()
    )

    class Meta:
        model = OrderedProduct
        fields = ['order_custom', 'invoice_no_custom',
                  'shipment_status']

    class Media:
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/select2/'
            '4.0.6-rc.0/js/select2.min.js',
        )
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/select2/'
                '4.0.6-rc.0/css/select2.min.css',
            )
        }

    def __init__(self, *args, **kwargs):
        super(OrderedProductDispatchForm, self).__init__(*args, **kwargs)
        #self.fields['order'].required = True


class TripForm(forms.ModelForm):
    delivery_boy = forms.ModelChoiceField(queryset=UserWithName.objects.all())
    trip_status = forms.ChoiceField(choices=TRIP_STATUS)
    search_by_area = forms.CharField(required=False)
    trip_id = forms.CharField(required=False)

    class Meta:
        model = Trip
        fields = ['seller_shop', 'delivery_boy', 'vehicle_no', 'trip_status',
                  'e_way_bill_no', 'starts_at', 'completed_at', 'search_by_area']

    class Media:
        js = ('admin/js/select2.min.js', )
        css = {
            'all': (
                'admin/css/select2.min.css',
            )
        }

    def __init__(self, user, *args, **kwargs):
        super(TripForm, self).__init__(*args, **kwargs)
        self.fields['trip_id'].widget = forms.HiddenInput()

        instance = getattr(self, 'instance', None)
        if user.is_superuser:
            self.fields['seller_shop'].queryset = Shop.objects.filter(shop_type__shop_type__in=['sp', 'gf'])
        else:
            self.fields['seller_shop'].queryset = Shop.objects.filter(related_users=user)

        trip = instance.pk
        if trip:
            trip_status = instance.trip_status
            self.fields['trip_id'].initial = trip
            if trip_status == 'READY':
                self.fields['seller_shop'].disabled = True
                self.fields['trip_status'].choices = TRIP_STATUS[1:]

            elif trip_status == 'STARTED':
                self.fields['delivery_boy'].disabled = True
                self.fields['seller_shop'].disabled = True
                self.fields['vehicle_no'].disabled = True
                self.fields['trip_status'].choices = TRIP_STATUS[3:]
                self.fields['starts_at'].disabled = True
                self.fields['completed_at'].required = True
                self.fields['search_by_area'].widget = forms.HiddenInput()

            elif trip_status == 'COMPLETED':
                for field_name in self.fields:
                    self.fields[field_name].disabled = True
                self.fields['search_by_area'].widget = forms.HiddenInput()
            else:
                for field_name in self.fields:
                    self.fields[field_name].disabled = True
                self.fields['trip_status'].choices = TRIP_STATUS[1:2]
        else:
            self.fields['trip_status'].choices = TRIP_STATUS[:1]

    # def clean(self):
    #     data = self.cleaned_data
    #     if data.get('starts_at') and data.get('starts_at') < datetime.datetime.today():
    #         raise forms.ValidationError("The Start Date cannot be in the past!")
    #     elif data.get('completed_at') and (data.get('completed_at') < data.get('starts_at')):
    #         raise forms.ValidationError("Completed Date should be greater than the Start Date")
    #     return data


class DispatchForm(forms.ModelForm):
    selected = forms.BooleanField(required=False)
    invoice_city = forms.CharField(disabled=True)
    shipment_address = forms.CharField(widget=forms.Textarea, disabled=True)
    invoice_amount = forms.CharField(disabled=True)
    invoice_date = forms.CharField(disabled=True)
    items = forms.CharField(widget=forms.Textarea, label='Invoice No', disabled=True)

    class Meta:
        model = Dispatch
        fields = ['selected', 'items', 'invoice_amount', 'invoice_city', 'invoice_date', 'order', 'shipment_address']

    def __init__(self, *args, **kwargs):
        super(DispatchForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance:
            invoice_no = instance.invoice_no
            pk = instance.pk
            self.fields['items'].initial = mark_safe('<b><a href="/admin/retailer_to_sp/dispatch/' +
                                                     str(pk) + '/change/" target="_blank">' +
                                                     invoice_no + '</a></b>')
            if instance.trip:
                trip_status = instance.trip.trip_status
                self.fields['selected'].initial = True
                if trip_status == 'READY' or trip_status == 'STARTED':
                    self.fields['items'].initial = mark_safe('<b><a href="/admin/retailer_to_sp/dispatch/'+
                                                             str(pk)+'/change/" target="_blank">'+
                                                             invoice_no+'</a></b>')
                else:
                    self.fields['items'].initial = mark_safe('<b><a href="/admin/retailer_to_sp/orderedproduct/'+
                                                             str(pk)+'/change/" target="_blank">'+
                                                             invoice_no+'</a></b>')
            self.fields['invoice_date'].initial = instance.created_at.strftime('%d-%m-%Y %H:%M')
            self.fields['invoice_date'].widget.attrs['id'] = 'hide_input_box'

            self.fields['invoice_city'].initial = instance.invoice_city
            self.fields['invoice_city'].widget.attrs['id'] = 'hide_input_box'

            self.fields['invoice_amount'].initial = instance.invoice_amount
            self.fields['invoice_amount'].widget.attrs['id'] = 'hide_input_box'

            self.fields['shipment_address'].initial = instance.shipment_address
            self.fields['shipment_address'].widget.attrs = {'id':'hide_input_box', "rows": "3", "cols": "25"}

            self.fields['order'].widget.attrs = {'id':'hide_input_box', 'class':'ui-select'}
            self.fields['order'].disabled = True
            self.fields['selected'].widget.attrs = {'value': pk}


class DispatchDisabledForm(DispatchForm):

    def __init__(self, *args, **kwargs):
        super(DispatchDisabledForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].disabled = True


class ShipmentForm(forms.ModelForm):

    class Meta:
        model = Shipment
        fields = ['order', 'shipment_status']

    class Media:
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/select2/'
            '4.0.6-rc.0/js/select2.min.js',
        )
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/select2/'
                '4.0.6-rc.0/css/select2.min.css',
            )
        }

    def __init__(self, *args, **kwargs):
        super(ShipmentForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        ordered_product = instance
        SHIPMENT_STATUS = OrderedProduct.SHIPMENT_STATUS
        if ordered_product:
            shipment_status = ordered_product.shipment_status
            if shipment_status == 'SHIPMENT_CREATED':
                self.fields['shipment_status'].choices = SHIPMENT_STATUS[:2]
            elif shipment_status == 'READY_TO_SHIP':
                self.fields['shipment_status'].disabled = True
            elif shipment_status == 'CANCELLED':
                self.fields['shipment_status'].disabled = True
        else:
            self.fields['shipment_status'].choices = SHIPMENT_STATUS[:1]


class ShipmentProductMappingForm(forms.ModelForm):
    ordered_qty = forms.CharField(required=False)
    already_shipped_qty = forms.CharField(required=False)

    class Meta:
        model = ShipmentProductMapping
        fields = [
            'product', 'ordered_qty', 'already_shipped_qty',
            'shipped_qty'
        ]

    def __init__(self, *args, **kwargs):
        super(ShipmentProductMappingForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance.pk:
            shipment_status = instance.ordered_product.shipment_status
            if shipment_status == 'READY_TO_SHIP' or shipment_status == 'CANCELLED':
                for field_name in self.fields:
                    self.fields[field_name].disabled = True

