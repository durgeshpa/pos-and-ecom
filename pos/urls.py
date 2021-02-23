from django.conf.urls import include, url

urlpatterns = [
    url(r'^api/', include('pos.api.urls')),
]
