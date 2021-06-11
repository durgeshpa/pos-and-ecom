from django.conf.urls import include, url
from .views import CategoryView

urlpatterns = [
    url(r'^category/$', CategoryView.as_view(), name='category'),

]
