import datetime
import csv
import codecs
import re
from dal import autocomplete
from django_select2.forms import Select2MultipleWidget, ModelSelect2Widget
from tempus_dominus.widgets import DatePicker
from django.db.models import F, FloatField, Sum
from django.contrib.auth import get_user_model
from django.contrib.admin import widgets
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.conf import settings
from django.forms import widgets
from django.utils.html import format_html
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from .signals import ReservedOrder
from sp_to_gram.models import (
    OrderedProductReserved,
    OrderedProductMapping as SpMappedOrderedProductMapping)
from retailer_backend.common_function import required_fields
from retailer_to_sp.models import (
    CustomerCare, ReturnProductMapping, OrderedProduct,
    OrderedProductMapping, Order, Dispatch, Trip,
    Shipment, ShipmentProductMapping, CartProductMapping, Cart,
    ShipmentRescheduling, PickerDashboard, generate_picklist_id, ResponseComment, BulkOrder, OrderedProductBatch,
    ShipmentNotAttempt
)
from products.models import Product
from shops.models import Shop
from accounts.models import UserWithName
from accounts.middlewares import get_current_user
from addresses.models import Address
from payments.models import ShipmentPayment

User = get_user_model()


class PlainTextWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe(value) if value else '---'


class RelatedFieldWidgetCanAdd(widgets.Select):

    def __init__(self, related_model, related_url=None, *args, **kw):
        super(RelatedFieldWidgetCanAdd, self).__init__(*args, **kw)
        if not related_url:
            rel_to = related_model
            info = (rel_to._meta.app_label, rel_to._meta.object_name.lower())
            related_url = 'admin:%s_%s_add' % info

        # Be careful that here "reverse" is not allowed
        self.related_url = related_url

    def render(self, name, value, *args, **kwargs):
        self.related_url = reverse(self.related_url)
        output = [super(RelatedFieldWidgetCanAdd, self).render(name, value, *args, **kwargs)]
        output.append('<a href="%s" class="related-widget-wrapper-link add-related" id="add_id_%s" \
            onclick="return showAddAnotherPopup(this);"> ' %
                      (self.related_url, name))
        output.append('<img src="/static/admin/img/icon-addlink.svg" width="10" height="10" \
            alt="Add"/>Add Delivery Boy</a>')
        return mark_safe(''.join(output))


class RelatedFieldWidgetCanAddPicker(widgets.Select):

    def __init__(self, related_model, related_url=None, *args, **kw):
        super(RelatedFieldWidgetCanAddPicker, self).__init__(*args, **kw)
        if not related_url:
            rel_to = related_model
            info = (rel_to._meta.app_label, rel_to._meta.object_name.lower())
            related_url = 'admin:%s_%s_add' % info

        # Be careful that here "reverse" is not allowed
        self.related_url = related_url

    def render(self, name, value, *args, **kwargs):
        self.related_url = reverse(self.related_url)
        output = [super(RelatedFieldWidgetCanAddPicker, self).render(name, value, *args, **kwargs)]
        output.append('<a href="%s" class="related-widget-wrapper-link add-related" id="add_id_%s" \
            onclick="return showAddAnotherPopup(this);"> ' %
                      (self.related_url, name))
        output.append('<img src="/static/admin/img/icon-addlink.svg" width="10" height="10" \
            alt="Add"/>Add Picker Boy</a>')
        return mark_safe(''.join(output))


class CustomerCareForm(forms.ModelForm):
    complaint_detail = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter your Message',
            'cols': 50, 'rows': 8})
    )

    class Meta:
        model = CustomerCare
        fields = '__all__'


class ResponseCommentForm(forms.ModelForm):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter your Message',
            'cols': 50, 'rows': 8})
    )

    class Meta:
        model = ResponseComment
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
    order = forms.ModelChoiceField(queryset=Order.objects.all(),
                                   widget=autocomplete.ModelSelect2(url='admin:ShipmentOrdersAutocomplete', ),
                                   required=True)

    class Meta:
        model = OrderedProduct
        fields = ['order', ]

    def __init__(self, *args, **kwargs):
        super(OrderedProductForm, self).__init__(*args, **kwargs)
        # self.fields['shipment_status'].choices = OrderedProduct.SHIPMENT_STATUS[:2]

    def clean(self):
        data = self.cleaned_data
        if not self.cleaned_data['order'].picker_order.all().exists():
            raise forms.ValidationError(_("Please assign picklist to the order"), )
        if self.cleaned_data['order'].picker_order.exclude(picking_status='picking_cancelled').count() != \
                self.cleaned_data['order'].picker_order.filter(picking_status='moved_to_qc').count():
            raise forms.ValidationError(_("Not all the pickings are yet moved to QC Area"), )
        return data


class OrderedProductMappingForm(forms.ModelForm):
    ordered_qty = forms.CharField(required=False, label="Ordered Pieces")
    shipped_qty = forms.CharField(required=False, label="Shipped Pieces")
    gf_code = forms.CharField(required=False)

    class Meta:
        model = OrderedProductMapping
        fields = ['product', 'gf_code', 'ordered_qty', 'shipped_qty', 'delivered_qty', 'returned_qty', 'damaged_qty',
                  'returned_damage_qty']

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
        self.fields['returned_damage_qty'] = "Returned Damaged"


