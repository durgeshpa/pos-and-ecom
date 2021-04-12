import datetime
import csv
import codecs
import re

from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from dateutil.relativedelta import relativedelta
from django.contrib.admin.widgets import AdminDateWidget
from django.db.models import Sum

from brand.models import Brand, Vendor
from addresses.models import State, Address
from products.models import Product, ProductVendorMapping, ParentProduct
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from .models import (Order, Cart, CartProductMapping, GRNOrder, GRNOrderProductMapping, BEST_BEFORE_MONTH_CHOICE,
                     BEST_BEFORE_YEAR_CHOICE, Document)


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'


class POGenerationForm(forms.ModelForm):
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.filter(active_status='active'),
        widget=autocomplete.ModelSelect2(url='brand-autocomplete', )
    )
    supplier_state = forms.ModelChoiceField(
        queryset=State.objects.all(),
        widget=autocomplete.ModelSelect2(url='state-autocomplete', )
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
    delivery_term = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'cols': 33}), required=True)

    class Media:
        js = (
            '/ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            '/static/admin/js/po_generation_form.js',
        )

    class Meta:
        model = Cart
        fields = ('brand', 'supplier_state', 'supplier_name', 'gf_shipping_address', 'gf_billing_address',
                  'po_validity_date', 'payment_term', 'delivery_term', 'cart_product_mapping_csv', 'po_status')

    def __init__(self, *args, **kwargs):
        super(POGenerationForm, self).__init__(*args, **kwargs)
        self.fields['cart_product_mapping_csv'].help_text = self.instance.products_sample_file

    def clean_cart_product_mapping_csv(self):
        if 'cart_product_mapping_csv' in self.changed_data and self.cleaned_data['cart_product_mapping_csv']:
            if self.cleaned_data['cart_product_mapping_csv'].name[-4:] != '.csv':
                raise forms.ValidationError("Sorry! Only csv file accepted")
            reader = csv.reader(
                codecs.iterdecode(self.cleaned_data['cart_product_mapping_csv'], 'utf-8', errors='ignore'))
            titles = next(reader)
            for row_id, row in enumerate(reader):
                # Input Format Validation
                if not row[0]:
                    self.error_csv(row_id, titles[0], row[0], VALIDATION_ERROR_MESSAGES['EMPTY'] % "Parent Product ID")
                if not row[2]:
                    self.error_csv(row_id, titles[0], row[0], VALIDATION_ERROR_MESSAGES['EMPTY'] % "Product ID")
                if not row[7] or not re.match("^[1-9][0-9]{0,}(\.\d{0,2})?$", row[7]):
                    self.error_csv(row_id, titles[0], row[0], VALIDATION_ERROR_MESSAGES['EMPTY_OR_NOT_VALID'] % "MRP")
                if not row[5] or not re.match("^[\d\,]*$", row[5]):
                    self.error_csv(row_id, titles[0], row[0],
                                   VALIDATION_ERROR_MESSAGES['EMPTY_OR_NOT_VALID'] % "Case Size")
                if not row[6] or not re.match("^[\d\,]*$", row[6]):
                    self.error_csv(row_id, titles[0], row[0],
                                   VALIDATION_ERROR_MESSAGES['EMPTY_OR_NOT_VALID'] % "No Of Cases")
                if row[8].lower() not in ["per piece", "per pack"]:
                    self.error_csv(row_id, titles[0], row[0],
                                   VALIDATION_ERROR_MESSAGES['EMPTY_OR_NOT_VALID_STRING'] % "Gram To Brand Price Unit")
                if not row[9] or not re.match("[0-9]*([1-9][0-9]*(\.[0-9]*)?|\.[0-9]*[1-9][0-9]*)", row[9]):
                    self.error_csv(row_id, titles[0], row[0],
                                   VALIDATION_ERROR_MESSAGES['EMPTY_OR_NOT_VALID'] % "Brand To Gram Price")
                # Input Value Validation
                try:
                    parent_product = ParentProduct.objects.get(parent_id=row[0])
                except ObjectDoesNotExist:
                    self.error_csv(row_id, titles[0], row[0], VALIDATION_ERROR_MESSAGES['INVALID_PARENT_ID'])
                try:
                    product = Product.objects.get(pk=row[2], parent_product=parent_product)
                except ObjectDoesNotExist:
                    self.error_csv(row_id, titles[2], row[2], VALIDATION_ERROR_MESSAGES['INVALID_PRODUCT_ID'])
                if product.status == 'deactivated':
                    self.error_csv(row_id, titles[4], row[4], VALIDATION_ERROR_MESSAGES['DEACTIVATE'] % "Product")
                if float(product.product_mrp) != float(row[7]):
                    self.error_csv(row_id, titles[7], row[7], VALIDATION_ERROR_MESSAGES['NOT_VALID'] % "MRP")
                vendor = ProductVendorMapping.objects.filter(product=row[2], vendor_id=self.data['supplier_name'],
                                                             status=True).last()
                if not vendor:
                    self.error_csv(row_id, titles[4], row[4], VALIDATION_ERROR_MESSAGES['VENDOR_NOT_MAPPED'] % "Vendor")
                if vendor.case_size != int(row[5]):
                    self.error_csv(row_id, titles[5], row[5], VALIDATION_ERROR_MESSAGES['NOT_VALID'] % "Case Size")

        return self.cleaned_data['cart_product_mapping_csv']

    def clean_po_validity_date(self):
        if self.cleaned_data['po_validity_date'] < datetime.date.today():
            raise ValidationError(_("Po validity date cannot be in the past!"))
        return self.cleaned_data['po_validity_date']

    def error_csv(self, row_id, title, value, error):
        """
            Raise Validation Error In Product Upload Csv
        """
        raise ValidationError("Row {}  -  {}: {}  -  {}".format(str(row_id + 1), title, value, error))

    change_form_template = 'admin/gram_to_brand/cart/change_form.html'


