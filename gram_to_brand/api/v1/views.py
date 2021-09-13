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
                       'order__ordered_cart__gf_shipping_address__shop_name',
                       'order__ordered_cart__gf_shipping_address__shop_name__shop_type'). \
        prefetch_related('grn_order_grn_order_product', 'grn_order_grn_order_product__product',
                         'grn_order_grn_order_product__product__parent_product'). \
        annotate(is_zone=Subquery(WarehouseAssortment.objects.select_related('warehouse', 'product', 'zone').filter(
                warehouse=Subquery(ParentRetailerMapping.objects.select_related('parent', 'retailer').filter(
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
            self.queryset = self.search_filter_grn_products_data()
            grn_products_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(grn_products_data, many=True)
        msg = "" if grn_products_data else "no grn_products found"
        return get_response(msg, serializer.data, True)

    def search_filter_grn_products_data(self):
        product = self.request.GET.get('product')
        parent_id = self.request.GET.get('parent_id')
        parent_product_id = self.request.GET.get('parent_product_id')
        parent_product_name = self.request.GET.get('parent_product_name')
        warehouse = self.request.GET.get('warehouse')

        '''Filters using warehouse, product, zone'''
        if product:
            self.queryset = self.queryset.filter(grn_order_grn_order_product__product__id=product)

        if parent_id:
            self.queryset = self.queryset.filter(grn_order_grn_order_product__product__parent_product__id=parent_id)

        if parent_product_id:
            self.queryset = self.queryset.filter(
                grn_order_grn_order_product__product__parent_product__parent_id=parent_product_id)

        if parent_product_name:
            self.queryset = self.queryset.filter(
                grn_order_grn_order_product__product__parent_product__name__icontains=parent_product_name)

        if warehouse:
            pm_obj = ParentRetailerMapping.objects.select_related(
                'parent', 'parent__shop_type', 'retailer', 'retailer__shop_type').filter(
                retailer_id=warehouse, status=True, parent__shop_type__shop_type='gf', parent__status=True).last()
            self.queryset = self.queryset.filter(
                grn_order__order__ordered_cart__gf_shipping_address__shop_name=pm_obj.parent)

        return self.queryset.distinct('id')


