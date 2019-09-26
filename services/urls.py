from django.conf.urls import url,include
from .views import ResizeImage, SalesReport

urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'^api/', include('services.api.urls')),
    url(r'^resize-img/(?P<image_path>.*)/(?P<image_name>.*)', ResizeImage.as_view(), name='resize-image'),

]
