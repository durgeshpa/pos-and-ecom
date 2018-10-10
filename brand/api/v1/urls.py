from django.conf.urls import include, url
from brand.api.v1 import views
from .views import (GetSlotBrandListView)

urlpatterns = [
    # URLs that do not require a session or valid token
    #url(r'^get-all-brand/$', GetAllBrandListView.as_view(), name='get_all_brand'),
    url(r'^get-brand/(?P<slot_position_name>[-\w]+)/$', GetSlotBrandListView.as_view(), name='get_slot_brand'),
    #url(r'^get-slot-brand/(?P<slot_position_name>[-\w]+)/$', GetSlotBrandListView.as_view(), name='get_slot_brand'),
    #url(r'^get-slot-banner/(?P<pk>\d+)/$', GetSlotBannerListView1.as_view(), name='get_slot_banner'),
    #url(r'^get-slot-banner/(?P<pk>\d+)/$', GetSlotIdBannerListView.as_view({'get': 'list'}), name='get_slot_banner'),
    #url(r'^get-all-slots/$', views.all_slot_list_view, name='get_all_slots'),
    #url(r'^get-all-slots/(?P<pk>\d+)/$', views.slot_detail_view, name='get_slots_detail'),
]
