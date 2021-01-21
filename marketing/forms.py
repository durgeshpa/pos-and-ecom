from django import forms
from django.db import transaction

from accounts.middlewares import get_current_user
from marketing.models import RewardPoint, RewardLog
from global_config.models import GlobalConfig


class RewardPointForm(forms.ModelForm):
    """
        To record discounts given to users
    """
    phone = forms.CharField(required=False, label="Phone Number", widget=forms.TextInput(attrs={'readonly': True}))
    name = forms.CharField(required=False, label='Customer Name', widget=forms.TextInput(attrs={'readonly': True}))
    email = forms.CharField(required=False, label='Email ID', widget=forms.TextInput(attrs={'readonly': True}))
    redeemable_reward_points = forms.IntegerField(required=False, label='Redeemable Reward Points',
                                                  widget=forms.TextInput(attrs={'readonly': True}))
    maximum_available_discount = forms.CharField(required=False, label='Maximum Available Discount (INR)',
                                                 widget=forms.TextInput(attrs={'readonly': True}))
    discount_given = forms.IntegerField(required=True, label='Discount Given For Last Purchase (INR)')
    points_used = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = RewardPoint
        fields = ('phone', 'name', 'email', 'redeemable_reward_points', 'maximum_available_discount',
                  'discount_given', 'points_used')

    def __init__(self, *args, **kwargs):
        super(RewardPointForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance:
            try:
                conf_obj = GlobalConfig.objects.get(key='used_reward_factor')
                used_reward_factor = int(conf_obj.value)
            except:
                used_reward_factor = 3
            self.fields['phone'].initial = instance.user.phone_number
            self.fields['name'].initial = instance.user.name
            self.fields['email'].initial = instance.user.email
            self.fields['redeemable_reward_points'].initial = instance.direct_earned + instance.indirect_earned \
                                                              - instance.points_used
            self.fields['maximum_available_discount'].initial = used_reward_factor * (
                        instance.direct_earned + instance.indirect_earned - instance.points_used)

    def clean(self):
        cleaned_data = self.cleaned_data

        if 'discount_given' not in cleaned_data:
            raise forms.ValidationError("Please Enter Discount Value")

        if not str(cleaned_data['discount_given']).isdigit():
            raise forms.ValidationError("Discount Invalid. Should Be An Integer")

        if int(cleaned_data['discount_given']) < 1:
            raise forms.ValidationError("Please Enter Discount Greater Than 0")

        try:
            conf_obj = GlobalConfig.objects.get(key='used_reward_factor')
            used_reward_factor = int(conf_obj.value)
        except:
            used_reward_factor = 3

        if int(cleaned_data['discount_given']) % used_reward_factor != 0:
            raise forms.ValidationError("Invalid Discount. Should Be In Multiples Of {}".format(used_reward_factor))

        points_used = int(int(cleaned_data['discount_given']) / used_reward_factor)

        if points_used > self.instance.direct_earned + self.instance.indirect_earned - self.instance.points_used:
            raise forms.ValidationError("Discount Used Cannot Be Greater Than The Maximum Available Discount")

        self.cleaned_data['points_used'] = self.instance.points_used + points_used
        self.cleaned_data['current_points_used'] = points_used

        return self.cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        cleaned_data = self.cleaned_data
        user = get_current_user()
        RewardLog.objects.create(user=self.instance.user, transaction_type='used_reward',
                                 transaction_id=self.instance.id, points=cleaned_data['current_points_used'],
                                 discount=cleaned_data['discount_given'], changed_by=user)
        return super(RewardPointForm, self).save(commit=commit)
