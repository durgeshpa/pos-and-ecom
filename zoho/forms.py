import logging

import csv
import codecs

from django import forms
# Logger
from zoho.models import ZohoFileUpload

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class ZohoInvoiceFileUploadForm(forms.ModelForm):

    def clean(self):
        """
            FileField validation Check if file ends with only .csv
        """
        if self.cleaned_data.get('file'):

            if not self.cleaned_data['file'].name[-4:] in '.csv':
                raise forms.ValidationError("Please upload only CSV File")
            else:
                reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
                headers = next(reader, None)

        return self.cleaned_data['file']

    class Meta:
        model = ZohoFileUpload
        fields = ['file']


class ZohoCreditNoteFileUploadForm(forms.ModelForm):

    def clean(self):
        """
            FileField validation Check if file ends with only .csv
        """
        if self.cleaned_data.get('file'):

            if not self.cleaned_data['file'].name[-4:] in '.csv':
                raise forms.ValidationError("Please upload only CSV File")
            else:
                reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
                headers = next(reader, None)

        return self.cleaned_data['file']

    class Meta:
        model = ZohoFileUpload
        fields = ['file']


class ZohoCustomerFileUploadForm(forms.ModelForm):

    def clean(self):
        """
            FileField validation Check if file ends with only .csv
        """
        if self.cleaned_data.get('file'):

            if not self.cleaned_data['file'].name[-4:] in '.csv':
                raise forms.ValidationError("Please upload only CSV File")
            else:
                reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
                headers = next(reader, None)

        return self.cleaned_data

    class Meta:
        model = ZohoFileUpload
        fields = ['file',]
