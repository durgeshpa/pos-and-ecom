from django.conf.urls import include, url

from .views import (GetAllCategoryListView)

urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'^get-all-banner/$', GetAllBannerListView.as_view({'get': 'list'}), name='get_all_banner'),
]
