from retailer_backend.admin import InputFilter
from dal import autocomplete
from dal_admin_filters import AutocompleteFilter

from accounts.models import User


class UserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'
    autocomplete_url = 'mlm-user-autocomplete'


class MlmUserAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()
        qs = User.objects.filter()
        if self.q:
            qs = qs.filter(phone_number=self.q)
        return qs


class MlmUserFilter(InputFilter):
    title = 'Phone Number'
    parameter_name = 'phone_number'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(phone_number=value)
        return queryset