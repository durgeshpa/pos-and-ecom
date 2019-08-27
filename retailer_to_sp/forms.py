import datetime

from dal import autocomplete
from django_select2.forms import Select2MultipleWidget, ModelSelect2Widget
from tempus_dominus.widgets import DatePicker

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

from .signals import ReservedOrder
from sp_to_gram.models import (
    OrderedProductReserved,
    OrderedProductMapping as SpMappedOrderedProductMapping)
from retailer_backend.common_function import required_fields
from retailer_to_sp.models import (
    CustomerCare, ReturnProductMapping, OrderedProduct,
    OrderedProductMapping, Order, Dispatch, Trip, TRIP_STATUS,
    Shipment, ShipmentProductMapping, CartProductMapping, Cart,
    ShipmentRescheduling, PickerDashboard, generate_picklist_id, ResponseComment
)
from products.models import Product
from shops.models import Shop
from accounts.models import UserWithName
from accounts.middlewares import get_current_user
from addresses.models import Address

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
                                   required=True)

    # order = forms.ModelChoiceField(queryset=Order.objects.filter(
    #     order_status__in=[Order.OPDP, 'ordered',
    #                       'PARTIALLY_SHIPPED', 'DISPATCH_PENDING'],
    #     order_closed=False),
    #     required=True)

    class Meta:
        model = OrderedProduct
        fields = ['order', 'shipment_status', 'no_of_crates', 'no_of_packets', 'no_of_sacks']

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
        self.fields['shipment_status'].choices = OrderedProduct.SHIPMENT_STATUS[:2]
        ordered_product = getattr(self, 'instance', None)
        # if ordered_product is None:
        qc_pending_orders = OrderedProduct.objects.filter(shipment_status="SHIPMENT_CREATED").values('order')
        self.fields['order'].queryset = Order.objects.filter(order_status__in=[Order.OPDP, 'ordered',
                                                                               'PARTIALLY_SHIPPED', 'DISPATCH_PENDING'],
                                                             order_closed=False).exclude(id__in=qc_pending_orders)

    def clean(self):
        data = self.cleaned_data
        if not self.cleaned_data['order'].picker_order.all().exists():
            raise forms.ValidationError(_("Please assign picklist to the order"),)
        if self.cleaned_data['shipment_status']=='SHIPMENT_CREATED' and \
            self.cleaned_data['order'].picker_order.last().picking_status != "picking_assigned":
            raise forms.ValidationError(_("Please set the picking status in picker dashboard"),)

        return data


