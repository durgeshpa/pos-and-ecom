import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()

from shops.models import Shop
from shops.models import ShopType
from copy import copy, deepcopy
#GFDN shops
gf_shop_ids= {7:172,599:600}

# create Addistro shops
sp_shop_type = ShopType.objects.all().filter(pk=3).last()
for key, value in gf_shop_ids.items():
    gf_shop = Shop.objects.all().filter(pk=key).last()
    sp_shop = Shop.objects.all().filter(pk=value).last()
    new_sp_shop = deepcopy(sp_shop)
#    new_sp_shop.shop_type=sp_shop_type
    new_sp_shop.pk=None
    new_sp_shop.shop_name = gf_shop.shop_name
    new_sp_shop.warehouse_code = gf_shop.warehouse_code
    new_sp_shop.save()


    #sp_shop.save()

gf_shop_set=Shop.objects.all().filter(shop_type=3,status=True)
print(gf_shop_set)
