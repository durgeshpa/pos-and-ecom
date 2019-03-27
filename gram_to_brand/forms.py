import datetime
import csv
import codecs
import re
from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from dateutil.relativedelta import relativedelta
from django.contrib.admin.widgets import AdminDateWidget
from django.urls import reverse
from django.forms import ModelForm
from django.db.models import Sum

from dal import autocomplete
from django_select2.forms import Select2MultipleWidget, ModelSelect2Widget

from shops.models import Shop, ShopType
from .models import (
    Order, Cart, CartProductMapping, GRNOrder, GRNOrderProductMapping,
    BrandNote, PickList, PickListItems, OrderedProductReserved, Po_Message,
    BEST_BEFORE_MONTH_CHOICE, BEST_BEFORE_YEAR_CHOICE
)
from brand.models import Brand
from addresses.models import State, Address
from brand.models import Vendor
from products.models import Product, ProductVendorMapping


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'


class POGenerationForm(forms.ModelForm):
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.all(),
        widget=autocomplete.ModelSelect2(url='brand-autocomplete',)
    )
    supplier_state = forms.ModelChoiceField(
        queryset=State.objects.all(),
        widget=autocomplete.ModelSelect2(url='state-autocomplete',)
    )
    supplier_name = forms.ModelChoiceField(
        queryset=Vendor.objects.all(),
        widget=autocomplete.ModelSelect2(url='supplier-autocomplete',
                                         forward=('supplier_state', 'brand'))
    )
    gf_shipping_address = forms.ModelChoiceField(
        queryset=Address.objects.filter(shop_name__shop_type__shop_type='gf'),
        widget=autocomplete.ModelSelect2(
            url='shipping-address-autocomplete',
            forward=('supplier_name', 'supplier_state',)
        )
    )
    gf_billing_address = forms.ModelChoiceField(
        queryset=Address.objects.filter(shop_name__shop_type__shop_type='gf'),
        widget=autocomplete.ModelSelect2(
            url='billing-address-autocomplete',
            forward=('supplier_state',)
        )
    )

    class Media:
        pass
        js = ('/static/admin/js/po_generation_form.js',)

    class Meta:
        model = Cart
        fields = ('brand', 'supplier_state', 'gf_shipping_address',
                  'gf_billing_address', 'po_validity_date', 'payment_term',
                  'delivery_term', 'supplier_name', 'cart_product_mapping_csv'
                  )

    def __init__(self, *args, **kwargs):
        super(POGenerationForm, self).__init__(*args, **kwargs)
        self.fields['cart_product_mapping_csv'].help_text = self.instance.\
            products_sample_file

    def clean(self):
        if self.cleaned_data['cart_product_mapping_csv']:
            if not self.cleaned_data['cart_product_mapping_csv'].name[-4:] in ('.csv'):
                raise forms.ValidationError("Sorry! Only csv file accepted")
            reader = csv.reader(codecs.iterdecode(self.cleaned_data['cart_product_mapping_csv'], 'utf-8'))
            first_row = next(reader)
            for id,row in enumerate(reader):
                try:
                    product = Product.objects.get(pk=row[0])
                except:
                    raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | Product does not exist with this ID")
                if not row[0]:
                    raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | Product ID cannot be empty")
                #if not row[2] and not re.match("^\d+$", row[2]):
                #    raise ValidationError("Row["+str(id+1)+"] | "+first_row[2]+":"+row[2]+" | Case size should be integer and cannot be empty")
                if not product.product_case_size == row[3]:
                    raise ValidationError("Row["+str(id+1)+"] | "+first_row[3]+":"+row[3]+" | Case size does not matched with original product's case size")
                #if row[3] and not re.match("^\d+$", row[3]):
                #    raise ValidationError("Row["+str(id+1)+"] | "+first_row[3]+":"+row[3]+" | No. of cases should be integer value")
                vendor_product = ProductVendorMapping.objects.filter(vendor=self.cleaned_data['supplier_name'], product=product).order_by('product','-created_at').distinct('product')
                for p in vendor_product:
                    if not p.product_price == float(row[6]):
                        raise ValidationError("Row["+str(id+1)+"] | "+first_row[6]+":"+row[6]+" | Price does not matched with original product's brand to gram price")
            return self.cleaned_data

        # date = self.cleaned_data['po_validity_date']
        # if date < datetime.date.today():
        #     raise forms.ValidationError("Po validity date cannot be in the past!")
        return self.cleaned_data


