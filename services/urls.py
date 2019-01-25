from django.conf.urls import url,include
from .views import ResizeImage

urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'^resize-img/', ResizeImage.as_view(), name='resize-image'),
]
