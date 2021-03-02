from django.db.models import Q
from rest_framework import authentication, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.data_wrapper_view import DataWrapperViewSet
from retailer_backend.messages import SUCCESS_MESSAGES
from retailer_incentive.api.v1.serializers import SchemeShopMappingSerializer, SchemeSlabSerializer
from retailer_incentive.models import SchemeShopMapping, SchemeSlab
from retailer_to_sp.models import Order, OrderedProduct, OrderedProductMapping
from shops.models import ShopUserMapping, Shop


class ShopSchemeMappingView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        shop_id = request.GET.get('shop_id')
        shop_scheme = SchemeShopMapping.objects.none()
        if shop_id is not None:
            shop_scheme = SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True).last()
        serializer = SchemeShopMappingSerializer(shop_scheme)
        msg = {'is_success': True, 'message': 'OK', 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class ShopPurchaseMatrix(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        shop_id = request.GET.get('shop_id')
        if not SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True).exists():
            msg = {'is_success': False, 'message': 'No Scheme Found for this shop', 'data': {}}
            return Response(msg, status=status.HTTP_200_OK)
        scheme_shop_mapping = SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True).last()
        scheme = scheme_shop_mapping.scheme
        total_sales = self.get_total_sales(shop_id, scheme_shop_mapping.start_date, scheme_shop_mapping.end_date)
        scheme_slab = SchemeSlab.objects.filter(scheme=scheme, min_value__lte=total_sales)\
                                        .order_by('min_value').last()

        discount_percentage = 0
        if scheme_slab is not None:
            discount_percentage = scheme_slab.discount_value
        discount_value = discount_percentage * total_sales/100
        next_slab = SchemeSlab.objects.filter(scheme=scheme, min_value__gt=total_sales).order_by('min_value').first()
        message = SUCCESS_MESSAGES['SCHEME_SLAB_HIGHEST']
        if next_slab is not None:
            message = SUCCESS_MESSAGES['SCHEME_SLAB_ADD_MORE'].format((next_slab.min_value - total_sales),
                        (next_slab.min_value * next_slab.discount_value / 100), next_slab.discount_value)
        msg = {'is_success': True, 'message': 'OK', 'data': {'total_sales' : total_sales,
                                                             'discount_percentage': discount_percentage,
                                                             'discount_value': discount_value,
                                                             'message': message}}
        return Response(msg, status=status.HTTP_200_OK)

    def get_total_sales(self, shop_id, start_date, end_date):
        total_sales = 0
        shipment_products = OrderedProductMapping.objects.filter(ordered_product__order__buyer_shop_id=shop_id,
                                                                 ordered_product__created_at__gte=start_date,
                                                                 ordered_product__created_at__lte=end_date,
                                                                 ordered_product__shipment_status__in=
                                                                     ['PARTIALLY_DELIVERED_AND_COMPLETED',
                                                                      'FULLY_DELIVERED_AND_COMPLETED',
                                                                      'PARTIALLY_DELIVERED_AND_VERIFIED',
                                                                      'FULLY_DELIVERED_AND_VERIFIED',
                                                                      'PARTIALLY_DELIVERED_AND_CLOSED',
                                                                      'FULLY_DELIVERED_AND_CLOSED'])
        for s in shipment_products:
            total_sales += s.basic_rate*s.delivered_qty
        return total_sales


class ShopUserMappingView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, )

    def get(self, request):
        shop = request.user.shop_employee.last().shop
        if shop is None:
            msg = {'is_success': False, 'message': 'No shop found', 'data':{} }
            return Response(msg, status=status.HTTP_200_OK)

        se = shop.shop_user.filter(employee_group__name='Sales Executive').last()
        sm = shop.shop_user.filter(employee_group__name='Sales Manager').last()

        msg = {'is_success': True, 'message': 'OK', 'data': {'se_name':se.employee.first_name+' '+se.employee.last_name,
                                                             'se_no':se.employee.phone_number,
                                                             'sm_name': sm.employee.first_name + ' ' + sm.employee.last_name,
                                                             'sm_no': sm.employee.phone_number
                                                             }}
        return Response(msg, status=status.HTTP_200_OK)

#
#
# class ShopSchemeMappingViewSet(DataWrapperViewSet):
#
#     model = SchemeShopMapping
#     serializer_class = SchemeShopMappingSerializer
#     queryset = SchemeShopMapping.objects.filter(is_active=True)
#     authentication_classes = (authentication.TokenAuthentication,)
#     permission_classes = (permissions.IsAuthenticated,)
#
#     def get_serializer_class(self):
#
#         serializer_action_classes = {
#             'retrieve': SchemeShopMappingSerializer
#         }
#
#         if hasattr(self, 'action'):
#             return serializer_action_classes.get(self.action, self.serializer_class)
#         return self.serializer_class
#
#     def get_queryset(self):
#         shop_id = self.request.user.shop_employee.last().shop_id
#         if shop_id is not None:
#             return SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True)
#         return SchemeShopMapping.objects.none()
#
#
#     @action(detail=True, methods=['get'])
#     def purchase_matrix(self, request, pk=None):
#         shop_id = request.user.shop_employee.last().shop_id
#         serializer = ShopSalesMatrixSerializer(context={'shop_id': shop_id})
#         return serializer.data