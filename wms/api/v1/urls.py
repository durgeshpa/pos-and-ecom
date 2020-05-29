from django.conf.urls import include, url
from .views import PutAwayViewSet, BinViewSet, PutAwayProduct

urlpatterns = [
    # url(r'^upload-csv/$', bins_upload, name="bins_upload"),
    url(r'^bins/$', BinViewSet.as_view(), name='bins'),
    url(r'^put-away/$', PutAwayViewSet.as_view(), name='put-away'),
    url(r'^putaway-products/$', PutAwayProduct.as_view(), name='putaway-products'),

]