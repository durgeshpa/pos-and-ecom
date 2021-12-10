from django.conf.urls import url,include

urlpatterns = [
    url(r'^v1/', include('retailer_to_sp.api.v1.urls')),
]
