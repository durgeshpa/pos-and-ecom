from django import forms
from gram_to_brand.models import Order,GRNOrder, Cart
from brand.models import Brand
from dal import autocomplete
from django_select2.forms import Select2MultipleWidget,ModelSelect2Widget
from addresses.models import State,Address
from brand.models import Vendor
from django.urls import reverse

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
        widget=autocomplete.ModelSelect2(url='shipping-address-autocomplete', forward=('supplier_state',))
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
        fields = ('brand','supplier_state','supplier_name','gf_shipping_address','gf_billing_address','po_validity_date','payment_term','delivery_term','cart_product_mapping_csv')

    def __init__(self, *args, **kwargs):
        super(POGenerationForm, self).__init__(*args, **kwargs)
        self.fields['cart_product_mapping_csv'].help_text = """<h3><a href="%s" target="_blank">Download Vendor products list</a></h3>"""%(reverse('admin:products_export_for_vendor'))

    def clean_vendor_products_csv(self):
        if not self.cleaned_data['vendor_products_csv'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['vendor_products_csv'], 'utf-8'))
        first_row = next(reader)
        for id,row in enumerate(reader):
            try:
                Product.objects.get(pk=row[0])
            except:
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | Product does not exist with this ID")
            if not row[0]:
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[0]+":"+row[0]+" | Product ID cannot be empty")
            if row[2] and not re.match("^\d{0,8}(\.\d{1,4})?$", row[2]):
                raise ValidationError("Row["+str(id+1)+"] | "+first_row[2]+":"+row[2]+" | "+VALIDATION_ERROR_MESSAGES['INVALID_PRICE'])
        return self.cleaned_data['vendor_products_csv']
