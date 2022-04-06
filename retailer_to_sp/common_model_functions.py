import datetime
import logging

from retailer_to_sp.models import ShopCrate, OrderedProduct, Trip, Order

today = datetime.datetime.today()

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class ShopCrateCommonFunctions(object):

    @staticmethod
    def create_update_shop_crate(shop_id, crate_id, is_available=True):
        info_logger.info(f"create_update_shop_crate|ShopCrateCommonFunctions|Started|"
                         f"shop_id: {shop_id}, crate_id: {crate_id}, is_available {is_available}")
        shop_crate_instance, _ = ShopCrate.objects.update_or_create(
            shop_id=shop_id, crate_id=crate_id,
            defaults={'is_available': is_available})
        info_logger.info(f"create_update_shop_crate|ShopCrateCommonFunctions|Ended|shop_id {shop_id} | "
                         f"crate_db_id {crate_id} | Crate Id {shop_crate_instance.crate.crate_id} | "
                         f"is_available {is_available}")
        return shop_crate_instance

    @classmethod
    def mark_crate_used(cls, shop_id, crate_id):
        info_logger.info(f"mark_crate_used|ShopCrateCommonFunctions|shop_id {shop_id}|crate_id {crate_id}")
        return ShopCrateCommonFunctions.create_update_shop_crate(shop_id, crate_id, False)

    @classmethod
    def mark_crate_available(cls, shop_id, crate_id):
        info_logger.info(f"mark_crate_available|ShopCrateCommonFunctions|shop_id {shop_id}|crate_id {crate_id}")
        return ShopCrateCommonFunctions.create_update_shop_crate(shop_id, crate_id, True)

    @classmethod
    def get_filtered_shop_crate(cls, **kwargs):
        map_data = ShopCrate.objects.filter(**kwargs)
        return map_data


class OrderCommonFunction(object):

    @classmethod
    def update_order_status_by_last_mile_trip(cls, trip_instance):
        shipments_ids = trip_instance.last_mile_trip_shipments_details.all().values_list('shipment__id', flat=True)
        order_instances = Order.objects.filter(rt_order_order_product__id__in=shipments_ids)
        if trip_instance.trip_status == Trip.READY:
            order_instances.update(order_status=Order.READY_TO_DISPATCH)
        if trip_instance.trip_status == Trip.STARTED:
            order_instances.update(order_status=Order.DISPATCHED)
        if trip_instance.trip_status == Trip.COMPLETED:
            order_instances.update(order_status=Order.COMPLETED)
