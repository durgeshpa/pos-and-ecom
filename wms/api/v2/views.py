import copy
import logging
from datetime import datetime
from itertools import groupby

from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q, OuterRef, Subquery, Count, CharField, Case, When
from django.db.models.functions import Cast
from django.http import HttpResponse
from rest_framework import authentication
from rest_framework import generics
from rest_framework.permissions import AllowAny

from gram_to_brand.common_validators import validate_assortment_against_warehouse_and_product
from gram_to_brand.models import GRNOrder
from products.models import Product
from retailer_backend.utils import SmallOffsetPagination
from shops.models import Shop
from wms.common_functions import get_response, serializer_error, get_logged_user_wise_query_set
from wms.common_validators import validate_ledger_request, validate_data_format, validate_id, \
    validate_id_and_warehouse, validate_putaways_by_token_id_and_zone, validate_putaway_user_by_zone, validate_zone, \
    validate_putaway_user_against_putaway
from wms.models import Zone, WarehouseAssortment, Bin, BIN_TYPE_CHOICES, ZonePutawayUserAssignmentMapping, Putaway, In, \
    PutawayBinInventory, Pickup
from wms.services import check_warehouse_manager, check_whc_manager_coordinator_supervisor, check_putaway_user, \
    zone_putaway_assignments_search, putaway_search, check_whc_manager_coordinator_supervisor_putaway
