from rest_framework import serializers
from django.db import transaction

from gram_to_brand.models import GRNOrderProductMapping, GRNOrder
from shops.models import Shop, ParentRetailerMapping
from retailer_to_sp.api.v1.serializers import ProductSerializer
from wms.api.v2.serializers import ZoneSerializer


class ParentRetailerMappingSerializer(serializers.ModelSerializer):

    class Meta:
        model = ParentRetailerMapping
        fields = ('id', 'retailer', 'parent')



class GRNOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = GRNOrder
        fields = ('id', 'order', 'invoice_no', 'invoice_date', 'invoice_amount', 'tcs_amount')


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'shop_name')


class GRNOrderNonZoneProductsCrudSerializers(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    zone_id = ZoneSerializer(read_only=True)

    class Meta:
        model = GRNOrderProductMapping
        fields = ('id', 'product', 'zone_id',)

    def validate(self, data):

        # if 'product' in self.initial_data and self.initial_data['product']:
        #     try:
        #         product = ParentProduct.objects.get(id=self.initial_data['product'])
        #     except:
        #         raise serializers.ValidationError("Invalid product")
        #     data['product'] = product
        # else:
        #     raise serializers.ValidationError("'product' | This is mandatory")
        #
        # if 'zone' in self.initial_data and self.initial_data['zone']:
        #     try:
        #         zone = Zone.objects.get(id=self.initial_data['zone'])
        #         if zone.warehouse != warehouse:
        #             raise serializers.ValidationError("Invalid zone for selected warehouse.")
        #     except:
        #         raise serializers.ValidationError("Invalid zone")
        #     data['zone'] = zone
        # else:
        #     raise serializers.ValidationError("'zone' | This is mandatory")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new WarehouseAssortment"""

        try:
            whc_assortment_instance = GRNOrderProductMapping.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return whc_assortment_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update WarehouseAssortment"""

        try:
            whc_assortment_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return whc_assortment_instance


class GRNOrderSerializers(serializers.ModelSerializer):
    warehouse = WarehouseSerializer(read_only=True)
    grn_order_grn_order_product = GRNOrderNonZoneProductsCrudSerializers(read_only=True, many=True)

    class Meta:
        model = GRNOrder
        fields = ('id', 'warehouse', 'grn_order_grn_order_product',)

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     response_data = {}
    #     if representation['grn_order_grn_order_product']:
    #         obj_needed = False
    #         for val in representation['grn_order_grn_order_product']:
    #             if val['zone_id'] is None:
    #                 if 'grn_order_grn_order_product' not in response_data:
    #                     response_data['grn_order_grn_order_product'] = []
    #                 obj_needed = True
    #                 response_data['grn_order_grn_order_product'].append(val)
    #         if obj_needed:
    #             response_data['id'] = representation['id']
    #             response_data['warehouse'] = representation['warehouse']
    #     return response_data