class OrderedProductMappingDeliveryForm(forms.ModelForm):
    ordered_qty = forms.CharField(required=False)
    already_shipped_qty = forms.CharField(required=False)

    class Meta:
        model = OrderedProductMapping
        fields = [
            'product', 'ordered_qty', 'already_shipped_qty', 'delivered_qty',
            'returned_qty', 'damaged_qty', 'returned_damage_qty'
        ]

    def clean(self):
        cleaned_data = self.cleaned_data
        delivered_qty = int(self.cleaned_data.get('delivered_qty', '0'))
        returned_qty = int(self.cleaned_data.get('returned_qty', '0'))
        damaged_qty = int(self.cleaned_data.get('damaged_qty', '0'))
        returned_damage_qty = int(self.cleaned_data.get('returned_damage_qty'), '0')
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
    ordered_qty = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    already_shipped_qty = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    to_be_shipped_qty = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    shipped_qty = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    picked_pieces = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(), widget=forms.TextInput)
    product_name = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))

    class Meta:
        model = OrderedProductMapping
        fields = [
            'product', 'ordered_qty', 'already_shipped_qty',
            'to_be_shipped_qty', 'shipped_qty', 'picked_pieces',
        ]

    def clean_shipped_qty(self):

        ordered_qty = int(float(self.cleaned_data.get('ordered_qty')))
        shipped_qty = int(float(self.cleaned_data.get('shipped_qty')))
        # picked_pieces = int(self.cleaned_data.get('picked_pieces'))
        to_be_shipped_qty = int(float(self.cleaned_data.get('to_be_shipped_qty')))
        # already_shipped_qty = int(self.cleaned_data.get('already_shipped_qty'))
        max_qty_allowed = ordered_qty - to_be_shipped_qty
        if max_qty_allowed < shipped_qty:
            raise forms.ValidationError(
                _('Max. Qty allowed: %s') % (max_qty_allowed),
            )
        else:
            return shipped_qty

    def __init__(self, *args, **kwargs):
        super(OrderedProductMappingShipmentForm, self).__init__(*args, **kwargs)
        # self.fields['ordered_qty'].widget.attrs['class'] = 'hide_input_box'
        # self.fields['already_shipped_qty'].widget.attrs['class'] = 'hide_input_box'
        # self.fields['to_be_shipped_qty'].widget.attrs['class'] = 'hide_input_box'
        self.fields['product'].widget = forms.HiddenInput()


class OrderedProductBatchForm(forms.ModelForm):
    ordered_qty = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    already_shipped_qty = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    to_be_shipped_qty = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    shipped_qty = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(), widget=forms.TextInput)
    product_name = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))

    class Meta:
        model = OrderedProductMapping
        fields = [
            'product', 'ordered_qty', 'already_shipped_qty',
            'to_be_shipped_qty', 'shipped_qty', 'picked_pieces'
        ]

    def clean_shipped_qty(self):

        ordered_qty = int(self.cleaned_data.get('ordered_qty'))
        shipped_qty = int(self.cleaned_data.get('shipped_qty'))
        to_be_shipped_qty = int(self.cleaned_data.get('to_be_shipped_qty'))
        # already_shipped_qty = int(self.cleaned_data.get('already_shipped_qty'))
        max_qty_allowed = ordered_qty - to_be_shipped_qty
        if max_qty_allowed < shipped_qty:
            raise forms.ValidationError(
                _('Max. Qty allowed: %s') % (max_qty_allowed),
            )
        else:
            return shipped_qty

    def __init__(self, *args, **kwargs):
        super(OrderedProductMappingShipmentForm, self).__init__(*args, **kwargs)
        # self.fields['ordered_qty'].widget.attrs['class'] = 'hide_input_box'
        # self.fields['already_shipped_qty'].widget.attrs['class'] = 'hide_input_box'
        # self.fields['to_be_shipped_qty'].widget.attrs['class'] = 'hide_input_box'
        self.fields['product'].widget = forms.HiddenInput()


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
        # self.fields['order'].required = True


