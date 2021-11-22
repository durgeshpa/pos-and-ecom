import datetime
from django import forms
from dal import autocomplete
from django_select2.forms import Select2MultipleWidget, ModelSelect2Widget
from brand.models import Brand
from categories.models import Category
from .models import Banner , BannerPosition, BannerData
from shops.models import Shop
from products.models import Product
from addresses.models import Pincode, City

class BannerForm(forms.ModelForm):
    category = forms.ModelChoiceField(required=False,
        queryset=Category.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='category-autocomplete',
        )
     )
    sub_category = forms.ModelChoiceField(required=False,
        queryset=Category.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='sub-category-autocomplete',
        )
     )
    brand = forms.ModelChoiceField(required=False,
        queryset=Brand.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='banner-brand-autocomplete',
            forward=('category',)
        )
     )
    sub_brand = forms.ModelChoiceField(required=False,
        queryset=Brand.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='banner-sub-brand-autocomplete',
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

    class Media:
        js = ('admin/js/banner.js',)


    def __init__(self, *args, **kwargs):
        super(BannerForm, self).__init__(*args, **kwargs)
        self.fields['products'].help_text = '<br/>You can select multiple list of products.'
        self.fields['category'].widget.attrs['class'] = 'banner-select2'
        self.fields['sub_category'].widget.attrs['class'] = 'banner-select2'
        self.fields['brand'].widget.attrs['class'] = 'banner-select2'
        self.fields['sub_brand'].widget.attrs['class'] = 'banner-select2'
        self.fields['products'].widget.attrs['class'] = 'banner-select2'

class BannerPositionForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp',]),
        widget=autocomplete.ModelSelect2(url='banner-shop-autocomplete', ),
        required=False
    )
    buyer_shop = forms.ModelMultipleChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2Multiple(url='admin:retailer-shop-autocomplete', ),
        required=False
    )
    pincode = forms.ModelMultipleChoiceField(
        queryset=Pincode.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url='admin:pincode-autocomplete', ),
        required=False
    )
    city = forms.ModelMultipleChoiceField(
        queryset=City.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url='admin:city-autocomplete', ),
        required=False
    )

    class Meta:
        Model = BannerPosition
        fields = '__all__'


class BannerDataPosition(forms.ModelForm):
    banner_data = forms.ModelChoiceField(
        queryset=Banner.objects.all(),
        widget=autocomplete.ModelSelect2(url='banner-data-autocomplete',),
    )

    class Meta:
        Model = BannerData
        fields = '__all__'