class OrderedProductMappingForm(forms.ModelForm):
    ordered_qty = forms.CharField(required=False, label="Ordered Pieces")
    shipped_qty = forms.CharField(required=False, label="Shipped Pieces")
    gf_code = forms.CharField(required=False)

    class Meta:
        model = OrderedProductMapping
        fields = ['product', 'gf_code', 'ordered_qty', 'shipped_qty', 'delivered_qty', 'returned_qty', 'damaged_qty']

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
    ordered_qty = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    already_shipped_qty = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    to_be_shipped_qty = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(), widget=forms.TextInput)
    product_name = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'readonly': True}))

    class Meta:
        model = OrderedProductMapping
        fields = [
            'product', 'ordered_qty', 'already_shipped_qty',
            'to_be_shipped_qty', 'shipped_qty',
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
        fields = ['order', 'shipment', 'picking_status', 'picklist_id', 'picker_boy']

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

    def __init__(self, *args, **kwargs):
        super(EditAssignPickerForm, self).__init__(*args, **kwargs)
        # import pdb; pdb.set_trace()
        instance = getattr(self, 'instance', None)

        shop = instance.order.seller_shop#Shop.objects.get(related_users=user)
        #shop = Shop.objects.get(shop_name="TEST SP 1")
        # find all picker for the shop
        self.fields['picker_boy'].queryset = shop.related_users.filter(groups__name__in=["Picker Boy"])
        if instance.picking_status == "picking_pending":
            self.fields['picker_boy'].required = False
        else:
            self.fields['picker_boy'].required = True
        # self.fields['picking_status'] = forms.ChoiceField(
        #     choices=self.get_my_choices() )
        # self.fields['picking_status'].choices = self.get_my_choices()


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
        # import pdb; pdb.set_trace()
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
        widget=RelatedFieldWidgetCanAdd(
            UserWithName,
            related_url="admin:accounts_user_add"))
    trip_status = forms.ChoiceField(choices=TRIP_STATUS)
    search_by_area = forms.CharField(required=False)
    search_by_pincode = forms.CharField(required=False)
    Invoice_No = forms.CharField(required=False)
    trip_id = forms.CharField(required=False)
    total_crates_shipped = forms.IntegerField(required=False)
    total_packets_shipped = forms.IntegerField(required=False)
    total_sacks_shipped = forms.IntegerField(required=False)
    total_crates_collected = forms.IntegerField(required=False)
    total_packets_collected = forms.IntegerField(required=False)
    total_sacks_collected = forms.IntegerField(required=False)
    selected_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    unselected_id = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Trip
        fields = ['seller_shop', 'delivery_boy', 'vehicle_no', 'trip_status',
                  'e_way_bill_no', 'search_by_area', 'search_by_pincode', 'Invoice_No', 'selected_id',
                  'unselected_id']

    class Media:
        js = ('admin/js/select2.min.js',)
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
        self.fields['total_crates_shipped'].initial = instance.total_crates_shipped
        self.fields['total_packets_shipped'].initial = instance.total_packets_shipped
        self.fields['total_sacks_shipped'].initial = instance.total_sacks_shipped


        trip = instance.pk
        if trip:
            trip_status = instance.trip_status
            self.fields['trip_id'].initial = trip
            if trip_status == 'READY':
                self.fields['seller_shop'].disabled = True
                self.fields['trip_status'].choices = TRIP_STATUS[0], TRIP_STATUS[2], TRIP_STATUS[1]
                self.fields['total_crates_shipped'].disabled = True
                self.fields['total_packets_shipped'].disabled = True
                self.fields['total_sacks_shipped'].disabled = True
                self.fields['total_crates_collected'].disabled = True
                self.fields['total_packets_collected'].disabled = True
                self.fields['total_sacks_collected'].disabled = True

            elif trip_status == 'STARTED':
                self.fields['delivery_boy'].disabled = True
                self.fields['seller_shop'].disabled = True
                self.fields['vehicle_no'].disabled = True
                self.fields['trip_status'].choices = TRIP_STATUS[2:4]
                self.fields['total_crates_shipped'].disabled = True
                self.fields['total_packets_shipped'].disabled = True
                self.fields['total_sacks_shipped'].disabled = True
                self.fields['total_crates_collected'].disabled = True
                self.fields['total_packets_collected'].disabled = True
                self.fields['total_sacks_collected'].disabled = True
                self.fields['search_by_area'].widget = forms.HiddenInput()
                self.fields['search_by_pincode'].widget = forms.HiddenInput()
                self.fields['Invoice_No'].widget = forms.HiddenInput()


            elif trip_status == 'COMPLETED':
                self.fields['delivery_boy'].disabled = True
                self.fields['seller_shop'].disabled = True
                self.fields['vehicle_no'].disabled = True
                self.fields['trip_status'].disabled = True
                self.fields['total_crates_shipped'].disabled = True
                self.fields['total_packets_shipped'].disabled = True
                self.fields['total_sacks_shipped'].disabled = True
                self.fields['total_crates_collected'].initial = instance.total_crates_collected
                self.fields['total_crates_collected'].disabled = True
                self.fields['total_packets_collected'].initial = instance.total_packets_collected
                self.fields['total_packets_collected'].disabled = True
                self.fields['total_sacks_collected'].initial = instance.total_sacks_collected
                self.fields['total_sacks_collected'].disabled = True
                self.fields['search_by_area'].widget = forms.HiddenInput()
                self.fields['search_by_pincode'].widget = forms.HiddenInput()
                self.fields['Invoice_No'].widget = forms.HiddenInput()

            else:
                for field_name in self.fields:
                    self.fields[field_name].disabled = True
                self.fields['trip_status'].choices = TRIP_STATUS[1:2]
        else:
            self.fields['trip_status'].initial = 'READY'
            fields = ['trip_status', 'e_way_bill_no']
            for field in fields:
                self.fields[field].required = False
                self.fields[field].widget = forms.HiddenInput()

    def clean(self):
        data = self.cleaned_data
        if self.instance and self.instance.trip_status == 'READY':
            shipment_ids = data.get('selected_id').split(',')
            cancelled_shipments = Shipment.objects.values('id', 'invoice_no'
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
                               args=[i.get('id')]), i.get('invoice_no'))
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
                if trip_status == 'READY' or trip_status == 'STARTED':
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
    close_order = forms.BooleanField(required=False)

    class Meta:
        model = Shipment
        fields = ['order', 'shipment_status', 'no_of_crates', 'no_of_packets', 'no_of_sacks']

    class Media:
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/select2/'
            '4.0.6-rc.0/js/select2.min.js', 'admin/js/sweetalert.min.js',
            'admin/js/order_close_message.js'
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

        if not get_current_user().is_superuser:
            ordered_product = getattr(self, 'instance', None)
            SHIPMENT_STATUS = OrderedProduct.SHIPMENT_STATUS
            if ordered_product:
                shipment_status = ordered_product.shipment_status
                if shipment_status == 'SHIPMENT_CREATED':
                    self.fields['shipment_status'].choices = SHIPMENT_STATUS[:2]
                elif shipment_status == 'READY_TO_SHIP':
                    setattr(self.fields['close_order'], 'disabled', True)
                    self.fields['shipment_status'].disabled = True
                elif shipment_status == 'CANCELLED':
                    setattr(self.fields['close_order'], 'disabled', True)
                    self.fields['shipment_status'].disabled = True
                if ordered_product.order.order_closed:
                    setattr(self.fields['close_order'], 'initial', True)
                    setattr(self.fields['close_order'], 'disabled', True)
            else:
                self.fields['shipment_status'].choices = SHIPMENT_STATUS[:1]

    def clean(self):
        data = self.cleaned_data
        # if self.instance and self.cleaned_data['shipment_status']=='SHIPMENT_CREATED' and \
        #     self.instance.order.picker_order.last().picking_status != "picking_assigned":
        #     raise forms.ValidationError(_("Please set the picking status in picker dashboard"),)

        if (data['close_order'] and
                not data['shipment_status'] == OrderedProduct.READY_TO_SHIP):
                raise forms.ValidationError(
                    _('You can only close the order in QC Passed state'),)
        order_closed_status = ['denied_and_closed', 'partially_shipped_and_closed',
                               'DENIED', 'CANCELLED', 'CLOSED', 'deleted']
        return data


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
        if not get_current_user().is_superuser:
            instance = getattr(self, 'instance', None)
            if instance.pk:
                shipment_status = instance.ordered_product.shipment_status
                if shipment_status == 'READY_TO_SHIP' or shipment_status == 'CANCELLED':
                    for field_name in self.fields:
                        self.fields[field_name].disabled = True


