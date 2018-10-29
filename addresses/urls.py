from django.conf.urls import url,include

urlpatterns = [
    url(r'^api/', include('addresses.api.urls')),
]
