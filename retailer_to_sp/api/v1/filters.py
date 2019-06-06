
import django_filters 
from django_filters import rest_framework as filters

from retailer_to_sp.models import OrderedProductMapping, OrderedProduct

class OrderedProductMappingFilter(filters.FilterSet):
    '''
    Filter class for services
    '''
    class Meta:
        model = OrderedProductMapping
        fields = '__all__'


class OrderedProductFilter(filters.FilterSet):
    '''
    Filter class for services
    '''
    class Meta:
        model = OrderedProduct
        fields = '__all__'        