from django.db.models import Q

from retailer_to_sp.models import ShopCrate, OrderedProduct
from wms.models import Crate


def run():
    print('create_shop_crate_mapping | STARTED')

    warehouses = Crate.objects.values_list('warehouse', flat=True).distinct()
    print(warehouses)
    for warehouse in warehouses:
        print(f"Started for Shop {warehouse}")
        # Used Crates
        used_crates = Crate.objects.filter(
            ~Q(crates_shipments__shipment__shipment_status__in=[OrderedProduct.FULLY_DELIVERED_AND_VERIFIED,
                                                                OrderedProduct.PARTIALLY_DELIVERED_AND_VERIFIED,
                                                                OrderedProduct.FULLY_RETURNED_AND_VERIFIED]),
            crates_shipments__isnull=False, warehouse=warehouse).values_list("id", flat=True)
        print(f"Warehouse {warehouse}, Used Crates Count {len(used_crates)}, List {used_crates}")
        create_shop_crate_mapping(used_crates, warehouse, False)
        # Available crates
        available_crates = Crate.objects.filter(
            ~Q(id__in=used_crates), warehouse=warehouse).values_list("id", flat=True)
        print(f"Warehouse {warehouse}, Available Crates Count {len(available_crates)}, List {available_crates}")
        create_shop_crate_mapping(available_crates, warehouse, True)
        print(f"Ended for Shop {warehouse}")
    print('create_shop_crate_mapping | ENDED')


def create_shop_crate_mapping(crates, warehouse, available=True):
    for crate_id in crates:
        shop_crate_instance, _ = ShopCrate.objects.update_or_create(
            shop_id=warehouse, crate_id=crate_id, defaults={'is_available': available})
        print("ShopCrate entry created, Instance " + str(shop_crate_instance))
