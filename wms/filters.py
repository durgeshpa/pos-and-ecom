from datetime import datetime, timedelta

from dal import autocomplete
from django.contrib.admin import SimpleListFilter, ListFilter, FieldListFilter
from django.contrib.auth.models import Permission
from django.db.models import Q, F

from products.models import ParentProduct
from shops.models import Shop
from wms.models import InventoryType, InventoryState, In, PickupBinInventory, Pickup, Zone
from accounts.models import User


class WarehousesAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Shop.objects.none()

        qs = Shop.objects.filter(
            shop_type__shop_type='sp')

        if self.q:
            qs = qs.filter(Q(shop_name__icontains=self.q) | Q(id__icontains=self.q))
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

        qs = InventoryState.objects.exclude(inventory_state='available')

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


class SupervisorFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()
        perm = Permission.objects.get(codename='can_have_zone_supervisor_permission')
        qs = User.objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm)).distinct()

        if self.q:
            qs = qs.filter(Q(first_name__icontains=self.q) | Q(phone_number__icontains=self.q))
        return qs


class CoordinatorFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()
        perm = Permission.objects.get(codename='can_have_zone_coordinator_permission')
        qs = User.objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm)).distinct()

        if self.q:
            qs = qs.filter(Q(first_name__icontains=self.q) | Q(phone_number__icontains=self.q))
        return qs


class CoordinatorAvailableFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()
        perm = Permission.objects.get(codename='can_have_zone_coordinator_permission')
        qs = User.objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm)).exclude(
            id__in=Zone.objects.values_list('coordinator', flat=True).distinct('coordinator')).distinct()

        if self.q:
            qs = qs.filter(Q(first_name__icontains=self.q) | Q(phone_number__icontains=self.q))
        return qs


class ParentProductFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return ParentProduct.objects.none()
        qs = ParentProduct.objects.all()

        if self.q:
            qs = qs.filter(Q(name__icontains=self.q) | Q(product_hsn__icontains=self.q))
        return qs


class ZoneFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Zone.objects.none()

        if self.request.user.has_perm('wms.can_have_zone_warehouse_permission'):
            qs = Zone.objects.all()
        elif self.request.user.has_perm('wms.can_have_zone_supervisor_permission'):
            qs = Zone.objects.filter(supervisor=self.request.user)
        elif self.request.user.has_perm('wms.can_have_zone_coordinator_permission'):
            qs = Zone.objects.filter(coordinator=self.request.user)
        else:
            qs = Zone.objects.none()

        # qs = Zone.objects.all()

        warehouse = self.forwarded.get('warehouse', None)
        if warehouse:
            qs = qs.filter(warehouse=warehouse)

        if self.q:
            qs = qs.filter(Q(id__icontains=self.q) | Q(zone_number__icontains=self.q) | Q(name__icontains=self.q) | Q(
                supervisor__first_name__icontains=self.q) | Q(supervisor__phone_number__icontains=self.q) | Q(
                coordinator__first_name__icontains=self.q) | Q(coordinator__phone_number__icontains=self.q) | Q(
                warehouse__id__icontains=self.q) | Q(warehouse__shop_name__icontains=self.q))
        return qs


class UserFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()

        qs = User.objects.all()

        if self.q:
            qs = qs.filter(Q(phone_number__icontains=self.q) | Q(first_name__icontains=self.q) | Q(
                last_name__icontains=self.q))
        return qs


class PickupStatusFilter(SimpleListFilter):
    title = 'Pickup Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return PickupBinInventory.PICKUP_STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value() == '0':
            queryset = queryset.filter(~Q(pickup__status__in=[Pickup.pickup_status_choices.picking_complete,
                                                              Pickup.pickup_status_choices.picking_cancelled]))
        elif self.value() == '1':
            queryset = queryset.filter(~Q(pickup_quantity=F('quantity')),
                                       pickup__status=Pickup.pickup_status_choices.picking_complete)
        elif self.value() == '2':
            queryset = queryset.filter(Q(pickup_quantity=F('quantity')),
                                       pickup__status=Pickup.pickup_status_choices.picking_complete)
        elif self.value() == '3':
            queryset = queryset.filter(pickup__status=Pickup.pickup_status_choices.picking_cancelled)
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