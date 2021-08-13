from django.conf.urls import url
from .views import (GetSlotOfferBannerListView, GetPageBannerListView, GetTopSKUListView, OfferPageView,
                    OfferBannerSlotView, OfferPageListView, TopSKUView, OfferBannerPositionView,
                    OfferBannerSlotListView)

urlpatterns = [

    url(r'^get-offer-banner/(?P<page_name>[-\w]+)/page-name/$', GetPageBannerListView.as_view(),
        name='get_slot_banner'),
    url(r'^get-offer-banner/(?P<page_name>[-\w]+)/page-name/(?P<banner_slot>[-\w]+)/slotname/$',
        GetSlotOfferBannerListView.as_view(), name='get_slot_banner'),
    url(r'^get-top-sku/$', GetTopSKUListView.as_view(), name='get_top_sku'),
    url(r'^offer-page/$', OfferPageView.as_view(), name='offer-page'),
    url(r'^offer-page-filter/$', OfferPageListView.as_view(), name='ooffer-page-filter'),
    url(r'^offer-banner-slot/$', OfferBannerSlotView.as_view(), name='offer-banner-slot'),
    url(r'^offer-top-sku/$', TopSKUView.as_view(), name='offer-top-sku'),
    url(r'^offer-banner-position/$', OfferBannerPositionView.as_view(), name='offer-banner-position'),
    url(r'^offer-banner-slot-list/$', OfferBannerSlotListView.as_view(), name='offer-banner-slot-list')

]