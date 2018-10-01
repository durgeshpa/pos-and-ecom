from django.conf.urls import include, url

from .views import (GetAllSubCategoryListView,GetCategoryListBySlot)

urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'^get-all-category/$', GetAllSubCategoryListView.as_view({'get': 'list'}), name='get_all_category'),
    url(r'^get-category-list-by-slot/$', GetCategoryListBySlot.as_view(), name='get_all_category'),
    url(r'^get-category-list-by-slot/(?P<slot_name>[\w\-]+)/$', GetCategoryListBySlot.as_view(), name='get_all_category'),
]
