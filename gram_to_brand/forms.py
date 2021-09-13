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
from shops.models import Shop, ParentRetailerMapping
from wms.models import WarehouseAssortment
from .models import (Order, Cart, CartProductMapping, GRNOrder, GRNOrderProductMapping, BEST_BEFORE_MONTH_CHOICE,
                     BEST_BEFORE_YEAR_CHOICE, Document, VendorShopMapping)


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'


class POGenerationForm(forms.ModelForm):
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.filter(status=True),
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
        """
            Validate products data to be uploaded in cart
        """
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
        """
            Validate po validity date
        """
        if self.cleaned_data['po_validity_date'] < datetime.date.today():
            raise ValidationError(_("Po validity date cannot be in the past!"))
        return self.cleaned_data['po_validity_date']

    def error_csv(self, row_id, title, value, error):
        """
            Raise Validation Error In Product Upload Csv
        """
        raise ValidationError("Row {}  -  {}: {}  -  {}".format(str(row_id + 1), title, value, error))



class POGenerationAccountForm(forms.ModelForm):
    brand = forms.ModelChoiceField(disabled=True,
        queryset=Brand.objects.filter(status=True),
        widget=autocomplete.ModelSelect2(url='brand-autocomplete', )
    )
    supplier_state = forms.ModelChoiceField(disabled=True,
        queryset=State.objects.all(),
        widget=autocomplete.ModelSelect2(url='state-autocomplete', )
    )
    supplier_name = forms.ModelChoiceField(disabled=True,
        queryset=Vendor.objects.all(),
        widget=autocomplete.ModelSelect2(url='supplier-autocomplete',
                                         forward=('supplier_state', 'brand'))
    )
    gf_shipping_address = forms.ModelChoiceField(disabled=True,
        queryset=Address.objects.filter(shop_name__shop_type__shop_type='gf'),
        widget=autocomplete.ModelSelect2(
            url='shipping-address-autocomplete',
            forward=('supplier_name', 'supplier_state',)
        )
    )
    gf_billing_address = forms.ModelChoiceField(disabled=True,
        queryset=Address.objects.filter(shop_name__shop_type__shop_type='gf'),
        widget=autocomplete.ModelSelect2(
            url='billing-address-autocomplete',
            forward=('supplier_state',)
        )
    )
    delivery_term = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'cols': 33}), required=True)
    class Meta:
        model = Cart
        fields = ('brand', 'supplier_state', 'supplier_name', 'gf_shipping_address', 'gf_billing_address',
                  'po_validity_date', 'payment_term', 'delivery_term', 'po_status', 'cart_product_mapping_csv')

    class Media:
        js = ('/static/admin/js/po_generation_form.js',)

    change_form_template = 'admin/gram_to_brand/acc-cart/change_form.html'


    def __init__(self, *args, **kwargs):
        super(POGenerationAccountForm, self).__init__(*args, **kwargs)
        self.fields['cart_product_mapping_csv'].help_text = self.instance.products_sample_file

    def clean_cart_product_mapping_csv(self):
        """
            Validate products data to be uploaded in cart
        """
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
                # if product.status == 'deactivated':
                #     self.error_csv(row_id, titles[4], row[4], VALIDATION_ERROR_MESSAGES['DEACTIVATE'] % "Product")
                if float(product.product_mrp) != float(row[7]):
                    self.error_csv(row_id, titles[7], row[7], VALIDATION_ERROR_MESSAGES['NOT_VALID'] % "MRP")
                vendor = ProductVendorMapping.objects.filter(product=row[2], vendor_id=self.initial['supplier_name'],
                                                             status=True).last()
                if not vendor:
                    self.error_csv(row_id, titles[4], row[4], VALIDATION_ERROR_MESSAGES['VENDOR_NOT_MAPPED'] % "Vendor")
                if vendor.case_size != int(row[5]):
                    self.error_csv(row_id, titles[5], row[5], VALIDATION_ERROR_MESSAGES['NOT_VALID'] % "Case Size")

        return self.cleaned_data['cart_product_mapping_csv']


    def error_csv(self, row_id, title, value, error):
        """
            Raise Validation Error In Product Upload Csv
        """
        raise ValidationError("Row {}  -  {}: {}  -  {}".format(str(row_id + 1), title, value, error))

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
        fields = ('order', 'invoice_no')
        readonly_fields = ('order')


class GRNOrderProductForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='product-autocomplete', forward=('order',))
    )
    product_mrp = forms.DecimalField()
    po_product_quantity = forms.IntegerField()
    po_product_price = forms.DecimalField()
    already_grned_product = forms.IntegerField()
    already_returned_product = forms.IntegerField()
    expiry_date = forms.DateField(required=False, widget=AdminDateWidget())
    best_before_year = forms.ChoiceField(choices=BEST_BEFORE_YEAR_CHOICE, )
    best_before_month = forms.ChoiceField(choices=BEST_BEFORE_MONTH_CHOICE, )
    zone = forms.CharField(required=False)

    class Meta:
        model = GRNOrderProductMapping
        fields = ('product', 'product_mrp', 'po_product_quantity', 'po_product_price', 'already_grned_product',
                  'already_returned_product', 'product_invoice_price', 'manufacture_date', 'expiry_date',
                  'best_before_year', 'best_before_month', 'product_invoice_qty', 'delivered_qty', 'returned_qty',
                  'barcode_id', 'zone',)
        readonly_fields = ('product', 'product_mrp', 'po_product_quantity', 'po_product_price', 'already_grned_product',
                           'already_returned_product', 'barcode_id', 'zone',)
        autocomplete_fields = ('product',)

    class Media:
        js = ('/static/admin/js/grn_form.js',)

    def __init__(self, *args, **kwargs):
        super(GRNOrderProductForm, self).__init__(*args, **kwargs)

    def fields_required(self, fields):
        for field in fields:
            if not self.cleaned_data.get(field, ''):
                msg = forms.ValidationError("This field is required.")
                self.add_error(field, msg)

    def clean(self):
        super(GRNOrderProductForm, self).clean()
        if self.cleaned_data.get('product', None):
            product_invoice_qty = self.cleaned_data.get('product_invoice_qty')
            manufacture_date = self.cleaned_data.get('manufacture_date')
            expiry_date = self.cleaned_data.get('expiry_date')
            best_before_year = self.cleaned_data.get('best_before_year')
            best_before_month = self.cleaned_data.get('best_before_month')

            if product_invoice_qty != 0:
                if expiry_date is None:
                    if not (int(best_before_year) or int(best_before_month)):
                        raise ValidationError(_('Expiry date is required | Format should be YYYY-MM-DD'))
                if manufacture_date is None:
                    raise ValidationError(_('Manufacture date is required | Format should be YYYY-MM-DD'))

            if product_invoice_qty is None or product_invoice_qty > 0:
                self.fields_required(['manufacture_date'])
                if manufacture_date and manufacture_date > datetime.date.today():
                    raise ValidationError(_('Manufacture Date cannot be in future'))
                if expiry_date:
                    if expiry_date < datetime.date.today():
                        raise ValidationError(_('Expiry Date cannot be in the past'))
                elif best_before_year or best_before_month:
                    expiry_date = manufacture_date + relativedelta(years=int(best_before_year),
                                                                   months=int(best_before_month))
                    if expiry_date < datetime.date.today():
                        raise ValidationError(_('Manufacture date + Best before cannot be in the past'))
                    self.cleaned_data['expiry_date'] = expiry_date
                else:
                    raise ValidationError(
                        _('Please enter either expiry date greater than manufactured date or best before'))
            return self.cleaned_data


