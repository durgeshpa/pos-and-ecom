from rest_framework import serializers
from wms.models import Bin, Putaway, Out, Pickup, BinInventory
from retailer_to_sp.models import Order
from shops.api.v1.serializers import ShopSerializer
from retailer_to_sp.api.v1.serializers import ProductSerializer
from django.db.models import Sum


class DynamicFieldsModelSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        """
        fields = kwargs.pop('fields', None)
        exclude = kwargs.pop('exclude', None)

        super(DynamicFieldsModelSerializer, self).__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        if exclude is not None:
            not_allowed = set(exclude)
            for exclude_name in not_allowed:
                self.fields.pop(exclude_name)


class PutAwaySerializer(DynamicFieldsModelSerializer):
    warehouse = ShopSerializer()
    sku = ProductSerializer()
    product_sku = serializers.SerializerMethodField('product_sku_dt')
    is_success= serializers.SerializerMethodField('is_success_dt')
    quantity = serializers.SerializerMethodField('grned_quantity_dt')
    putaway_quantity = serializers.SerializerMethodField('putaway_quantity_dt')

    class Meta:
        model = Putaway
        fields = ('is_success','id','warehouse', 'putaway_type', 'putaway_type_id', 'sku','product_sku', 'batch_id', 'quantity', 'putaway_quantity', 'created_at', 'modified_at')

    def product_sku_dt(self, obj):
        return obj.sku.product_sku

    def is_success_dt(self,obj):
        return True

    def grned_quantity_dt(self, obj):
        return Putaway.objects.filter(batch_id=obj.batch_id).aggregate(total=Sum('quantity'))['total']

    def putaway_quantity_dt(self, obj):
        return Putaway.objects.filter(batch_id=obj.batch_id).aggregate(total=Sum('putaway_quantity'))['total']


class OutSerializer(serializers.ModelSerializer):
    warehouse = ShopSerializer()
    sku=ProductSerializer()

    class Meta:
        model = Out
        fields = ('id', 'warehouse', 'out_type', 'out_type_id', 'sku', 'quantity', 'created_at')


class PickupSerializer(DynamicFieldsModelSerializer):
    warehouse = ShopSerializer()
    sku = ProductSerializer()
    out = OutSerializer()
    bin_ids = serializers.SerializerMethodField('bin_ids_dt')
    batch_id_with_sku = serializers.SerializerMethodField('batch_sku')
    product_mrp = serializers.SerializerMethodField('product_mrp_dt')
    sku_id = serializers.SerializerMethodField('sku_id_dt')
    is_success = serializers.SerializerMethodField('is_success_dt')

    class Meta:
        model = Pickup
        fields = ('is_success','id', 'warehouse', 'pickup_type', 'pickup_type_id', 'sku', 'quantity', 'pickup_quantity','out',
                  'product_mrp', 'bin_ids','batch_id_with_sku', 'sku_id')

    def bin_ids_dt(self, obj):
        pickup_obj = [i.bin.bin_id for i in obj.sku.rt_product_sku.all()]
        return pickup_obj

    def batch_sku(self, obj):
        batch_id = obj.sku.rt_product_sku.filter(quantity__gt=0).order_by('-batch_id', '-quantity').last().batch_id if obj.sku.rt_product_sku.filter(quantity__gt=0).order_by('-batch_id', '-quantity').last() else None
        sku = obj.sku.product_name
        return '{}:{}'.format(batch_id, sku)

    def product_mrp_dt(self, obj):
        mrp = obj.sku.rt_cart_product_mapping.all().last().cart_product_price.mrp
        return mrp

    def sku_id_dt(self, obj):
        sku_id = obj.sku.id
        return sku_id

    def is_success_dt(self, obj):
        return True



class OrderSerializer(serializers.ModelSerializer):
    picker_status = serializers.SerializerMethodField('picker_status_dt')

    class Meta:
        model = Order
        fields = ('id', 'order_no', 'picker_status')

    def picker_status_dt(self, obj):
        return obj.picker_order.all().last().picking_status


class BinSerializer(DynamicFieldsModelSerializer):
    warehouse = ShopSerializer()

    class Meta:
        model = Bin
        fields = ('id','warehouse', 'bin_id', 'bin_type', 'is_active', 'bin_barcode', 'created_at', 'modified_at')



class BinInventorySerializer(serializers.ModelSerializer):
    bin = BinSerializer()
    sku = ProductSerializer()

    class Meta:
        model = BinInventory
        fields = ('id', 'bin', 'batch_id', 'sku',)






