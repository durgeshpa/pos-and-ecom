
import django_filters 
from django_filters import rest_framework as filters

from retailer_to_sp.models import OrderedProductMapping, OrderedProduct

class OrderedProductMappingFilter(django_filters.FilterSet):
    '''
    Filter class for shipment-products
    '''
    class Meta:
        model = OrderedProductMapping
        fields = ('ordered_product','product','shipped_qty','delivered_qty','returned_qty','damaged_qty',
                  'last_modified_by','created_at','modified_at')


class OrderedProductFilter(django_filters.FilterSet):
    '''
    Filter class for shipments
    '''
    class Meta:
        model = OrderedProduct
        fields = '__all__'        

