from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe
from rest_framework import serializers
from wms.models import Bin, Putaway, Out, Pickup, BinInventory, PickupBinInventory
from retailer_to_sp.models import Order, Repackaging
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
    is_success = serializers.SerializerMethodField('is_success_dt')
    inventory_type = serializers.SerializerMethodField('inventory_type_dt')
    quantity = serializers.SerializerMethodField('grned_quantity_dt')
    putaway_quantity = serializers.SerializerMethodField('putaway_quantity_dt')
    product_name = serializers.SerializerMethodField('product_name_dt')
    max_putaway_qty = serializers.SerializerMethodField('max_putaway_qty_dt')

    class Meta:
        model = Putaway
        fields = ('is_success','id','warehouse', 'putaway_type', 'putaway_type_id', 'sku','product_sku', 'batch_id',
                  'inventory_type', 'quantity', 'putaway_quantity', 'created_at', 'modified_at', 'product_name', 'max_putaway_qty')

    def product_sku_dt(self, obj):
        return obj.sku.product_sku

    def is_success_dt(self,obj):
        return True

    def inventory_type_dt(self, obj):
        return obj.inventory_type.inventory_type

    def grned_quantity_dt(self, obj):
        return Putaway.objects.filter(batch_id=obj.batch_id, warehouse=obj.warehouse_id, putaway_type='GRN').aggregate(total=Sum('quantity'))['total']

    def putaway_quantity_dt(self, obj):
        return Putaway.objects.filter(batch_id=obj.batch_id, warehouse=obj.warehouse_id, putaway_type='GRN').aggregate(total=Sum('putaway_quantity'))['total']

    def product_name_dt(self, obj):
        return obj.sku.product_name

    def max_putaway_qty_dt(self, obj):
        qs = Putaway.objects.filter(batch_id=obj.batch_id, warehouse=obj.warehouse_id, putaway_type='GRN')\
                            .aggregate(total=Sum('quantity'), putaway_qty=Sum('putaway_quantity'))
        total_qty = qs['total']
        putaway_qty = qs['putaway_qty']
        max_putaway_allowed = total_qty - putaway_qty
        return max_putaway_allowed


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
    order_create_date = serializers.SerializerMethodField()
    delivery_location = serializers.SerializerMethodField('m_delivery_location')
    picking_assigned_time = serializers.SerializerMethodField('get_assigned_time')
    picking_completed_time = serializers.SerializerMethodField('get_completed_time')
    
    class Meta:
        model = Order
        fields = ('id', 'order_no', 'picker_status', 'order_create_date', 'delivery_location', 'picking_assigned_time', 'picking_completed_time')

    def picker_status_dt(self, obj):
        return str(obj.order_status).lower()

    def get_order_create_date(self, obj):
        return obj.created_at.strftime("%d-%m-%Y")

    def m_delivery_location(self, obj):
        return obj.shipping_address.city.city_name

    def get_assigned_time(self, obj):
        return obj.picker_order.last().picker_assigned_date

    def get_completed_time(self, obj):
        return obj.pickup_completed_at

class BinSerializer(DynamicFieldsModelSerializer):
    warehouse = ShopSerializer()

    class Meta:
        model = Bin
        fields = ('id','warehouse', 'bin_id', 'bin_type', 'is_active', 'bin_barcode','bin_barcode_txt', 'created_at', 'modified_at')


class BinInventorySerializer(serializers.ModelSerializer):
    # inventory_type = serializers.SerializerMethodField()
    bin_id = serializers.SerializerMethodField()

    class Meta:
        model = BinInventory
        fields = ('bin_id', 'batch_id', 'quantity',
                  # 'inventory_type'
                  )

    @staticmethod
    def get_inventory_type(obj):
        return obj.inventory_type.inventory_type

    @staticmethod
    def get_bin_id(obj):
        return obj.bin.bin_id


class PickupBinInventorySerializer(serializers.ModelSerializer):
    sku_id = serializers.SerializerMethodField('sku_id_dt')
    batch_id_with_sku = serializers.SerializerMethodField('batch_sku')
    product_mrp = serializers.SerializerMethodField('product_mrp_dt')
    is_success = serializers.SerializerMethodField('is_success_dt')
    product_image = serializers.SerializerMethodField('m_product_image')
    # bin_id = serializers.SerializerMethodField('bin_id_dt')

    class Meta:
        model = PickupBinInventory
        fields = ('is_success', 'id', 'quantity','pickup_quantity','product_mrp','batch_id_with_sku','sku_id',
                  'product_image')

    def sku_id_dt(self, obj):
        sku_id = obj.pickup.sku.id
        return sku_id

    def product_mrp_dt(self, obj):
        # mrp = obj.pickup.sku.rt_cart_product_mapping.all().last().cart_product_price.mrp
        if obj.pickup.sku.product_mrp:
            return obj.pickup.sku.product_mrp
        # product_mrp = obj.pickup.sku.product_pro_price.filter(seller_shop=obj.warehouse, approval_status=2)
        # if product_mrp:
        #    return product_mrp.last().mrp
        else:
            return None

    def batch_sku(self, obj):
        batch_id = obj.batch_id
        sku = obj.pickup.sku.product_name
        return '{}:{}'.format(batch_id, sku)

    def is_success_dt(self, obj):
        return True

    def m_product_image(self,obj):
        if obj.pickup.sku.product_pro_image.exists():
            return obj.pickup.sku.product_pro_image.last().image.url


class RepackagingSerializer(serializers.ModelSerializer):
    picker_status = serializers.SerializerMethodField('picker_status_dt')
    order_create_date = serializers.SerializerMethodField()
    delivery_location = serializers.SerializerMethodField('m_delivery_location')
    order_no = serializers.SerializerMethodField()

    class Meta:
        model = Repackaging
        fields = ('id', 'order_no', 'picker_status', 'order_create_date', 'delivery_location',)

    def picker_status_dt(self, obj):
        return str(obj.source_picking_status).lower()

    def get_order_create_date(self, obj):
        return obj.created_at.strftime("%d-%m-%Y")

    def m_delivery_location(self, obj):
        return ''

    def get_order_no(self, obj):
        return obj.repackaging_no


    # def bin_id_dt(self, obj):
    #     return obj.bin.bin.bin_id