class EditAssignPickerForm(forms.ModelForm):
    # form to edit assgined picker
    picker_boy = forms.ModelChoiceField(
        queryset=UserWithName.objects.all(),
        widget=RelatedFieldWidgetCanAddPicker(
            UserWithName,
            related_url="admin:accounts_user_add"))

    class Meta:
        model = PickerDashboard
        fields = ['order', 'repackaging', 'shipment', 'picking_status', 'picklist_id', 'picker_boy']

    class Media:
        js = ('admin/js/select2.min.js',)
        css = {
            'all': (
                'admin/css/select2.min.css',
            )
        }

    def get_my_choices(self):
        # you place some logic here
        picking_status = self.instance.picking_status
        if picking_status == "picking_pending":
            choices_list = "picking_assigned"
        elif picking_status == "picking_assigned":
            choices_list = "picking_in_progress"
        elif picking_status == "picking_in_progress":
            choices_list = "picking_complete"
        else:
            choices_list = ""
        return choices_list

    # def __init__(self, *args, **kwargs):
    #     super(EditAssignPickerForm, self).__init__(*args, **kwargs)
    #     instance = getattr(self, 'instance', None)
    #     if instance.order:
    #         shop = instance.order.seller_shop  # Shop.objects.get(related_users=user)
    #     else:
    #         shop = instance.repackaging.seller_shop
    #     # shop = Shop.objects.get(shop_name="TEST SP 1")
    #
    #     # find all picker for the shop
    #     self.fields['picker_boy'].queryset = shop.related_users.filter(groups__name__in=["Picker Boy"])
    #     if instance.picking_status == "picking_pending":
    #         self.fields['picker_boy'].required = False
    #     else:
    #         self.fields['picker_boy'].required = True
    #     # self.fields['picking_status'] = forms.ChoiceField(
    #     #     choices=self.get_my_choices() )
    #     # self.fields['picking_status'].choices = self.get_my_choices()

    def __init__(self, *args, **kwargs):
        super(EditAssignPickerForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        self.fields['picker_boy'].queryset = User.objects.exclude(picker_zone_users__isnull=True). \
            filter(picker_zone_users=instance.zone)

        if instance.picking_status == "picking_pending":
            self.fields['picker_boy'].required = False
        else:
            self.fields['picker_boy'].required = True

    def clean(self):
        data = self.cleaned_data
        if self.instance and self.instance.order:
            if self.instance.order.order_status == Order.CANCELLED:
                raise forms.ValidationError("You can't assign picker boy to a Cancelled Order")
        return data


# tbd: test for warehouse manager, superuser, other users
class AssignPickerForm(forms.ModelForm):
    # selecting shop related to user
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.all(),
    )
    picker_boy = forms.ModelChoiceField(
        queryset=UserWithName.objects.all(),
        widget=RelatedFieldWidgetCanAddPicker(
            UserWithName,
            related_url="admin:accounts_user_add"))

    # for receiving selected orders
    selected_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    unselected_id = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = PickerDashboard
        fields = ['shop', 'picker_boy', 'selected_id', 'unselected_id', ]

    class Media:
        js = ('admin/js/select2.min.js',)
        css = {
            'all': (
                'admin/css/select2.min.css',
            )
        }

    def __init__(self, user, shop_id, *args, **kwargs):
        super(AssignPickerForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        # assign shop name as readonly with value for shop name for user
        self.fields['picker_boy'].queryset = User.objects.none()
        if user.is_superuser:
            # load all parent shops
            self.fields['shop'].queryset = Shop.objects.filter(shop_type__shop_type__in=["sp"])
        else:
            # set shop field as read only
            self.fields['shop'].queryset = Shop.objects.filter(related_users=user)

        if shop_id:
            shop = Shop.objects.get(id=shop_id)
            self.fields['picker_boy'].queryset = shop.related_users.filter(groups__name__in=["Picker Boy"])


class TripForm(forms.ModelForm):
    delivery_boy = forms.ModelChoiceField(
        queryset=UserWithName.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:user_with_name_autocomplete', )
    )
    trip_status = forms.ChoiceField(choices=Trip.TRIP_STATUS)
    search_by_area = forms.CharField(required=False)
    search_by_pincode = forms.CharField(required=False)
    Invoice_No = forms.CharField(required=False)
    trip_id = forms.CharField(required=False)
    trip_weight = forms.CharField(required=False, disabled=True)
    total_trip_amount_value = forms.CharField(required=False, disabled=True)
    selected_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    unselected_id = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Trip
        fields = ['seller_shop', 'delivery_boy', 'vehicle_no', 'trip_status',
                  'e_way_bill_no', 'search_by_area', 'search_by_pincode',
                  'Invoice_No', 'selected_id', 'unselected_id', 'trip_weight',
                  'opening_kms', 'closing_kms', 'no_of_crates', 'no_of_packets',
                  'no_of_sacks', 'no_of_crates_check', 'no_of_packets_check',
                  'no_of_sacks_check']

    class Media:
        js = ('admin/js/select2.min.js',)
        css = {
            'all': (
                'admin/css/select2.min.css',
            )
        }

    def __init__(self, user, *args, **kwargs):
        super(TripForm, self).__init__(*args, **kwargs)
        self.fields['closing_kms'].disabled = True
        self.fields['no_of_crates_check'].disabled = True
        self.fields['no_of_packets_check'].disabled = True
        self.fields['no_of_sacks_check'].disabled = True
        self.fields['trip_id'].widget = forms.HiddenInput()

        instance = getattr(self, 'instance', None)
        if user.is_superuser:
            self.fields['seller_shop'].queryset = Shop.objects.filter(shop_type__shop_type__in=['sp', 'gf'])
        else:
            self.fields['seller_shop'].queryset = Shop.objects.filter(related_users=user)
        self.fields['trip_weight'].initial = instance.trip_weight()
        self.fields['trip_weight'].disabled = True
        self.fields['total_trip_amount_value'].initial = instance.total_trip_amount_value
        self.fields['total_trip_amount_value'].disabled = True
        self.fields['total_trip_amount_value'].initial = instance.trip_amount

        trip = instance.pk
        if trip:
            trip_status = instance.trip_status
            self.fields['trip_id'].initial = trip

            if trip and not trip_status == Trip.READY:
                self.fields['opening_kms'].disabled = True
                self.fields['no_of_crates'].disabled = True
                self.fields['no_of_packets'].disabled = True
                self.fields['no_of_sacks'].disabled = True

            if trip_status == Trip.READY:
                self.fields['seller_shop'].disabled = True
                self.fields['trip_status'].choices = Trip.TRIP_STATUS[0], Trip.TRIP_STATUS[2], Trip.TRIP_STATUS[1]
                self.fields['no_of_crates'].disabled = True
                self.fields['no_of_packets'].disabled = True
                self.fields['no_of_sacks'].disabled = True

            elif trip_status == Trip.STARTED:
                self.fields['delivery_boy'].disabled = True
                self.fields['seller_shop'].disabled = True
                self.fields['vehicle_no'].disabled = True
                self.fields['trip_status'].choices = Trip.TRIP_STATUS[2:4]
                self.fields['search_by_area'].widget = forms.HiddenInput()
                self.fields['search_by_pincode'].widget = forms.HiddenInput()
                self.fields['Invoice_No'].widget = forms.HiddenInput()

            elif trip_status == Trip.COMPLETED:
                self.fields['delivery_boy'].disabled = True
                self.fields['seller_shop'].disabled = True
                self.fields['vehicle_no'].disabled = True
                self.fields['trip_status'].choices = Trip.TRIP_STATUS[3:5]
                self.fields['search_by_area'].widget = forms.HiddenInput()
                self.fields['search_by_pincode'].widget = forms.HiddenInput()
                self.fields['Invoice_No'].widget = forms.HiddenInput()
                self.fields['closing_kms'].disabled = False
                self.fields['no_of_crates_check'].disabled = False
                self.fields['no_of_packets_check'].disabled = False
                self.fields['no_of_sacks_check'].disabled = False

            elif trip_status == Trip.RETURN_VERIFIED:
                self.fields['e_way_bill_no'].disabled = True
                self.fields['delivery_boy'].disabled = True
                self.fields['seller_shop'].disabled = True
                self.fields['vehicle_no'].disabled = True
                self.fields['trip_status'].disabled = True
                self.fields['search_by_area'].widget = forms.HiddenInput()
                self.fields['search_by_pincode'].widget = forms.HiddenInput()
                self.fields['Invoice_No'].widget = forms.HiddenInput()

            else:
                for field_name in self.fields:
                    self.fields[field_name].disabled = True
                if trip_status == 'CLOSED':
                    self.fields['trip_status'].choices = Trip.TRIP_STATUS[4:5]  # "CLOSED"
                elif trip_status == Trip.PAYMENT_VERIFIED:
                    self.fields['trip_status'].choices = Trip.TRIP_STATUS[5:]  # "CLOSED"
                else:
                    self.fields['trip_status'].choices = Trip.TRIP_STATUS[1:2]
                # self.fields['trip_status'].choices = TRIP_STATUS[1:2]

        else:
            self.fields['trip_status'].initial = Trip.READY
            fields = ['trip_status', 'e_way_bill_no']
            for field in fields:
                self.fields[field].required = False
                self.fields[field].widget = forms.HiddenInput()

    def clean(self):
        data = self.cleaned_data
        shipment_status_verify = ['FULLY_RETURNED_AND_VERIFIED', 'PARTIALLY_DELIVERED_AND_VERIFIED',
                                  'FULLY_DELIVERED_AND_VERIFIED','FULLY_DELIVERED_AND_COMPLETED']

        shipment_ids = data.get('selected_id').split(',')
        if self.instance and self.instance.trip_status == Trip.COMPLETED and data[
            'trip_status'] == Trip.RETURN_VERIFIED:
            shipment_list = Shipment.objects.filter(id__in=shipment_ids)
            for shipment in shipment_list:
                if shipment.shipment_status not in shipment_status_verify:
                    raise forms.ValidationError("Please Verify all shipments before closing the Trip")

        if self.instance and self.instance.trip_status == Trip.READY:

            cancelled_shipments = Shipment.objects.values('id', 'invoice__invoice_no'
                                                          ).filter(id__in=shipment_ids, shipment_status='CANCELLED')

            if cancelled_shipments.exists():
                shipment_ids_upd = [i for i in shipment_ids if int(i) not in [j['id'] for j in cancelled_shipments]]
                data['selected_id'] = ", ".join(shipment_ids_upd)
                raise forms.ValidationError(
                    ['Following invoices are removed from the trip because'
                     ' the retailer has cancelled the Order'] +
                    [format_html(i) for i in
                     ["<a href=%s target='blank'>%s</a>" %
                      (reverse("admin:retailer_to_sp_shipment_change",
                               args=[i.get('id')]), i.get('invoice__invoice_no'))
                      for i in cancelled_shipments]])
        return data


class DispatchForm(forms.ModelForm):
    selected = forms.BooleanField(required=False)
    shipment_address = forms.CharField(widget=forms.Textarea, disabled=True)
    invoice_date = forms.CharField(disabled=True, widget=PlainTextWidget)
    items = forms.CharField(widget=forms.Textarea, label='Invoice No', disabled=True)

    class Meta:
        model = Dispatch
        fields = ['selected', 'items', 'shipment_status', 'invoice_date', 'order', 'shipment_address']

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
                if trip_status == Trip.READY or trip_status == Trip.STARTED:
                    self.fields['items'].initial = mark_safe('<b><a href="/admin/retailer_to_sp/dispatch/' +
                                                             str(pk) + '/change/" target="_blank">' +
                                                             invoice_no + '</a></b>')
                else:
                    self.fields['items'].initial = mark_safe('<b><a href="/admin/retailer_to_sp/orderedproduct/' +
                                                             str(pk) + '/change/" target="_blank">' +
                                                             invoice_no + '</a></b>')
            self.fields['invoice_date'].initial = instance.created_at.strftime('%d-%m-%Y %H:%M')

            self.fields['shipment_address'].initial = instance.shipment_address
            self.fields['shipment_address'].widget.attrs = {'id': 'hide_input_box', "rows": "3", "cols": "25"}

            self.fields['order'].widget.attrs = {'id': 'hide_input_box', 'class': 'ui-select'}
            self.fields['order'].disabled = True
            self.fields['shipment_status'].widget.attrs = {'id': 'hide_input_box', 'class': 'ui-select'}
            self.fields['shipment_status'].disabled = True
            self.fields['selected'].widget.attrs = {'value': pk}


class DispatchDisabledForm(DispatchForm):

    def __init__(self, *args, **kwargs):
        super(DispatchDisabledForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].disabled = True


class ShipmentForm(forms.ModelForm):
    close_order = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = Shipment
        fields = ['order', 'shipment_status']

    class Media:
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/select2/'
            '4.0.6-rc.0/js/select2.min.js', 'admin/js/sweetalert.min.js',
            # 'admin/js/order_close_message.js'
        )
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/select2/'
                '4.0.6-rc.0/css/select2.min.css',
                'admin/css/hide_admin_inline_object_name.css'
            )
        }

    def __init__(self, *args, **kwargs):
        super(ShipmentForm, self).__init__(*args, **kwargs)
        # order with status picking pending
        setattr(self.fields['close_order'], 'initial', True)
        setattr(self.fields['close_order'], 'disabled', True)

        ordered_product = getattr(self, 'instance', None)
        SHIPMENT_STATUS = OrderedProduct.SHIPMENT_STATUS
        if ordered_product:
            shipment_status = ordered_product.shipment_status
            if shipment_status == 'SHIPMENT_CREATED':
                self.fields['shipment_status'].choices = SHIPMENT_STATUS[:2]
            else:
                self.fields['shipment_status'].disabled = True
        else:
            self.fields['shipment_status'].choices = SHIPMENT_STATUS[:1]

    def clean(self):
        data = self.cleaned_data

        # if order is cancelled don't let the user to save data
        if self.instance and (self.instance.order.order_status == Order.CANCELLED):
            raise forms.ValidationError(_('Order for this shipment has been cancelled!'), )

        if self.instance and self.instance.order.order_closed:
            return data
        if (data['close_order'] and
                data['shipment_status'] != OrderedProduct.READY_TO_SHIP):
            raise forms.ValidationError(
                _('You can only close the order in QC Passed state'), )
        return data


