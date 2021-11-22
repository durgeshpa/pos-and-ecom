
from .views import (SupplierAutocomplete, ShippingAddressAutocomplete, BillingAddressAutocomplete, BrandAutocomplete,
                    StateAutocomplete,
                    OrderAutocomplete, ProductAutocomplete, VendorProductAutocomplete, VendorProductPrice,
                    DownloadPurchaseOrder,
                    GRNProductPriceMappingData, GRNProductAutocomplete, GRNProductMappingData, GRNProduct1MappingData,
                    GRNOrderAutocomplete,
                    GRNedProductData, ApproveView, DisapproveView, DownloadDebitNote, MergedBarcode,
                    ParentProductAutocomplete,
                    FetchLastGRNProduct, VendorAutocomplete)


from django.conf.urls import url,include

urlpatterns = [
    url(r'^api/', include('gram_to_brand.api.urls')),
    url(r'^vendor-autocomplete/$',VendorAutocomplete.as_view(),name='vendor-autocomplete',),
    url(r'^supplier-autocomplete/$',SupplierAutocomplete.as_view(),name='supplier-autocomplete',),
    url(r'^shipping-address-autocomplete/$',ShippingAddressAutocomplete.as_view(),name='shipping-address-autocomplete',),
    url(r'^billing-address-autocomplete/$',BillingAddressAutocomplete.as_view(),name='billing-address-autocomplete',),

    url(r'^brand-autocomplete/$',BrandAutocomplete.as_view(),name='brand-autocomplete',),
    url(r'^state-autocomplete/$',StateAutocomplete.as_view(),name='state-autocomplete',),
    url(r'^order-autocomplete/$',OrderAutocomplete.as_view(),name='order-autocomplete',),
    url(r'^parent-product-autocomplete/$', ParentProductAutocomplete.as_view(), name='parent-product-autocomplete',),
    url(r'^fetch-last-grn-product/$', FetchLastGRNProduct, name='fetch-last-grn-product',),
    url(r'^product-autocomplete/$', ProductAutocomplete.as_view(), name='product-autocomplete', ),
    url('^download-purchase-order/(?P<pk>\d+)/purchase_order/$', DownloadPurchaseOrder.as_view(), name='download_purchase_order'),
    url(r'^vendor-product-autocomplete/$', VendorProductAutocomplete.as_view(), name='vendor-product-autocomplete', ),
    url(r'^vendor-product-price/$', VendorProductPrice.as_view(), name='vendor-product-price', ),
    #url(r'^vendor-product1-price/$', VendorProduct1Price.as_view(), name='vendor-product1-price', ),
    #url(r'^product-autocomplete/$', GRNProductAutocomplete.as_view(), name='product-autocomplete', ),
    url(r'^po-product-price/$', GRNProductPriceMappingData.as_view(), name='po-product-price', ),
    url(r'^po-product-quantity/$', GRNProductMappingData.as_view(), name='po-product-quantity', ),
    url(r'^po-product/$', GRNProduct1MappingData.as_view(), name='po-product', ),
    #url(r'^order-autocomplete/$', GRNOrderAutocomplete.as_view(), name='order-autocomplete', ),
    url(r'^po-grned/$', GRNedProductData.as_view(), name='po-grned', ),
    #url(r'^po-grned1/$', GRNProduct2MappingData.as_view(), name='po-grned1', ),
    url('^download-debit-note/(?P<pk>\d+)/debit_note/$', DownloadDebitNote.as_view(), name='download_debit_note'),

    url(r'^approve/(?P<pk>\d+)/$', ApproveView.as_view(), name='approve-account', ),
    url(r'^dis-approve/(?P<pk>\d+)/$', DisapproveView.as_view(), name='dis-approve-account', ),
    url(r'^merged_barcode/(?P<pk>\d+)/$', MergedBarcode.as_view(), name='batch_barcodes', ),
    # url(r'^demands/$', PendingDemands.as_view(), name='pending-demands'),

]
