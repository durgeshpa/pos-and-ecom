
from .views import (SupplierAutocomplete,ShippingAddressAutocomplete,BillingAddressAutocomplete,BrandAutocomplete,StateAutocomplete,


                    OrderAutocomplete,ProductAutocomplete,VendorProductAutocomplete,VendorProductPrice, DownloadPurchaseOrder, GRNProductPriceMappingData,GRNProductAutocomplete,GRNProductMappingData,GRNProduct1MappingData,GRNOrderAutocomplete)


from django.conf.urls import url,include

urlpatterns = [
    url(r'^supplier-autocomplete/$',SupplierAutocomplete.as_view(),name='supplier-autocomplete',),
    url(r'^shipping-address-autocomplete/$',ShippingAddressAutocomplete.as_view(),name='shipping-address-autocomplete',),
    url(r'^billing-address-autocomplete/$',BillingAddressAutocomplete.as_view(),name='billing-address-autocomplete',),

    url(r'^brand-autocomplete/$',BrandAutocomplete.as_view(),name='brand-autocomplete',),
    url(r'^state-autocomplete/$',StateAutocomplete.as_view(),name='state-autocomplete',),
    url(r'^order-autocomplete/$',OrderAutocomplete.as_view(),name='order-autocomplete',),
    url(r'^product-autocomplete/$', ProductAutocomplete.as_view(), name='product-autocomplete', ),
    url('^download-purchase-order/(?P<pk>\d+)/purchase_order/$', DownloadPurchaseOrder.as_view(), name='download_purchase_order'),
    url(r'^vendor-product-autocomplete/$', VendorProductAutocomplete.as_view(), name='vendor-product-autocomplete', ),
    url(r'^vendor-product-price/$', VendorProductPrice.as_view(), name='vendor-product-price', ),
    url(r'^product-autocomplete/$', GRNProductAutocomplete.as_view(), name='product-autocomplete', ),
    url(r'^po-product-price/$', GRNProductPriceMappingData.as_view(), name='po-product-price', ),
    url(r'^po-product-quantity/$', GRNProductMappingData.as_view(), name='po-product-quantity', ),
    url(r'^po-product/$', GRNProduct1MappingData.as_view(), name='po-product', ),
    url(r'^order-autocomplete/$', GRNOrderAutocomplete.as_view(), name='order-autocomplete', ),

]
