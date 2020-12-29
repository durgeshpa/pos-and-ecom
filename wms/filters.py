from datetime import datetime, timedelta

from dal import autocomplete
from django.contrib.admin import SimpleListFilter, ListFilter, FieldListFilter
from django.db.models import Q, F

from shops.models import Shop
from wms.models import InventoryType, InventoryState, In, PickupBinInventory
from accounts.models import User


class WareHouseComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Shop.objects.none()

        qs = Shop.objects.filter(
            shop_type__shop_type='sp')

        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class InventoryTypeFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return InventoryType.objects.none()

        qs = InventoryType.objects.all()

        if self.q:
            qs = qs.filter(inventory_type_name__icontains=self.q)
        return qs


class InventoryStateFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return InventoryState.objects.none()

        qs = InventoryState.objects.all()

        if self.q:
            qs = qs.filter(inventory_state_name__icontains=self.q)
        return qs


class PutawayUserFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()

        qs = User.objects.all()

        if self.q:
            qs = qs.filter(first_name__icontains=self.q)
        return qs


class PickupStatusFilter(SimpleListFilter):
    title = 'Pickup Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return ((0, 'Partial' ),)

    def queryset(self, request, queryset):
        if self.value() == '0':
            queryset = queryset.filter(~Q(pickup_quantity=F('quantity')), pickup__status='picking_complete')
        return queryset


class ExpiryDateFilter(SimpleListFilter):
    title = 'expiry_date'
    parameter_name = 'expiry_date'

    def lookups(self, request, model_admin):
        return ( (0, 'Expired' ), (1, 'Expiring in 7 days'), (2, 'Expiring after 7 days'), )

    def queryset(self, request, queryset):
        if self.value() == '0':
            subquery = In.objects.filter(expiry_date__lte=datetime.now()).values_list('batch_id', flat=True)
            queryset = queryset.filter(batch_id__in=subquery)
            return queryset
        elif self.value() == '1':
            subquery = In.objects.filter(expiry_date__gt=datetime.now(),
                                         expiry_date__lte=datetime.now()+timedelta(7))\
                                 .values_list('batch_id', flat=True)
            queryset = queryset.filter(batch_id__in=subquery)
            return queryset
        elif self.value() == '2':
            subquery = In.objects.filter(expiry_date__gt=datetime.now() + timedelta(7)) \
                                 .values_list('batch_id', flat=True)
            queryset = queryset.filter(batch_id__in=subquery)
            return queryset
        else:
            return queryset