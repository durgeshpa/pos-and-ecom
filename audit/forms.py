from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError

from accounts.middlewares import get_current_user
from audit.models import AuditDetail, AUDIT_DETAIL_STATUS_CHOICES
from shops.models import Shop


class AuditCreationForm(forms.ModelForm):
    warehouse_choices = Shop.objects.filter(shop_type__shop_type='sp')
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    def clean(self):
        data = self.cleaned_data
        if AuditDetail.objects.filter(audit_type=data['audit_type'],
                                      audit_inventory_type=data['audit_inventory_type'],
                                      warehouse=data['warehouse'],
                                      status=data['status']).exists():
            raise ValidationError('An audit already exists for this combination!!')