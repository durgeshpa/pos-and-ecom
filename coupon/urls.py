from django.conf.urls import include, url

from coupon.filters import RulesetAutoComplete

urlpatterns = [
    url(r'^api/', include('coupon.api.urls')),
    url(r'^ruleset-autocomplete/$', RulesetAutoComplete.as_view(), name='ruleset-autocomplete'),
]