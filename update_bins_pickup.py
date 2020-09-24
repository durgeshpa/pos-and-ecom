import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from wms.models import Bin,PickupBinInventory,BinInventory,InventoryType
from gram_to_brand.models import GRNOrderProductMapping

virtual_bin = Bin.objects.filter(bin_id='V2VZ01SR001-0001').last()
pickup_bin_inventory_list = PickupBinInventory.objects.filter(bin = None)
inventory_type = InventoryType.objects.filter(inventory_type='normal').last()
for pickup_bin_inventory in pickup_bin_inventory_list:
    bin_inventory = BinInventory.objects.filter(warehouse=pickup_bin_inventory.pickup.warehouse,
                                                    bin=virtual_bin,
                                                    sku=pickup_bin_inventory.pickup.sku,
                                                    batch_id=pickup_bin_inventory.batch_id,
                                                    inventory_type=inventory_type
                                                    ).last()
    pickup_bin_inventory.bin = bin_inventory
    pickup_bin_inventory.save()