class ShipmentProductMappingForm(forms.ModelForm):
    ordered_qty = forms.CharField(required=False)
    already_shipped_qty = forms.CharField(required=False)
    # shipped_qty = forms.IntegerField(disabled=True)
    # picked_pieces = forms.IntegerField(disabled=True)
    # damaged_qty = forms.IntegerField(disabled=True)

    class Meta:
        model = ShipmentProductMapping
        fields = [
            'product', 'ordered_qty', 'already_shipped_qty',
            'shipped_qty', 'picked_pieces',
        ]

    def __init__(self, *args, **kwargs):
        super(ShipmentProductMappingForm, self).__init__(*args, **kwargs)
        # self.fields['shipped_qty'].disabled = True
        # self.fields['damaged_qty'].disabled = True
        # self.fields['expired_qty'].disabled = True
        self.fields['picked_pieces'].disabled = True
        if not get_current_user().is_superuser:
            instance = getattr(self, 'instance', None)
            if instance.pk:
                shipment_status = instance.ordered_product.shipment_status
                if shipment_status == 'READY_TO_SHIP' or shipment_status == 'CANCELLED':
                    for field_name in self.fields:
                        self.fields[field_name].disabled = True
        instance = getattr(self, 'instance', None)
        if instance.pk:
            shipment_status = instance.ordered_product.shipment_status
            if shipment_status != 'SHIPMENT_CREATED':
                for field_name in self.fields:
                    self.fields[field_name].disabled = True

    def clean(self):
        data = self.cleaned_data
        data['shipped_qty'] = self.instance.picked_pieces - (data.get('damaged_qty') + data.get('expired_qty') +
                                                             data.get('missing_qty') + data.get('rejected_qty'))
        if float(self.instance.picked_pieces) != float(data['shipped_qty'] + data.get('damaged_qty') +
                                                       data.get('expired_qty') + data.get('missing_qty') +
                                                       data.get('rejected_qty')):
            raise forms.ValidationError(
                'Sorry Quantity mismatch!! Picked pieces must be equal to sum of (damaged_qty, expired_qty, no.of pieces to ship)')
        return data