class POGenerationAccountForm(forms.ModelForm):
    class Meta:
        model = Cart
        fields = ('brand', 'supplier_state', 'supplier_name', 'gf_shipping_address', 'gf_billing_address',
                  'po_validity_date', 'payment_term', 'delivery_term', 'po_status')

    class Media:
        js = ('/static/admin/js/po_generation_acc_form.js',)

    change_form_template = 'admin/gram_to_brand/acc-cart/change_form.html'


class CartProductMappingForm(forms.ModelForm):
    cart_parent_product = forms.ModelChoiceField(
        queryset=ParentProduct.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='parent-product-autocomplete',
            attrs={
                "onChange": 'getLastGrnProductDetails(this)'
            },
            forward=['supplier_name']
        )
    )
    cart_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='vendor-product-autocomplete',
            attrs={
                "onChange": 'getProductVendorPriceDetails(this)'
            },
            forward=['supplier_name', 'cart_parent_product']
        ),
        label='CART CHILD PRODUCT'
    )
    mrp = forms.CharField(disabled=True, required=False)
    sku = forms.CharField(disabled=True, required=False)
    tax_percentage = forms.CharField(disabled=True, required=False)
    case_sizes = forms.CharField(disabled=True, required=False, label='case size')
    no_of_cases = forms.CharField(max_length=64, widget=forms.TextInput(attrs={'style': 'max-width: 8em'}),
                                  required=True)
    no_of_pieces = forms.CharField(max_length=64, widget=forms.TextInput(attrs={'style': 'max-width: 8em'}),
                                   required=False)
    brand_to_gram_price_units = forms.CharField(disabled=True, required=False)
    sub_total = forms.CharField(disabled=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs and kwargs['instance'].pk:
            self.fields['mrp'].initial = kwargs['instance'].mrp
            self.fields['sku'].initial = kwargs['instance'].sku
            self.fields['no_of_cases'].initial = kwargs['instance'].no_of_cases
            self.fields['brand_to_gram_price_units'].initial = kwargs['instance'].brand_to_gram_price_units
            self.fields['no_of_pieces'].initial = kwargs['instance'].no_of_pieces if kwargs[
                'instance'].no_of_pieces else \
                int(kwargs['instance'].cart_product.product_inner_case_size) * int(
                    kwargs['instance'].cart_product.product_case_size) * int(kwargs['instance'].number_of_cases)

    class Meta:
        model = CartProductMapping
        fields = ('cart', 'cart_parent_product', 'cart_product', 'mrp', 'sku', 'tax_percentage', 'case_sizes',
                  'no_of_cases', 'price', 'sub_total', 'no_of_pieces', 'vendor_product', 'brand_to_gram_price_units')
        search_fields = ('cart_product',)
        exclude = ('qty',)

    class Media:
        js = (
            '/ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            'admin/js/po_generation_form.js'
        )


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
    already_returned_product = forms.IntegerField()
    expiry_date = forms.DateField(required=False, widget=AdminDateWidget())
    best_before_year = forms.ChoiceField(choices=BEST_BEFORE_YEAR_CHOICE,)
    best_before_month = forms.ChoiceField(choices=BEST_BEFORE_MONTH_CHOICE,)

    class Meta:
        model = GRNOrderProductMapping
        fields = ('product', 'product_mrp', 'po_product_quantity','po_product_price','already_grned_product','already_returned_product','product_invoice_price','manufacture_date',
                  'expiry_date','best_before_year','best_before_month','product_invoice_qty','delivered_qty','returned_qty', 'barcode_id',)
        readonly_fields = ('product','product_mrp', 'po_product_quantity', 'po_product_price', 'already_grned_product', 'already_returned_product', 'barcode_id',)
        autocomplete_fields = ('product',)


    class Media:
        #css = {'all': ('pretty.css',)}
        js = ('/static/admin/js/grn_form.js', )

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
        if self.cleaned_data.get('product', None):
            if self.cleaned_data.get('product_invoice_qty') != 0:

                if self.cleaned_data.get('expiry_date') is None:

                    if not (int(self.cleaned_data.get('best_before_year')) or int(
                            self.cleaned_data.get('best_before_month'))):
                        raise ValidationError(_('Expiry date is required | Format should be YYYY-MM-DD'))

                if self.cleaned_data.get('manufacture_date') is None:
                    raise ValidationError(_('Manufacture date is required | Format should be YYYY-MM-DD'))

            manufacture_date = self.cleaned_data.get('manufacture_date')
            expiry_date = self.cleaned_data.get('expiry_date')

            if self.cleaned_data.get('product_invoice_qty') is None or self.cleaned_data.get('product_invoice_qty') >0:
                self.fields_required(['manufacture_date'])
                if self.cleaned_data.get('manufacture_date') and self.cleaned_data.get('manufacture_date') > datetime.date.today():
                    raise ValidationError(_('Manufacture Date cannot be in future'))
                if self.cleaned_data.get('expiry_date') and self.cleaned_data.get('expiry_date') < datetime.date.today():
                    raise ValidationError(_('Expiry Date cannot be in the past'))
                elif self.cleaned_data.get('expiry_date') and self.cleaned_data.get('expiry_date') >= datetime.date.today():
                    pass
                elif int(self.cleaned_data.get('best_before_year')) or int(self.cleaned_data.get('best_before_month')):
                    expiry_date = self.cleaned_data.get('manufacture_date') + relativedelta(years=int(self.cleaned_data.get('best_before_year')), months=int(self.cleaned_data.get('best_before_month')))
                    if expiry_date < datetime.date.today():
                        raise ValidationError(_('Manufacture date + Best before cannot be in the past'))
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
            for item in ordered_cart.products.order_by('product_name'):
                already_grn = item.product_grn_order_product.filter(grn_order__order__ordered_cart=ordered_cart).aggregate(Sum('delivered_qty'))
                already_return = item.product_grn_order_product.filter(grn_order__order__ordered_cart=ordered_cart).aggregate(Sum('returned_qty'))
                def price(self):
                    if item.cart_product_mapping.filter(cart=ordered_cart).last().vendor_product.product_price:
                        po_product_price = item.cart_product_mapping.filter(cart=ordered_cart).last().vendor_product.product_price if item.cart_product_mapping.filter(cart=ordered_cart).last().vendor_product else item.cart_product_mapping.filter(cart=ordered_cart).last().price
                        return po_product_price
                    else :
                        po_product_price =  item.cart_product_mapping.filter(cart=ordered_cart).last().vendor_product.product_price_pack if item.cart_product_mapping.filter(cart=ordered_cart).last().vendor_product else item.cart_product_mapping.filter(cart=ordered_cart).last().price
                        return po_product_price
                initial.append({
                    'product' : item,
                    'product_mrp': item.cart_product_mapping.filter(cart=ordered_cart).last().vendor_product.product_mrp if item.cart_product_mapping.filter(cart=ordered_cart).last().vendor_product else '-',
                    'po_product_quantity': item.cart_product_mapping.filter(cart=ordered_cart).last().qty,
                    'po_product_price':price(self),
                    'already_grned_product': 0 if already_grn.get('delivered_qty__sum') == None else already_grn.get('delivered_qty__sum'),
                    'already_returned_product': 0 if already_return.get('returned_qty__sum') == None else already_return.get('returned_qty__sum'),
                    })
            self.extra = len(initial)
            self.initial= initial

    def clean(self):
        super(GRNOrderProductFormset, self).clean()
        products_dict = {}
        count=0
        for form in self.forms:
            if form.cleaned_data.get('product_invoice_qty'):
                count += 1
            if form.cleaned_data.get('delivered_qty') is None:
                raise ValidationError('This field is required')
            if form.cleaned_data.get('returned_qty') is None:
                raise ValidationError('This field is required')

            if form.instance.product.id in products_dict:
                product_data = products_dict[form.instance.product.id]
                product_data['total_items'] = product_data['total_items'] + (form.cleaned_data.get('delivered_qty') + form.cleaned_data.get('returned_qty'))
                product_data['product_invoice_qty'] = product_data['product_invoice_qty'] + form.cleaned_data.get('product_invoice_qty')
            else:
                products_data = {'total_items':(form.cleaned_data.get('delivered_qty') + form.cleaned_data.get('returned_qty')),
                                 'diff':(form.instance.po_product_quantity - (form.instance.already_grned_product + form.instance.already_returned_product)),
                                 'product_invoice_qty':form.cleaned_data.get('product_invoice_qty'),
                                 'product_name':form.cleaned_data.get('product')}
                products_dict[form.instance.product.id] = products_data

        if count <1:
            raise ValidationError("Please fill the product invoice quantity of at least one product.")

        for k,v in products_dict.items():
            if v.get('product_invoice_qty') <= v.get('diff'):
                if v.get('product_invoice_qty') < v.get('total_items'):
                    raise ValidationError(_('Product invoice quantity cannot be less than the sum of delivered quantity and returned quantity for %s') % v.get('product_name'))
                elif v.get('total_items') < v.get('product_invoice_qty'):
                    raise ValidationError(_('Product invoice quantity must be equal to the sum of delivered quantity and returned quantity for %s') % v.get('product_name'))
            else:
                raise ValidationError(_('Product invoice quantity cannot be greater than the difference of PO product quantity and (already_grned_product + already_returned_product) for %s') % v.get('product_name'))


class DocumentForm(forms.ModelForm):
    document_image = forms.FileField(required=True)
    document_number = forms.CharField(required=True)


class DocumentFormset(forms.models.BaseInlineFormSet):
    model = Document

    def clean(self):
        super(DocumentFormset, self).clean()
        for form in self:
            if form.cleaned_data.get('document_number') is None:
                raise ValidationError("Document Number is Required.")

            if form.cleaned_data.get('document_image') is None:
                raise ValidationError("Document Image is Required.")
