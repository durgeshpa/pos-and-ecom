from django.conf.urls import url
from .views import (GetSlotBrandListView, GetSubBrandsListView, BrandView, BrandVendorMappingView)

urlpatterns = [

    url(r'^get-brand/(?P<slot_position_name>[-\w]+)/$', GetSlotBrandListView.as_view(), name='get_slot_brand'),
    url(r'^get-subbrands/(?P<brand>[-\w]+)/$', GetSubBrandsListView.as_view(), name='get_subbrands'),
    url(r'^brand/$', BrandView.as_view(), name='brand'),
    url(r'^brand-vendor-map/$', BrandVendorMappingView.as_view(), name='brand-vendor-map'),

]
