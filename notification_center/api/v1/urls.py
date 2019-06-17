from django.conf.urls import url
from django.urls import path
from notification_center.api.v1.views import (DeviceViewSet,)
from rest_framework import routers


router = routers.DefaultRouter()
router.register(r'devices', DeviceViewSet)

urlpatterns = [
    url(r'^v1/', include(router.urls))

]

#urlpatterns += router.urls