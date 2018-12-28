from django import forms
from django.forms import ModelForm
from shops.models import Shop,ShopType
from .models import Order, Cart, CartProductMapping
from brand.models import Brand
from dal import autocomplete
from django_select2.forms import Select2MultipleWidget,ModelSelect2Widget
from addresses.models import State,Address
from brand.models import Vendor
from django.urls import reverse
from products.models import Product, ProductVendorMapping
from django.core.exceptions import ValidationError
import datetime, csv, codecs, re


class CartProductMappingForm(forms.ModelForm):

    cart_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='gf-product-autocomplete', forward=('gram_factory',))
    )

    class Meta:
        model = CartProductMapping
        fields = ('cart_product','case_size', 'number_of_cases','scheme','price','total_price',)
        search_fields=('cart_product',)
        exclude = ('qty',)

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
    state = forms.ModelChoiceField(
        queryset=State.objects.all(),
        widget=autocomplete.ModelSelect2(url='state-autocomplete',)
    )
    gram_factory = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='gf'),
        widget=autocomplete.ModelSelect2(url='gf-shop-autocomplete', forward=('state',))
    )

    class Media:
        js = ('/static/admin/js/sp_po_generation_form.js',)

    class Meta:
        model = Cart
        fields = ('state','gram_factory','po_validity_date','payment_term','delivery_term')

