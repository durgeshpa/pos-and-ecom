import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from wms.models import Bin,PickupBinInventory,BinInventory,InventoryType,Putaway
from gram_to_brand.models import GRNOrderProductMapping

# virtual_bin = Bin.objects.filter(bin_id='V2VZ01SR001-0001').last()
# pickup_bin_inventory_list = PickupBinInventory.objects.all()
# #putaway_list = Putaway.objects.all()
# inventory_type = InventoryType.objects.filter(inventory_type='normal').last()
# print(pickup_bin_inventory_list.count())
# for pickup_bin_inventory in pickup_bin_inventory_list:
#     if len(pickup_bin_inventory.batch_id)==25:
#         pickup_bin_inventory.batch_id=pickup_bin_inventory.batch_id[0:22]+'1'
#         pickup_bin_inventory.save()
#     if pickup_bin_inventory.pickup.warehouse.id != 32154:
#         continue
#     if pickup_bin_inventory.bin is None:
#         bin_inventory = BinInventory.objects.filter(warehouse=pickup_bin_inventory.pickup.warehouse,bin=virtual_bin,
#                                                         sku=pickup_bin_inventory.pickup.sku,
#                                                         batch_id=pickup_bin_inventory.batch_id,
#                                                         inventory_type=inventory_type
#                                                         ).last()
#         print(pickup_bin_inventory.pickup.warehouse)
#         print(virtual_bin)
#         print(pickup_bin_inventory.pickup.sku)
#         print(pickup_bin_inventory.batch_id)
#         print(inventory_type)
#         print("=================")
#         print(pickup_bin_inventory.pickup.sku)
#         print(bin_inventory)
#         print(pickup_bin_inventory.id)
#         pickup_bin_inventory.bin = bin_inventory
#         pickup_bin_inventory.save()