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
from payments.models import ShipmentPayment#, ShipmentPaymentApproval

User = get_user_model()

class ShipmentPaymentForm(forms.ModelForm):

    class Meta:
        model = ShipmentPayment
        fields = "__all__"

# class ShipmentPaymentApprovalForm(forms.ModelForm):

#     class Meta:
#         model = ShipmentPaymentApproval
#         fields = "__all__"
