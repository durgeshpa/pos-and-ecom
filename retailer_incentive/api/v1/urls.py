# basic URL Configurations
from django.conf.urls import url

from .views import ShopSchemeMappingView, ShopPurchaseMatrix, ShopUserMappingView, \
    SalesManagerLogin, IncentiveDashBoard

# specify URL Path for rest_framework
urlpatterns = [
    url(r'^scheme/$', ShopSchemeMappingView.as_view(), name='scheme'),
    url(r'^purchase-matrix/$', ShopPurchaseMatrix.as_view(), name='purchase-matrix'),
    url(r'^contact/$', ShopUserMappingView.as_view(), name='contact'),
    url(r'^incentive-dashboard/$', IncentiveDashBoard.as_view(), name='incentive-dashboard'),
    url(r'^manager-login/$', SalesManagerLogin.as_view(), name='manager-login')

]
