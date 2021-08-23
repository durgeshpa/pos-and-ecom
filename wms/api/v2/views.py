import logging

from dal import autocomplete
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import authentication
from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group

from products.models import Product
from retailer_backend.utils import SmallOffsetPagination
from shops.models import Shop
from wms.common_functions import get_response, serializer_error
from wms.services import check_warehouse_manager
from .serializers import InOutLedgerSerializer, InOutLedgerCSVSerializer, ZoneCrudSerializers, UserSerializers
from wms.common_validators import validate_ledger_request, validate_data_format, validate_id, validate_id_and_warehouse
from wms.models import Zone

# Logger
from wms.services import zone_search, user_search

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class InOutLedger(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = InOutLedgerSerializer

    def get(self, request):
        """ GET In Out Ledger """
        validated_data = validate_ledger_request(request)
        if 'error' in validated_data:
            return get_response(validated_data['error'])
        validated_data = validated_data['data']

        self.queryset = Product.objects.filter(product_sku=validated_data['sku'])
        if not self.queryset:
            return get_response("Invalid SKU!")
        serializer = self.serializer_class(self.queryset, many=True,
                                           context={'start_date': validated_data['start_date'],
                                                    'end_date': validated_data['end_date']})
        msg = "" if serializer.data else "No data found"
        return get_response(msg, serializer.data, True)


class InOutLedgerCSV(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = InOutLedgerCSVSerializer

    def post(self, request):
        """ POST API for Download InOutLedger CSV """

        info_logger.info("InOutLedgerCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save(created_by=request.user)
            info_logger.info("InOutLedgerCSV Exported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class ProductSkuAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Product.objects.all()
        if self.q:
            qs = qs.filter(Q(product_sku__icontains=self.q) | Q(product_name__icontains=self.q))
        return qs


class WarehouseAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type='sp')
        if self.q:
            qs = qs.filter(Q(shop_name__icontains=self.q))
            # qs = qs.filter(Q(shop_name__icontains=self.q) | Q(shop_owner__phone_number__icontains=self.q) |
            #                Q(shop_owner__first_name__icontains=self.q) | Q(shop_owner__last_name__icontains=self.q))
        return qs


class ZoneCrudView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Zone.objects. \
        select_related('warehouse', 'warehouse__shop_owner', 'warehouse__shop_type',
                       'warehouse__shop_type__shop_sub_type', 'supervisor', 'coordinator'). \
        prefetch_related('putaway_users'). \
        only('id', 'warehouse__id', 'warehouse__status', 'warehouse__shop_name', 'warehouse__shop_type',
             'warehouse__shop_type__shop_type', 'warehouse__shop_type__shop_sub_type',
             'warehouse__shop_type__shop_sub_type__retailer_type_name',
             'warehouse__shop_owner', 'warehouse__shop_owner__first_name', 'warehouse__shop_owner__last_name',
             'warehouse__shop_owner__phone_number', 'supervisor__id', 'supervisor__first_name', 'supervisor__last_name',
             'supervisor__phone_number', 'coordinator__id', 'coordinator__first_name',
             'coordinator__last_name', 'coordinator__phone_number', 'created_at', 'updated_at',). \
        order_by('-id')
    serializer_class = ZoneCrudSerializers

    def get(self, request):
        """ GET API for Zone """
        info_logger.info("Zone GET api called.")
        zone_total_count = self.queryset.count()
        if not request.GET.get('warehouse'):
            return get_response("'warehouse' | This is mandatory.")
        if request.GET.get('id'):
            """ Get Zone for specific ID """
            id_validation = validate_id_and_warehouse(
                self.queryset, int(request.GET.get('id')), int(request.GET.get('warehouse')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            zones_data = id_validation['data']
        else:
            """ GET Zone List """
            self.queryset = self.search_filter_zones_data()
            zone_total_count = self.queryset.count()
            zones_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(zones_data, many=True)
        msg = f"total count {zone_total_count}" if zones_data else "no zone found"
        return get_response(msg, serializer.data, True)

    @check_warehouse_manager
    def post(self, request):
        """ POST API for Zone Creation with Image """

        info_logger.info("Zone POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Zone Created Successfully.")
            return get_response('zone created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    @check_warehouse_manager
    def put(self, request):
        """ PUT API for Zone Updation """

        info_logger.info("Zone PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update zone', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        zone_instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=zone_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Zone Updated Successfully.")
            return get_response('zone updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    @check_warehouse_manager
    def delete(self, request):
        """ Delete Zone """

        info_logger.info("Zone DELETE api called.")
        if not request.data.get('zone_id'):
            return get_response('please provide zone_id', False)
        try:
            for z_id in request.data.get('zone_id'):
                zone_id = self.queryset.get(id=int(z_id))
                try:
                    zone_id.delete()
                except:
                    return get_response(f'can not delete zone | {zone_id.id} | getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid zone id {z_id}', False)
        return get_response('zone were deleted successfully!', True)

    def search_filter_zones_data(self):
        search_text = self.request.GET.get('search_text')
        warehouse = self.request.GET.get('warehouse')
        supervisor = self.request.GET.get('supervisor')
        coordinator = self.request.GET.get('coordinator')

        '''search using warehouse name, supervisor's firstname  and coordinator's firstname'''
        if search_text:
            self.queryset = zone_search(self.queryset, search_text)

        '''Filters using warehouse, supervisor, coordinator'''
        if warehouse:
            self.queryset = self.queryset.filter(warehouse__id=warehouse)

        if supervisor:
            self.queryset = self.queryset.filter(supervisor__id=supervisor)

        if coordinator:
            self.queryset = self.queryset.filter(coordinator__id=coordinator)

        return self.queryset.distinct('id')


class ZoneSupervisorsView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = get_user_model().objects.values('id', 'phone_number', 'first_name', 'last_name').order_by('-id')
    serializer_class = UserSerializers

    def get(self, request):
        info_logger.info("Zone Supervisors api called.")
        """ GET Zone Supervisors List """
        perm = Permission.objects.get(codename='can_have_zone_supervisor_permission')
        self.queryset = self.queryset.filter(Q(groups__permissions=perm) | Q(user_permissions=perm)).distinct()
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = user_search(self.queryset, search_text)
        zone_supervisor = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(zone_supervisor, many=True)
        msg = "" if zone_supervisor else "no zone supervisors found"
        return get_response(msg, serializer.data, True)


class ZoneCoordinatorsView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = get_user_model().objects.values('id', 'phone_number', 'first_name', 'last_name').order_by('-id')
    serializer_class = UserSerializers

    def get(self, request):
        info_logger.info("Zone Coordinators api called.")
        """ GET Zone Coordinators List """
        perm = Permission.objects.get(codename='can_have_zone_coordinator_permission')
        self.queryset = self.queryset.filter(Q(groups__permissions=perm) | Q(user_permissions=perm)).distinct()
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = user_search(self.queryset, search_text)
        zone_coordinator = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(zone_coordinator, many=True)
        msg = "" if zone_coordinator else "no zone coordinators found"
        return get_response(msg, serializer.data, True)


class ZonePutawaysView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = get_user_model().objects.values('id', 'phone_number', 'first_name', 'last_name').order_by('-id')
    serializer_class = UserSerializers

    def get(self, request):
        info_logger.info("Zone Putaways api called.")
        """ GET Zone Putaways List """
        group = Group.objects.get(name='Putaway')
        self.queryset = self.queryset.filter(groups=group)
        self.queryset = self.queryset. \
            exclude(id__in=Zone.objects.values_list('putaway_users', flat=True).distinct('putaway_users'))
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = user_search(self.queryset, search_text)
        zone_putaway_users = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(zone_putaway_users, many=True)
        msg = "" if zone_putaway_users else "no putaway users found"
        return get_response(msg, serializer.data, True)


