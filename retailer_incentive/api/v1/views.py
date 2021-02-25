from rest_framework import authentication, permissions

from common.data_wrapper_view import DataWrapperViewSet
from retailer_incentive.api.v1.serializers import SchemeShopMappingSerializer
from retailer_incentive.models import SchemeShopMapping


class ShopSchemeMappingViewSet(DataWrapperViewSet):

    model = SchemeShopMapping
    serializer_class = SchemeShopMappingSerializer
    queryset = SchemeShopMapping.objects.filter(is_active=True)
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):

        serializer_action_classes = {
            'retrieve': SchemeShopMappingSerializer
        }

        if hasattr(self, 'action'):
            return serializer_action_classes.get(self.action, self.serializer_class)
        return self.serializer_class

    def get_queryset(self):
        shop = self.request.query_params.get('shop', None)
        scheme_shop_mapping = SchemeShopMapping.objects.all()
        if shop is not None:
            scheme_shop_mapping = scheme_shop_mapping.filter(shop_id=shop)
        return scheme_shop_mapping