from django import forms
from .models import ProductCSV

class ProductCSVForm(forms.ModelForm):
    class Meta:
        model = ProductCSV
        fields = ('file', )
