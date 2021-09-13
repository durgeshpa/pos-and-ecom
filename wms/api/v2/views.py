import logging

from dal import autocomplete
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import authentication
from rest_framework import generics
from rest_framework.permissions import AllowAny

from products.models import Product
from retailer_backend.utils import SmallOffsetPagination
from shops.models import Shop
from wms.common_functions import get_response, serializer_error
from .serializers import InOutLedgerSerializer, InOutLedgerCSVSerializer, BinInventorySerializer, \
    InventoryTypeSerializer
from ...common_validators import validate_ledger_request
from ...models import BinInventory, InventoryType

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


class InventoryTypeView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = InventoryType.objects.all()
    serializer_class = InventoryTypeSerializer

    def get(self, request):
        count = self.queryset.count()
        inventory_type_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(inventory_type_data, many=True)
        msg = f'{count} records found'
        return get_response(msg, serializer.data, True)


class BinInventoryDataView(generics.GenericAPIView):

    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BinInventorySerializer
    queryset = BinInventory.objects.all()

    def get(self, request):
        if not request.GET.get('warehouse'):
            return get_response("'warehouse' | This is required")

        sku = request.GET.get('sku')
        bin = request.GET.get('bin')

        if not sku and not bin:
            return get_response("'sku' or 'bin' is required")

        """ GET BinInventory List """
        self.queryset = self.search_filter_inventory_data()
        total_count = self.queryset.count()
        bin_inventory_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(bin_inventory_data, many=True)
        msg = f"total count {total_count}" if bin_inventory_data else "no record found"
        return get_response(msg, serializer.data, True)

    def search_filter_inventory_data(self):
        warehouse = self.request.GET.get('warehouse')
        sku = self.request.GET.get('sku')
        bin = self.request.GET.get('bin')
        batch = self.request.GET.get('batch')
        inventory_type = self.request.GET.get('inventory_type')

        '''Filters using warehouse, sku, batch, bin, inventory_type'''

        if warehouse:
            self.queryset = self.queryset.filter(warehouse_id=warehouse)

        if sku:
            self.queryset = self.queryset.filter(sku_id=sku)

        if bin:
            self.queryset = self.queryset.filter(bin_id=bin)

        if batch:
            self.queryset = self.queryset.filter(batch=batch)

        if inventory_type:
            self.queryset = self.queryset.filter(inventory_type_id=inventory_type)

        return self.queryset

    def post(self, request):
        try:
            modified_data = request.data["data"]
        except Exception as e:
            return get_response("Invalid Data Format")

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Product movement done.")
            return get_response('Product moved successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)
