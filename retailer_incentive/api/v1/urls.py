# basic URL Configurations
from django.conf.urls import url

from .views import ShopPurchaseMatrix, SalesManagerLogin, IncentiveDashBoard, ShopSchemeDetails, \
    BulkIncentiveSampleFileView, BulkCreateIncentiveView

# specify URL Path for rest_framework
urlpatterns = [
    url(r'^purchase-matrix/$', ShopPurchaseMatrix.as_view(), name='purchase-matrix'),
    url(r'^incentive-dashboard/$', IncentiveDashBoard.as_view(), name='incentive-dashboard'),
    url(r'^manager-login/$', SalesManagerLogin.as_view(), name='manager-login'),
    url(r'^scheme-details/$', ShopSchemeDetails.as_view(), name='scheme-details'),
    url(r'^download/bulk-download-incentive-sample/$', BulkIncentiveSampleFileView.as_view(),
        name='bulk-download-incentive-sample'),
    url(r'^upload/bulk-upload-incentive/$', BulkCreateIncentiveView.as_view(),
        name='bulk-upload-incentive')
]
