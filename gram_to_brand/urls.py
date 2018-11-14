
from .views import SupplierAutocomplete,ShippingAddressAutocomplete,BillingAddressAutocomplete,BrandAutocomplete,StateAutocomplete
from django.conf.urls import url,include

urlpatterns = [
    url(r'^supplier-autocomplete/$',SupplierAutocomplete.as_view(),name='supplier-autocomplete',),
    url(r'^shipping-address-autocomplete/$',ShippingAddressAutocomplete.as_view(),name='shipping-address-autocomplete',),
    url(r'^billing-address-autocomplete/$',BillingAddressAutocomplete.as_view(),name='billing-address-autocomplete',),

    url(r'^brand-autocomplete/$',BrandAutocomplete.as_view(),name='brand-autocomplete',),
    url(r'^state-autocomplete/$',StateAutocomplete.as_view(),name='state-autocomplete',),
]