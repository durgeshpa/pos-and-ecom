import django
import os

from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from wms.models import Bin, PickupBinInventory
from gram_to_brand.models import GRNOrderProductMapping
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from retailer_to_sp.models import OrderedProduct



def common_on_return_and_partial(shipment, flag):
    with transaction.atomic():
        putaway_qty = 0
        # inv_type = {'E': InventoryType.objects.get(inventory_type='expired'),
        #             'D': InventoryType.objects.get(inventory_type='damaged'),
        #             'N': InventoryType.objects.get(inventory_type='normal')}
        for shipment_product in shipment.rt_order_product_order_product_mapping.all():
            for shipment_product_batch in shipment_product.rt_ordered_product_mapping.all():
                # first bin with non 0 inventory for a batch or last empty bin
                shipment_product_batch_bin_list = PickupBinInventory.objects.filter(
                    shipment_batch=shipment_product_batch)
                bin_id_for_input = None
                shipment_product_batch_bin_temp = None
                for shipment_product_batch_bin in shipment_product_batch_bin_list:
                    if shipment_product_batch_bin.bin.quantity == 0:
                        bin_id_for_input = shipment_product_batch_bin.bin
                        continue
                    else:
                        bin_id_for_input = shipment_product_batch_bin.bin
                        break
                if flag == "return":
                    putaway_qty = shipment_product_batch.returned_qty + shipment_product_batch.returned_damage_qty
                    if putaway_qty == 0:
                        continue
                    else:
                        print("hello")
                        # In.objects.create(warehouse=shipment_product_batch.rt_pickup_batch_mapping.last().warehouse, in_type='RETURN',
                        #                   in_type_id=shipment.id, sku=shipment_product_batch.ordered_product_mapping.product,
                        #                   batch_id=shipment_product_batch.batch_id, quantity=putaway_qty)
                        # pu, _ = Putaway.objects.update_or_create(putaway_user=shipment.last_modified_by,
                        #                                          warehouse=shipment_product_batch.rt_pickup_batch_mapping.last().warehouse,
                        #                                          putaway_type='RETURNED',
                        #                                          putaway_type_id=shipment.invoice_no,
                        #                                          sku=shipment_product_batch.ordered_product_mapping.product,
                        #                                          batch_id=shipment_product_batch.batch_id,
                        #                                          defaults={'quantity': putaway_qty,
                        #                                                    'putaway_quantity': 0})
                        # PutawayBinInventory.objects.update_or_create(warehouse=shipment_product_batch.rt_pickup_batch_mapping.last().warehouse,
                        #                                              sku=shipment_product_batch.ordered_product_mapping.product,
                        #                                              batch_id=shipment_product_batch.batch_id,
                        #                                              putaway_type='RETURNED',
                        #                                              putaway=pu, bin=bin_id_for_input,
                        #                                              putaway_status=False,
                        #                                              defaults={'putaway_quantity': putaway_qty})

                else:
                    pass


shipment=OrderedProduct.objects.filter(id=177117).last()
common_on_return_and_partial(shipment,'return')