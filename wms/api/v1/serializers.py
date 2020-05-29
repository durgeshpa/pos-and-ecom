from rest_framework import serializers
from wms.models import Bin, Putaway
from shops.api.v1.serializers import ShopSerializer
from retailer_to_sp.api.v1.serializers import ProductSerializer


class BinSerializer(serializers.ModelSerializer):
    warehouse = ShopSerializer()

    class Meta:
        model = Bin
        fields = ('id','warehouse', 'bin_id', 'bin_type', 'is_active', 'bin_barcode', 'created_at', 'modified_at')



class PutAwaySerializer(serializers.ModelSerializer):
    warehouse = ShopSerializer()
    sku = ProductSerializer()

    class Meta:
        model = Putaway
        fields = ('id','warehouse', 'putaway_type', 'putaway_type_id', 'sku', 'batch_id', 'quantity', 'putaway_quantity', 'created_at', 'modified_at')