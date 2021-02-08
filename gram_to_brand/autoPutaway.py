from wms.models import Bin, Putaway, PutawayBinInventory, BinInventory, InventoryType, Pickup, InventoryState, \
    PickupBinInventory, StockMovementCSVUpload, In
from shops.models import Shop
# from wms.common_functions import PutawayCommonFunctions
from global_config.models import GlobalConfig
from wms.views import PickupInventoryManagement, update_putaway
from wms.common_functions import (CommonBinInventoryFunctions, PutawayCommonFunctions, CommonBinFunctions,updating_tables_on_putaway,
from django.db.models import Q, Sum
from wms.api.v1  import .serializers
from serializers import PutAwaySerializer,
from django.db import transaction


def autoPutAway(request,warehouse, batch_id, quantity):

    virtual_bin_ids = GlobalConfig.objects.get(key='virtual_bins')
    bin_ids = virtual_bin_ids.value

    data, key = {}, 0
    lis_data = []
    inventory_type = 'normal'
    type_normal = InventoryType.objects.filter(inventory_type=inventory_type).last()
    diction = {i[0]: i[1] for i in zip(batch_id, quantity)}
    for i, value in diction.items():
        key += 1
        val = value
        put_away = PutawayCommonFunctions.get_filtered_putaways(batch_id=i, warehouse=warehouse,
                                                                inventory_type=type_normal).order_by('created_at')
        ids = [i.id for i in put_away]
        sh = Shop.objects.filter(id=int(warehouse)).last()
        state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()
        if sh.shop_type.shop_type == 'sp':
            for bin_id in bin_ids:
                pass
            bin_inventory = CommonBinInventoryFunctions.get_filtered_bin_inventory(sku=i[:17], bin__bin_id=bin_id) \
                .exclude(batch_id=i)
            with transaction.atomic():
                if bin_inventory.exists():
                    qs = bin_inventory.filter(inventory_type=type_normal) \
                        .aggregate(available=Sum('quantity'), to_be_picked=Sum('to_be_picked_qty'))
                    total = qs['available'] + qs['to_be_picked']
                    continue

            pu = PutawayCommonFunctions.get_filtered_putaways(id=ids[0], batch_id=i, warehouse=warehouse)
            put_away_status = False
            while len(ids):
                put_away_done = update_putaway(ids[0], i, warehouse, int(value), request.user)
                value = put_away_done
                put_away_status = True
                ids.remove(ids[0])

                updating_tables_on_putaway(sh, bin_id, put_away, i, type_normal, state_total_available, 't', val,
                                           put_away_status, pu)
        serializer = (PutAwaySerializer(Putaway.objects.filter(batch_id=i, warehouse=warehouse).last(),
                                        fields=('is_success', 'product_sku', 'inventory_type', 'batch_id',
                                                'max_putaway_qty', 'putaway_quantity', 'product_name')))
        msg = serializer.data
        lis_data.append(msg)
        data.update({'is_success': True, 'message': "quantity has been updated in put away.", 'data': lis_data})



