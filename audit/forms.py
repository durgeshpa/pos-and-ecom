from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError

from accounts.middlewares import get_current_user
from accounts.models import User
from audit.models import AuditDetail, AUDIT_DETAIL_STATUS_CHOICES
from products.models import Product
from shops.models import Shop
from wms.models import Bin


class AuditCreationForm(forms.ModelForm):
    warehouse_choices = Shop.objects.filter(shop_type__shop_type='sp')
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)
    bin = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Bin.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url='bin-autocomplete')
    )
    sku = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url='sku-autocomplete')
    )

    auditor = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.all(),
        widget=autocomplete.ModelSelect2(url='assigned-user-autocomplete')
    )

    def clean(self):
        data = self.cleaned_data
        audit_type = data.get('audit_type')
        if audit_type is None:
            raise ValidationError('Please select Audit Type!!')
        elif audit_type == 0:
            audit_level = data.get('audit_level')
            audit_bins = data.get('bin')
            audit_product = data.get('sku')
            auditor = data.get('auditor')
            if audit_level is None:
                raise ValidationError('Please select Audit Level!')
            elif audit_level == 0:
                if audit_bins.count() == 0:
                    raise ValidationError('Please select bins to audit!')
            elif audit_level == 1:
                if audit_product.count() == 0:
                    raise ValidationError('Please select product to audit!')
            if auditor is None:
                raise ValidationError('Please select an auditor!')
        elif audit_type == 2:
            audit_inventory_type = data.get('audit_inventory_type')
            if audit_inventory_type is None:
                raise ValidationError('Please select Audit Inventory Type!')
            if AuditDetail.objects.filter(audit_type=audit_type,
                                          audit_inventory_type=audit_inventory_type,
                                          warehouse=data['warehouse'],
                                          status=data['status']).exists():
                raise ValidationError('An active automated audit already exists for this combination!!')
        return self.cleaned_data
