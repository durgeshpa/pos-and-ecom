from django.conf.urls import include, url
from banner.api.v1 import views
from .views import (GetSlotBannerListView, GetPageBannerListView, GetMessageListView)

urlpatterns = [
    # URLs that do not require a session or valid token
    #url(r'^get-all-banner/$', GetAllBannerListView.as_view(), name='get_all_banner'),
    url(r'^get-banner/(?P<page_name>[-\w]+)/page-name/$', GetPageBannerListView.as_view(), name='get_slot_banner'),
    url(r'^get-banner/(?P<page_name>[-\w]+)/page-name/(?P<banner_slot>[-\w]+)/slotname/$', GetSlotBannerListView.as_view(), name='get_slot_banner'),
    #url(r'^get-slot-banner/(?P<pk>\d+)/$', GetSlotBannerListView1.as_view(), name='get_slot_banner'),
    #url(r'^get-slot-banner/(?P<pk>\d+)/$', GetSlotIdBannerListView.as_view({'get': 'list'}), name='get_slot_banner'),
    #url(r'^get-all-slots/$', views.all_slot_list_view, name='get_all_slots'),
    #url(r'^get-all-slots/(?P<pk>\d+)/$', views.slot_detail_view, name='get_slots_detail'),
    url(r'^get-message/$', GetMessageListView.as_view(), name='get_message'),
]
