from django.conf.urls import url
from .views import (GetSlotOfferBannerListView, GetPageBannerListView, GetTopSKUListView, OfferPageView,
                    OfferBannerSlotView, OfferPageListView, TopSKUView, OfferBannerPositionView,
                    OfferBannerSlotListView, OfferBannerListView, OfferBannerView, OfferBannerTypeView,
                    ParentCategoryList, ChildCategoryList, ParentBrandListView, ChildBrandListView, ProductListView)

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
    url(r'^offer-banner-slot-list/$', OfferBannerSlotListView.as_view(), name='offer-banner-slot-list'),
    url(r'^offer-banner-list/$', OfferBannerListView.as_view(), name='offer-banner-list'),
    url(r'^offer-banner-type/$', OfferBannerTypeView.as_view(), name='offer-banner-type'),
    url(r'^offer-banner/$', OfferBannerView.as_view(), name='offer-banner'),
    url(r'^offer-banner-parent-category/$', ParentCategoryList.as_view(), name='offer-banner-parent-category'),
    url(r'^offer-banner-child-category/$', ChildCategoryList.as_view(), name='offer-banner-child-category'),
    url(r'^offer-banner-parent-brand/$', ParentBrandListView.as_view(), name='offer-banner-parent-brand'),
    url(r'^offer-banner-child-brand/$', ChildBrandListView.as_view(), name='offer-banner-child-brand'),
    url(r'^offer-banner-product-list/$', ProductListView.as_view(), name='offer-banner-product-list'),


]