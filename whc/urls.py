from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^auto-process/$', views.process_auto_order, name="auto-process"),

]