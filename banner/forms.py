import datetime
from django import forms
from dal import autocomplete
from django_select2.forms import Select2MultipleWidget, ModelSelect2Widget
from brand.models import Brand
from categories.models import Category
from .models import Banner

from products.models import Product

class BannerForm(forms.ModelForm):
    category = forms.ModelChoiceField(required=False,
        queryset=Category.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='category-autocomplete',
        )
     )
    brand = forms.ModelChoiceField(required=False,
        queryset=Brand.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='banner-brand-autocomplete',
            forward=('category',)
        )
     )
    products = forms.ModelMultipleChoiceField(required=False,
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(
            url='banner-product-autocomplete',
            forward=('brand',)
        )
     )

    class Meta:
        model = Banner
        fields = ('__all__')


    def __init__(self, *args, **kwargs):
        super(BannerForm, self).__init__(*args, **kwargs)
        self.fields['products'].help_text = '<br/>You can select multiple list of products.'

    # def clean(self):
    #
    #     products = self.cleaned_data.get('products')
    #     banner_type = self.cleaned_data.get('banner_type')
    #     if banner_type == 'product':
    #         if products in banner.product_set.all():
    #             raise ValidationError("dsffdsew")
    #     return self.cleaned_data
