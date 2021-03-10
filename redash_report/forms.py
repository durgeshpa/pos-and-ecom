from django import forms
from .models import RedashScheduledReport
from django.core.exceptions import ValidationError


class ScheduledRedashForm(forms.ModelForm):
    class Meta:
        model = RedashScheduledReport
        fields = ['csv_url', 'recipients', 'subject', 'body', 'schedule']
        help_texts = {'recipients': "use commas as separators for multiple email recipients", }

    def clean_recipients(self):
        # email validation
        recipients = self.cleaned_data['recipients']
        emails = recipients.split(',')
        for email in emails:
            if "@gramfactory.com" not in email:
                raise ValidationError("Only gramfactory.com email addresses allowed")

        return recipients


