import django_filters
from django.db.models import Q
from django_filters import rest_framework as filters
from .models import FavouriteProduct 


class FavouriteProductFilter(filters.FilterSet):
    '''
    Filter class for favourite product
    '''
    class Meta:
        model = FavouriteProduct
        fields = '__all__'
