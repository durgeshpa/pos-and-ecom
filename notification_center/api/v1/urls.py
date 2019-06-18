from django.conf.urls import url, include
from django.urls import path
from notification_center.api.v1.views import (DeviceViewSet,)
from rest_framework import routers


router = routers.DefaultRouter()
router.register(r'devices', DeviceViewSet)

urlpatterns = [
    url(r'', include(router.urls))

]

#urlpatterns += router.urls