# Logger
from wms.services import zone_search, user_search, whc_assortment_search, bin_search
from .serializers import InOutLedgerSerializer, InOutLedgerCSVSerializer, ZoneCrudSerializers, UserSerializers, \
    WarehouseAssortmentCrudSerializers, WarehouseAssortmentExportAsCSVSerializers, BinExportAsCSVSerializers, \
    WarehouseAssortmentSampleCSVSerializer, WarehouseAssortmentUploadSerializer, BinCrudSerializers, \
    BinExportBarcodeSerializers, ZonePutawayAssignmentsCrudSerializers, CancelPutawayCrudSerializers, \
    UpdateZoneForCancelledPutawaySerializers, GroupedByGRNPutawaysSerializers, \
    PutawayItemsCrudSerializer, PutawaySerializers, PutawayModelSerializer, ZoneFilterSerializer, \
    PostLoginUserSerializers, PutawayActionSerializer, POSummarySerializers, ZonewiseSummarySerializers, \
    PutawaySummarySerializers

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
        only('id', 'zone_number', 'name', 'warehouse__id', 'warehouse__status', 'warehouse__shop_name',
             'warehouse__shop_type', 'warehouse__shop_type__shop_type', 'warehouse__shop_type__shop_sub_type',
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
                    mappings = ZonePutawayUserAssignmentMapping.objects.filter(zone=zone_id)
                    if mappings:
                        mappings.delete()
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


class WarehouseAssortmentCrudView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = WarehouseAssortment.objects. \
        select_related('warehouse', 'warehouse__shop_owner', 'warehouse__shop_type',
                       'warehouse__shop_type__shop_sub_type', 'product',
                       'zone', 'zone__warehouse', 'zone__warehouse__shop_owner', 'zone__warehouse__shop_type',
                       'zone__warehouse__shop_type__shop_sub_type', 'zone__supervisor', 'zone__coordinator'). \
        prefetch_related('zone__putaway_users'). \
        only('id', 'warehouse__id', 'warehouse__status', 'warehouse__shop_name', 'warehouse__shop_type',
             'warehouse__shop_type__shop_type', 'warehouse__shop_type__shop_sub_type',
             'warehouse__shop_type__shop_sub_type__retailer_type_name',
             'warehouse__shop_owner', 'warehouse__shop_owner__first_name', 'warehouse__shop_owner__last_name',
             'warehouse__shop_owner__phone_number', 'zone__id', 'zone__warehouse__id', 'zone__warehouse__status',
             'zone__warehouse__shop_name', 'zone__warehouse__shop_type',
             'zone__warehouse__shop_type__shop_type', 'zone__warehouse__shop_type__shop_sub_type',
             'zone__warehouse__shop_type__shop_sub_type__retailer_type_name', 'zone__warehouse__shop_owner',
             'zone__warehouse__shop_owner__first_name', 'zone__warehouse__shop_owner__last_name',
             'zone__warehouse__shop_owner__phone_number', 'zone__supervisor__id', 'zone__supervisor__first_name',
             'zone__supervisor__last_name', 'zone__supervisor__phone_number', 'zone__coordinator__id',
             'zone__coordinator__first_name', 'zone__coordinator__last_name', 'zone__coordinator__phone_number',
             'product__id', 'product__name', 'created_at', 'updated_at',). \
        order_by('-id')
    serializer_class = WarehouseAssortmentCrudSerializers

    def get(self, request):
        """ GET API for WarehouseAssortment """
        info_logger.info("WarehouseAssortment GET api called.")
        whc_assortment_total_count = self.queryset.count()
        if not request.GET.get('warehouse'):
            return get_response("'warehouse' | This is mandatory.")
        if request.GET.get('id'):
            """ Get WarehouseAssortment for specific ID """
            id_validation = validate_id_and_warehouse(
                self.queryset, int(request.GET.get('id')), int(request.GET.get('warehouse')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            whc_assortments_data = id_validation['data']
        else:
            """ GET WarehouseAssortment List """
            self.queryset = self.search_filter_whc_assortments_data()
            whc_assortment_total_count = self.queryset.count()
            whc_assortments_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(whc_assortments_data, many=True)
        msg = f"total count {whc_assortment_total_count}" if whc_assortments_data else "no whc_assortment found"
        return get_response(msg, serializer.data, True)

    @check_warehouse_manager
    def post(self, request):
        """ POST API for WarehouseAssortment Creation """

        info_logger.info("WarehouseAssortment POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("WarehouseAssortment Created Successfully.")
            return get_response('whc_assortment created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    @check_warehouse_manager
    def put(self, request):
        """ PUT API for WarehouseAssortment Updation """

        info_logger.info("WarehouseAssortment PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update whc_assortment', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        whc_assortment_instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=whc_assortment_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("WarehouseAssortment Updated Successfully.")
            return get_response('whc_assortment updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    @check_warehouse_manager
    def delete(self, request):
        """ Delete WarehouseAssortment """

        info_logger.info("Zone DELETE api called.")
        if not request.data.get('whc_assortment_id'):
            return get_response('please provide whc_assortment_id', False)
        try:
            for whc_ass_id in request.data.get('whc_assortment_id'):
                whc_assortment_id = self.queryset.get(id=int(whc_ass_id))
                try:
                    whc_assortment_id.delete()
                except:
                    return get_response(f'can not delete whc_assortment | {whc_assortment_id.id} | getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid whc_assortment id {whc_ass_id}', False)
        return get_response('whc_assortment were deleted successfully!', True)

    def search_filter_whc_assortments_data(self):
        search_text = self.request.GET.get('search_text')
        warehouse = self.request.GET.get('warehouse')
        product = self.request.GET.get('product')
        zone = self.request.GET.get('zone')

        '''search using warehouse name, product's name  and zone's coordination / supervisor firstname'''
        if search_text:
            self.queryset = whc_assortment_search(self.queryset, search_text)

        '''Filters using warehouse, product, zone'''
        if warehouse:
            self.queryset = self.queryset.filter(warehouse__id=warehouse)

        if product:
            self.queryset = self.queryset.filter(product__id=product)

        if zone:
            self.queryset = self.queryset.filter(zone__id=zone)

        return self.queryset.distinct('id')


class WarehouseAssortmentExportAsCSVView(generics.CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = WarehouseAssortmentExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected Warehouse Assortment CSV """

        info_logger.info("WarehouseAssortmentExportAsCSVView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("Warehouse Assortment CSV exported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class WarehouseAssortmentSampleCSV(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = WarehouseAssortmentSampleCSVSerializer

    def post(self, request):
        """ POST API for Download Sample CSV for Warehouse Assortment """

        info_logger.info("WarehouseAssortmentSampleCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save(created_by=request.user)
            info_logger.info("WarehouseAssortmentSampleCSV Exported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class WarehouseAssortmentUploadView(generics.GenericAPIView):
    """
    This class is used to upload csv file for Warehouse Assortment to map the product with zone and warehouse
    """
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = WarehouseAssortmentUploadSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('data uploaded successfully!', serializer.data, True)
        return get_response(serializer_error(serializer), False)


class BinTypeView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for ApprovalStatusList """
        info_logger.info("ApprovalStatusList GET api called.")
        fields = ['id', 'bin_type']
        data = [dict(zip(fields, d)) for d in BIN_TYPE_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class BinCrudView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Bin.objects. \
        select_related('warehouse', 'warehouse__shop_owner', 'warehouse__shop_type',
                       'warehouse__shop_type__shop_sub_type',
                       'zone', 'zone__warehouse', 'zone__warehouse__shop_owner', 'zone__warehouse__shop_type',
                       'zone__warehouse__shop_type__shop_sub_type', 'zone__supervisor', 'zone__coordinator'). \
        prefetch_related('zone__putaway_users'). \
        only('id', 'warehouse__id', 'warehouse__status', 'warehouse__shop_name', 'warehouse__shop_type',
             'warehouse__shop_type__shop_type', 'warehouse__shop_type__shop_sub_type',
             'warehouse__shop_type__shop_sub_type__retailer_type_name',
             'warehouse__shop_owner', 'warehouse__shop_owner__first_name', 'warehouse__shop_owner__last_name',
             'warehouse__shop_owner__phone_number', 'zone__id', 'zone__warehouse__id', 'zone__warehouse__status',
             'zone__warehouse__shop_name', 'zone__warehouse__shop_type',
             'zone__warehouse__shop_type__shop_type', 'zone__warehouse__shop_type__shop_sub_type',
             'zone__warehouse__shop_type__shop_sub_type__retailer_type_name', 'zone__warehouse__shop_owner',
             'zone__warehouse__shop_owner__first_name', 'zone__warehouse__shop_owner__last_name',
             'zone__warehouse__shop_owner__phone_number', 'zone__supervisor__id', 'zone__supervisor__first_name',
             'zone__supervisor__last_name', 'zone__supervisor__phone_number', 'zone__coordinator__id',
             'zone__coordinator__first_name', 'zone__coordinator__last_name', 'zone__coordinator__phone_number',
             'bin_id', 'bin_type', 'is_active', 'bin_barcode_txt', 'bin_barcode', 'created_at', 'modified_at',). \
        order_by('-id')
    serializer_class = BinCrudSerializers

    @check_whc_manager_coordinator_supervisor
    def get(self, request):
        """ GET API for Bin """
        info_logger.info("Bin GET api called.")
        bin_total_count = self.queryset.count()
        if not request.GET.get('warehouse'):
            return get_response("'warehouse' | This is mandatory.")
        if request.GET.get('id'):
            """ Get Bin for specific ID """
            id_validation = validate_id_and_warehouse(
                self.queryset, int(request.GET.get('id')), int(request.GET.get('warehouse')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            bins_data = id_validation['data']
        else:
            """ GET Bin List """
            self.queryset = self.search_filter_bins_data()
            bin_total_count = self.queryset.count()
            bins_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(bins_data, many=True)
        msg = f"total count {bin_total_count}" if bins_data else "no bin found"
        return get_response(msg, serializer.data, True)

    @check_whc_manager_coordinator_supervisor
    def post(self, request):
        """ POST API for Bin Creation """

        info_logger.info("Bin POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save()
            info_logger.info("Bin Created Successfully.")
            return get_response('Bin created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    @check_whc_manager_coordinator_supervisor
    def delete(self, request):
        """ Delete Bin """

        info_logger.info("Zone DELETE api called.")
        if not request.data.get('bin_id'):
            return get_response('please provide bin_id', False)
        try:
            for b_id in request.data.get('bin_id'):
                bin_id = self.queryset.get(id=int(b_id))
                try:
                    bin_id.delete()
                except:
                    return get_response(f'can not delete bin | {bin_id.id} | getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid bin id {b_id}', False)
        return get_response('bin were deleted successfully!', True)

    def search_filter_bins_data(self):
        search_text = self.request.GET.get('search_text')
        warehouse = self.request.GET.get('warehouse')
        bin_type = self.request.GET.get('bin_type')
        is_active = self.request.GET.get('is_active')
        zone = self.request.GET.get('zone')

        '''search using warehouse name, bin_type's name  and zone's coordination / supervisor firstname'''
        if search_text:
            self.queryset = bin_search(self.queryset, search_text)

        '''Filters using warehouse, bin_type, is_active, zone'''
        if warehouse:
            self.queryset = self.queryset.filter(warehouse__id=warehouse)

        if bin_type:
            self.queryset = self.queryset.filter(bin_type=bin_type)

        if is_active:
            self.queryset = self.queryset.filter(is_active=is_active)

        if zone:
            self.queryset = self.queryset.filter(zone__id=zone)

        return self.queryset.distinct('id')


class BinExportAsCSVView(generics.CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BinExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected Bins CSV """

        info_logger.info("BinExportAsCSVView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("Bins CSV exported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class BinExportBarcodeView(generics.CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BinExportBarcodeSerializers

    def post(self, request):
        """ POST API for Download Selected Bins CSV """

        info_logger.info("BinExportBarcodeView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("Bins Barcode exported successfully ")
            return response
        return get_response(serializer_error(serializer), False)


class ZonePutawayAssignmentsView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ZonePutawayUserAssignmentMapping.objects. \
        select_related('user', 'zone', 'zone__warehouse', 'zone__warehouse__shop_owner', 'zone__warehouse__shop_type',
                       'zone__warehouse__shop_type__shop_sub_type', 'zone__supervisor', 'zone__coordinator'). \
        prefetch_related('zone__putaway_users'). \
        only('id', 'user', 'zone__id', 'zone__warehouse__id', 'zone__warehouse__status',
             'zone__warehouse__shop_name', 'zone__warehouse__shop_type',
             'zone__warehouse__shop_type__shop_type', 'zone__warehouse__shop_type__shop_sub_type',
             'zone__warehouse__shop_type__shop_sub_type__retailer_type_name', 'zone__warehouse__shop_owner',
             'zone__warehouse__shop_owner__first_name', 'zone__warehouse__shop_owner__last_name',
             'zone__warehouse__shop_owner__phone_number', 'zone__supervisor__id', 'zone__supervisor__first_name',
             'zone__supervisor__last_name', 'zone__supervisor__phone_number', 'zone__coordinator__id',
             'zone__coordinator__first_name', 'zone__coordinator__last_name', 'zone__coordinator__phone_number',
             'zone__putaway_users__id', 'zone__putaway_users__first_name', 'zone__putaway_users__last_name',
             'zone__putaway_users__phone_number', 'last_assigned_at', 'created_at', 'updated_at', ). \
        order_by('-id')
    serializer_class = ZonePutawayAssignmentsCrudSerializers

    def get(self, request):
        """ GET API for Zone """
        info_logger.info("Zone GET api called.")
        if request.GET.get('id'):
            """ Get Zone for specific ID """
            total_count = self.queryset.count()
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            data = id_validation['data']
        else:
            """ GET Zone List """
            self.queryset = self.search_filter_zone_putaway_assignments_data()
            total_count = self.queryset.count()
            data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(data, many=True)
        msg = f"total count {total_count}" if data else "no zone putaway assignments found"
        return get_response(msg, serializer.data, True)

    def search_filter_zone_putaway_assignments_data(self):
        """
        :- Search using warehouse name, supervisor's id  and coordinator's id, user's id
        :- Filters using warehouse, supervisor, coordinator
        @return: queryset
        """
        search_text = self.request.GET.get('search_text')
        warehouse = self.request.GET.get('warehouse')
        supervisor = self.request.GET.get('supervisor')
        coordinator = self.request.GET.get('coordinator')
        user = self.request.GET.get('user')

        '''search using warehouse name, supervisor's id  and coordinator's id, user's id'''
        if search_text:
            self.queryset = zone_putaway_assignments_search(self.queryset, search_text)

        '''Filters using warehouse, supervisor, coordinator'''
        if warehouse:
            """
                Filter queryset with warehouse id
            """
            self.queryset = self.queryset.filter(zone__warehouse__id=warehouse)

        if supervisor:
            """
                Filter queryset with upervisor id
            """
            self.queryset = self.queryset.filter(zone__supervisor__id=supervisor)

        if coordinator:
            """
                Filter queryset with coordinator id
            """
            self.queryset = self.queryset.filter(zone__coordinator__id=coordinator)

        if user:
            """
                Filter queryset with user id
            """
            self.queryset = self.queryset.filter(user__id=user)

        return self.queryset.distinct('id')


class CancelPutawayCrudView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Putaway.objects. \
        select_related('warehouse', 'warehouse__shop_owner', 'warehouse__shop_type',
                       'warehouse__shop_type__shop_sub_type', 'putaway_user', 'inventory_type'). \
        only('id', 'warehouse__id', 'warehouse__status', 'warehouse__shop_name', 'warehouse__shop_type',
             'warehouse__shop_type__shop_type', 'warehouse__shop_type__shop_sub_type', 'warehouse__shop_owner',
             'warehouse__shop_type__shop_sub_type__retailer_type_name', 'warehouse__shop_owner__first_name',
             'warehouse__shop_owner__last_name', 'warehouse__shop_owner__phone_number', 'putaway_user__id',
             'putaway_user__first_name', 'putaway_user__last_name', 'putaway_user__phone_number', 'inventory_type__id',
             'inventory_type__inventory_type', 'created_at', 'modified_at', 'putaway_quantity',). \
        order_by('-id')
    serializer_class = CancelPutawayCrudSerializers

    @check_whc_manager_coordinator_supervisor
    def put(self, request):
        """ PUT API for Putaway Updation """
        info_logger.info("Putaway PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update putaway', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        putaway_instance = id_validation['data'].last()
        if putaway_instance.status == str(Putaway.PUTAWAY_STATUS_CHOICE.CANCELLED):
            return get_response("Putaway id: " + str(putaway_instance.pk) + " is already cancelled.")
        elif putaway_instance.status not in [Putaway.NEW, Putaway.ASSIGNED] or putaway_instance.putaway_quantity != 0:
            return get_response("Putaway id: " + str(putaway_instance.pk) + " is not allowed to be cancel.")
        else:
            putaway_instance.status = Putaway.PUTAWAY_STATUS_CHOICE.CANCELLED

        serializer = self.serializer_class(
            instance=putaway_instance, data=PutawayModelSerializer(putaway_instance).data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Putaway Updated Successfully.")
            return get_response('putaway cancelled successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


class PutawayItemsCrudView(generics.GenericAPIView):
    """API view for Putaway"""
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        select_related('warehouse', 'warehouse__shop_owner', 'warehouse__shop_type',
                       'warehouse__shop_type__shop_sub_type', 'putaway_user',
                       'sku', 'sku__parent_product').\
        only('id', 'warehouse__id', 'warehouse__status', 'warehouse__shop_name', 'warehouse__shop_type',
             'warehouse__shop_type__shop_type', 'warehouse__shop_type__shop_sub_type',
             'warehouse__shop_type__shop_sub_type__retailer_type_name',
             'warehouse__shop_owner', 'warehouse__shop_owner__first_name', 'warehouse__shop_owner__last_name',
             'warehouse__shop_owner__phone_number', 'putaway_user__id', 'putaway_user__first_name',
             'putaway_user__last_name', 'putaway_user__phone_number', 'sku__product_sku', 'sku__product_name',
             'sku__parent_product__id', 'sku__parent_product__name', 'created_at', 'modified_at'). \
        order_by('-id')

    serializer_class = PutawayItemsCrudSerializer

    def get(self, request):
        """ GET API for Putaway """
        putaway_total_count = self.queryset.count()
        if not request.GET.get('warehouse'):
            return get_response("'warehouse' | This is mandatory.")
        if not request.GET.get('putaway_type'):
            return get_response("'putaway type' | This is mandatory.")
        if not request.GET.get('putaway_type_id'):
            return get_response("'putaway_type_id' | This is mandatory.")
        if request.GET.get('id'):
            """ Get Putaways for specific warehouse """
            id_validation = validate_id_and_warehouse(
                self.queryset, int(request.GET.get('id')), int(request.GET.get('warehouse')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            putaway_data = id_validation['data']

        else:
            """ GET Putaway List """
            self.queryset = self.search_filter_putaway_data()
            putaway_total_count = self.queryset.count()
            putaway_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(putaway_data, many=True)
        msg = f"total count {putaway_total_count}" if putaway_data else "no putaway found"
        return get_response(msg, serializer.data, True)

    @check_putaway_user
    def put(self, request):
        """ Updates the given Putaway"""
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update putaway', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        putaway_instance = id_validation['data'].last()
        serializer = self.serializer_class(instance=putaway_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Putaway Updated Successfully.")
            return get_response('Putaway updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_putaway_data(self):
        """ Filters the Putaway data based on request"""
        search_text = self.request.GET.get('search_text')
        warehouse = self.request.GET.get('warehouse')
        zone = self.request.GET.get('zone')
        product = self.request.GET.get('product')
        date = self.request.GET.get('date')
        status = self.request.GET.get('status')
        putaway_type = self.request.GET.get('putaway_type')
        putaway_type_id = self.request.GET.get('putaway_type_id')
        is_zone_not_assigned = self.request.GET.get('is_zone_not_assigned')

        '''search using warehouse name, product's name'''
        if search_text:
            self.queryset = putaway_search(self.queryset, search_text)

        '''Filters using warehouse, product, zone, date, status, putaway_type_id'''
        if warehouse:
            self.queryset = self.queryset.filter(warehouse__id=warehouse)

        if product:
            self.queryset = self.queryset.filter(sku__id=product)

        if date:
            self.queryset = self.queryset.filter(created_at__date=date)

        if zone:
            zone_product_ids = WarehouseAssortment.objects.filter(zone__id=zone).values_list('product_id', flat=True)
            self.queryset = self.queryset.filter(sku__parent_product__id__in=zone_product_ids)

        elif is_zone_not_assigned:
            no_zone_product_ids = WarehouseAssortment.objects.filter(zone__isnull=True).values_list('product_id', flat=True)
            self.queryset = self.queryset.filter(sku__parent_product__id__in=no_zone_product_ids)

        if status:
            self.queryset = self.queryset.filter(status=status)

        if putaway_type_id:
            if putaway_type == 'GRN':
                self.queryset = self.queryset.filter(putaway_type=putaway_type,
                                                     putaway_type_id__in=In.objects.filter(in_type=putaway_type,
                                                                                           in_type_id=putaway_type_id)
                                                     .annotate(id_key=Cast('id', CharField()))
                                                     .values_list('id_key', flat=True))
            if putaway_type == 'picking_cancelled':
                self.queryset = self.queryset.filter(putaway_type=putaway_type,
                                                     putaway_type_id__in=Pickup.objects.filter(
                                                         pickup_type_id=putaway_type_id)
                                                     .annotate(id_key=Cast('id', CharField()))
                                                     .values_list('id_key', flat=True))
            if putaway_type in ['RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING']:
                self.queryset = self.queryset.filter(putaway_type=putaway_type, putaway_type_id=putaway_type_id)
        return self.queryset.distinct('id')


class UpdateZoneForCancelledPutawayView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = UpdateZoneForCancelledPutawaySerializers

    @check_whc_manager_coordinator_supervisor
    def put(self, request):
        """ PUT API for Update Zone For Cancelled Putaways """

        info_logger.info("WarehouseAssortment PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if not ('warehouse' in modified_data and modified_data['warehouse']) or \
                not ('sku' in modified_data and modified_data['sku']) or \
                not ('zone' in modified_data and modified_data['zone']):
            return get_response(
                'please provide warehouse, sku and zone to update zone for cancelled putaways', False)

        # validations for input warehouse, sku
        id_validation = validate_assortment_against_warehouse_and_product(
            int(modified_data['warehouse']), modified_data['sku'])
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        whc_assortment_instance = id_validation['data']

        serializer = self.serializer_class(instance=whc_assortment_instance, data=modified_data)
        if serializer.is_valid():
            resp = serializer.save(updated_by=request.user)
            info_logger.info("Zone assigned for Cancelled Putaways Successfully.")
            return get_response('Zone assigned for Cancelled Putaways Successfully!', resp.data)
        return get_response(serializer_error(serializer), False)


class PutawayTypeListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for PutawayTypeList """
        info_logger.info("PutawayTypeList GET api called.")
        putaway_type_list = ['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']
        data = [{'id': d, 'type': d} for d in putaway_type_list]
        msg = ""
        return get_response(msg, data, True)


class GroupedByGRNPutawaysView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        annotate(token_id=Case(
                    When(putaway_type='GRN',
                         then=Cast(Subquery(In.objects.filter(
                             id=Cast(OuterRef('putaway_type_id'), models.IntegerField())).
                                 order_by('-in_type_id').values('in_type_id')[:1]), models.CharField())),
                    When(putaway_type='picking_cancelled',
                         then=Cast(Subquery(Pickup.objects.filter(
                             id=Cast(OuterRef('putaway_type_id'), models.IntegerField())).
                                            order_by('-pickup_type_id').
                                            values('pickup_type_id')[:1]), models.CharField())),
                    When(putaway_type__in=['RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING'],
                         then=Cast('putaway_type_id', models.CharField())),
                    output_field=models.CharField(),
                 ),
                 zone=Subquery(WarehouseAssortment.objects.filter(
                     warehouse=OuterRef('warehouse'), product=OuterRef('sku__parent_product')).values('zone')[:1])
                 ). \
        exclude(zone__isnull=True). \
        exclude(token_id__isnull=True). \
        values('token_id', 'zone', 'putaway_user', 'status', 'putaway_type', 'created_at__date'). \
        annotate(total_items=Count('token_id')).order_by('-created_at__date')
    serializer_class = GroupedByGRNPutawaysSerializers

    @check_whc_manager_coordinator_supervisor_putaway
    def get(self, request):
        """ GET API for Putaways grouped by GRN """
        info_logger.info("Putaway GET api called.")
        """ GET Putaway List """

        self.queryset = get_logged_user_wise_query_set(self.request.user, self.queryset)
        self.queryset = self.filter_grouped_putaways_data()
        putaways_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(putaways_data, many=True)
        msg = "" if putaways_data else "no putaway found"
        return get_response(msg, serializer.data, True)

    def filter_grouped_putaways_data(self):
        token_id = self.request.GET.get('token_id')
        zone = self.request.GET.get('zone')
        putaway_user = self.request.GET.get('putaway_user')
        putaway_type = self.request.GET.get('putaway_type')
        status = self.request.GET.get('status')
        created_at = self.request.GET.get('created_at')

        '''Filters using token_id, zone, putaway_user, putaway_type'''
        if token_id:
            self.queryset = self.queryset.filter(token_id=token_id)

        if zone:
            self.queryset = self.queryset.filter(zone=zone)

        if putaway_user:
            self.queryset = self.queryset.filter(putaway_user=putaway_user)

        if putaway_type:
            self.queryset = self.queryset.filter(putaway_type=putaway_type)

        if status:
            if status == Putaway.ASSIGNED:
                self.queryset = self.queryset.filter(status__in=[Putaway.ASSIGNED, Putaway.INITIATED])
            else:
                self.queryset = self.queryset.filter(status=status)

        if created_at:
            try:
                created_at = datetime.strptime(created_at, "%Y-%m-%d")
                self.queryset = self.queryset.filter(created_at__date=created_at)
            except Exception as e:
                error_logger.error(e)

        return self.queryset


class AssignPutawayUserByGRNAndZoneView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        select_related('warehouse', 'warehouse__shop_owner', 'warehouse__shop_type', 'sku',
                       'warehouse__shop_type__shop_sub_type', 'putaway_user', 'inventory_type'). \
        prefetch_related('sku__product_pro_image'). \
        annotate(token_id=Case(
                    When(putaway_type='GRN',
                         then=Cast(Subquery(In.objects.filter(
                             id=Cast(OuterRef('putaway_type_id'), models.IntegerField())).
                                            order_by('-in_type_id').values('in_type_id')[:1]), models.CharField())),
                    When(putaway_type='picking_cancelled',
                         then=Cast(Subquery(Pickup.objects.filter(
                             id=Cast(OuterRef('putaway_type_id'), models.IntegerField())).
                                            order_by('-pickup_type_id').
                                            values('pickup_type_id')[:1]), models.CharField())),
                    When(putaway_type__in=['RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING'],
                         then=Cast('putaway_type_id', models.CharField())),
                    output_field=models.CharField(),
                ),
                    zone_id=Subquery(WarehouseAssortment.objects.filter(
                        warehouse=OuterRef('warehouse'), product=OuterRef('sku__parent_product')).values('zone')[:1])
                ). \
        exclude(zone_id__isnull=True). \
        exclude(token_id__isnull=True). \
        order_by('-id')
    serializer_class = PutawaySerializers

    def get(self, request):
        """ GET API for Zone """
        info_logger.info("Zone GET api called.")
        if request.GET.get('id'):
            """ Get Zone for specific ID """
            total_count = self.queryset.count()
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            data = id_validation['data']
        else:
            """ GET Zone List """
            self.queryset = self.search_filter_zone_putaway_assignments_data()
            total_count = self.queryset.count()
            data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(data, many=True)
        msg = f"total count {total_count}" if data else "no zone putaway assignments found"
        return get_response(msg, serializer.data, True)

    @check_whc_manager_coordinator_supervisor
    def put(self, request):
        """ PUT API for Putaway Updation """
        info_logger.info("Putaway PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'token_id' not in modified_data or not modified_data['token_id'] or 'zone_id' not in modified_data or not \
                modified_data['zone_id'] or 'putaway_user' not in modified_data or not modified_data['putaway_user']:
            return get_response('please provide token_id, zone_id and putaway_user to update putaway', False)

        # validations for input id
        id_validation = validate_putaways_by_token_id_and_zone(modified_data['token_id'], int(modified_data['zone_id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        putaway_instances = id_validation['data']

        pu_validation = validate_putaway_user_by_zone(int(modified_data['zone_id']), int(modified_data['putaway_user']))
        if 'error' in pu_validation:
            return get_response(pu_validation['error'])
        putaway_user = pu_validation['data']

        putaways_reflected = [x.id for x in putaway_instances]
        if putaway_instances.last().putaway_user == putaway_user:
            return get_response("Selected putaway user already assigned.")
        putaway_instances.update(putaway_user=putaway_user)
        serializer = self.serializer_class(Putaway.objects.filter(id__in=putaways_reflected), many=True)
        info_logger.info("Putaways Updated Successfully.")
        return get_response('putaways updated successfully!', serializer.data)

    def search_filter_zone_putaway_assignments_data(self):
        token_id = self.request.GET.get('token_id')
        warehouse = self.request.GET.get('warehouse')
        zone = self.request.GET.get('zone')
        putaway_user = self.request.GET.get('putaway_user')
        putaway_type = self.request.GET.get('putaway_type')
        putaway_type_id = self.request.GET.get('putaway_type_id')
        status = self.request.GET.get('status')
        created_at = self.request.GET.get('created_at')

        '''Filters using token_id, warehouse, zone, putaway_user, putaway_type'''
        if token_id:
            self.queryset = self.queryset.filter(token_id=token_id)

        if warehouse:
            self.queryset = self.queryset.filter(warehouse=warehouse)

        if zone:
            self.queryset = self.queryset.filter(zone=zone)

        if putaway_user:
            self.queryset = self.queryset.filter(putaway_user=putaway_user)

        if putaway_type:
            self.queryset = self.queryset.filter(putaway_type=putaway_type)

        if putaway_type_id:
            self.queryset = self.queryset.filter(putaway_type_id=putaway_type_id)

        if status:
            self.queryset = self.queryset.filter(status=status)

        if created_at:
            try:
                created_at = datetime.strptime(created_at, "%Y-%m-%d")
                self.queryset = self.queryset.filter(created_at__date=created_at)
            except Exception as e:
                error_logger.error(e)

        return self.queryset


class PutawayUsersListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = get_user_model().objects.values('id', 'phone_number', 'first_name', 'last_name').order_by('-id')
    serializer_class = UserSerializers

    def get(self, request):
        info_logger.info("Zone Putaway users api called.")
        """ GET Zone Putaway users List """

        if not request.GET.get('zone'):
            return get_response("'zone' | This is mandatory.")
        zone_validation = validate_zone(request.GET.get('zone'))
        if 'error' in zone_validation:
            return get_response(zone_validation['error'])
        zone = zone_validation['data']

        group = Group.objects.get(name='Putaway')
        self.queryset = self.queryset.filter(groups=group)
        self.queryset = self.queryset. \
            filter(putaway_zone_users__id=zone.id)
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = user_search(self.queryset, search_text)
        zone_putaway_users = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(zone_putaway_users, many=True)
        msg = "" if zone_putaway_users else "no putaway users found"
        return get_response(msg, serializer.data, True)


class ZoneFilterView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Zone.objects. \
        select_related('warehouse', 'warehouse__shop_owner', 'warehouse__shop_type',
                       'warehouse__shop_type__shop_sub_type', 'supervisor', 'coordinator'). \
        prefetch_related('putaway_users'). \
        only('id', 'zone_number', 'name', 'warehouse__id', 'warehouse__status', 'warehouse__shop_name',
             'warehouse__shop_type', 'warehouse__shop_type__shop_type', 'warehouse__shop_type__shop_sub_type',
             'warehouse__shop_type__shop_sub_type__retailer_type_name',
             'warehouse__shop_owner', 'warehouse__shop_owner__first_name', 'warehouse__shop_owner__last_name',
             'warehouse__shop_owner__phone_number', 'supervisor__id', 'supervisor__first_name', 'supervisor__last_name',
             'supervisor__phone_number', 'coordinator__id', 'coordinator__first_name',
             'coordinator__last_name', 'coordinator__phone_number', 'created_at', 'updated_at',). \
        order_by('-id')
    serializer_class = ZoneFilterSerializer

    def get(self, request):
        info_logger.info("Zone Coordinators api called.")
        """ GET Zone Coordinators List """
        self.queryset = self.search_filter_zones_data()
        zone_coordinator = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(zone_coordinator, many=True)
        msg = "" if zone_coordinator else "no zone found"
        return get_response(msg, serializer.data, True)

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


class PutawayStatusListView(generics.GenericAPIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for PutawayStatusList """
        info_logger.info("PutawayStatusList GET api called.")
        fields = ['id', 'status']
        data = [dict(zip(fields, d)) for d in Putaway.PUTAWAY_STATUS_CHOICE]
        msg = ""
        return get_response(msg, data, True)


class PutawayRemarkView(generics.GenericAPIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for Putaway Remarks """
        fields = ['id', 'remark']
        data = [dict(zip(fields, d)) for d in PutawayBinInventory.REMARK_CHOICE]
        msg = ""
        return get_response(msg, data, True)


class UserDetailsPostLoginView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = PostLoginUserSerializers
    queryset = get_user_model().objects.all()

    def get(self, request):
        """ GET User Details post login """
        self.queryset = self.queryset.filter(id=request.user.id)
        user = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(user, many=True)
        msg = "" if user else "no user found"
        return get_response(msg, serializer.data, True)


class PerformPutawayView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = PutawayActionSerializer

    @check_putaway_user
    def put(self, request):
        """ PUT API for performing putaway """
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        # validations for assigned putaway user
        id_validation = validate_putaway_user_against_putaway(int(modified_data['id']), request.user.id)
        if 'error' in id_validation:
            return get_response(id_validation['error'], modified_data)
        putaway_instance = id_validation['data']
        serializer = self.serializer_class(instance=putaway_instance, data=modified_data)
        if serializer.is_valid():
            putaway_instance = serializer.save(updated_by=request.user)
            response = PutawayItemsCrudSerializer(putaway_instance)
            info_logger.info(f'Putaway Completed. Id-{putaway_instance.id}, Batch Id-{putaway_instance.batch_id}, '
                             f'Putaway Type Id-{putaway_instance.putaway_type_id}')
            return get_response('Putaways Done Successfully!', response.data)
        return get_response(serializer_error(serializer), False)


class POSummaryView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        annotate(putaway_type_id_key=Case(
                    When(putaway_type='GRN',
                         then=Cast('putaway_type_id', models.IntegerField())
                         ),
                    output_field=models.CharField()
                 ),
                 po_no=Case(
                    When(putaway_type='GRN',
                         then=Cast(
                             Subquery(GRNOrder.objects.filter(
                                 grn_id=Subquery(In.objects.filter(
                                     id=OuterRef(OuterRef('putaway_type_id_key'))
                                 ).order_by('-in_type_id').values('in_type_id')[:1])
                             ).order_by('-order__order_no').values('order__order_no')[:1]), models.CharField())
                         ),
                    When(putaway_type='picking_cancelled',
                         then=Cast(Subquery(Pickup.objects.filter(
                             id=Cast(OuterRef('putaway_type_id'), models.IntegerField())).
                                            order_by('-pickup_type_id').
                                            values('pickup_type_id')[:1]), models.CharField())),
                    When(putaway_type__in=['RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING'],
                         then=Cast('putaway_type_id', models.CharField())),
                    output_field=models.CharField(),
                 ),
                 zone=Subquery(WarehouseAssortment.objects.filter(
                     warehouse=OuterRef('warehouse'), product=OuterRef('sku__parent_product')).values('zone')[:1])
                 ). \
        exclude(zone__isnull=True). \
        exclude(po_no__isnull=True). \
        values('po_no', 'putaway_type').annotate(total_items=Count('po_no')).order_by('-po_no')
    serializer_class = POSummarySerializers

    @check_whc_manager_coordinator_supervisor_putaway
    def get(self, request):
        """ GET API for Putaways po summary """
        info_logger.info("Putaway PO Summary GET api called.")
        """ GET Putaway PO Summary List """
        self.queryset = get_logged_user_wise_query_set(self.request.user, self.queryset)
        self.queryset = self.filter_po_putaways_data()
        putaways_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(putaways_data, many=True)
        msg = "" if putaways_data else "no putaway found"
        return get_response(msg, serializer.data, True)

    def filter_po_putaways_data(self):
        po_no = self.request.GET.get('po_no')
        putaway_type = self.request.GET.get('putaway_type')

        '''Filters using po_no, putaway_type'''
        if po_no:
            self.queryset = self.queryset.filter(po_no=po_no)

        if putaway_type:
            self.queryset = self.queryset.filter(putaway_type=putaway_type)

        return self.queryset


class PutawaySummaryView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        annotate(zone=Subquery(WarehouseAssortment.objects.filter(
                     warehouse=OuterRef('warehouse'), product=OuterRef('sku__parent_product')).values('zone')[:1])
                 ). \
        exclude(status__isnull=True).exclude(zone__isnull=True)
    serializer_class = PutawaySummarySerializers

    @check_whc_manager_coordinator_supervisor_putaway
    def get(self, request):
        """ GET API for Putaways po summary """
        info_logger.info("Putaway PO Summary GET api called.")
        """ GET Putaway PO Summary List """

        self.queryset = get_logged_user_wise_query_set(self.request.user, self.queryset)
        self.queryset = self.filter_putaway_summary_data()
        self.queryset = self.queryset.values('status').annotate(total_items=Count('status'))
        putaways_data = {"total": 0, "pending": 0, "completed": 0, "cancelled": 0}
        for obj in self.queryset:
            if obj['status'] in [Putaway.NEW, Putaway.ASSIGNED, Putaway.INITIATED]:
                putaways_data['total'] += obj['total_items']
                putaways_data['pending'] += obj['total_items']
            elif obj['status'] == Putaway.COMPLETED:
                putaways_data['total'] += obj['total_items']
                putaways_data['completed'] += obj['total_items']
            elif obj['status'] == Putaway.CANCELLED:
                putaways_data['total'] += obj['total_items']
                putaways_data['cancelled'] += obj['total_items']
        serializer = self.serializer_class(putaways_data)
        msg = "" if putaways_data else "no putaway found"
        return get_response(msg, serializer.data, True)

    def filter_putaway_summary_data(self):
        date = self.request.GET.get('date')

        '''Filters using date'''
        if date:
            self.queryset = self.queryset.filter(created_at__date=date)

        return self.queryset


class ZoneWiseSummaryView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        annotate(zone=Subquery(WarehouseAssortment.objects.filter(
                     warehouse=OuterRef('warehouse'), product=OuterRef('sku__parent_product')).values('zone')[:1])
                 ). \
        exclude(status__isnull=True). \
        order_by('zone', 'status')
    serializer_class = ZonewiseSummarySerializers

    @check_whc_manager_coordinator_supervisor_putaway
    def get(self, request):
        """ GET API for Putaways po summary """
        info_logger.info("Putaway PO Summary GET api called.")
        """ GET Putaway PO Summary List """
        self.queryset = get_logged_user_wise_query_set(self.request.user, self.queryset)
        self.queryset = self.filter_zone_wise_summary_putaways_data()
        # putaways_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        zone_wise_data = []
        for zone, group in groupby(self.queryset, lambda x: x.zone):
            zones_dict = {"zone": zone, "status_count": {"total": 0, "pending": 0, "completed": 0, "cancelled": 0}}
            for status, inner_group in groupby(group, lambda x: x.status):
                obj_count = len(list(inner_group))
                if status in [Putaway.NEW, Putaway.ASSIGNED, Putaway.INITIATED]:
                    zones_dict['status_count']['total'] += obj_count
                    zones_dict['status_count']['pending'] += obj_count
                elif status == Putaway.COMPLETED:
                    zones_dict['status_count']['total'] += obj_count
                    zones_dict['status_count']['completed'] += obj_count
                elif status == Putaway.CANCELLED:
                    zones_dict['status_count']['total'] += obj_count
                    zones_dict['status_count']['cancelled'] += obj_count
            zone_wise_data.append(zones_dict)

        serializer = self.serializer_class(zone_wise_data, many=True)
        msg = "" if zone_wise_data else "no putaway found"
        return get_response(msg, serializer.data, True)

    def filter_zone_wise_summary_putaways_data(self):
        zone = self.request.GET.get('zone')
        date = self.request.GET.get('date')

        '''Filters using zone '''
        if zone:
            self.queryset = self.queryset.filter(zone=zone)

        if date:
            self.queryset = self.queryset.filter(created_at__date=date)

        return self.queryset
