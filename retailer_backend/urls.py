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
from decouple import config, Csv
from django.conf import settings
from retailer_backend.cron import CronToDeleteOrderedProductReserved,cron_to_delete_ordered_product_reserved
from accounts.views import (terms_and_conditions, privacy_policy)
from shops.views import ShopMappedProduct

schema_view = get_swagger_view(title='GramFactory API')


urlpatterns = [
    url(r'^api-auth/', include('rest_framework.urls')),
    url(r'^rest-auth/', include('rest_auth.urls')),
    url(r'^otp/', include('otp.urls')),
    url(r'^api/', include('api.urls')),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^addresses/', include('addresses.urls')),
    url(r'^shops/', include('shops.urls')),
    url(r'^category/', include('categories.urls')),
    url(r'^rest-auth/registration/', include('rest_auth.registration.urls')),
    url(r'^bannerapi/', include('banner.urls')),
    url(r'^brandapi/', include('brand.urls')),
    url(r'^service-partner/', include('sp_to_gram.urls')),
    url(r'^retailer/sp/', include('retailer_to_sp.urls')),
    url(r'^gram/brand/', include('gram_to_brand.urls')),
    url(r'^retailer/gram/', include('retailer_to_gram.urls')),
    url(r'^services/', include('services.urls')),
    url(r'^admin/shops/shop-mapped/(?P<pk>\d+)/product/$', ShopMappedProduct.as_view(), name='shop_mapped_product'),

    url('^delete-ordered-product-reserved/$', CronToDeleteOrderedProductReserved.as_view(), name='delete_ordered_product_reserved'),
    url('^terms-and-conditions/$', terms_and_conditions, name='terms_and_conditions'),
    url('^privacy-policy/$', privacy_policy, name='privacy_policy'),

    url('^delete-ordered-product-reserved1/$', cron_to_delete_ordered_product_reserved, name='delete_ordered_product_reserved'),
    path('admin/', admin.site.urls),
    url(r'^nested_admin/', include('nested_admin.urls')),

]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# if settings.DEBUG:
#     urlpatterns += [url(r'^$', schema_view)]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),

        # For django versions before 2.0:
        # url(r'^__debug__/', include(debug_toolbar.urls)),

    ] + urlpatterns
