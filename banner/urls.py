from django.conf.urls import include, url
from django.contrib import admin
from banner import views

urlpatterns = [
url(r'^banner/$', views.banner_list),
url(r'^banner/(?P<pk>\d+)/$', views.banner_detail),
url(r'^api/', include('banner.api.urls')),
]
