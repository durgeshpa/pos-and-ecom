from django import forms
from retailer_to_sp.models import CustomerCare

class CustomerCareForm( forms.ModelForm ):
    complaint_detail = forms.CharField( widget=forms.Textarea(attrs={'placeholder':'Enter your Message','cols': 50, 'rows': 8}) )
    class Meta:
        model =CustomerCare
        fields='__all__'