class CartProductMappingForm(forms.ModelForm):
    product_case_size = forms.CharField(
        required=False, widget=forms.HiddenInput())
    product_inner_case_size = forms.CharField(
        required=False, widget=forms.HiddenInput())
    item_effective_prices = forms.CharField(
        required=False, widget=forms.HiddenInput())

    class Meta:
        model = CartProductMapping
        fields = (
            'cart', 'cart_product', 'cart_product_price', 'qty',
            'no_of_pieces', 'product_case_size', 'product_inner_case_size', 'item_effective_prices')

    def __init__(self, *args, **kwargs):
        super(CartProductMappingForm, self).__init__(*args, **kwargs)
        self.empty_permitted = False

    def clean_cart_product_price(self):
        product_price = self.cleaned_data.get('cart_product_price')
        if not product_price:
            raise forms.ValidationError('This field is required')
        return product_price

    def clean_no_of_pieces(self):
        cart = self.cleaned_data.get('cart')
        product = self.cleaned_data.get('cart_product')
        ordered_qty = self.cleaned_data.get('no_of_pieces')
        reserve_order = ReservedOrder(
            cart.seller_shop,
            cart.buyer_shop,
            cart, CartProductMapping, SpMappedOrderedProductMapping,
            OrderedProductReserved, get_current_user())
        if not reserve_order.sp_product_availability(product, ordered_qty):
            raise forms.ValidationError(
                ('Available Qty is %(value)s'),
                params={
                    'value': reserve_order.sp_product_available_qty(product)
                })
        return ordered_qty


class CartForm(forms.ModelForm):
    seller_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='sp'),
        widget=autocomplete.ModelSelect2(url='banner-shop-autocomplete', ),
        required=False
    )
    buyer_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(url='admin:retailer-shop-autocomplete', ),
        required=False
    )

    class Meta:
        model = Cart
        fields = ('seller_shop', 'buyer_shop')
        widgets = {
            'seller_shop': autocomplete.ModelSelect2(url='seller-shop-autocomplete'),
            'buyer_shop': autocomplete.ModelSelect2(url='buyer-shop-autocomplete')
        }


