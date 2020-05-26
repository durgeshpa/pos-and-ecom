from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Bin
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from django.core.exceptions import ObjectDoesNotExist


class BulkBinUpdation(forms.Form):
    file = forms.FileField(label='Select a file')

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name[-5:] == '.xlsx':
            raise forms.ValidationError("Sorry! Only Excel file accepted")
        return file