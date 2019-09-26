import re

from dal import autocomplete

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from retailer_backend.validators import PinCodeValidator

from addresses.models import City, Pincode
from shops.models import Shop
from notification_center.models import(
    Template, TextSMSActivity, VoiceCallActivity,
    EmailActivity, GCMActivity, GroupNotificationScheduler
    )


class GroupNotificationForm(forms.ModelForm):

    # city = forms.ModelChoiceField(
    #     queryset=City.objects.all(),
    #     widget=autocomplete.ModelSelect2(url='admin:city_autocomplete'),
    #     required=False
    # )
    buyer_shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='r'),
        #widget=autocomplete.ModelSelect2(url='admin:retailer_autocomplete'),
        widget=autocomplete.ModelSelect2(
            url='admin:retailer_autocomplete',
            forward=('city','pincode_from', 'pincode_to')),
        required=False
    )
    pincode_from = forms.ModelChoiceField(
        queryset=Pincode.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:pincode_autocomplete',
            forward=('city',)),
        required=False
    )
    pincode_to = forms.ModelChoiceField(
        queryset=Pincode.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:pincode_autocomplete',
            forward=('city',)),
        required=False
    )
    # pincode_from = forms.CharField(max_length=6, min_length=6, required=False,
    #                                validators=[PinCodeValidator])
    # pincode_to = forms.CharField(max_length=6, min_length=6, required=False,
    #                              validators=[PinCodeValidator])

    def clean_pincode_from(self):
        cleaned_data = self.cleaned_data
        data = self.data
        if (data.get('pincode_to', None) and not
                cleaned_data.get('pincode_from', None)):
            raise forms.ValidationError('This field is required')
        return cleaned_data['pincode_from']

    def clean_pincode_to(self):
        cleaned_data = self.cleaned_data
        if (cleaned_data.get('pincode_from', None) and not
                cleaned_data.get('pincode_to', None)):
            raise forms.ValidationError('This field is required')
        return cleaned_data['pincode_to']

    class Meta:
        # model = GroupNotificationScheduler
        fields = ('city', 'pincode_from', 'pincode_to', 'template',)
#                 'buyer_shop',  'run_at', 'repeat')  #'__all__'
        

class TemplateForm(forms.ModelForm):
    class Meta:
        model = Template
        fields = [
            'name', 'type', 'notification_groups', 'text_email_template', 'html_email_template',
            'text_sms_template', 'voice_call_template', 'gcm_title',
            'gcm_description', 'gcm_image', 'email_alert',
            'text_sms_alert', 'voice_call_alert', 'gcm_alert', 'status'
            ]

    def clean(self):
        data = self.cleaned_data
        if (
            data.get('email_alert')
            and (
                not data.get('text_email_template')
                or not data.get('html_email_template')
            )
        ):
            raise ValidationError(
                _(
                    '''Both Plain and HTML E-mail content are required to
                    enable email notification'''
                )
            )
        elif (
            data.get('text_sms_alert')
            and not data.get('text_sms_template')
        ):
            raise ValidationError(
                _(
                    '''Text SMS content is required to
                    enable sms notification'''
                )
            )
        elif (
            data.get('voice_call_alert')
            and not data.get('voice_call_template')
        ):
            raise ValidationError(
                _(
                    '''Voice Call content is required to
                    enable voice call notification'''
                )
            )
        elif (
            data.get('gcm_alert')
            and (
                not data.get('gcm_title')
                or not data.get('gcm_description')
            )
        ):
            raise ValidationError(
                _(
                    '''Both Title and Description are required to
                    enable push notification'''
                )
            )
        return data
