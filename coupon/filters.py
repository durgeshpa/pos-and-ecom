from dal import autocomplete

from coupon.models import CouponRuleSet


class RulesetAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return CouponRuleSet.objects.none()
        qs = CouponRuleSet.objects.all()
        if self.q:
            qs = qs.filter(rulename__istartswith=self.q)
        return qs
