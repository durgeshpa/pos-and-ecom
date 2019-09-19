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
from shops.models import Shop


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

    def render(self, name, value, *args, **kwargs):
        self.related_url = reverse(self.related_url)
        output = [super(RelatedFieldWidgetCanAdd, self).render(name, value, *args, **kwargs)]
        output.append('<a href="%s" class="related-widget-wrapper-link add-related" id="add_id_%s" \
            onclick="return showAddAnotherPopup(this);"> ' %
                      (self.related_url, name))
        output.append('<img src="/static/admin/img/icon-addlink.svg" width="10" height="10" \
            alt="Add"/>Add Delivery Boy</a>')
        return mark_safe(''.join(output))


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
        users = Shop.objects.all().values('shop_owner')
        self.fields.get('paid_by').queryset = users
        # if self.data and self.data.get('payment_mode_name') != 'cash_payment':
        #     self.fields.get('reference_no').required = True


class OrderPaymentForm(forms.ModelForm):

    order = forms.ModelChoiceField(
        queryset=Order.objects.all(),
        widget=autocomplete.ModelSelect2(url='order-autocomplete',)
    )
    parent_payment = forms.ModelChoiceField(
        queryset=Payment.objects.all(),
        widget=autocomplete.ModelSelect2(url='order-payment-autocomplete',
                                         forward=('order'))
    )

    class Meta:
        model = OrderPayment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(OrderPaymentForm, self).__init__(*args, **kwargs)
        self.fields.get('parent_payment').required = True
        self.fields.get('paid_amount').required = True
        # if self.data and self.data.get('payment_mode_name') != 'cash_payment':
        #     self.fields.get('reference_no').required = True
        # select queryset on the basis of user
    
    
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
