
from rest_framework import serializers
from wms.models import WarehouseInternalInventoryChange, WarehouseInventory, BinInventory, BinInternalInventoryChange, \
    Pickup

from audit.models import AuditDetail
class WarehouseInventorySerializer(serializers.ModelSerializer):
    inventory_type = serializers.SerializerMethodField('get_type')
    inventory_state = serializers.SerializerMethodField('get_state')

    class Meta:
        model = WarehouseInventory
        fields = ('sku_id', 'inventory_type', 'inventory_state', 'quantity')

    def get_type(self, obj):
        return obj.audit_inventory_type.audit_inventory_type

    def get_state(self, obj):
        return obj.inventory_state.inventory_state


class WarehouseInventoryTransactionSerializer(serializers.ModelSerializer):
    sku = serializers.SerializerMethodField('product_sku')
    initial_inventory_type = serializers.SerializerMethodField('initial_type')
    initial_inventory_stage = serializers.SerializerMethodField('initial_stage')
    final_inventory_type = serializers.SerializerMethodField('final_type')
    final_inventory_stage = serializers.SerializerMethodField('final_stage')

    class Meta:
        model = WarehouseInternalInventoryChange
        fields = ('sku', 'initial_inventory_type', 'initial_inventory_stage', 'final_inventory_type',
                  'final_inventory_stage', 'quantity', 'created_at')

    def product_sku(self, obj):
        sku_id = obj.sku.product_sku
        return sku_id

    def initial_type(self, obj):
        return obj.initial_type.audit_inventory_type

    def final_type(self, obj):
        return obj.final_type.audit_inventory_type

    def initial_stage(self, obj):
        return obj.initial_stage.inventory_state

    def final_stage(self, obj):
        return obj.final_stage.inventory_state



class BinInventorySerializer(serializers.ModelSerializer):
    inventory_type = serializers.SerializerMethodField('get_type')
    bin = serializers.SerializerMethodField('bin_id')

    class Meta:
        model = BinInventory
        fields = ('sku_id', 'bin', 'batch_id', 'inventory_type', 'quantity')

    def get_type(self, obj):
        if obj.audit_inventory_type:
            return obj.audit_inventory_type.audit_inventory_type

    def bin_id(self, obj):
        return obj.bin.bin_id


class BinInventoryTransactionSerializer(serializers.ModelSerializer):
    initial_inventory_type = serializers.SerializerMethodField('initial_type')
    final_inventory_type = serializers.SerializerMethodField('final_type')
    initial_bin = serializers.SerializerMethodField('start_bin')
    final_bin = serializers.SerializerMethodField('end_bin')

    class Meta:
        model = BinInternalInventoryChange
        fields = ('sku_id', 'initial_inventory_type', 'initial_bin', 'final_inventory_type', 'final_bin',
                  'quantity', 'created_at')

    def initial_type(self, obj):
        if obj.initial_inventory_type:
            return obj.initial_inventory_type.audit_inventory_type

    def final_type(self, obj):
        if obj.final_inventory_type:
            return obj.final_inventory_type.audit_inventory_type

    def start_bin(self, obj):
        if obj.initial_bin:
            return obj.initial_bin.bin_id

    def end_bin(self, obj):
        if obj.final_bin:
            return obj.final_bin.bin_id


class PickupBlockedQuantitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Pickup
        fields = ('warehouse', 'pickup_type_id', 'status', 'sku_id', 'quantity')


class AuditBulkCreation(serializers.ModelSerializer):
    class Meta:
        model = AuditDetail
        fields = '__all__'