import codecs
import csv
from itertools import chain

from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from products.models import Product, ParentProduct
from shops.models import Shop
from wms.common_functions import ZoneCommonFunction, WarehouseAssortmentCommonFunction
from wms.models import In, Out, InventoryType, Zone, WarehouseAssortment
from wms.common_validators import get_validate_putaway_users, read_warehouse_assortment_file

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


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentProduct
        fields = ('id', 'name')


class ZoneSerializer(serializers.ModelSerializer):
    warehouse = WarehouseSerializer(read_only=True)
    supervisor = UserSerializers(read_only=True)
    coordinator = UserSerializers(read_only=True)
    putaway_users = UserSerializers(read_only=True, many=True)

    class Meta:
        model = Zone
        fields = ('id', 'warehouse', 'supervisor', 'coordinator', 'putaway_users')


class WarehouseAssortmentCrudSerializers(serializers.ModelSerializer):
    warehouse = WarehouseSerializer(read_only=True)
    product = ProductSerializer(read_only=True)
    zone = ZoneSerializer(read_only=True)

    class Meta:
        model = WarehouseAssortment
        fields = ('id', 'warehouse', 'product', 'zone', 'created_at', 'updated_at')

    def validate(self, data):

        if 'warehouse' in self.initial_data and self.initial_data['warehouse']:
            try:
                warehouse = Shop.objects.get(id=self.initial_data['warehouse'], shop_type__shop_type='sp')
                data['warehouse'] = warehouse
            except:
                raise serializers.ValidationError("Invalid warehouse")
        else:
            raise serializers.ValidationError("'warehouse' | This is mandatory")

        if 'product' in self.initial_data and self.initial_data['product']:
            try:
                product = ParentProduct.objects.get(id=self.initial_data['product'])
            except:
                raise serializers.ValidationError("Invalid product")
            data['product'] = product
        else:
            raise serializers.ValidationError("'product' | This is mandatory")

        if 'zone' in self.initial_data and self.initial_data['zone']:
            try:
                zone = Zone.objects.get(id=self.initial_data['zone'])
                if zone.warehouse != warehouse:
                    raise serializers.ValidationError("Invalid zone for selected warehouse.")
            except:
                raise serializers.ValidationError("Invalid zone")
            data['zone'] = zone
        else:
            raise serializers.ValidationError("'zone' | This is mandatory")

        if WarehouseAssortment.objects.filter(warehouse=warehouse, product=product, zone=zone).exists():
            raise serializers.ValidationError(
                "Warehouse assortment already exist for selected 'warehouse', 'product' and 'zone'")

        if 'id' in self.initial_data and self.initial_data['id']:
            if not WarehouseAssortment.objects.filter(
                    id=self.initial_data['id'], warehouse=warehouse, product=product).exists():
                raise serializers.ValidationError("Only zone updation is allowed.")
        else:
            if WarehouseAssortment.objects.filter(warehouse=warehouse, product=product).exists():
                raise serializers.ValidationError("Warehouse Assortment already exist for selected warehouse and "
                                                  "product, only zone updation is allowed.")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new WarehouseAssortment"""

        try:
            whc_assortment_instance = WarehouseAssortment.objects.create(**validated_data)
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


class WarehouseAssortmentExportAsCSVSerializers(serializers.ModelSerializer):
    whc_assortment_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = WarehouseAssortment
        fields = ('whc_assortment_id_list',)

    def validate(self, data):

        if len(data.get('whc_assortment_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one warehouse assortment id must be selected '))

        for c_id in data.get('whc_assortment_id_list'):
            try:
                WarehouseAssortment.objects.get(id=c_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'warehouse assortment not found for id {c_id}')
        return data

    def create(self, validated_data):
        meta = WarehouseAssortment._meta
        field_names = ["Warehouse ID", "Warehouse", "Product ID", "Product", "Zone ID",
                       "Zone Supervisor (Number - Name)", "Zone Coordinator (Number - Name)",
                       "Created Datetime", "Updated Datetime"]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)

        queryset = WarehouseAssortment.objects.filter(id__in=validated_data['whc_assortment_id_list']). \
            select_related('warehouse', 'warehouse__shop_owner', 'warehouse__shop_type',
                           'warehouse__shop_type__shop_sub_type', 'product',
                           'zone', 'zone__warehouse', 'zone__warehouse__shop_owner', 'zone__warehouse__shop_type',
                           'zone__warehouse__shop_type__shop_sub_type', 'zone__supervisor', 'zone__coordinator'). \
            prefetch_related('zone__putaway_users'). \
            only('id', 'warehouse__id', 'warehouse__status', 'warehouse__shop_name', 'warehouse__shop_type',
                 'warehouse__shop_type__shop_type', 'warehouse__shop_type__shop_sub_type',
                 'warehouse__shop_type__shop_sub_type__retailer_type_name',
                 'warehouse__shop_owner', 'warehouse__shop_owner__first_name', 'warehouse__shop_owner__last_name',
                 'warehouse__shop_owner__phone_number', 'zone__id', 'zone__warehouse__id', 'zone__warehouse__status',
                 'zone__warehouse__shop_name', 'zone__warehouse__shop_type',
                 'zone__warehouse__shop_type__shop_type', 'zone__warehouse__shop_type__shop_sub_type',
                 'zone__warehouse__shop_type__shop_sub_type__retailer_type_name', 'zone__warehouse__shop_owner',
                 'zone__warehouse__shop_owner__first_name', 'zone__warehouse__shop_owner__last_name',
                 'zone__warehouse__shop_owner__phone_number', 'zone__supervisor__id', 'zone__supervisor__first_name',
                 'zone__supervisor__last_name', 'zone__supervisor__phone_number', 'zone__coordinator__id',
                 'zone__coordinator__first_name', 'zone__coordinator__last_name', 'zone__coordinator__phone_number',
                 'product__id', 'product__name', 'created_at', 'updated_at', )
        for row in queryset:
            writer.writerow([row.warehouse.id, row.warehouse, row.product.id, row.product.name, row.zone.id,
                             (str(row.zone.supervisor.phone_number) + " - " + str(row.zone.supervisor.first_name)),
                             (str(row.zone.coordinator.phone_number) + " - " + str(row.zone.coordinator.first_name)),
                             row.created_at.strftime('%b %d,%Y %H:%M:%S'),
                             row.updated_at.strftime('%b %d,%Y %H:%M:%S')])
        return response


class WarehouseAssortmentSampleCSVSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id',)

    def validate(self, data):
        if 'id' not in self.initial_data or not self.initial_data['id']:
            raise serializers.ValidationError(_('Warehouse must be selected '))
        w_id = self.initial_data['id']
        try:
            Shop.objects.get(id=w_id, shop_type__shop_type='sp')
        except ObjectDoesNotExist:
            raise serializers.ValidationError(f'Warehouse not found for id {w_id}')
        data['id'] = w_id
        return data

    def create(self, validated_data):
        meta = WarehouseAssortment._meta
        field_names = ['warehouse_id', 'warehouse', 'product_id', 'product', 'zone_id', 'zone_supervisor',
                       'zone_coordinator']
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)

        queryset = WarehouseAssortment.objects.filter(warehouse__id=validated_data['id']). \
            select_related('warehouse', 'warehouse__shop_owner', 'warehouse__shop_type',
                           'warehouse__shop_type__shop_sub_type', 'product',
                           'zone', 'zone__warehouse', 'zone__warehouse__shop_owner', 'zone__warehouse__shop_type',
                           'zone__warehouse__shop_type__shop_sub_type', 'zone__supervisor', 'zone__coordinator'). \
            prefetch_related('zone__putaway_users'). \
            only('id', 'warehouse__id', 'warehouse__status', 'warehouse__shop_name', 'warehouse__shop_type',
                 'warehouse__shop_type__shop_type', 'warehouse__shop_type__shop_sub_type',
                 'warehouse__shop_type__shop_sub_type__retailer_type_name',
                 'warehouse__shop_owner', 'warehouse__shop_owner__first_name', 'warehouse__shop_owner__last_name',
                 'warehouse__shop_owner__phone_number', 'zone__id', 'zone__warehouse__id', 'zone__warehouse__status',
                 'zone__warehouse__shop_name', 'zone__warehouse__shop_type',
                 'zone__warehouse__shop_type__shop_type', 'zone__warehouse__shop_type__shop_sub_type',
                 'zone__warehouse__shop_type__shop_sub_type__retailer_type_name', 'zone__warehouse__shop_owner',
                 'zone__warehouse__shop_owner__first_name', 'zone__warehouse__shop_owner__last_name',
                 'zone__warehouse__shop_owner__phone_number', 'zone__supervisor__id', 'zone__supervisor__first_name',
                 'zone__supervisor__last_name', 'zone__supervisor__phone_number', 'zone__coordinator__id',
                 'zone__coordinator__first_name', 'zone__coordinator__last_name', 'zone__coordinator__phone_number',
                 'product__id', 'product__name', 'created_at', 'updated_at', )
        for row in queryset:
            writer.writerow([row.warehouse.id, row.warehouse, row.product.id, row.product.name, row.zone.id,
                             (str(row.zone.supervisor.phone_number) + " - " + str(row.zone.supervisor.first_name)),
                             (str(row.zone.coordinator.phone_number) + " - " + str(row.zone.coordinator.first_name))])
        return response


class WarehouseAssortmentUploadSerializer(serializers.ModelSerializer):
    warehouse_id = serializers.IntegerField(required=True)
    file = serializers.FileField(
        label='Upload Warehouse Assortment', required=True, write_only=True)

    def __init__(self, *args, **kwargs):
        super(WarehouseAssortmentUploadSerializer, self).__init__(*args, **kwargs)  # call the super()
        self.fields['warehouse_id'].error_messages['required'] = 'Please select a Warehouse.'

    class Meta:
        model = WarehouseAssortment
        fields = ('warehouse_id', 'file',)

    def validate(self, data):
        if not Shop.objects.filter(id=data['warehouse_id']).exists():
            raise serializers.ValidationError(_('Please select a valid warehouse.'))
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError(
                _('Sorry! Only csv file accepted.'))
        warehouse = Shop.objects.filter(id=data['warehouse_id']).last()
        csv_file_data = csv.reader(codecs.iterdecode(
            data['file'], 'utf-8', errors='ignore'))
        # Checking, whether csv file is empty or not!
        if csv_file_data:
            read_warehouse_assortment_file(warehouse, csv_file_data, "warehouse_assortment")
        else:
            raise serializers.ValidationError(
                "CSV File cannot be empty.Please add some data to upload it!")

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            WarehouseAssortmentCommonFunction.create_warehouse_assortment(validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(
                e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return validated_data

