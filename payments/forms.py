import datetime

from dal import autocomplete
from django.db.models import Sum, Q
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

from accounts.middlewares import get_current_user
from accounts.models import UserWithName
from payments.models import Payment, ShipmentPayment, OrderPayment, \
    ShipmentPaymentApproval, PaymentApproval, PAYMENT_MODE_NAME, ShipmentData, ONLINE_PAYMENT_TYPE_CHOICES
from retailer_to_sp.models import Order
from shops.models import Shop
from shops.views import UserAutocomplete

User = get_user_model()


# add data in args, kwargs
class RelatedFieldWidgetCanAdd(widgets.Select):

    def __init__(self, related_model, related_url=None, *args, **kw):

        super(RelatedFieldWidgetCanAdd, self).__init__(*args, **kw)

        if not related_url:
            rel_to = related_model
            info = (rel_to._meta.app_label, rel_to._meta.object_name.lower())
            related_url = 'admin:%s_%s_add' % info

        # Be careful that here "reverse" is not allowed
        self.related_url = related_url
        self.args = args
        self.kwargs = kw

    def render(self, name, value, *args, **kwargs):
        self.related_url = reverse(self.related_url)
        output = [super(RelatedFieldWidgetCanAdd, self).render(name, value, *args, **kwargs)]
        output.append('<a href="%s?_to_field=id&_popup=1&user_id=%s&object_id=%s" class="add-another" id="add_id_%s" onclick="return showAddAnotherPopup(this);"> ' % \
            (self.related_url, self.args[0].get('user_id'), self.args[0].get('object_id'), name))
        output.append('<img src="%sadmin/img/icon_addlink.gif" width="10" height="10" alt="%s"/></a>' % (settings.STATIC_URL, 'Add Another'))
        return mark_safe(''.join(output))


class ShipmentPaymentForm(forms.ModelForm):

    class Meta:
        model = ShipmentPayment
        fields = "__all__"


class PaymentForm(forms.ModelForm):
    paid_by = forms.ModelChoiceField(
        queryset=UserWithName.objects.all(),
        widget=autocomplete.ModelSelect2(url='admin:userwithname-autocomplete',)
    )

    class Meta:
        model = Payment
        fields = ('description', 'reference_no', 'payment_screenshot', 'paid_amount', 'payment_mode_name',
                  'prepaid_or_postpaid', 'payment_approval_status', 'payment_received',
                  'is_payment_approved', 'mark_as_settled', 'payment_status', 'online_payment_type',
                  'initiated_time', 'timeout_time')

    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)
        self.fields.get('paid_by').required = True
        users = Shop.objects.filter(shop_type__shop_type="r").values('shop_owner__id')
        self.fields.get('paid_by').queryset = UserWithName.objects.filter(pk__in=users)
        # if self.data and self.data.get('payment_mode_name') != 'cash_payment':
        #     self.fields.get('reference_no').required = True


