from rest_framework import serializers

from gram_to_brand.models import GRNOrderProductMapping, GRNOrder
from products.models import Product, ParentProduct
from shops.models import Shop
from wms.models import Zone


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        ref_name = "WarehouseSerializer v1"
        fields = ('id', 'shop_name')


class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = ParentProduct
        fields = ('id', 'parent_id', 'name',)
        ref_name = "GramBrandParentProduct"


class ProductSerializer(serializers.ModelSerializer):
    parent_product = ProductSerializer(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'product_name', 'parent_product')
        ref_name = "GramBrandProduct"


class GRNOrderNonZoneProductsCrudSerializers(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

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
                if 'zone_id' in val and val['zone_id'] is None:
                    if 'grn_order_grn_order_product' not in response_data:
                        response_data['grn_order_grn_order_product'] = []
                    obj_needed = True
                    sub_val = val.copy()
                    sub_val.pop('zone_id')
                    response_data['grn_order_grn_order_product'].append(sub_val)
            if obj_needed:
                response_data['id'] = representation['id']
                response_data['warehouse'] = representation['warehouse']
        return response_data