class GRNOrderProductFormset(forms.models.BaseInlineFormSet):
    model = GRNOrderProductMapping

    def __init__(self, *args, **kwargs):
        super(GRNOrderProductFormset, self).__init__(*args, **kwargs)
        if hasattr(self, 'order') and self.order:
            ordered_cart = self.order
            products = ordered_cart.products.order_by('product_name')
            gf_shop = ordered_cart.gf_shipping_address.shop_name
            prm_obj = ParentRetailerMapping.objects.filter(
                parent=gf_shop, status=True, retailer__shop_type__shop_type='sp', retailer__status=True).last()
            initial = []
            for item in products:
                zone = None
                whc_assrtment_obj = WarehouseAssortment.objects.filter(
                    warehouse=prm_obj.retailer, product=item.parent_product).last()
                if whc_assrtment_obj:
                    zone = whc_assrtment_obj.zone
                # print(prm_obj.retailer.id, item.parent_product.id, zone_id)
                already_grn = item.product_grn_order_product.filter(grn_order__order__ordered_cart=ordered_cart). \
                    aggregate(Sum('delivered_qty')).get('delivered_qty__sum')
                already_return = item.product_grn_order_product.filter(grn_order__order__ordered_cart=ordered_cart). \
                    aggregate(Sum('returned_qty')).get('returned_qty__sum')
                cart_product = item.cart_product_mapping.filter(cart=ordered_cart).last()
                # Price and Mrp
                price = cart_product.price
                mrp = '-'
                vendor_mapping = cart_product.vendor_product
                if vendor_mapping:
                    piece_price, pack_price = vendor_mapping.product_price, vendor_mapping.product_price_pack
                    price = piece_price if piece_price else (pack_price if pack_price else price)
                    mrp = vendor_mapping.product_mrp
                # Quantity
                po_product_quantity = cart_product.qty
                initial.append({
                    'product': item, 'product_mrp': mrp, 'po_product_quantity': po_product_quantity,
                    'po_product_price': price, 'already_grned_product': already_grn if already_grn else 0,
                    'already_returned_product': already_return if already_return else 0,
                    'zone': str(zone) if zone else "-"
                })
            self.extra = len(initial)
            self.initial = initial

    def clean(self):
        super(GRNOrderProductFormset, self).clean()
        products_dict = {}
        count = 0
        for form in self.forms:
            product_invoice_qty = form.cleaned_data.get('product_invoice_qty')
            delivered_qty = form.cleaned_data.get('delivered_qty')
            returned_qty = form.cleaned_data.get('returned_qty')
            count = count + 1 if product_invoice_qty else count
            if delivered_qty is None or returned_qty is None:
                raise ValidationError('This field is required')

            if form.instance.product.id in products_dict:
                product_data = products_dict[form.instance.product.id]
                product_data['total_items'] = product_data['total_items'] + (delivered_qty + returned_qty)
                product_data['product_invoice_qty'] = product_data['product_invoice_qty'] + product_invoice_qty
            else:
                products_data = {'total_items': (delivered_qty + returned_qty),
                                 'diff': (form.instance.po_product_quantity - (form.instance.already_grned_product +
                                                                               form.instance.already_returned_product)),
                                 'product_invoice_qty': product_invoice_qty,
                                 'product_name': form.cleaned_data.get('product')}
                products_dict[form.instance.product.id] = products_data

        if count < 1:
            raise ValidationError("Please fill the product invoice quantity of at least one product.")

        for k, v in products_dict.items():
            name = v.get('product_name')
            if v.get('product_invoice_qty') <= v.get('diff'):
                v_msg = 'Product invoice quantity {} the sum of delivered quantity and returned quantity for {}'
                if v.get('product_invoice_qty') < v.get('total_items'):
                    raise ValidationError(v_msg.format('cannot be less than', name))
                elif v.get('total_items') < v.get('product_invoice_qty'):
                    raise ValidationError(v_msg.format('must be equal to', name))
            else:
                raise ValidationError('Product invoice quantity cannot be greater than the difference of PO product'
                                      ' quantity and (already_grned_product + already_returned_product) for {}'.
                                      format(name))


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


class VendorShopMappingForm(forms.ModelForm):
    vendor = forms.ModelChoiceField(
        queryset=Vendor.objects.all(),
        widget=autocomplete.ModelSelect2(url='vendor-autocomplete')
    )
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='gf', status=True)
    )

    class Meta:
        model = VendorShopMapping
        fields = ('vendor', 'shop')
