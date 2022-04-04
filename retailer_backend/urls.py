"""retailer_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.conf.urls import include, url
from rest_framework.documentation import include_docs_urls
from rest_framework_swagger.views import get_swagger_view
from rest_framework import permissions
from decouple import config, Csv
from django.conf import settings
from retailer_backend.cron import CronToDeleteOrderedProductReserved, DailyStock
from accounts.views import (terms_and_conditions, privacy_policy)
from shops.views import ShopMappedProduct
from franchise.views import ProductList

from django_ses.views import handle_bounce
from django.views.decorators.csrf import csrf_exempt
from retailer_backend.swagger_urls import schema_view

urlpatterns = [
    url(r'^api-auth/', include('rest_framework.urls')),
    url(r'^rest-auth/', include('rest_auth.urls')),
    url(r'^otp/', include('otp.urls')),
    url(r'^marketing/', include('marketing.urls')),
    url(r'^api/', include('api.urls')),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^addresses/', include('addresses.urls')),
    url(r'^shops/', include('shops.urls')),
    url(r'^category/', include('categories.urls')),
    url(r'^product/', include('products.urls')),
    url(r'^brand/', include('brand.urls')),
    url(r'^rest-auth/registration/', include('rest_auth.registration.urls')),
    url(r'^bannerapi/', include('banner.urls')),
    url(r'^offerbannerapi/', include('offer.urls')),
    url(r'^brandapi/', include('brand.urls')),
    url(r'^service-partner/', include('sp_to_gram.urls')),
    url(r'^retailer/sp/', include('retailer_to_sp.urls')),
    url(r'^gram/brand/', include('gram_to_brand.urls')),
    url(r'^retailer/gram/', include('retailer_to_gram.urls')),
    url(r'^services/', include('services.urls')),
    url(r'^payments/', include('payments.urls')),
    url(r'^fcm/', include('fcm.urls')),
    url(r'^notification-center/', include('notification_center.urls')),
    url(r'^admin/shops/shop-mapped/(?P<pk>\d+)/product/$', ShopMappedProduct.as_view(), name='shop_mapped_product'),
    url(r'^admin/statuscheck/', include('celerybeat_status.urls')),
    url('^delete-ordered-product-reserved/$', CronToDeleteOrderedProductReserved.as_view(), name='delete_ordered_product_reserved'),
    url('^terms-and-conditions/$', terms_and_conditions, name='terms_and_conditions'),
    url('^privacy-policy/$', privacy_policy, name='privacy_policy'),
    url('^daily-stock/$', DailyStock.as_view(), name='daily_stock'),
    path('admin/', admin.site.urls),
    url(r'^ses/bounce/$', csrf_exempt(handle_bounce)),
    url(r'^analytics/', include('analytics.urls')),
    url(r'^wms/', include('wms.urls')),
    url(r'^nested_admin/', include('nested_admin.urls')),
    url(r'^audit/', include('audit.urls')),
    url(r'^franchise/', include('franchise.urls')),
    url(r'^admin/franchise/product-list/$', ProductList.as_view(), name='product-list'),
    url(r'^whc/', include('whc.urls')),
    url(r'^pos/', include('pos.urls')),
    url(r'^retailer-incentive/', include('retailer_incentive.urls')),
    url(r'^ars/', include('ars.urls')),
    url(r'^ecom/', include('ecom.urls')),
    url(r'^cms/', include('cms.urls')),
    url(r'^coupon/', include('coupon.urls')),
    url(r'^reports/', include('report.urls')),
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    url(r'^tinymce/', include('tinymce.urls')),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += (url(r'^admin/django-ses/', include('django_ses.urls')),)
# if settings.DEBUG:
#     urlpatterns += [url(r'^$', schema_view)]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),

        # For django versions before 2.0:
        # url(r'^__debug__/', include(debug_toolbar.urls)),

    ] + urlpatterns
