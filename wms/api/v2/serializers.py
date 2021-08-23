import csv
from itertools import chain

from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from products.models import Product
from shops.models import Shop
from wms.common_functions import ZoneCommonFunction
from wms.models import In, Out, InventoryType, Zone
from wms.common_validators import get_validate_putaway_users

User = get_user_model()


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


class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'phone_number',)


class WarehouseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shop
        fields = ('id', '__str__')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['warehouse'] = {
            'id': representation['id'],
            'shop': representation['__str__']
        }
        return representation['warehouse']


class ZoneCrudSerializers(serializers.ModelSerializer):
    warehouse = WarehouseSerializer(read_only=True)
    supervisor = UserSerializers(read_only=True)
    coordinator = UserSerializers(read_only=True)
    putaway_users = UserSerializers(read_only=True, many=True)

    class Meta:
        model = Zone
        fields = ('id', 'warehouse', 'supervisor', 'coordinator', 'putaway_users', 'created_at', 'updated_at')

    def validate(self, data):

        if 'warehouse' in self.initial_data and self.initial_data['warehouse']:
            try:
                warehouse = Shop.objects.get(id=self.initial_data['warehouse'], shop_type__shop_type='sp')
                data['warehouse'] = warehouse
            except:
                raise serializers.ValidationError("Invalid warehouse")
        else:
            raise serializers.ValidationError("'warehouse' | This is mandatory")

        if 'supervisor' in self.initial_data and self.initial_data['supervisor']:
            try:
                supervisor = User.objects.get(id=self.initial_data['supervisor'])
            except:
                raise serializers.ValidationError("Invalid supervisor")
            if supervisor.has_perm('wms.can_have_zone_supervisor_permission'):
                data['supervisor'] = supervisor
            else:
                raise serializers.ValidationError("Supervisor does not have required permission.")
        else:
            raise serializers.ValidationError("'supervisor' | This is mandatory")

        if 'coordinator' in self.initial_data and self.initial_data['coordinator']:
            try:
                coordinator = User.objects.get(id=self.initial_data['coordinator'])
            except:
                raise serializers.ValidationError("Invalid coordinator")
            if coordinator.has_perm('wms.can_have_zone_coordinator_permission'):
                data['coordinator'] = coordinator
            else:
                raise serializers.ValidationError("Coordinator does not have required permission.")
        else:
            raise serializers.ValidationError("'coordinator' | This is mandatory")

        # if self.initial_data['warehouse'] and self.initial_data['supervisor'] and self.initial_data['coordinator']:
        #     if Zone.objects.filter(warehouse=self.initial_data['warehouse'], supervisor=self.initial_data['supervisor'],
        #                         coordinator=self.initial_data['coordinator']).exists():
        #         raise serializers.ValidationError(
        #             "Zone already exist for selected 'warehouse', 'supervisor' and 'coordinator'")

        if 'putaway_users' in self.initial_data and self.initial_data['putaway_users']:
            if len(self.initial_data['putaway_users']) > 2:
                raise serializers.ValidationError("Maximum 2 putaway users are allowed.")
            putaway_users = get_validate_putaway_users(self.initial_data['putaway_users'])
            if 'error' in putaway_users:
                raise serializers.ValidationError((putaway_users["error"]))
            data['putaway_users'] = putaway_users['putaway_users']
        else:
            raise serializers.ValidationError("'putaway_users' | This is mandatory")

        if 'id' in self.initial_data and self.initial_data['id']:
            if not Zone.objects.filter(id=self.initial_data['id'], warehouse=warehouse).exists():
                raise serializers.ValidationError("Warehouse updation is not allowed.")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new Zone with Putaway Users"""
        putaway_users = validated_data.pop('putaway_users', None)

        try:
            zone_instance = Zone.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        ZoneCommonFunction.update_putaway_users(zone_instance, putaway_users)
        return zone_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update Zone with Putaway Users"""
        putaway_users = validated_data.pop('putaway_users', None)

        try:
            zone_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        ZoneCommonFunction.update_putaway_users(zone_instance, putaway_users)
        return zone_instance





