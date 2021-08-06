import logging

from dal import autocomplete
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import authentication
from rest_framework import generics
from rest_framework.permissions import AllowAny

from products.models import Product
from wms.common_functions import get_response, serializer_error
from .serializers import InOutLedgerSerializer, InOutLedgerCSVSerializer
from ...common_validators import validate_ledger_request

# Logger

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
