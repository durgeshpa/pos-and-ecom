import django_filters 
from django_filters import rest_framework as filters

from payments.models import ShipmentPayment

class ShipmentPaymentFilter(filters.FilterSet):
    '''
    Filter class for payment
    '''
    class Meta:
        model = ShipmentPayment
        fields = '__all__' 
