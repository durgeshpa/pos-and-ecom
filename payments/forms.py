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
from payments.models import Payment, ShipmentPayment, OnlinePayment,\
    OrderPayment #, ShipmentPaymentApproval
from retailer_to_sp.models import Order

User = get_user_model()


class ShipmentPaymentForm(forms.ModelForm):

    class Meta:
        model = ShipmentPayment
        fields = "__all__"


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)
        self.fields.get('paid_by').required = True
        # if self.data and self.data.get('payment_mode_name') != 'cash_payment':
        #     self.fields.get('reference_no').required = True


class OrderPaymentForm(forms.ModelForm):
    class Meta:
        model = OrderPayment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(OrderPaymentForm, self).__init__(*args, **kwargs)
        self.fields.get('parent_payment').required = True
        self.fields.get('paid_amount').required = True
        # if self.data and self.data.get('payment_mode_name') != 'cash_payment':
        #     self.fields.get('reference_no').required = True
    
    
    
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




# class ShipmentPaymentApprovalForm(forms.ModelForm):

#     class Meta:
#         model = ShipmentPaymentApproval
#         fields = "__all__"

class OnlinePaymentInlineForm(forms.ModelForm):

    class Meta:
        model = OnlinePayment
        fields = "__all__"