class BulkCartForm(forms.ModelForm):
    seller_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='sp'),
        widget=autocomplete.ModelSelect2(url='banner-shop-autocomplete', ),
        required=True
    )
    buyer_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(url='admin:buyer-parent-autocomplete', forward=('seller_shop')),
        required=True
    )
    shipping_address = forms.ModelChoiceField(
        queryset=Address.objects.filter(shop_name__shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(
            url='bulk-shipping-address-autocomplete',
            forward=('buyer_shop',)
        ),
        required=True
    )
    billing_address = forms.ModelChoiceField(
        queryset=Address.objects.filter(shop_name__shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(
            url='bulk-billing-address-autocomplete',
            forward=('buyer_shop',)
        ),
        required=True
    )

    class Meta:
        model = BulkOrder
        fields = ('seller_shop', 'buyer_shop', 'shipping_address', 'billing_address', 'cart_products_csv', 'order_type')

    def __init__(self, *args, **kwargs):
        super(BulkCartForm, self).__init__(*args, **kwargs)
        if self.fields:
            self.fields['cart_products_csv'].help_text = self.instance. \
                cart_products_sample_file

    def clean(self):
        if 'cart_products_csv' in self.cleaned_data:
            if self.cleaned_data['cart_products_csv']:
                if not self.cleaned_data['cart_products_csv'].name[-4:] in ('.csv'):
                    raise forms.ValidationError("Sorry! Only csv file accepted")

        return self.cleaned_data


class CommercialForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['dispatch_no', 'delivery_boy', 'seller_shop', 'trip_status',
                  'starts_at', 'completed_at', 'e_way_bill_no', 'vehicle_no']

    class Media:
        js = ('admin/js/CommercialLoadShipments.js',)

    def __init__(self, *args, **kwargs):
        super(CommercialForm, self).__init__(*args, **kwargs)
        self.fields['trip_status'].choices = Trip.TRIP_STATUS[3:]
        instance = getattr(self, 'instance', None)
        if instance.pk:
            # seperate screen for transferred: access only to finance team
            if (instance.trip_status == Trip.RETURN_VERIFIED):
                self.fields['trip_status'].choices = Trip.TRIP_STATUS[4:6]

            if (instance.trip_status == Trip.PAYMENT_VERIFIED):
                self.fields['trip_status'].choices = Trip.TRIP_STATUS[5:6]
                for field_name in self.fields:
                    self.fields[field_name].disabled = True

    def clean(self):
        data = self.cleaned_data
        # setup check for payment verified
        if data['trip_status'] == Trip.PAYMENT_VERIFIED:
            if float(self.instance.cash_to_be_collected()) != float(self.instance.total_received_amount):
                raise forms.ValidationError(_("Amount to be Collected should be equal to Total Received Amount"), )

            # setup check for transferred
            # check if number of pending payment approval is 0
            trip_shipments = self.instance.rt_invoice_trip.values_list('id', flat=True)
            # pending_payments_count = trip_shipments.filter(parent_order_payment__parent_payment__payment_approval_status="approval_pending").count()
            pending_payments_count = ShipmentPayment.objects.filter(
                shipment__in=trip_shipments,
                parent_order_payment__parent_payment__payment_approval_status="pending_approval"
            ).count()
            if pending_payments_count:
                raise forms.ValidationError(_("All shipment payments are not verified"), )
        return data


class OrderedProductReschedule(forms.ModelForm):
    class Meta:
        model = OrderedProduct
        fields = (
            'order', 'shipment_status', 'trip',
            'return_reason'
        )

    class Media:
        js = ('admin/js/OrderedProductShipment.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        self.fields['shipment_status'].disabled = True
        if not (instance.shipment_status == 'PARTIALLY_DELIVERED_AND_COMPLETED' or \
                instance.shipment_status == 'FULLY_RETURNED_AND_COMPLETED'
                or instance.shipment_status == 'FULLY_DELIVERED_AND_COMPLETED'):
            self.fields['return_reason'].disabled = True

    def clean_return_reason(self):
        return_reason = self.cleaned_data.get('return_reason')
        if self.instance.shipment_status == 'PARTIALLY_DELIVERED_AND_COMPLETED' or \
                self.instance.shipment_status == 'FULLY_RETURNED_AND_COMPLETED' or \
                self.instance.shipment_status == 'FULLY_DELIVERED_AND_COMPLETED':
            return_qty = 0
            returned_damage_qty = 0
            total_products = self.data.get(
                'rt_order_product_order_product_mapping-TOTAL_FORMS')
            for product in range(int(total_products)):
                return_field = ("rt_order_product_order_product_mapping-%s-returned_qty") \
                               % product
                returned_damage_field = ("rt_order_product_order_product_mapping-%s-returned_damage_qty") \
                                        % product
                if self.data.get(return_field) is not None:
                    return_qty += int(self.data.get(return_field))
                if self.data.get(returned_damage_field) is not None:
                    returned_damage_qty += int(self.data.get(returned_damage_field))
            if (return_qty or returned_damage_qty) and not return_reason:
                raise forms.ValidationError(_('This field is required'), )
            elif (not return_qty and not returned_damage_qty) and return_reason:
                raise forms.ValidationError(
                    _('Either enter Return Qty for any product'
                      ' or Deselect this option'),
                )
        return return_reason

    def clean(self):
        data = self.cleaned_data
        if not self.instance.trip and not data['shipment_status'] == 'RESCHEDULED':
            raise forms.ValidationError(
                _('Please add the shipment in a'
                  ' trip first'),
            )
        return data


class ShipmentReschedulingForm(forms.ModelForm):
    shipment = forms.ModelChoiceField(
        queryset=Shipment.objects.all(),
        widget=forms.TextInput
    )

    rescheduling_date = forms.DateField(input_formats=['%Y-%m-%d'])

    class Meta:
        model = ShipmentRescheduling
        fields = ('shipment', 'rescheduling_reason', 'rescheduling_date', 'rescheduled_count')

    class Media:
        js = (
            'https://cdn.jsdelivr.net/npm/flatpickr',
            'admin/js/sweetalert.min.js',
            'admin/js/ShipmentRescheduling.js',
        )
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css',
            )
        }

    def clean_rescheduling_date(self):
        date = self.cleaned_data['rescheduling_date']
        if date > (datetime.date.today() + datetime.timedelta(days=3)):
            raise forms.ValidationError("The date must be within 3 days!")
        return date

    def clean_rescheduled_count(self):
        count = self.cleaned_data['rescheduled_count']
        return count + 1

    def __init__(self, *args, **kwargs):
        super(ShipmentReschedulingForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        self.fields['rescheduled_count'].widget.attrs['readonly'] = True

        # if instance.shipment:
        #     if not (self.instance.shipment.shipment_status == 'PARTIALLY_DELIVERED_AND_COMPLETED' or \
        #             self.instance.shipment.shipment_status == 'FULLY_RETURNED_AND_COMPLETED'):
        #         self.fields['rescheduling_reason'].disabled = True
        #         self.fields['rescheduling_date'].disabled = True


class ShipmentNotAttemptForm(forms.ModelForm):
    shipment = forms.ModelChoiceField(
        queryset=Shipment.objects.all(),
        widget=forms.TextInput
    )

    class Meta:
        model = ShipmentNotAttempt
        fields = ('shipment', 'not_attempt_reason',)

    class Media:
        js = (
            'https://cdn.jsdelivr.net/npm/flatpickr',
            'admin/js/sweetalert.min.js',
            'admin/js/ShipmentNotAttempt.js',
        )
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css',
            )
        }

    def __init__(self, *args, **kwargs):
        super(ShipmentNotAttemptForm, self).__init__(*args, **kwargs)


