from django.core.management.base import BaseCommand
from django.db import transaction

from franchise.models import FranchiseReturns
from products.models import Product
from franchise.models import ShopLocationMap
from wms.common_functions import CommonWarehouseInventoryFunctions, BinInternalInventoryChange
from wms.models import InventoryType, InventoryState, WarehouseInternalInventoryChange, Bin, BinInventory


class Command(BaseCommand):
    """
        Undo shipped inventory subtract for returns on sales before 29 Dec 2020
    """
    def handle(self, *args, **options):

        with transaction.atomic():
            processed_returns = FranchiseReturns.objects.filter(invoice_date__lt='2020-12-29', process_status__in=[1])
            count = 0
            for ret in processed_returns:
                print(ret)
                initial_type1 = InventoryType.objects.filter(inventory_type='new').last(),
                initial_stage1 = InventoryState.objects.filter(inventory_state='new').last(),
                shop = ShopLocationMap.objects.get(location_name__iexact=ret.shop_loc)
                sku = Product.objects.get(product_sku=ret.product_sku)

                # add shipped back - ret.quantity is negative by default
                CommonWarehouseInventoryFunctions.create_warehouse_inventory(shop.shop, sku, 'normal', 'shipped',
                                                                             ret.quantity * -1, True)

                # change initial type and initial stage from "normal", "shipped" to "new", "new"
                wiic_obj = WarehouseInternalInventoryChange.objects.get(warehouse=shop.shop, sku=sku,
                                                                        transaction_type='franchise_returns',transaction_id=ret.id)
                wiic_obj.initial_type = initial_type1[0]
                wiic_obj.initial_stage = initial_stage1[0]
                wiic_obj.save()
                biic_obj = BinInternalInventoryChange.objects.get(warehouse=shop.shop, sku=sku, transaction_type='franchise_returns',
                                                                  transaction_id=ret.id)
                biic_obj.initial_inventory_type = initial_type1[0]
                biic_obj.save()
                count += 1
            print(count)