from retailer_to_sp.models import ShipmentPackaging
from wms.models import Crate


# def validate_shipment_crates_list(crates_dict, quantity, warehouse_id):
#     if 'crates' not in crates_dict or not crates_dict['crates']:
#         return {"error": "Missing 'crates' in shipment_crates for packaging_type 'CRATE'."}
#     if not isinstance(crates_dict['crates'], list):
#         return {"error": "Key 'crates' can be of list type only."}
#     total_crate_qty = 0
#     for crate_obj in crates_dict['crates']:
#         if not isinstance(crate_obj, dict):
#             return {"error": "Key 'crates' can be of list of object type only."}
#         if 'crate_id' not in crate_obj or not crate_obj['crate_id']:
#             return {"error": "Missing 'crate_id' in shipment_crates for packaging_type 'CRATE'."}
#         if 'quantity' not in crate_obj or not crate_obj['quantity']:
#             return {"error": "Missing 'quantity' in shipment_crates for packaging_type 'CRATE'."}
#         try:
#             crate_qty = int(crate_obj['quantity'])
#         except:
#             return {"error": "'crate.quantity' | Invalid crate quantity."}
#         if not Crate.objects.filter(crate_id=crate_obj['crate_id'], warehouse__id=warehouse_id,
#                                     crate_type=Crate.DISPATCH).exists():
#             return {"error": "Invalid crates selected in packaging."}
#         total_crate_qty += crate_qty
#     if total_crate_qty != int(quantity):
#         return {"error": "Crates quantity should be matched with shipped quantity."}
#     return {"data": crates_dict}


def validate_shipment_package_list(packaging_type, package_dict, quantity, warehouse_id):
    if 'packages' not in package_dict or not package_dict['packages']:
        return {"error": f"Missing 'packages' in packaging for packaging_type {packaging_type}'."}
    if not isinstance(package_dict['packages'], list):
        return {"error": "Key 'packages' can be of list type only."}
    total_packages_qty = 0
    for package_obj in package_dict['packages']:
        if not isinstance(package_obj, dict):
            return {"error": "Key 'packages' can be of list of object type only."}
        if packaging_type == ShipmentPackaging.CRATE and \
                ('package_id' not in package_obj or not package_obj['package_id']):
            return {"error": "Missing 'package_obj' in shipment packages for packaging_type 'CRATE'."}
        if 'quantity' not in package_obj or not package_obj['quantity']:
            return {"error": f"Missing 'quantity' in shipment packages for packaging_type {packaging_type}."}
        if packaging_type != ShipmentPackaging.CRATE and ('is_new' not in package_obj or package_obj['is_new'] is None):
            return {"error": "'packaging.is_new' | This is mandatory for SACK & BOX."}
        if package_obj['is_new'] not in [True, False]:
            return {"error": "'packaging.is_new' | Invalid choice."}

        try:
            package_qty = int(package_obj['quantity'])
        except:
            return {"error": "'package.quantity' | Invalid package quantity."}

        if packaging_type == ShipmentPackaging.CRATE and\
                not Crate.objects.filter(crate_id=package_obj['package_id'], warehouse__id=warehouse_id,
                                    crate_type=Crate.DISPATCH).exists():
            return {"error": "Invalid crates selected in packaging."}

        total_packages_qty += package_qty
    if total_packages_qty != int(quantity):
        return {"error": "package quantity should match shipped quantity."}
    return {"data": package_dict}


def validate_shipment_dispatch_item(queryset, dispatch_item_id, shipment_id):
    if not queryset.filter(id=dispatch_item_id, shipment_packaging__shipment_id=shipment_id).exists():
        return {"error": "Invalid item for this shipment"}
    return {"data": queryset.filter(id=dispatch_item_id, shipment_packaging__shipment_id=shipment_id).last()}
    