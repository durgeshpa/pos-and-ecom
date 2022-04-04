from dal import autocomplete
from django.db.models import Q
from accounts.models import User


class ZohoUserFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()

        qs = User.objects.all()

        if self.q:
            qs = qs.filter(Q(phone_number__icontains=self.q) | Q(first_name__icontains=self.q) | Q(
                last_name__icontains=self.q))
        return qs

