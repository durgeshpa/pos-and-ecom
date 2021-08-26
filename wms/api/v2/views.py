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
from .serializers import InOutLedgerSerializer, InOutLedgerCSVSerializer, ZoneCrudSerializers, UserSerializers, \
    WarehouseAssortmentCrudSerializers, WarehouseAssortmentExportAsCSVSerializers, BinExportAsCSVSerializers, \
    WarehouseAssortmentSampleCSVSerializer, WarehouseAssortmentUploadSerializer, BinCrudSerializers, \
    BinExportBarcodeSerializers
from wms.common_validators import validate_ledger_request, validate_data_format, validate_id, validate_id_and_warehouse
from wms.models import Zone, WarehouseAssortment, Bin, BIN_TYPE_CHOICES

# Logger
from wms.services import zone_search, user_search, whc_assortment_search, bin_search

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

    # @check_warehouse_manager
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

    @check_warehouse_manager
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

    @check_warehouse_manager
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
