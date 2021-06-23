from dal import autocomplete
from dal_admin_filters import AutocompleteFilter
from django.db.models import Q

from retailer_backend.admin import InputFilter
from accounts.models import User


class UserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'
    autocomplete_url = 'mlm-user-autocomplete'


class PosBuyerFilter(AutocompleteFilter):
    title = 'Buyer'
    field_name = 'buyer'
    autocomplete_url = 'mlm-user-autocomplete'


class ReferralToUserFilter(AutocompleteFilter):
    title = 'Referral To User'
    field_name = 'referral_to_user'
    autocomplete_url = 'mlm-user-autocomplete'


class ReferralByUserFilter(AutocompleteFilter):
    title = 'Referral By User'
    field_name = 'referral_by_user'
    autocomplete_url = 'mlm-user-autocomplete'


class RewardUserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'reward_user'
    autocomplete_url = 'mlm-user-autocomplete'


class MlmUserAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()
        qs = User.objects.filter()
        if self.q:
            qs = qs.filter(phone_number__icontains=self.q)
        return qs


class ReferralCodeFilter(InputFilter):
    title = 'Referral Code'
    parameter_name = 'referral_code'

    def queryset(self, request, queryset):
        value = self.value()
        if value is not None:
            return queryset.filter(Q(referral_code__icontains=value))
