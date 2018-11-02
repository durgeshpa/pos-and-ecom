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
    url('^delete-ordered-product-reserved/$', CronToDeleteOrderedProductReserved.as_view(), name='delete_ordered_product_reserved'),
    url('^delete-ordered-product-reserved1/$', cron_to_delete_ordered_product_reserved, name='delete_ordered_product_reserved'),
    path('admin/', admin.site.urls),

]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += [url(r'^$', schema_view)]
