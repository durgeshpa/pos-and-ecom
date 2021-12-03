import logging
from math import floor

from accounts.models import User
from .models import SchemeSlab, IncentiveDashboardDetails
from shops.models import Shop, ShopUserMapping, ParentRetailerMapping
from retailer_to_sp.models import OrderedProductMapping

logger = logging.getLogger('dashboard-api')


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
    """
        Store active scheme data in database before creating new scheme for shop
    """
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
    shop_user_mapping = shop.shop_user.filter(employee_group__name__in=['Sales Executive', 'Sales Manager'], status=True).last()
    sales_executive = None
    sales_manager = None
    if shop_user_mapping is not None:
        try:
            sales_executive = shop_user_mapping.employee
            sales_manager = shop_user_mapping.manager.employee
        except:
            sales_executive = None
            sales_manager = None
    try:
        IncentiveDashboardDetails.objects.create(sales_manager=sales_manager, sales_executive=sales_executive,
                                                 shop=shop, mapped_scheme=scheme, purchase_value=total_sales,
                                                 incentive_earned=discount_value, start_date=active_mapping.start_date,
                                                 end_date=active_mapping.end_date,
                                                 discount_percentage=discount_percentage,
                                                 scheme_priority=active_mapping.priority)

        logger.info(f'incentive dashboard details saved in database for shop {shop.shop_name}')
    except Exception as error:
        logger.exception(error)


def get_total_sales(shop_id, start_date, end_date):
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
        total_sales += float(shipped_item.basic_rate)*float(shipped_item.delivered_qty)
    return floor(total_sales)


def shop_scheme_not_mapped(shop):
    scheme_data = {'shop_id': shop.id,
                   'shop_name': str(shop.shop_name),
                   'mapped_scheme_id': "NA",
                   'mapped_scheme': "NA",
                   'discount_value': "NA",
                   'discount_percentage': "NA",
                   'incentive_earned': "NA",
                   'start_date': "NA",
                   'end_date': "NA"
                   }
    return scheme_data