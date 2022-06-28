import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from retailer_to_sp.models import Trip, LastMileTripReturnMapping, ReturnOrder
from django.db.models import Count
from retailer_to_sp.api.v1.serializers import ShopExecutiveUserSerializer, ShopSerializer, RetailerShopSerializer
from shops.models import ShopTiming, Shop

trip = Trip.objects.get(id=16374)
trip_mappings = trip.last_mile_trip_returns_details.all()
trip_return = []
grouped_return_list = ReturnOrder.objects.filter(last_mile_trip_returns__in=
                                                 trip_mappings).values('buyer_shop', 'seller_shop').annotate(
    return_count=Count('id')).order_by()
for grouped_return in grouped_return_list:
    grouped_return_dict = {}
    grouped_return_dict['item_type'] = 'return'
    grouped_return_dict['shop_id'] = grouped_return['buyer_shop']
    shop_timing = ShopTiming.objects.filter(shop_id=grouped_return['buyer_shop'])
    if shop_timing.exists():
        final_timing = shop_timing.last()
        grouped_return_dict['shop_open_time'] = final_timing.open_timing
        grouped_return_dict['shop_close_time'] = final_timing.closing_timing
        grouped_return_dict['break_start_time'] = final_timing.break_start_time
        grouped_return_dict['break_end_time'] = final_timing.break_end_time
        grouped_return_dict['off_day'] = final_timing.off_day
    else:
        grouped_return_dict['shop_open_time'] = None
        grouped_return_dict['shop_close_time'] = None
        grouped_return_dict['break_start_time'] = None
        grouped_return_dict['break_end_time'] = None
        grouped_return_dict['off_day'] = None
    buyerShop = Shop.objects.filter(id=grouped_return['buyer_shop']).last()
    sellerShop = Shop.objects.filter(id=grouped_return['seller_shop']).last()
    shop_user_mapping = buyerShop.shop_user.filter(status=True,
                                                    employee_group__name='Sales Executive').last()
    sales_executive = None
    if shop_user_mapping:
        sales_executive = shop_user_mapping.employee
    sales_executive = ShopExecutiveUserSerializer(sales_executive)
    grouped_return_dict['sales_executive'] = sales_executive.data
    print(sellerShop)
    grouped_return_dict['seller_shop'] = RetailerShopSerializer(sellerShop).data
    grouped_return_dict['buyer_shop'] = RetailerShopSerializer(buyerShop).data
    grouped_return_dict['return_count'] = grouped_return['return_count']
    trip_return.append(grouped_return_dict)

print(trip_return)