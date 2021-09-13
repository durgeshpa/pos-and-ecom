from django.conf.urls import include, url
from .views import GRNOrderNonZoneProductsCrudView

urlpatterns = [
    url(r'^non-zone-grn-products/$', GRNOrderNonZoneProductsCrudView.as_view(), name='non-zone-grn-products'),

]