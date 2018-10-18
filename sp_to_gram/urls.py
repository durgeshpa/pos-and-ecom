from django.conf.urls import url,include
from .views import abc
urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'^api/', abc, name='abc'),
]
