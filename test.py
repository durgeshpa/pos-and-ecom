import datetime
import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from retailer_to_sp.models import OrderedProduct

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
shipment=OrderedProduct.objects.filter(id=101739).last()
for shipment_product in shipment.rt_order_product_order_product_mapping.all():
    for shipment_product_batch in shipment_product.rt_ordered_product_mapping.all():
        putaway_qty = shipment_product_batch.returned_qty + shipment_product_batch.returned_damage_qty
        if putaway_qty == 0:
            continue
        else:
            print(shipment_product_batch.batch_id)