class CartProductMappingForm(forms.ModelForm):
    product_case_size = forms.CharField(
        required=False, widget=forms.HiddenInput())
    product_inner_case_size = forms.CharField(
        required=False, widget=forms.HiddenInput())

    class Meta:
        model = CartProductMapping
        fields = (
            'cart', 'cart_product', 'cart_product_price', 'qty',
            'no_of_pieces', 'product_case_size', 'product_inner_case_size')

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
    class Meta:
        model = Cart
        fields = ('seller_shop', 'buyer_shop')


class CommercialForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['dispatch_no', 'delivery_boy', 'seller_shop', 'trip_status',
                  'starts_at', 'completed_at', 'e_way_bill_no', 'vehicle_no',
                  'trip_amount', 'received_amount']

    class Media:
        js = ('admin/js/CommercialLoadShipments.js',)

    def __init__(self, *args, **kwargs):
        super(CommercialForm, self).__init__(*args, **kwargs)
        self.fields['trip_status'].choices = TRIP_STATUS[3:5]
        instance = getattr(self, 'instance', None)
        if instance.pk:
            if (instance.trip_status == 'TRANSFERRED' or
                    instance.trip_status == 'CLOSED'):
                self.fields['trip_status'].choices = TRIP_STATUS[-3:]
                for field_name in self.fields:
                    self.fields[field_name].disabled = True

    def clean_received_amount(self):
        trip_status = self.cleaned_data.get('trip_status')
        received_amount = self.cleaned_data.get('received_amount')
        if trip_status == 'CLOSED' and not received_amount:
            raise forms.ValidationError(('This field is required'), )
        return received_amount

    def clean(self):
        data = self.cleaned_data
        if data['trip_status'] == 'CLOSED':
            if self.instance.received_cash_amount + self.instance.received_online_amount < self.instance.cash_to_be_collected_value:
                raise forms.ValidationError(_("Amount to be collected is less than sum of received cash amount and online amount"),)

        return data



