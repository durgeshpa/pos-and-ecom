import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from wms.models import Bin
from gram_to_brand.models import GRNOrderProductMapping
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()

bin_list = Bin.objects.all()
for bin in bin_list:
    bin.bin_barcode_txt = '1' + str(bin.id).zfill(11)
    bin.save()

grnproduct_list= GRNOrderProductMapping.objects.all()
for grnproduct in grnproduct_list:
    if grnproduct.barcode_id is None:
        grnproduct.save()