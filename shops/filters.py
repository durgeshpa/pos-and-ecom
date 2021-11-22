import django_filters
from django.db.models import Q
from django_filters import rest_framework as filters

from products.models import Product
from .models import FavouriteProduct, Shop
from dal import autocomplete

class FavouriteProductFilter(filters.FilterSet):
    '''
    Filter class for favourite product
    '''
    class Meta:
        model = FavouriteProduct
        fields = '__all__'

class SkuFilterComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Product.objects.none()

        qs = Product.objects.all()

        if self.q:
            qs = qs.filter(product_sku__icontains=self.q)
        return qs