class CartProductMappingForm(forms.ModelForm):

    cart_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='vendor-product-autocomplete', forward=('supplier_name',))
    )
    tax_percentage = forms.CharField(disabled=True, required=False)
    case_size = forms.CharField(disabled=True, required=False)
    no_of_case = forms.CharField(disabled=True, required=False)
    # total_price = forms.DecimalField(decimal_places=2,)

    class Meta:
        model = CartProductMapping
        fields = ('cart_product','tax_percentage','case_size','no_of_case','price',)
        search_fields=('cart_product',)
        exclude = ('qty',)

class GRNOrderForm(forms.ModelForm):
    class Meta:
        model = GRNOrder
        fields = ('order','invoice_no')
        readonly_fields = ('order')

class GRNOrderProductForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='product-autocomplete',forward=('order',))
     )
    po_product_quantity = forms.IntegerField()
    po_product_price = forms.DecimalField()
    already_grned_product = forms.IntegerField()
    expiry_date = forms.DateField(required=False,widget=AdminDateWidget())
    best_before_year = forms.ChoiceField(choices=BEST_BEFORE_YEAR_CHOICE,)
    best_before_month = forms.ChoiceField(choices=BEST_BEFORE_MONTH_CHOICE,)

    class Meta:
        model = GRNOrderProductMapping
        fields = ('product','po_product_quantity','po_product_price','already_grned_product','product_invoice_price','manufacture_date',
                  'expiry_date','best_before_year','best_before_month','product_invoice_qty','delivered_qty','returned_qty')
        readonly_fields = ('product', 'po_product_quantity', 'po_product_price', 'already_grned_product')
        autocomplete_fields = ('product',)

    class Media:
        #css = {'all': ('pretty.css',)}
        js = ('/static/admin/js/grn_form.js',)

    def __init__(self, *args, **kwargs):
        super(GRNOrderProductForm, self).__init__(*args, **kwargs)

    def fields_required(self, fields):
        """Used for conditionally marking fields as required."""
        for field in fields:
            if not self.cleaned_data.get(field, ''):
                msg = forms.ValidationError("This field is required.")
                self.add_error(field, msg)

    def clean(self):
        super(GRNOrderProductForm, self).clean()
        manufacture_date = self.cleaned_data.get('manufacture_date')
        expiry_date = self.cleaned_data.get('expiry_date')
        if self.cleaned_data.get('product_invoice_qty') >0:
            self.fields_required(['manufacture_date'])
            if self.cleaned_data.get('expiry_date') and self.cleaned_data.get('expiry_date') > self.cleaned_data.get('manufacture_date'):
                pass
            elif int(self.cleaned_data.get('best_before_year')) or int(self.cleaned_data.get('best_before_month')):
                expiry_date = self.cleaned_data.get('manufacture_date') + relativedelta(years=int(self.cleaned_data.get('best_before_year')), months=int(self.cleaned_data.get('best_before_month')))
                self.cleaned_data['expiry_date'] = expiry_date
            else:
                raise ValidationError(_('Please enter either expiry date greater than manufactured date or best before'))
        return self.cleaned_data


class GRNOrderProductFormset(forms.models.BaseInlineFormSet):
    model = GRNOrderProductMapping
    def __init__(self, *args, **kwargs):
        super(GRNOrderProductFormset, self).__init__(*args, **kwargs)
        if hasattr(self, 'order') and self.order:
            ordered_cart = self.order
            initial = []
            for item in ordered_cart.products.all():
                already_grn = item.product_grn_order_product.filter(grn_order__order__ordered_cart=ordered_cart).aggregate(Sum('delivered_qty'))
                initial.append({
                    'product' : item,
                    'po_product_quantity': item.cart_product_mapping.last().qty,
                    'po_product_price': item.cart_product_mapping.last().price,
                    'already_grned_product': 0 if already_grn.get('delivered_qty__sum') == None else already_grn.get('delivered_qty__sum'),
                    })
            self.extra = len(initial)
            self.initial= initial

    def clean(self):
        super(GRNOrderProductFormset, self).clean()
        count=0
        for form in self:
            if form.cleaned_data.get('product_invoice_qty'):
                count+=1
        if count <1:
            raise ValidationError("Please fill the product invoice quantity of at least one product.")
