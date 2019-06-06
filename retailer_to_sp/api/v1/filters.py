
import django_filters 
from django_filters import rest_framework as filters

from retailer_to_sp.models import OrderedProductMapping

class OrderedProductMappingFilter(filters.FilterSet):
    '''
    Filter class for services
    '''
    class Meta:
        model = OrderedProductMapping
        fields = '__all__'