from django import forms
from django.forms import ModelForm
from shops.models import Shop,ShopType
from .models import (Order,Cart,CartProductMapping,GRNOrder,GRNOrderProductMapping,OrderItem,BrandNote,PickList,PickListItems,
                     OrderedProductReserved,Po_Message)
from brand.models import Brand
from dal import autocomplete
from django_select2.forms import Select2MultipleWidget,ModelSelect2Widget
from addresses.models import State,Address
from brand.models import Vendor
from django.urls import reverse
from products.models import Product, ProductVendorMapping
from django.core.exceptions import ValidationError
import datetime, csv, codecs, re


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
        widget=autocomplete.ModelSelect2(url='supplier-autocomplete',forward=('supplier_state','brand'))
    )
    gf_shipping_address = forms.ModelChoiceField(
        queryset=Address.objects.filter(shop_name__shop_type__shop_type='gf'),
        widget=autocomplete.ModelSelect2(url='shipping-address-autocomplete', forward=('supplier_name','supplier_state',))
    )
    gf_billing_address = forms.ModelChoiceField(
        queryset=Address.objects.filter(shop_name__shop_type__shop_type='gf'),
        widget=autocomplete.ModelSelect2(url='billing-address-autocomplete', forward=('supplier_state',))
    )

    class Media:
        pass
        js = ('/static/admin/js/po_generation_form.js',)


    class Meta:
        model = Cart
        fields = ('brand','supplier_state','gf_shipping_address','gf_billing_address','po_validity_date','payment_term','delivery_term','supplier_name','cart_product_mapping_csv')

    def __init__(self, *args, **kwargs):
        super(POGenerationForm, self).__init__(*args, **kwargs)
        self.fields['cart_product_mapping_csv'].help_text = self.instance.products_sample_file

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
                if not product.product_case_size == row[2]:
                    raise ValidationError("Row["+str(id+1)+"] | "+first_row[2]+":"+row[2]+" | Case size does not matched with original product's case size")
                #if row[3] and not re.match("^\d+$", row[3]):
                #    raise ValidationError("Row["+str(id+1)+"] | "+first_row[3]+":"+row[3]+" | No. of cases should be integer value")
                vendor_product = ProductVendorMapping.objects.filter(vendor=self.cleaned_data['supplier_name'], product=product).order_by('product','-created_at').distinct('product')
                for p in vendor_product:
                    if not p.product_price == float(row[5]):
                        raise ValidationError("Row["+str(id+1)+"] | "+first_row[5]+":"+row[5]+" | Price does not matched with original product's brand to gram price")
            return self.cleaned_data

        date = self.cleaned_data['po_validity_date']
        if date < datetime.date.today():
            raise forms.ValidationError("Po validity date cannot be in the past!")
        return self.cleaned_data


class CartProductMappingForm(forms.ModelForm):

    cart_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='vendor-product-autocomplete', forward=('supplier_name',))
    )

    class Meta:
        model = CartProductMapping
        fields = ('cart_product','inner_case_size','case_size', 'number_of_cases','scheme','price','total_price',)
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

    class Meta:
        model = GRNOrderProductMapping
        fields = ('product','po_product_quantity','po_product_price','already_grned_product','product_invoice_price','manufacture_date','expiry_date','product_invoice_qty','available_qty','delivered_qty','returned_qty')
        readonly_fields = ('product')
        autocomplete_fields = ('product',)


    class Media:
        #css = {'all': ('pretty.css',)}
        js = ('/static/admin/js/grn_form.js',)

class GRNOrderProductFormset(forms.models.BaseInlineFormSet):
    model = GRNOrderProductMapping

    def __init__(self, *args, **kwargs):
        super(GRNOrderProductFormset, self).__init__(*args, **kwargs)
        if hasattr(self, 'order') and self.order:
            order = self.order
            initial = []
            for item in order.order_order_item.all():
                already_grn = 0
                for pre_grn in item.ordered_product.product_grn_order_product.filter(grn_order__order=order):
                    already_grn += pre_grn.delivered_qty
                initial.append({
                    'product' : item.ordered_product,
                    'po_product_quantity': item.ordered_qty,
                    'po_product_price': item.ordered_price,
                    'already_grned_product': already_grn,
                    })
            self.initial= initial
