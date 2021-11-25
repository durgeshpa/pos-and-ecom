from django.urls import path
from django.conf.urls import include, url
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

urlpatterns_swagger = [
    url(r'^api-auth/', include('rest_framework.urls')),
    url(r'^rest-auth/', include('rest_auth.urls')),
    url(r'^marketing/api/', include('marketing.api.urls')),
    url(r'^api/api/', include('analytics.api.v1.urls')),
    url(r'^accounts/api/', include('accounts.api.urls')),
    url(r'^addresses/api/', include('addresses.api.urls')),
    url(r'^shops/api/', include('shops.api.urls')),
    url(r'^category/api/', include('categories.api.urls')),
    url(r'^product/api/', include('products.api.urls')),
    url(r'^brand/api/', include('brand.api.urls')),
    url(r'^bannerapi/api/', include('banner.api.urls')),
    url(r'^offerbannerapi/api/', include('offer.api.urls')),
    url(r'^brandapi/api/', include('brand.api.urls')),
    url(r'^retailer/sp/api/', include('retailer_to_sp.api.urls')),
    url(r'^gram/brand/api/', include('gram_to_brand.api.urls')),
    url(r'^payments/api/', include('payments.api.urls')),
    url(r'^notification-center/api/', include('notification_center.api.urls')),
    url(r'^wms/api/', include('wms.api.urls')),
    url(r'^audit/api/', include('audit.api.urls')),
    url(r'^pos/api/', include('pos.api.urls')),
    url(r'^retailer-incentive/api/', include('retailer_incentive.api.v1.urls')),
    url(r'^ecom/api/', include('ecom.api.urls')),
    url(r'^cms/api/', include('cms.api.urls')),
    url(r'^coupon/api/', include('coupon.api.urls')),
]
schema_view = get_schema_view(
   openapi.Info(
      title="GramFactory API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),

   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
   patterns=urlpatterns_swagger,
)