from django.db.models import Q

from retailer_to_sp.models import ShipmentPackaging, ShipmentPackagingMapping, DispatchTrip, OrderedProduct
from wms.models import Crate


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

        if not Crate.objects.filter(crate_id=crate_obj['crate_id'], warehouse__id=warehouse_id,
                                    crate_type=Crate.DISPATCH).exists():
            return {"error": "Invalid crates selected in packaging."}
        crate = Crate.objects.filter(crate_id=crate_obj['crate_id'], warehouse__id=warehouse_id,
                                    crate_type=Crate.DISPATCH).last()
        if crate.crates_shipments.filter(
            ~Q(shipment=shipment),
            ~Q(status__in=[ShipmentPackaging.DISPATCH_STATUS_CHOICES.DELIVERED,
                           ShipmentPackaging.DISPATCH_STATUS_CHOICES.REJECTED])).exists():
            return {"error" : "This crate is being used for some other shipment."}
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


def validate_package_by_crate_id(queryset, crate_id, crate_type=None, shipment_id=None):
    """ validation only crate_id that belong to a selected related model """
    if shipment_id:
        queryset = queryset.filter(shipment_id=shipment_id)
        if not queryset.exists():
            return {'error': 'please provide a valid shipment_id'}
    obj = queryset.filter(crate__crate_id=crate_id).last()
    if not obj:
        return {'error': 'please provide a valid crate_id'}
    if crate_type and obj.crate.crate_type != crate_type:
        return {'error': 'selected carte type is not allowed.'}
    return {'data': obj}


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

def get_shipment_by_shipment_label(shipment_label_id):
    obj = ShipmentPackaging.objects.filter(id=shipment_label_id).last()
    if not obj:
        return {'error': 'please provide a valid shipment_label_id'}
    return {'data': obj.shipment.pk}

def validate_shipment_id(shipment_id):
    obj = OrderedProduct.objects.filter(id=shipment_id).last()
    if not obj:
        return {'error': 'please provide a valid shipment_label_id'}
    return {'data': obj.pk}

