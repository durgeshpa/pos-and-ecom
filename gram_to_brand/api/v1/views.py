import logging

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import authentication
from rest_framework import generics
from rest_framework.permissions import AllowAny

from gram_to_brand.common_functions import get_response, serializer_error
from gram_to_brand.common_validators import validate_id, validate_data_format
from gram_to_brand.models import GRNOrderProductMapping, GRNOrder
from retailer_backend.utils import SmallOffsetPagination
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
        prefetch_related('grn_order_grn_order_product', 'grn_order_grn_order_product__product',). \
        only('id', 'order__id', 'order__ordered_cart__id', 'order__ordered_cart__gf_shipping_address__id',
             'order__ordered_cart__gf_shipping_address__shop_name__id',
             'order__ordered_cart__gf_shipping_address__shop_name__shop_name'). \
        order_by('-id')

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

    def post(self, request):
        """ POST API for GRNOrderProductMapping Creation """

        info_logger.info("GRNOrderProductMapping POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("GRNOrderProductMapping Created Successfully.")
            return get_response('grn_products created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for GRNOrderProductMapping Updation """

        info_logger.info("GRNOrderProductMapping PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update grn_products', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        grn_products_instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=grn_products_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("GRNOrderProductMapping Updated Successfully.")
            return get_response('grn_products updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete GRNOrderProductMapping """

        info_logger.info("Zone DELETE api called.")
        if not request.data.get('grn_products_id'):
            return get_response('please provide grn_products_id', False)
        try:
            for whc_ass_id in request.data.get('grn_products_id'):
                grn_products_id = self.queryset.get(id=int(whc_ass_id))
                try:
                    grn_products_id.delete()
                except:
                    return get_response(f'can not delete grn_products | {grn_products_id.id} | getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid grn_products id {whc_ass_id}', False)
        return get_response('grn_products were deleted successfully!', True)

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


