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
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'


class POGenerationForm(forms.ModelForm):
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.filter(brand_parent__isnull=True,active_status='active'),
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
    delivery_term = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'cols': 33}),required=True)

    class Media:
        js = ('/static/admin/js/po_generation_form.js',)

    class Meta:
        model = Cart
        fields = ('brand', 'supplier_state','supplier_name', 'gf_shipping_address',
                  'gf_billing_address', 'po_validity_date', 'payment_term',
                  'delivery_term', 'cart_product_mapping_csv'
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
                if not row[0]:
                    raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | Product ID cannot be empty")

                try:
                    product = Product.objects.get(pk=row[0])
                except:
                    raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | "+VALIDATION_ERROR_MESSAGES[
                    'INVALID_PRODUCT_ID'])

                if not row[3] or not re.match("^[\d\,]*$", row[3]):
                    raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | "+VALIDATION_ERROR_MESSAGES[
                    'EMPTY']%("Case_Size"))

                if not row[4] or not re.match("^[\d\,]*$", row[4]):
                    raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | "+VALIDATION_ERROR_MESSAGES[
                    'EMPTY']%("No_of_cases"))

                if not row[5] or not re.match("^[1-9][0-9]{0,}(\.\d{0,2})?$", row[5]):
                    raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | "+VALIDATION_ERROR_MESSAGES[
                    'EMPTY_OR_NOT_VALID']%("MRP"))

                if not row[6] or not re.match("^[1-9][0-9]{0,}(\.\d{0,2})?$", row[6]):
                    raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | "+VALIDATION_ERROR_MESSAGES[
                    'EMPTY_OR_NOT_VALID']%("Gram_to_brand"))

        if 'po_validity_date' in self.cleaned_data and self.cleaned_data['po_validity_date'] < datetime.date.today():
            raise ValidationError(_("Po validity date cannot be in the past!"))

        return self.cleaned_data

    change_form_template = 'admin/gram_to_brand/cart/change_form.html'

class POGenerationAccountForm(forms.ModelForm):

    class Meta:
        model = Cart
        fields = ('brand', 'supplier_state','supplier_name', 'gf_shipping_address',
                  'gf_billing_address', 'po_validity_date', 'payment_term',
                  'delivery_term')

    class Media:
        js = ('/static/admin/js/po_generation_acc_form.js',)

    change_form_template = 'admin/gram_to_brand/acc-cart/change_form.html'

class CartProductMappingForm(forms.ModelForm):
    cart_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='vendor-product-autocomplete', forward=('supplier_name',))
    )
    mrp = forms.CharField(disabled=True, required=False)
    sku = forms.CharField(disabled=True, required=False)
    tax_percentage = forms.CharField(disabled=True, required=False)
    case_sizes = forms.CharField(disabled=True, required=False, label='case size')
    no_of_cases = forms.CharField(required=True)
    no_of_pieces = forms.CharField(required=False)
    sub_total = forms.CharField(disabled=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs and kwargs['instance'].pk:
            self.fields['mrp'].initial = kwargs['instance'].mrp
            self.fields['sku'].initial = kwargs['instance'].sku
            self.fields['no_of_cases'].initial = kwargs['instance'].no_of_cases
            self.fields['no_of_pieces'].initial = kwargs['instance'].no_of_pieces if kwargs['instance'].no_of_pieces else \
                int(kwargs['instance'].cart_product.product_inner_case_size)*int(kwargs['instance'].cart_product.product_case_size)*int(kwargs['instance'].number_of_cases)

    class Meta:
        model = CartProductMapping
        fields = ('cart','cart_product','mrp','sku','tax_percentage','case_sizes','no_of_cases','price','sub_total','no_of_pieces','vendor_product')
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
    product_mrp = forms.DecimalField()
    po_product_quantity = forms.IntegerField()
    po_product_price = forms.DecimalField()
    already_grned_product = forms.IntegerField()
    expiry_date = forms.DateField(required=False,widget=AdminDateWidget())
    best_before_year = forms.ChoiceField(choices=BEST_BEFORE_YEAR_CHOICE,)
    best_before_month = forms.ChoiceField(choices=BEST_BEFORE_MONTH_CHOICE,)

    class Meta:
        model = GRNOrderProductMapping
        fields = ('product', 'product_mrp', 'po_product_quantity','po_product_price','already_grned_product','product_invoice_price','manufacture_date',
                  'expiry_date','best_before_year','best_before_month','product_invoice_qty','delivered_qty','returned_qty')
        readonly_fields = ('product','product_mrp', 'po_product_quantity', 'po_product_price', 'already_grned_product')
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
                    'product_mrp': item.cart_product_mapping.filter(cart=ordered_cart).last().vendor_product.product_mrp if item.cart_product_mapping.filter(cart=ordered_cart).last().vendor_product else '-',
                    'po_product_quantity': item.cart_product_mapping.filter(cart=ordered_cart).last().qty,
                    'po_product_price':  item.cart_product_mapping.filter(cart=ordered_cart).last().vendor_product.product_price if item.cart_product_mapping.filter(cart=ordered_cart).last().vendor_product else item.cart_product_mapping.filter(cart=ordered_cart).last().price,
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