class OrderPaymentForm(forms.ModelForm):

    order = forms.ModelChoiceField(
        queryset=Order.objects.all(),
        widget=autocomplete.ModelSelect2(url='order-autocomplete',)
    )
    # parent_payment = forms.ModelChoiceField(
    #     queryset=Payment.objects.all(),
    #     widget=autocomplete.ModelSelect2(url='order-payment-autocomplete',
    #                                      forward=('order',))
    # )
    parent_payment = forms.ModelChoiceField(
        queryset=Payment.objects.all(),
        widget=forms.TextInput(attrs={'hidden': 'hidden'}), required=False)
    paid_by = forms.ModelChoiceField(
        queryset=UserWithName.objects.all(),
        widget=autocomplete.ModelSelect2(url='admin:userwithname-autocomplete', )
    )
    payment_mode_name = forms.ChoiceField(choices=PAYMENT_MODE_NAME)
    online_payment_type = forms.ChoiceField(choices=ONLINE_PAYMENT_TYPE_CHOICES)
    paid_amount = forms.FloatField(required=True)
    reference_no = forms.CharField(required=False)

    class Meta:
        model = OrderPayment
        fields = ('description', 'order', 'paid_amount', 'payment_id', 'parent_payment')

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(OrderPaymentForm, self).__init__(*args, **kwargs)

        self.fields.get('paid_amount').required = True
        self.fields.get('paid_by').required = True
        users = Shop.objects.filter(shop_type__shop_type="r").values('shop_owner__id')
        self.fields.get('paid_by').queryset = UserWithName.objects.filter(pk__in=users)
        instance = getattr(self, 'instance', None)
        if instance.pk:
            self.fields['paid_by'].initial = instance.parent_payment.paid_by.id
            self.fields['reference_no'].initial = instance.parent_payment.reference_no
            self.fields['payment_mode_name'].initial = instance.parent_payment.payment_mode_name
            self.fields['online_payment_type'].initial = instance.parent_payment.online_payment_type
            self.fields.get('order').disabled = True
        elif kwargs is not None and kwargs.get('initial', None):
            if kwargs.get('initial').get('object_id', None) is not None:
                object_id = kwargs.get('initial').get('object_id')
                shipment_data_instance = ShipmentData.objects.filter(id=object_id).last()
                self.fields['order'].initial = shipment_data_instance.order.id
        # elif not instance.pk:
        #     print(request.user.id)
        #     if request:
        #         self.fields['paid_by'].initial = request.user.id

    def clean(self):
        cleaned_data = super(OrderPaymentForm, self).clean()
        paid_by = cleaned_data.get('paid_by')
        paid_amount = cleaned_data.get('paid_amount', 0)
        reference_no = cleaned_data.get('reference_no')
        payment_mode_name = cleaned_data.get('payment_mode_name')
        online_payment_type = cleaned_data.get('online_payment_type')
        order = cleaned_data.get('order')
        existing_payment = None
        if order:
            cash_to_be_collected = 0
            shipment = order.rt_order_order_product.last()
            # if paid_amount <= 0:
            #     raise ValidationError(_('Paid amount should be greater than 0'))
            if shipment:
                cash_to_be_collected = shipment.cash_to_be_collected()
                total_payments = Payment.objects.filter(order=order, 
                                                        parent_payment_order__shipment_order_payment__isnull=False)
                if self.instance.pk:
                    existing_payment = self.instance.parent_payment
                    total_payments = total_payments.exclude(id=existing_payment.pk)
                total_paid_amount = total_payments.aggregate(paid_amount=Sum('paid_amount')).get('paid_amount')
                total_paid_amount = total_paid_amount if total_paid_amount else 0
                if (float(total_paid_amount) + float(paid_amount)) > float(cash_to_be_collected):
                    raise ValidationError(_(f"Max amount to be paid is {cash_to_be_collected-total_paid_amount}"))

            if paid_by and paid_amount >= 0 and order and payment_mode_name:
                if not self.instance.pk:
                    if existing_payment:
                        if existing_payment.order.filter(~Q(id=order.pk)).exists():
                            existing_payment.order.remove(order)
                        else:
                            existing_payment.delete()
                if payment_mode_name == "online_payment" and not reference_no:
                    raise ValidationError(_('Reference number is required.'))
                if total_payments.filter(payment_mode_name='online_payment', reference_no=reference_no).exists():
                    raise ValidationError(_('Reference number already present.'))
                if not existing_payment:
                    payment = Payment.objects.create(paid_by=paid_by,
                                                    paid_amount=paid_amount,
                                                    payment_mode_name=payment_mode_name,
                                                    )
                else:
                    payment = existing_payment
                    payment.paid_by = paid_by
                    payment.paid_amount = paid_amount
                    payment.payment_mode_name = payment_mode_name
                if payment_mode_name == "online_payment":
                    payment.reference_no = reference_no
                    payment.online_payment_type = online_payment_type
                if self.instance.pk:
                    #prev_mode = OrderPayment.objects.get(pk=self.instance.pk).parent_payment.payment_mode_name
                    #if prev_mode != 'cash_payment' and 
                    if payment_mode_name == 'cash_payment':
                        payment.payment_approval_status = 'approved_and_verified'
                        payment.reference_no = None
                    #elif prev_mode == 'cash_payment' and 
                    elif payment_mode_name != 'cash_payment':
                        payment.payment_approval_status = 'pending_approval'
                payment.save()
                cleaned_data['parent_payment'] = payment
        return cleaned_data


