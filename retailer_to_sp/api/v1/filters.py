
import django_filters 
from django_filters import rest_framework as filters

from retailer_to_sp.models import OrderedProductMapping, OrderedProduct

class OrderedProductMappingFilter(django_filters.FilterSet):
    '''
    Filter class for shipment-products
    '''
    class Meta:
        model = OrderedProductMapping
        fields = '__all__'    


class OrderedProductFilter(django_filters.FilterSet):
    '''
    Filter class for shipments
    '''
    class Meta:
        model = OrderedProduct
        fields = '__all__'        

