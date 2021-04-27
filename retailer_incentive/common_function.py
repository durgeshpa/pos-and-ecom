import datetime
import logging
from math import floor

from accounts.models import User
from .models import SchemeSlab, IncentiveDashboardDetails
from shops.models import Shop, ShopUserMapping
from retailer_to_sp.models import OrderedProductMapping


def get_user_id_from_token(request):
    """
        If Token is valid get User from token
    """
    if request.user.id:
        if User.objects.filter(id=request.user.id).exists():
            user = User.objects.filter(id=request.user.id).last()
            return user
        return "Please provide Token"


def save_scheme_shop_mapping_data(active_mapping):
    scheme = active_mapping.scheme
    total_sales = get_total_sales(active_mapping.shop_id, active_mapping.start_date,
                                  active_mapping.end_date)
    scheme_slab = SchemeSlab.objects.filter(scheme=scheme, min_value__lt=total_sales).order_by(
        'min_value').last()

    discount_percentage = 0
    if scheme_slab is not None:
        discount_percentage = scheme_slab.discount_value
    discount_value = floor(discount_percentage * total_sales / 100)

    shop = Shop.objects.filter(id=active_mapping.shop_id).last()
    shop_user_map = ShopUserMapping.objects.filter(shop=shop).last()
    manager = User.objects.filter(id=shop_user_map.manager.employee.id).last()
    sales_executive = User.objects.filter(id=shop_user_map.employee.id).last()
    IncentiveDashboardDetails.objects.create(sales_manager=manager, sales_executive=sales_executive,
                                             shop=shop, mapped_scheme=scheme, purchase_value=total_sales,
                                             incentive_earned=discount_value, start_date=active_mapping.start_date,
                                             end_date=active_mapping.end_date)



def get_total_sales(shop_id, start_date, end_date):
    total_sales = 0
    shipment_products = OrderedProductMapping.objects.filter(ordered_product__order__buyer_shop_id=shop_id,
                                                             ordered_product__order__created_at__gte=start_date,
                                                             ordered_product__order__created_at__lte=end_date,
                                                             ordered_product__shipment_status__in=
                                                             ['PARTIALLY_DELIVERED_AND_COMPLETED',
                                                              'FULLY_DELIVERED_AND_COMPLETED',
                                                              'PARTIALLY_DELIVERED_AND_VERIFIED',
                                                              'FULLY_DELIVERED_AND_VERIFIED',
                                                              'PARTIALLY_DELIVERED_AND_CLOSED',
                                                              'FULLY_DELIVERED_AND_CLOSED'])
    for shipped_item in shipment_products:
        total_sales += shipped_item.basic_rate * shipped_item.delivered_qty
    return floor(total_sales)