class ShipmentPaymentInlineForm(forms.ModelForm):

    class Meta:
        model = ShipmentPayment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        # show only the payments for the relevant order
        super(ShipmentPaymentInlineForm, self).__init__(*args, **kwargs)
        self.fields.get('parent_order_payment').required = True
        instance = getattr(self, 'instance', None)
        if instance.pk:
            payment_mode = instance.parent_order_payment.parent_payment.payment_mode_name
            payment_status = instance.parent_order_payment.parent_payment.payment_approval_status
            if payment_mode == 'online_payment' and payment_status == 'approved_and_verified':
                widget = self.fields.get('parent_order_payment').widget
                widget.can_add_related = False
                widget.can_change_related = False
        # shipment_payment = getattr(self, 'instance', None)

        # self.fields['parent_payment'].queryset = Payment.objects.filter(order=shipment_payment.shipment.order)


def ShipmentPaymentInlineFormFactory(object_id):
    class ShipmentPaymentInlineForm(forms.ModelForm):
        paid_amount = forms.DecimalField(widget=forms.TextInput(attrs={'hidden': 'hidden'}), required=False)

        class Meta:
            model = ShipmentPayment
            fields = ('paid_amount', 'description', 'shipment', 'parent_order_payment', 'paid_amount',)

        def __init__(self, *args, **kwargs):
            # show only the payments for the relevant order
            super(ShipmentPaymentInlineForm, self).__init__(*args, **kwargs)
            self.fields.get('parent_order_payment').required = True
            # shipment_payment = getattr(self, 'instance', None)

            # self.fields['parent_payment'].queryset = Payment.objects.filter(order=shipment_payment.shipment.order)
            self.fields.get('parent_order_payment').queryset = OrderPayment.objects.filter(
                order__rt_order_order_product__id=object_id)
            instance = getattr(self, 'instance', None)
            if instance.pk:
                payment_mode = instance.parent_order_payment.parent_payment.payment_mode_name
                payment_status = instance.parent_order_payment.parent_payment.payment_approval_status
                if payment_mode == 'online_payment' and payment_status == 'approved_and_verified':
                    self.fields.get('parent_order_payment').disabled = True
                    widget = self.fields.get('parent_order_payment').widget
                    widget.can_add_related = False
                    widget.can_change_related = False
            # self.fields.get('parent_order_payment').widget = RelatedFieldWidgetCanAdd(
            #         OrderPayment, None, {"user_id": user_id, "object_id": object_id})

        def clean(self):
            cleaned_data = super(ShipmentPaymentInlineForm, self).clean()
            parent_order_payment = cleaned_data.get('parent_order_payment')
            if parent_order_payment:
                self.instance.paid_amount = float(parent_order_payment.paid_amount)
            return cleaned_data

    return ShipmentPaymentInlineForm


class PaymentApprovalForm(forms.ModelForm):

    class Meta:
        model = PaymentApproval
        fields = "__all__"
    
    def __init__(self, *args, **kwargs):
        super(PaymentApprovalForm, self).__init__(*args, **kwargs)

        instance = getattr(self, 'instance', None)
        self.fields['payment_approval_status'].disabled = True
        if instance.is_payment_approved:   
            # for field_name in self.fields:
            #     self.fields[field_name].disabled = True
            self.fields['is_payment_approved'].disabled = True 
            # adding payment approval status

