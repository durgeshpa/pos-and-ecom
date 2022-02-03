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

from accounts.middlewares import get_current_user
from accounts.models import UserWithName
from payments.models import Payment, ShipmentPayment, OrderPayment, \
    ShipmentPaymentApproval, PaymentApproval, PAYMENT_MODE_NAME
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
        output.append('<a href="%s?_to_field=id&_popup=1&order=%s" class="add-another" id="add_id_%s" onclick="return showAddAnotherPopup(this);"> ' % \
            (self.related_url, self.args[0].get('order'), name))
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
    paid_by = forms.ModelChoiceField(
        queryset=UserWithName.objects.all(),
        widget=autocomplete.ModelSelect2(url='admin:userwithname-autocomplete', )
    )
    payment_mode_name = forms.ChoiceField(choices=PAYMENT_MODE_NAME)
    paid_amount = forms.FloatField(required=True)
    reference_no = forms.CharField(required=False)

    class Meta:
        model = OrderPayment
        fields = ('description', 'order', 'paid_amount', 'payment_id')

    def __init__(self, *args, **kwargs):
        super(OrderPaymentForm, self).__init__(*args, **kwargs)
        # self.fields.get('parent_payment').required = True
        self.fields.get('paid_amount').required = True
        if kwargs is not None and kwargs.get('initial'):
            if kwargs.get('initial').get('order') is not None:
                self.fields['order'].initial = kwargs.get('initial').get('order')
                self.fields['order'].widget.attrs['readonly'] = True
        self.fields.get('paid_by').required = True
        users = Shop.objects.filter(shop_type__shop_type="r").values('shop_owner__id')
        self.fields.get('paid_by').queryset = UserWithName.objects.filter(pk__in=users)

    def save(self, commit=True):
        # instance = super(OrderPaymentForm, self).save(commit=False)
        payment = Payment.objects.create(paid_by=self.cleaned_data['paid_by'],
                                         paid_amount=self.cleaned_data['paid_amount'],
                                         reference_no=self.cleaned_data['reference_no'])
        payment.order.add(self.cleaned_data['order'])
        self.cleaned_data['parent_payment_id'] = payment.id
        return super(OrderPaymentForm, self).save(commit)


class ShipmentPaymentInlineForm(forms.ModelForm):

    class Meta:
        model = ShipmentPayment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        # show only the payments for the relevant order
        super(ShipmentPaymentInlineForm, self).__init__(*args, **kwargs)
        self.fields.get('parent_order_payment').required = True
        # shipment_payment = getattr(self, 'instance', None)

        # self.fields['parent_payment'].queryset = Payment.objects.filter(order=shipment_payment.shipment.order)

        if self.fields.get('shipment') is not None:
            self.fields.get('parent_order_payment').widget = RelatedFieldWidgetCanAdd(
                OrderPayment, None, {"order": self.fields['shipment'].order})


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