class OrderedProductMappingRescheduleForm(forms.ModelForm):
    class Meta:
        model = OrderedProductMapping
        fields = ['product', 'shipped_qty',
                  'returned_qty', 'returned_damage_qty', 'delivered_qty']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            if not (instance.ordered_product.shipment_status == 'PARTIALLY_DELIVERED_AND_COMPLETED' or \
                    instance.ordered_product.shipment_status == 'FULLY_RETURNED_AND_COMPLETED' or
                    instance.ordered_product.shipment_status == 'FULLY_DELIVERED_AND_COMPLETED'):
                self.fields['returned_qty'].disabled = True
                self.fields['returned_damage_qty'].disabled = True
                self.fields['delivered_qty'].disabled = True
                self.fields['shipped_qty'].disabled = True
            self.initial['shipped_qty'] = int(instance.shipped_qty)
            self.initial['delivered_qty'] = int(instance.delivered_qty)

    def clean(self):
        data = self.cleaned_data
        if self.instance.ordered_product.shipment_status == 'PARTIALLY_DELIVERED_AND_COMPLETED' or \
                self.instance.ordered_product.shipment_status == 'FULLY_RETURNED_AND_COMPLETED' or \
                self.instance.ordered_product.shipment_status == 'FULLY_DELIVERED_AND_COMPLETED':
            sku_return_qty = data['returned_qty']
            sku_returned_damage_qty = data['returned_damage_qty']
            product_batch_list_field = self.prefix + '-rt_ordered_product_mapping-TOTAL_FORMS'
            product_batch_list = self.data.get(product_batch_list_field)
            batch_return_qty = 0
            batch_damaged_qty = 0
            for batch in range(int(product_batch_list)):
                batch_return_field = self.prefix + '-rt_ordered_product_mapping-{0}-returned_qty'.format(batch)
                batch_damaged_field = self.prefix + '-rt_ordered_product_mapping-{0}-returned_damage_qty'.format(batch)
                if self.data.get(batch_return_field) is not None:
                    batch_return_qty = batch_return_qty + int(self.data.get(batch_return_field))
                if self.data.get(batch_damaged_field) is not None:
                    batch_damaged_qty = batch_damaged_qty + int(self.data.get(batch_damaged_field))
            if sku_return_qty != batch_return_qty or sku_returned_damage_qty != batch_damaged_qty:
                raise forms.ValidationError(
                    'Sum of Return or Damaged return quantity of batches should be equal to Return or Damaged return '
                    'quantity of SKU')

            data['delivered_qty'] = int(self.instance.shipped_qty) - (
                    data.get('returned_qty') + data.get('returned_damage_qty'))
            if int(self.instance.shipped_qty) != data.get('returned_qty') + data.get('returned_damage_qty') + data.get(
                    'delivered_qty'):
                raise forms.ValidationError(
                    'No. of pieces to ship must be equal to sum of (damaged, returned, delivered)')
        return data