class OrderedProductReschedule(forms.ModelForm):
    class Meta:
        model = OrderedProduct
        fields = (
            'order', 'invoice_no', 'shipment_status', 'trip',
            'return_reason'
        )

    class Media:
        js = ('admin/js/OrderedProductShipment.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not get_current_user().is_superuser:
            instance = getattr(self, 'instance', None)
            if instance.shipment_status == OrderedProduct.RESCHEDULED or instance.return_reason:
                self.fields['return_reason'].disabled = True

    def clean_return_reason(self):
        return_reason = self.cleaned_data.get('return_reason')
        if not self.instance.shipment_status == OrderedProduct.RESCHEDULED and not self.instance.return_reason:
            return_qty = 0
            damaged_qty = 0
            total_products = self.data.get(
                'rt_order_product_order_product_mapping-TOTAL_FORMS')
            for product in range(int(total_products)):
                return_field = ("rt_order_product_order_product_mapping-%s-returned_qty") \
                               % product
                damaged_field = ("rt_order_product_order_product_mapping-%s-damaged_qty") \
                                % product
                return_qty += int(self.data.get(return_field))
                damaged_qty += int(self.data.get(damaged_field))
            if (return_qty or damaged_qty) and not return_reason:
                raise forms.ValidationError(_('This field is required'), )
            elif (not return_qty and not damaged_qty) and return_reason:
                raise forms.ValidationError(
                    _('Either enter Return Qty for any product'
                      ' or Deselect this option'),
                )
        return return_reason

    def clean(self):
        data = self.cleaned_data
        if not self.instance.trip:
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
        fields = ('shipment', 'rescheduling_reason', 'rescheduling_date')

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

    def __init__(self, *args, **kwargs):
        super(ShipmentReschedulingForm, self).__init__(*args, **kwargs)
        if not get_current_user().is_superuser:
            instance = getattr(self, 'instance', None)
            if instance and instance.pk:
                self.fields['rescheduling_reason'].disabled = True
                self.fields['rescheduling_date'].disabled = True


class OrderedProductMappingRescheduleForm(forms.ModelForm):
    class Meta:
        model = OrderedProductMapping
        fields = ['product', 'shipped_qty',
                  'returned_qty', 'damaged_qty', 'delivered_qty']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not get_current_user().is_superuser:
            instance = getattr(self, 'instance', None)
            if instance and instance.pk:
                if instance.ordered_product.shipment_status == OrderedProduct.RESCHEDULED or instance.ordered_product.return_reason:
                    self.fields['returned_qty'].disabled = True
                    self.fields['damaged_qty'].disabled = True


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
            raise forms.ValidationError(_('Please select cancellation reason!'),)
        if (data['cancellation_reason'] and
                not data['order_status'] == 'CANCELLED'):
            raise forms.ValidationError(
                _('The reason does not match with the action'),)
        return data['cancellation_reason']

    def clean(self):
        if self.instance.order_status == 'CANCELLED':
            raise forms.ValidationError(_('This order is already cancelled!'), )
        data = self.cleaned_data
        if self.cleaned_data.get('order_status') == 'CANCELLED':
            shipments_data = list(self.instance.rt_order_order_product.values(
                'id', 'shipment_status', 'trip__trip_status'))
            if len(shipments_data) == 1:
                # last shipment
                s = shipments_data[-1]
                if (s['shipment_status'] not in [i[0] for i in OrderedProduct.SHIPMENT_STATUS[:3]]):
                    raise forms.ValidationError(
                        _('Sorry! This order cannot be cancelled'), )
                elif (s['trip__trip_status'] and s['trip__trip_status'] != 'READY'):
                    raise forms.ValidationError(
                        _('Sorry! This order cannot be cancelled'), )
            elif len(shipments_data) > 1:
                status = [x[0] for x in OrderedProduct.SHIPMENT_STATUS[1:]
                          if x[0] in [x['shipment_status'] for x in shipments_data]]
                if status:
                    raise forms.ValidationError(
                        _('Sorry! This order cannot be cancelled'), )
            else:
                return data

    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            if instance.order_status == 'CANCELLED':
                self.fields['order_status'].disabled = True
                self.fields['cancellation_reason'].disabled = True
