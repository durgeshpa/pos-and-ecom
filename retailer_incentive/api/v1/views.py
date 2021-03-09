import datetime
from math import floor

from rest_framework import authentication, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from retailer_backend.messages import SUCCESS_MESSAGES
from retailer_incentive.api.v1.serializers import SchemeShopMappingSerializer
from retailer_incentive.models import SchemeSlab
from retailer_incentive.utils import get_shop_scheme_mapping
from retailer_to_sp.models import OrderedProductMapping
from shops.models import ShopUserMapping, Shop, ParentRetailerMapping


class ShopSchemeMappingView(APIView):
    """
    This class is used to get Scheme mapped with a shop
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        shop_id = request.GET.get('shop_id')
        shop = Shop.objects.filter(id=shop_id).last()
        if shop is None:
            msg = {'is_success': False, 'message': ['No shop found'], 'data':{} }
            return Response(msg, status=status.HTTP_200_OK)
        scheme_shop_mapping = get_shop_scheme_mapping(shop_id)
        if scheme_shop_mapping is None:
            msg = {'is_success': False, 'message': ['No Scheme Found for this shop'], 'data': {}}
            return Response(msg, status=status.HTTP_200_OK)
        serializer = SchemeShopMappingSerializer(scheme_shop_mapping)
        msg = {'is_success': True, 'message': ['OK'], 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class ShopPurchaseMatrix(APIView):
    """
    This class is used to get the purchase matrix of a shop under mapped scheme
    """

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        shop_id = request.GET.get('shop_id')
        shop = Shop.objects.filter(id=shop_id).last()
        if shop is None:
            msg = {'is_success': False, 'message': ['No shop found'], 'data':{} }
            return Response(msg, status=status.HTTP_200_OK)
        scheme_shop_mapping = get_shop_scheme_mapping(shop_id)
        if scheme_shop_mapping is None:
            msg = {'is_success': False, 'message': ['No Scheme Found for this shop'], 'data': {}}
            return Response(msg, status=status.HTTP_200_OK)
        scheme = scheme_shop_mapping.scheme
        total_sales = self.get_total_sales(shop_id, scheme.start_date, scheme.end_date)
        scheme_slab = SchemeSlab.objects.filter(scheme=scheme, min_value__lt=total_sales).order_by('min_value').last()

        discount_percentage = 0
        if scheme_slab is not None:
            discount_percentage = scheme_slab.discount_value
        discount_value = floor(discount_percentage * total_sales/100)
        next_slab = SchemeSlab.objects.filter(scheme=scheme, min_value__gt=total_sales).order_by('min_value').first()
        message = SUCCESS_MESSAGES['SCHEME_SLAB_HIGHEST']
        if next_slab is not None:
            message = SUCCESS_MESSAGES['SCHEME_SLAB_ADD_MORE'].format(floor(next_slab.min_value - total_sales),
                        (next_slab.min_value * next_slab.discount_value / 100), next_slab.discount_value)
        msg = {'is_success': True, 'message': ['OK'], 'data': {'total_sales' : total_sales,
                                                               'discount_percentage': discount_percentage,
                                                               'discount_value': discount_value,
                                                               'message': message}}
        return Response(msg, status=status.HTTP_200_OK)


    def get_total_sales(self, shop_id, start_date, end_date):
        """
        Returns the total purchase of a shop between given start_date and end_date
        Param :
            shop_id : id of shop
            start_date : start date from which sales to be considered
            end_date : date till which the sales to be considered
        Returns:
            floor value of total purchase of a shop between given start_date and end_date
        """
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
        for shipped_item in shipment_products:
            total_sales += shipped_item.basic_rate*shipped_item.delivered_qty
        return floor(total_sales)


class ShopUserMappingView(APIView):

    """
    This class is used to get the Shop User Mapping related data
    Returns:
        Sales Executive name and number
        Sales Manager name and number
    """

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, )

    def get(self, request):
        shop_id = request.GET.get('shop_id')
        shop = Shop.objects.filter(id=shop_id).last()
        if shop is None:
            msg = {'is_success': False, 'message': ['No shop found'], 'data':{} }
            return Response(msg, status=status.HTTP_200_OK)

        sales_executive_name = ''
        sales_executive_number = ''
        sales_manager_name = ''
        sales_manager_number = ''

        shop_user_mapping = shop.shop_user.filter(employee_group__name='Sales Executive', status=True).last()

        if shop_user_mapping is not None:
            sales_executive = shop_user_mapping.employee
            sales_executive_name = sales_executive.first_name + ' ' + sales_executive.last_name
            sales_executive_number = sales_executive.phone_number
            parent_shop_id = ParentRetailerMapping.objects.filter(retailer_id=shop_id).last().parent_id
            parent_shop_user_mapping = ShopUserMapping.objects.filter(shop=parent_shop_id,
                                                                      employee=sales_executive, status=True).last()
            if parent_shop_user_mapping and parent_shop_user_mapping.manager is not None:
                sales_manager = parent_shop_user_mapping.manager.employee
                sales_manager_name = sales_manager.first_name + ' ' + sales_manager.last_name
                sales_manager_number = sales_manager.phone_number
        msg = {'is_success': True, 'message': ['OK'], 'data': {'se_name': sales_executive_name,
                                                               'se_no': sales_executive_number,
                                                               'sm_name': sales_manager_name,
                                                               'sm_no': sales_manager_number
                                                               }}
        return Response(msg, status=status.HTTP_200_OK)
