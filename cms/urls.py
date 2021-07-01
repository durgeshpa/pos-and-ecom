from django.conf.urls import url
from django.urls import path, include


urlpatterns = [
    url(r'^api/', include('cms.api.urls')),

]