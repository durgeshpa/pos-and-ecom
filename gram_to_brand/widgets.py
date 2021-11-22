from django import forms


class CustomAdminDateWidget(forms.DateInput):
    class Media:
        pass

    def __init__(self, attrs=None, format=None):
        attrs = {'class': 'vDateField', 'size': '10', **(attrs or {})}
        super().__init__(attrs=attrs, format=format)
