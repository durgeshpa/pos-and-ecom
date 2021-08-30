import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Exists, OuterRef, Subquery
from rest_framework import authentication
from rest_framework import generics
from rest_framework.permissions import AllowAny

from gram_to_brand.common_functions import get_response, serializer_error
from gram_to_brand.common_validators import validate_id, validate_data_format
from gram_to_brand.models import GRNOrderProductMapping, GRNOrder
from retailer_backend.utils import SmallOffsetPagination
from shops.models import ParentRetailerMapping
from wms.models import WarehouseAssortment
from .serializers import GRNOrderNonZoneProductsCrudSerializers, GRNOrderSerializers

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class GRNOrderNonZoneProductsCrudView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = GRNOrder.objects. \
        select_related('order', 'order__ordered_cart', 'order__ordered_cart__gf_shipping_address',
                       'order__ordered_cart__gf_shipping_address__shop_name'). \
        prefetch_related('grn_order_grn_order_product', 'grn_order_grn_order_product__product',
                         'grn_order_grn_order_product__product__parent_product'). \
        only('id', 'order__id', 'order__ordered_cart__id', 'order__ordered_cart__gf_shipping_address__id',
             'order__ordered_cart__gf_shipping_address__shop_name__id',
             'order__ordered_cart__gf_shipping_address__shop_name__shop_name'). \
        annotate(is_zone=Subquery(WarehouseAssortment.objects.filter(
                warehouse=Subquery(ParentRetailerMapping.objects.filter(
                    parent=OuterRef(OuterRef('order__ordered_cart__gf_shipping_address__shop_name')), status=True,
                    retailer__shop_type__shop_type='sp', retailer__status=True).order_by('-id').values('retailer')[:1]),
                product=OuterRef('grn_order_grn_order_product__product__parent_product')
            ).order_by('-id').values('zone__id')[:1])). \
        exclude(is_zone__isnull=False). \
        order_by('-id').distinct('id')

    serializer_class = GRNOrderSerializers

    def get(self, request):
        """ GET API for GRNOrderProductMapping """
        info_logger.info("GRNOrderProductMapping GET api called.")
        if request.GET.get('id'):
            """ Get GRNOrderProductMapping for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            grn_products_data = id_validation['data']
        else:
            """ GET GRNOrderProductMapping List """
            # self.queryset = self.search_filter_grn_products_data()
            grn_products_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(grn_products_data, many=True)
        msg = "" if grn_products_data else "no grn_products found"
        return get_response(msg, serializer.data, True)

    def search_filter_grn_products_data(self):
        search_text = self.request.GET.get('search_text')
        product = self.request.GET.get('product')

        '''search using warehouse name, product's name  and zone's coordination / supervisor firstname'''
        if search_text:
            pass
            # self.queryset = grn_products_search(self.queryset, search_text)

        '''Filters using warehouse, product, zone'''
        if product:
            self.queryset = self.queryset.filter(product__id=product)

        return self.queryset.distinct('id')


