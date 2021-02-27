# basic URL Configurations
from django.conf.urls import url
from django.urls import include, path
# import routers
from rest_framework import routers

# import everything from views
from .views import *

# define the router
router = routers.DefaultRouter()

# define the router path and viewset to be used
# router.register(r'scheme', ShopSchemeMappingViewSet)

# specify URL Path for rest_framework
urlpatterns = [
	# path('', include(router.urls))
	url(r'^scheme/$', ShopSchemeMappingView.as_view(), name='scheme'),
    url(r'^purchase-matrix/$', ShopPurchaseMatrix.as_view(), name='purchase-matrix'),
]
