from retailer_backend.admin import InputFilter
from dal import autocomplete
from dal_admin_filters import AutocompleteFilter

from marketing.models import MLMUser


class UserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'
    autocomplete_url = 'mlm-user-autocomplete'


class MlmUserAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return MLMUser.objects.none()
        qs = MLMUser.objects.filter()
        if self.q:
            qs = qs.filter(phone_number=self.q)
        return qs