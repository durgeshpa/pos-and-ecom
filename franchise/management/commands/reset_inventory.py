from django.core.management.base import BaseCommand

from shops.models import Shop
from wms.models import In, Putaway, BinInventory, PutawayBinInventory, WarehouseInventory,\
    WarehouseInternalInventoryChange, BinInternalInventoryChange


class Command(BaseCommand):
    """
        Reset GRN related changes in franchise inventory
    """
    def handle(self, *args, **options):
        franchise_shops = Shop.objects.filter(shop_type__shop_type='f')

        for shop in franchise_shops:
            PutawayBinInventory.objects.filter(warehouse=shop).delete()
            Putaway.objects.filter(warehouse=shop).delete()
            WarehouseInventory.objects.filter(warehouse=shop).delete()
            BinInventory.objects.filter(warehouse=shop).delete()
            WarehouseInternalInventoryChange.objects.filter(warehouse=shop).delete()
            BinInternalInventoryChange.objects.filter(warehouse=shop).delete()
            In.objects.filter(warehouse=shop).delete()




