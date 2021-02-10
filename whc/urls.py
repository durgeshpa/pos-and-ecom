from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^auto-process/$', views.start_auto_processing, name="auto-process"),

]