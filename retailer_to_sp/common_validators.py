from functools import wraps

from django.db.models import Q

from retailer_to_sp.models import ShipmentPackaging, ShipmentPackagingMapping, DispatchTrip, OrderedProduct, \
    DispatchTripShipmentMapping, Trip, DispatchTripShipmentPackages, TRIP_TYPE_CHOICE
from wms.common_functions import get_response
from wms.models import Crate


def check_user_can_plan_trip(view_func):
    """
        Decorator to validate logged-in user can can plan trip
    """

    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if not user.has_perm('retailer_to_sp.can_plan_trip'):
            return get_response("Logged In user does not have required permission to perform this action.")
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


def validate_shipment_crates_list(crates_dict, warehouse_id, shipment):
    if 'packages' not in crates_dict or not crates_dict['packages']:
        return {"error": "Missing 'packages' for packaging_type 'CRATE'."}
    if not isinstance(crates_dict['packages'], list):
        return {"error": "Key 'packages' can be of list type only."}
    crate_already_used = []
    for crate_obj in crates_dict['packages']:
        if not isinstance(crate_obj, dict):
            return {"error": "crate_obj can be of object type only."}
        if 'crate_id' not in crate_obj or not crate_obj['crate_id']:
            return {"error": "Missing 'crate_id' in shipment_crates for packaging_type 'CRATE'."}
        if 'quantity' not in crate_obj or not crate_obj['quantity']:
            return {"error": "Missing 'quantity' in shipment_crates for packaging_type 'CRATE'."}
        if crate_obj['crate_id'] in crate_already_used:
            return {"error": f"Crate {crate_obj['crate_id']} seems to be added multiple times"}
        try:
            crate_qty = int(crate_obj['quantity'])
        except:
            return {"error": "'crate.quantity' | Invalid crate quantity."}

        if not Crate.objects.filter(crate_id=crate_obj['crate_id'], crate_type=Crate.DISPATCH,
                                    shop_crates__shop__id=warehouse_id, shop_crates__is_available=True).exists():
            return {"error": "Invalid crates selected in packaging."}
        crate = Crate.objects.filter(crate_id=crate_obj['crate_id'], crate_type=Crate.DISPATCH,
                                     shop_crates__shop__id=warehouse_id, shop_crates__is_available=True).last()
        if crate.crates_shipments.filter(
            ~Q(shipment=shipment),
            Q(status__in=[ShipmentPackaging.DISPATCH_STATUS_CHOICES.PACKED,
                           ShipmentPackaging.DISPATCH_STATUS_CHOICES.READY_TO_DISPATCH]),
            ~Q(shipment__shipment_status__in=[OrderedProduct.PARTIALLY_DELIVERED_AND_VERIFIED,
                                              OrderedProduct.FULLY_RETURNED_AND_VERIFIED,
                                              OrderedProduct.FULLY_DELIVERED_AND_VERIFIED])).exists():
            return {"error": "This crate is being used for some other shipment."}
        crate_already_used.append(crate_obj['crate_id'])
    return {"data": crates_dict}


def validate_shipment_package_list(package_dict):
    if 'packages' not in package_dict or not package_dict['packages']:
        return {"error": f"Missing 'packages' for packaging_type {package_dict['type']}."}
    if not isinstance(package_dict['packages'], list):
        return {"error": "Key 'packages' can be of list type only."}
    for package in package_dict['packages']:
        if not isinstance(package, dict):
            return {"error": "package can be of list of object type only."}
        if 'quantity' not in package or not package['quantity']:
            return {"error": f"Missing 'quantity' in package for packaging_type {package_dict['type']}."}
        try:
            package_qty = int(package['quantity'])
        except:
            return {"error": "'crate.quantity' | Invalid crate quantity."}
    return {"data": package_dict}


def validate_shipment_dispatch_item(queryset, dispatch_item_id, shipment_id):
    if not queryset.filter(id=dispatch_item_id, shipment_id=shipment_id).exists():
        return {"error": "Invalid item for this shipment"}
    return {"data": queryset.filter(id=dispatch_item_id, shipment_id=shipment_id).last()}

def get_shipment_by_crate_id(crate_id, crate_type=None):
    """ validation only crate_id that belong to a selected related model """
    obj = ShipmentPackaging.objects.filter(crate__crate_id=crate_id).last()
    if not obj:
        return {'error': 'please provide a valid crate_id'}
    if crate_type and obj.crate.crate_type != crate_type:
        return {'error': 'selected carte type is not allowed.'}
    return {'data': obj.shipment.pk}


def validate_trip_user(trip_id, user):
    if DispatchTrip.objects.filter(id=trip_id, seller_shop=user.shop_employee.last().shop).exists():
        return {"data": DispatchTrip.objects.get(id=trip_id, seller_shop=user.shop_employee.last().shop)}
    return {"error": "Invalid trip"}


def validate_last_mile_trip_user(trip_id, user):
    if Trip.objects.filter(id=trip_id, seller_shop=user.shop_employee.last().shop).exists():
        return {"data": Trip.objects.get(id=trip_id, seller_shop=user.shop_employee.last().shop)}
    return {"error": "Invalid trip"}


def get_shipment_by_shipment_label(shipment_label_id):
    obj = ShipmentPackaging.objects.filter(id=shipment_label_id).last()
    if not obj:
        return {'error': 'please provide a valid shipment_label_id'}
    return {'data': obj.shipment.pk}


def validate_shipment_id(shipment_id):
    obj = OrderedProduct.objects.filter(id=shipment_id).last()
    if not obj:
        return {'error': 'please provide a valid shipment_id'}
    return {'data': obj.pk}


def validate_trip_shipment(trip_id, shipment_id):
    if DispatchTripShipmentMapping.objects.filter(trip_id=trip_id, shipment_id=shipment_id).exists():
        return {"data": DispatchTripShipmentMapping.objects.filter(
                                trip_id=trip_id, shipment_id=shipment_id).last()}
    return {"error": 'Invalid Shipment'}


def validate_trip_shipment_package(trip_id, package_id):
    if DispatchTripShipmentPackages.objects.filter(
            trip_shipment__trip_id=trip_id, shipment_packaging_id=package_id).exists():
        return {"data": DispatchTripShipmentPackages.objects.filter(
                                trip_shipment__trip_id=trip_id, shipment_packaging_id=package_id).last()}
    return {"error": 'Invalid Package'}


def validate_trip(trip_id, trip_type):
    if trip_type and trip_type in [TRIP_TYPE_CHOICE.DISPATCH_FORWARD, TRIP_TYPE_CHOICE.DISPATCH_BACKWARD]:
        if DispatchTrip.objects.filter(id=trip_id).exists():
            return {"data": DispatchTrip.objects.filter(id=trip_id).last()}
        else:
            return {"error": 'Invalid Trip'}
    if Trip.objects.filter(id=trip_id).exists():
        return {"data": Trip.objects.filter(id=trip_id).last()}
    return {"error": 'Invalid Trip'}


def validate_shipment_label(shipment_label_id):
    obj = ShipmentPackaging.objects.filter(id=shipment_label_id).last()
    if not obj:
        return {'error': 'please provide a valid shipment_label_id'}
    return {'data': obj}
