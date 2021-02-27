from django.db.models import Q
from rest_framework import authentication, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.data_wrapper_view import DataWrapperViewSet
from retailer_backend.messages import SUCCESS_MESSAGES
from retailer_incentive.api.v1.serializers import SchemeShopMappingSerializer, SchemeSlabSerializer, \
    ShopSalesMatrixSerializer
from retailer_incentive.models import SchemeShopMapping, SchemeSlab

class ShopSchemeMappingView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        shop_id = request.user.shop_employee.last().shop_id
        shop_scheme = SchemeShopMapping.objects.none()
        if shop_id is not None:
            shop_scheme = SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True).last()
        serializer = SchemeShopMappingSerializer(shop_scheme)
        msg = {'is_success': True, 'message': 'OK', 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class ShopPurchaseMatrix(APIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        shop_id = request.user.shop_employee.last().shop_id
        total_sales = self.get_total_sales(shop_id)
        discount_percentage = 0
        if SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True).exists():
            scheme = SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True).last().scheme
            scheme_slab = SchemeSlab.objects.filter(scheme=scheme, min_value__lte=total_sales)\
                                            .order_by('min_value').last()
            if scheme_slab is not None:
                discount_percentage = scheme_slab.discount_value
            discount_value = discount_percentage * total_sales/100
            next_slab = SchemeSlab.objects.filter(scheme=scheme, min_value__gt=total_sales).last()
            message = SUCCESS_MESSAGES['SCHEME_SLAB_HIGHEST']
            if next_slab is not None:
                message = SUCCESS_MESSAGES['SCHEME_SLAB_ADD_MORE'].format((next_slab.min_value - total_sales),
                            (next_slab.min_value * next_slab.discount_value / 100), next_slab.discount_value)
        msg = {'is_success': True, 'message': 'OK', 'data': {'total_sales' : total_sales,
                                                             'discount_percentage': discount_percentage,
                                                             'discount_value': discount_value,
                                                             'message': message}}
        return Response(msg, status=status.HTTP_200_OK)

    def get_total_sales(self, shop_id):
        return 15000

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