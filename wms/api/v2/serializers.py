import csv
from itertools import chain

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from products.models import Product
from shops.models import Shop
from wms.common_functions import BinInventoryCommonFunction, get_sku_from_batch
from wms.models import In, Out, InventoryType, BinInventory, Bin


class InSerializer(serializers.ModelSerializer):

    class Meta:
        model = In
        fields = ('sku', 'in_type', 'in_type_id', 'warehouse', 'quantity', 'created_at')


class OutSerializer(serializers.ModelSerializer):

    class Meta:
        model = Out
        fields = ('sku', 'out_type', 'out_type_id', 'warehouse', 'quantity', 'created_at')


class InOutLedgerSerializer(serializers.ModelSerializer):
    ins = serializers.SerializerMethodField('ins_data')
    outs = serializers.SerializerMethodField('outs_data')

    class Meta:
        model = Product
        fields = ('ins', 'outs',)

    def ins_data(self, obj):
        ins = In.objects.filter(sku=obj, created_at__gte=self.context.get('start_date'),
                                created_at__lte=self.context.get('end_date'))
        serializer = InSerializer(ins, many=True)
        return serializer.data

    def outs_data(self, obj):
        outs = Out.objects.filter(sku=obj, created_at__gte=self.context.get('start_date'),
                                  created_at__lte=self.context.get('end_date'))
        serializer = OutSerializer(outs, many=True)
        return serializer.data


class InOutLedgerCSVSerializer(serializers.ModelSerializer):
    start_date = serializers.DateTimeField(required=True)
    end_date = serializers.DateTimeField(required=True)

    class Meta:
        model = In
        fields = ('sku', 'warehouse', 'start_date', 'end_date')

    def validate(self, data):
        if 'sku' not in self.initial_data or not self.initial_data['sku']:
            raise serializers.ValidationError(_('sku must be selected '))
        sku_id = self.initial_data['sku']
        try:
            Product.objects.get(product_sku=sku_id)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(f'Product not found for sku {sku_id}')
        data['sku'] = sku_id

        if 'warehouse' not in self.initial_data or not self.initial_data['warehouse']:
            raise serializers.ValidationError(_('warehouse must be selected '))
        warehouse_id = self.initial_data['warehouse']
        try:
            Shop.objects.get(id=warehouse_id)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(f'Warehouse not found for {warehouse_id}')
        data['warehouse'] = warehouse_id
        return data

    def create(self, validated_data):
        # product_qs = Product.objects.filter(product_sku=validated_data['sku']).last()
        ins = In.objects.filter(sku=validated_data['sku'], created_at__gte=validated_data['start_date'],
                                created_at__lte=validated_data['end_date'], warehouse=validated_data['warehouse'])
        outs = Out.objects.filter(sku=validated_data['sku'], created_at__gte=validated_data['start_date'],
                                  created_at__lte=validated_data['end_date'], warehouse=validated_data['warehouse'])

        meta = Product._meta
        field_names = ['TRANSACTION TIMESTAMP', 'SKU', 'WAREHOUSE', 'INVENTORY TYPE', 'MOVEMENT TYPE',
                       'TRANSACTION TYPE', 'TRANSACTION ID', 'QUANTITY']

        inventory_types_qs = InventoryType.objects.values('id', 'inventory_type').order_by('id')
        inventory_types = list(x['inventory_type'].upper() for x in inventory_types_qs)

        data = sorted(chain(ins, outs), key=lambda instance: instance.created_at)

        # Sum of qty
        ins_type_wise_qty = ins.values('inventory_type').order_by('inventory_type').annotate(total_qty=Sum('quantity'))
        out_type_wise_qty = outs.values('inventory_type').order_by('inventory_type').annotate(total_qty=Sum('quantity'))

        in_type_ids = {x['inventory_type']: x['total_qty'] for x in ins_type_wise_qty}
        out_type_ids = {x['inventory_type']: x['total_qty'] for x in out_type_wise_qty}

        ins_count_list = ['TOTAL IN QUANTITY']
        outs_count_list = ['TOTAL OUT QUANTITY']
        for i in range(len(inventory_types_qs)):
            if i+1 in in_type_ids:
                ins_count_list.append(in_type_ids[i+1])
            else:
                ins_count_list.append('0')
            if i+1 in out_type_ids:
                outs_count_list.append(out_type_ids[i+1])
            else:
                outs_count_list.append('0')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow([''] + inventory_types)
        writer.writerow(ins_count_list)
        writer.writerow(outs_count_list)
        writer.writerow([])
        writer.writerow(field_names)
        for obj in data:
            created_at = obj.created_at.strftime('%b %d,%Y %H:%M:%S')
            if obj.__class__.__name__ == 'In':
                writer.writerow([created_at, obj.sku, obj.warehouse, obj.inventory_type, "IN", obj.in_type,
                                 obj.in_type_id, obj.quantity])
            elif obj.__class__.__name__ == 'Out':
                writer.writerow([created_at, obj.sku, obj.warehouse, obj.inventory_type, "OUT", obj.out_type,
                                 obj.out_type_id, obj.quantity])
            else:
                writer.writerow([created_at, obj.sku, obj.warehouse, obj.inventory_type, None, None, None,
                                 obj.quantity])
        return response


class WarehouseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shop
        fields = ('id', 'shop_name')


class BinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bin
        fields = ('id', 'bin_id', 'warehouse_id')


class InventoryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryType
        fields = ('id', 'inventory_type')


class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name')


class BinInventorySerializer(serializers.ModelSerializer):
    warehouse = WarehouseSerializer()
    bin = BinSerializer()
    inventory_type = InventoryTypeSerializer()
    sku = ProductSerializer()
    bin_quantity = serializers.SerializerMethodField()

    def get_bin_quantity(self, obj):
        return obj.quantity+obj.to_be_picked_qty

    class Meta:
        model = BinInventory
        fields = ('warehouse', 'bin', 'sku', 'batch_id', 'inventory_type', 'bin_quantity')


    def validate(self, data):
        target_bin_batch_dict = {}
        if 's_bin' in self.initial_data and self.initial_data['s_bin']:
            try:
                s_bin = Bin.objects.get(id=self.initial_data['s_bin'])
            except Exception as e:
                raise serializers.ValidationError("Invalid source Bin")
            data['s_bin'] = s_bin
        else:
            raise serializers.ValidationError("'s_bin' is required")

        if 't_bin' in self.initial_data and self.initial_data['t_bin']:
            try:
                t_bin = Bin.objects.get(id=self.initial_data['t_bin'])
            except Exception as e:
                raise serializers.ValidationError("Invalid target Bin")
            data['t_bin'] = t_bin
        else:
            raise serializers.ValidationError("'t_bin' is required")

        if 'batch_id' in self.initial_data and self.initial_data['batch_id']:
            data['batch_id'] = self.initial_data['batch_id']
        else:
            raise serializers.ValidationError("'batch_id' is required")

        if 'qty' in self.initial_data and self.initial_data['qty']:
            if self.initial_data['qty'] <= 0:
                raise serializers.ValidationError("Invalid Quantity {self.initial_data['qty']}")
            data['qty'] = self.initial_data['qty']
        else:
            raise serializers.ValidationError("'qty' is required")

        if 'inventory_type' in self.initial_data and self.initial_data['inventory_type']:
            try:
                inventory_type = InventoryType.objects.get(id=self.initial_data['inventory_type'])
            except Exception as e:
                raise serializers.ValidationError("Invalid Inventory Type")
            data['inventory_type'] = inventory_type
        else:
            raise serializers.ValidationError("'inventory_type' is required")

        bin_inv = BinInventory.objects.filter(bin=s_bin, batch_id=self.initial_data['batch_id'],
                                              inventory_type=inventory_type).last()
        if bin_inv.quantity+bin_inv.to_be_picked_qty < self.initial_data['qty']:
            raise serializers.ValidationError("Invalid Quantity to move | "
                                              "Available Quantity {bin_inv.quantity+bin_inv.to_be_picked_qty}")
        sku = get_sku_from_batch(self.initial_data['batch_id'])
        if BinInventory.objects.filter(~Q(batch_id=self.initial_data['batch_id']),
                                    Q(quantity_gt=0)|Q(to_be_picked_qty_gt=0), bin=t_bin, sku=sku).exists():
            raise serializers.ValidationError("Invalid Movement | "
                                              "Target bin already has same product with different batch ID")
        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            BinInventoryCommonFunction.product_shift_across_bins(validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return validated_data