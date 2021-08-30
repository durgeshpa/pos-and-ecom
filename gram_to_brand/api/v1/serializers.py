from rest_framework import serializers
from django.db import transaction

from gram_to_brand.models import GRNOrderProductMapping, GRNOrder
from shops.models import Shop
from products.models import Product
from wms.api.v2.serializers import ZoneSerializer


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'shop_name')


class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ('id', 'product_name',)


class GRNOrderNonZoneProductsCrudSerializers(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    zone_id = ZoneSerializer(read_only=True)

    class Meta:
        model = GRNOrderProductMapping
        fields = ('id', 'product', 'zone_id',)


class GRNOrderSerializers(serializers.ModelSerializer):
    warehouse = WarehouseSerializer(read_only=True)
    grn_order_grn_order_product = GRNOrderNonZoneProductsCrudSerializers(read_only=True, many=True)

    class Meta:
        model = GRNOrder
        fields = ('id', 'warehouse', 'grn_order_grn_order_product',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        response_data = {}
        if representation['grn_order_grn_order_product']:
            obj_needed = False
            for val in representation['grn_order_grn_order_product']:
                if val['zone_id'] is None:
                    if 'grn_order_grn_order_product' not in response_data:
                        response_data['grn_order_grn_order_product'] = []
                    obj_needed = True
                    response_data['grn_order_grn_order_product'].append(val)
            if obj_needed:
                response_data['id'] = representation['id']
                response_data['warehouse'] = representation['warehouse']
            else:
                pass
        return response_data
