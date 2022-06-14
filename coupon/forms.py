from dal import autocomplete
from django import forms

from accounts.models import User
from brand.models import Brand
from coupon.models import CouponRuleSet
from pos.models import RetailerProduct
from products.models import Product


class RulesetCreationForm(forms.ModelForm):
    no_of_users_allowed = forms.ModelMultipleChoiceField(
        required=False,
        queryset=User.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url='user-autocomplete'))

    free_product = forms.ModelChoiceField(
        required=False,
        queryset=RetailerProduct.objects.all(),
        widget=autocomplete.ModelSelect2(url='pos-product-autocomplete'))

    def __init__(self, *args, **kwargs):
        super(RulesetCreationForm, self).__init__(*args, **kwargs)


class CouponCreationForm(forms.ModelForm):

    rule = forms.ModelChoiceField(
        required=False,
        queryset=CouponRuleSet.objects.all(),
        widget=autocomplete.ModelSelect2(url='ruleset-autocomplete'))

    def __init__(self, *args, **kwargs):
        super(CouponCreationForm, self).__init__(*args, **kwargs)


class RulesetBrandMappingForm(forms.ModelForm):

    rule = forms.ModelChoiceField(
        required=False,
        queryset=CouponRuleSet.objects.all(),
        widget=autocomplete.ModelSelect2(url='ruleset-autocomplete'))

    brand = forms.ModelChoiceField(
        required=False,
        queryset=Brand.objects.all(),
        widget=autocomplete.ModelSelect2(url='brand-autocomplete'))

    def __init__(self, *args, **kwargs):
        super(RulesetBrandMappingForm, self).__init__(*args, **kwargs)
