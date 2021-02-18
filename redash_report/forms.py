from django import forms
from .models import RedashScheduledReport


class RedashForm(forms.ModelForm):
    class Meta:
        model = RedashScheduledReport
        fields = "__all__"

