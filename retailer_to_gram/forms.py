from django import forms
from retailer_to_sp.models import CustomerCare
from .models import OrderedProduct, Order, Cart
from django.urls import reverse

class CustomerCareForm( forms.ModelForm ):
    complaint_detail = forms.CharField( widget=forms.Textarea(attrs={'placeholder':'Enter your Message','cols': 50, 'rows': 8}) )
    class Meta:
        model =CustomerCare
        fields='__all__'

class OrderedProductForm(forms.ModelForm):
    order = forms.ModelChoiceField(queryset=Order.objects.all())

    class Media:
        js = ('https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.6-rc.0/js/select2.min.js',
        'admin/js/orderedproduct.js')
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.6-rc.0/css/select2.min.css',)
            }

    class Meta:
        model = OrderedProduct
        fields = '__all__'
        exclude = ('invoice_no','shipped_by','received_by','last_modified_by',)

    def __init__(self, *args, **kwargs):
        super(OrderedProductForm, self).__init__(*args, **kwargs)
