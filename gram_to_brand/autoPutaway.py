from wms.models import Bin, Putaway, PutawayBinInventory, BinInventory, InventoryType, Pickup, InventoryState, \
    PickupBinInventory, StockMovementCSVUpload, In
from shops.models import Shop
# from wms.common_functions import PutawayCommonFunctions
from global_config.models import GlobalConfig

def autoPutAway(request,warehouse, batch_id, quantity):

    warehouse = request.user.shop_employee.all().last().shop_id
    batch_id = batch_id
    put_away_quantity =quantity
    warehouse = warehouse
    virtual_bin_ids = GlobalConfig.objects.get(key='virtual_bins')
    bin_ids = virtual_bin_ids.value
    for bin_id in bin_ids:
        bin_inv_obj = BinInventory.objects.filter(warehouse=warehouse, bin=bin_id,
                                                                  batch_id=batch_id,
                                                                  quantity=quantity).last()

    bin_obj = Bin.objects.filter(bin_id=bin_id, is_active=True)
    bin_ware_obj = Bin.objects.filter(bin_id=bin_id, is_active=True, warehouse=warehouse)
    put_away_quantity = put_away_quantity
    inventory_type = 'normal'
    type_normal = InventoryType.objects.filter(inventory_type=inventory_type).last()
    bin_skus = PutawayBinInventory.objects.values_list('putaway__sku__product_sku', flat=True)
    sh = Shop.objects.filter(id=int(warehouse)).last()
    state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()

