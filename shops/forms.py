from django import forms
from .models import ParentRetailerMapping, Shop, ShopType
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class ParentRetailerMappingForm(forms.ModelForm):
    class Meta:
        Model = ParentRetailerMapping
        fields = ('parent','retailer','status')

    def __init__(self, *args, **kwargs):
        super(ParentRetailerMappingForm, self).__init__(*args, **kwargs)
        shop_type_gf_sp = ShopType.objects.filter(shop_type__in=['sp','gf'])
        self.fields['parent'].queryset = Shop.objects.filter(shop_type__in=shop_type_gf_sp)
        shop_type_retailer= ShopType.objects.filter(shop_type='r')
        self.fields['retailer'].queryset = Shop.objects.filter(shop_type__in=shop_type_retailer)

    def clean(self):
        cleaned_data = super().clean()
        retailer = cleaned_data.get("retailer")
        parent_mapping = ParentRetailerMapping.objects.filter(retailer=retailer, status=True)
        if parent_mapping.exists():
            for parent in parent_mapping:
                parent.status=False
                parent.save()
        return cleaned_data