class OrderForm(forms.ModelForm):
    seller_shop = forms.ChoiceField(required=False, choices=Shop.objects.values_list('id', 'shop_name'))
    buyer_shop = forms.ChoiceField(required=False, choices=Shop.objects.values_list('id', 'shop_name'))
    ordered_cart = forms.ChoiceField(choices=Cart.objects.values_list('id', 'order_id'))
    billing_address = forms.ChoiceField(required=False, choices=Address.objects.values_list('id', 'address_line1'))
    shipping_address = forms.ChoiceField(required=False, choices=Address.objects.values_list('id', 'address_line1'))
    ordered_by = forms.ChoiceField(required=False, choices=UserWithName.objects.values_list('id', 'phone_number'))
    last_modified_by = forms.ChoiceField(required=False, choices=UserWithName.objects.values_list('id', 'phone_number'))

    class Meta:
        model = Order
        fields = ('seller_shop', 'buyer_shop', 'ordered_cart', 'order_no', 'billing_address', 'shipping_address',
                  'total_discount_amount', 'total_tax_amount', 'order_status',
                  'cancellation_reason', 'ordered_by', 'last_modified_by')

    class Media:
        js = ('/static/admin/js/retailer_cart.js',)

    def clean_cancellation_reason(self):
        data = self.cleaned_data
        if (data['order_status'] == 'CANCELLED' and
                not data['cancellation_reason']):
            raise forms.ValidationError(_('Please select cancellation reason!'), )
        if (data['cancellation_reason'] and
                not data['order_status'] == 'CANCELLED'):
            raise forms.ValidationError(
                _('The reason does not match with the action'), )
        return data['cancellation_reason']

    def clean(self):
        if self.instance.order_status == 'CANCELLED':
            raise forms.ValidationError(_('This order is already cancelled!'), )
        data = self.cleaned_data
        if self.cleaned_data.get('order_status') == 'CANCELLED':
            if self.instance.order_status in [Order.DISPATCHED, Order.COMPLETED]:
                raise forms.ValidationError(
                    _('Sorry! This order cannot be cancelled'), )
        return data

    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            if instance.order_status in [Order.CANCELLED, Order.DISPATCHED, Order.COMPLETED]:
                self.fields['order_status'].disabled = True
                self.fields['cancellation_reason'].disabled = True
            else:
                order_status_choices = tuple(set(
                    [i for i in Order.ORDER_STATUS if i[0] == instance.order_status] +
                    [('CANCELLED', 'Cancelled')]))
                self.fields['order_status'].choices = order_status_choices


class OrderedProductBatchForm(forms.ModelForm):
    class Meta:
        model = OrderedProductBatch
        fields = ('pickup_quantity', 'quantity', 'damaged_qty', 'expired_qty')

    def __init__(self, *args, **kwargs):
        super(OrderedProductBatchForm, self).__init__(*args, **kwargs)
        self.fields['quantity'].disabled = True
        self.fields['pickup_quantity'].disabled = True
        if not get_current_user().is_superuser:
            instance = getattr(self, 'instance', None)
            if instance.pk:
                shipment_status = instance.ordered_product_mapping.ordered_product.shipment_status
                if shipment_status == 'READY_TO_SHIP' or shipment_status == 'CANCELLED':
                    for field_name in self.fields:
                        self.fields[field_name].disabled = True

        instance = getattr(self, 'instance', None)
        if instance.pk:
            shipment_status = instance.ordered_product_mapping.ordered_product.shipment_status
            if shipment_status != 'SHIPMENT_CREATED':
                for field_name in self.fields:
                    self.fields[field_name].disabled = True
        if instance:
            self.initial['quantity'] = int(instance.quantity)
            self.initial['pickup_quantity'] = int(instance.pickup_quantity)

    def clean(self):
        data = self.cleaned_data
        if self.instance.ordered_product_mapping.ordered_product.shipment_status != 'SHIPMENT_CREATED':
            return data
        else:
            if data.get('damaged_qty') is None:
                raise forms.ValidationError('Damaged Quantity can not be blank.')
            if data.get('expired_qty') is None:
                raise forms.ValidationError('Expired Quantity can not be blank.')
            data['quantity'] = self.instance.pickup_quantity - (data.get('damaged_qty') + data.get('expired_qty') +
                                                                data.get('missing_qty') + data.get('rejected_qty'))
            if float(self.instance.pickup_quantity) != float(data['quantity'] + data.get('damaged_qty') + data.get(
                    'expired_qty') + data.get('missing_qty') + data.get('rejected_qty')) :
                raise forms.ValidationError(
                    'Sorry Quantity mismatch!! Picked pieces must be equal to sum of (damaged_qty, expired_qty, no.of pieces to ship.)')
            return data


class OrderedProductBatchingForm(forms.ModelForm):
    class Meta:
        model = OrderedProductBatch
        fields = ('quantity', 'returned_damage_qty', 'returned_qty', 'delivered_qty')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            if not (
                    instance.ordered_product_mapping.ordered_product.shipment_status == 'PARTIALLY_DELIVERED_AND_COMPLETED' or \
                    instance.ordered_product_mapping.ordered_product.shipment_status == 'FULLY_RETURNED_AND_COMPLETED' or
                    instance.ordered_product_mapping.ordered_product.shipment_status == 'FULLY_DELIVERED_AND_COMPLETED'):
                self.fields['returned_qty'].disabled = True
                self.fields['returned_damage_qty'].disabled = True
                self.fields['delivered_qty'].disabled = True
                self.fields['quantity'].disabled = True
            self.initial['quantity'] = int(instance.quantity)

    def clean(self):
        data = self.cleaned_data
        if self.instance.ordered_product_mapping.ordered_product.shipment_status == 'PARTIALLY_DELIVERED_AND_COMPLETED' or \
                self.instance.ordered_product_mapping.ordered_product.shipment_status == 'FULLY_RETURNED_AND_COMPLETED':
            data['delivered_qty'] = int(self.instance.quantity) - (
                    data.get('returned_damage_qty') + data.get('returned_qty'))
            if int(self.instance.quantity) != data.get('returned_damage_qty') + data.get('returned_qty') + data.get(
                    'delivered_qty'):
                raise forms.ValidationError('No. of pieces to ship must be equal to sum of (damaged, returned, '
                                            'delivered)')
        return data
