from django import forms
from .models import RedashScheduledReport
from django.core.exceptions import ValidationError


class ScheduledRedashForm(forms.ModelForm):
    class Meta:
        model = RedashScheduledReport
        fields = "__all__"

    def clean_recipients(self):
        # email validation
        data = self.cleaned_data['recipients']
        if "@gramfactory.com" not in data:
            raise ValidationError("Only gramfactory.com email addresses allowed")

        return data

