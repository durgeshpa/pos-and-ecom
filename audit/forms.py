from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError

from accounts.middlewares import get_current_user
from accounts.models import User
from audit.models import AUDIT_DETAIL_STATUS_CHOICES, AUDIT_RUN_TYPE_CHOICES, AUDIT_DETAIL_STATE_CHOICES, \
    AuditTicketManual, AUDIT_TICKET_STATUS_CHOICES
from audit.views import get_existing_audit_for_product, get_existing_audit_for_bin
from products.models import Product
from shops.models import Shop
from wms.models import Bin

class AuditCreationForm(forms.ModelForm):
    warehouse_choices = Shop.objects.filter(shop_type__shop_type='sp')
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)
    bin = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Bin.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url='bin-autocomplete',
                                                 forward=('warehouse',)))
    sku = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url='sku-autocomplete',
                                                 forward=('warehouse',))
    )

    auditor = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.all(),
        widget=autocomplete.ModelSelect2(url='assigned-user-autocomplete', forward=('warehouse',)))

    def __init__(self, *args, **kwargs):
        super(AuditCreationForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            return
        self.fields['audit_run_type'].initial = AUDIT_RUN_TYPE_CHOICES.MANUAL

    def clean(self):
        data = self.cleaned_data
        if self.instance.id:
            if self.instance.state != AUDIT_DETAIL_STATE_CHOICES.CREATED:
                raise ValidationError('Audit update is not allowed once audit is initiated!!')
            return self.cleaned_data
        warehouse = data.get('warehouse')
        audit_run_type = data.get('audit_run_type')
        if warehouse is None:
            raise ValidationError('Please select Warehuse!!')
        if audit_run_type is None:
            raise ValidationError('Please select Audit Run Type!!')
        elif audit_run_type == 0:
            audit_level = data.get('audit_level')
            audit_bins = data.get('bin')
            audit_product = data.get('sku')
            auditor = data.get('auditor')
            if audit_level is None:
                raise ValidationError('Please select Audit Level!')
            elif audit_level == 0:
                if audit_bins.count() == 0:
                    raise ValidationError('Please select bins to audit!')
                for b in audit_bins:
                    existing_audits = get_existing_audit_for_bin(warehouse, b)
                    if existing_audits.count() > 0:
                        audit_ids = list(existing_audits.only('id').values_list('audit_no', flat=True))
                        raise ValidationError('Bin {} is already under audit {}!'
                                              .format(b, audit_ids))
            elif audit_level == 1:
                if audit_product.count() == 0:
                    raise ValidationError('Please select product to audit!')
                for s in audit_product:
                    existing_audits = get_existing_audit_for_product(warehouse, s)
                    if existing_audits.count() > 0:
                        audit_ids = list(existing_audits.only('id').values_list('audit_no', flat=True))
                        raise ValidationError('SKU {} is already under audit {}!'
                                              .format(s, audit_ids))
            if auditor is None:
                raise ValidationError('Please select an auditor!')

        elif audit_run_type == 2:
            audit_inventory_type = data.get('audit_inventory_type')
            if audit_inventory_type is None:
                raise ValidationError('Please select Audit Inventory Type!')
            is_historic = data.get('is_historic')
            if is_historic:
                audit_from = data.get('audit_from')
                if audit_from is None:
                    raise ValidationError('Please select a date to start audit from!')
            if AuditDetail.objects.filter(audit_run_type=audit_run_type,
                                          audit_inventory_type=audit_inventory_type,
                                          warehouse=warehouse,
                                          is_historic=is_historic).exists():
                raise ValidationError('An active automated audit already exists for this combination!!')

        return self.cleaned_data


class AuditTicketForm(forms.ModelForm):
    warehouse_choices = Shop.objects.filter(shop_type__shop_type='sp')
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)
    assigned_user = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.all(),
        widget=autocomplete.ModelSelect2(url='assigned-user-autocomplete',
                                         forward=('warehouse',)))

    def clean(self):
        data = self.cleaned_data
        if self.instance.warehouse != data['warehouse']:
            raise ValidationError('Warehouse cannot be changed of a ticket')

        if self.instance.status == AUDIT_TICKET_STATUS_CHOICES.CLOSED:
            raise ValidationError('Ticket cannot be updated once its closed')

    class Meta:
        model = AuditTicketManual
        fields = ('warehouse', 'status', 'assigned_user')


class WarehouseSelectionForm(forms.ModelForm):
    warehouse_choices = Shop.objects.filter(shop_type__shop_type='sp')
