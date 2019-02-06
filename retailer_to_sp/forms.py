from django import forms
from retailer_to_sp.models import CustomerCare, ReturnProductMapping
from products.models import Product
from django_select2.forms import Select2MultipleWidget,ModelSelect2Widget
from dal import autocomplete

class CustomerCareForm( forms.ModelForm ):
    complaint_detail = forms.CharField( widget=forms.Textarea(attrs={'placeholder':'Enter your Message','cols': 50, 'rows': 8}) )
    class Meta:
        model =CustomerCare
        fields='__all__'

class ReturnProductMappingForm(forms.ModelForm):
    returned_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='return-product-autocomplete',forward=('invoice_no',))
     )

    class Meta:
        model= ReturnProductMapping
        fields= ('returned_product','total_returned_qty', 'reusable_qty', 'damaged_qty','manufacture_date','expiry_date')
