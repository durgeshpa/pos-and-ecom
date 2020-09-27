from django import forms
from django.forms import ModelForm
from shops.models import Shop,ShopType
from .models import Order, Cart, CartProductMapping,OrderedProductMapping
from brand.models import Brand
from dal import autocomplete
from django_select2.forms import Select2MultipleWidget,ModelSelect2Widget
from addresses.models import State,Address
from brand.models import Vendor
from django.urls import reverse
from products.models import Product, ProductVendorMapping,ProductPrice
from django.core.exceptions import ValidationError
import datetime, csv, codecs, re

class CartProductMappingForm(forms.ModelForm):
    cart_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='gf-product-autocomplete', forward=('shop',))
    )

    gf_code = forms.CharField(disabled=True, required=False)
    ean_number = forms.CharField(disabled=True, required=False)
    taxes = forms.CharField(disabled=True, required=False)

    class Meta:
        model = CartProductMapping
        #search_fields=('cart_product',)
        fields= '__all__'
        exclude = ('qty',)

    def save(self, commit=True):
        # gf_code = self.cleaned_data.pop('gf_code')
        # ean_number = self.cleaned_data.pop('ean_number')
        # taxes = self.cleaned_data.pop('taxes')
        return super(CartProductMappingForm, self).save(commit=commit)

class OrderedProductMappingForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='ordered-product-autocomplete', forward=('order',))
    )
    batch_id = forms.CharField(disabled=True)

    class Meta:
        model = OrderedProductMapping
        #search_fields=('cart_product',)
        fields= '__all__'
        

class OrderForm(forms.ModelForm):
#
    class Meta:
        model= Order
        fields= '__all__'
#
    def __init__(self, exp = None, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        shop_type= ShopType.objects.filter(shop_type__in=['gf'])
        shops = Shop.objects.filter(shop_type__in=shop_type)
        self.fields["shop"].queryset = shops

class POGenerationForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='sp'),
        widget=autocomplete.ModelSelect2(url='my-shop-autocomplete',)
    )

    class Media:
        js = ('/static/admin/js/sp_po_generation_form.js',)

    def __init__(self, *args, **kwargs):
        super(POGenerationForm, self).__init__(*args, **kwargs)
        self.fields['shop'].label = "Recipient Warehouse"

    class Meta:
        model = Cart
        fields = ('shop','po_validity_date','payment_term','delivery_term')
