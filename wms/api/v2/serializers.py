import codecs
import copy
import csv
import re
from itertools import chain

from django.db import transaction, models
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum, F, Subquery, OuterRef, Count, Q
from django.db.models.functions import Cast
from django.db import transaction
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


from barCodeGenerator import merged_barcode_gen
from gram_to_brand.models import GRNOrder
from products.models import Product, ParentProduct, ProductImage, Repackaging
from retailer_to_sp.models import PickerDashboard, Order, OrderedProduct
from shops.models import Shop, ShopUserMapping

from wms.common_functions import ZoneCommonFunction, WarehouseAssortmentCommonFunction, PutawayCommonFunctions, \
    CommonBinInventoryFunctions, CommonWarehouseInventoryFunctions, get_sku_from_batch, post_picking_order_update
from global_config.views import get_config
from wms.models import In, Out, InventoryType, Zone, WarehouseAssortment, Bin, BIN_TYPE_CHOICES, \
    ZonePutawayUserAssignmentMapping, Putaway, PutawayBinInventory, BinInventory, InventoryState, \
    ZonePickerUserAssignmentMapping,  QCArea
from wms.common_validators import get_validate_putaway_users, read_warehouse_assortment_file, get_validate_picker_users

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
            if i + 1 in in_type_ids:
                ins_count_list.append(in_type_ids[i + 1])
            else:
                ins_count_list.append('0')
            if i + 1 in out_type_ids:
                outs_count_list.append(out_type_ids[i + 1])
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


class GRNOrderSerializers(serializers.ModelSerializer):
    class Meta:
        model = GRNOrder
        fields = ('id', 'grn_id', 'created_at',)


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


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image_name', 'image', 'status',)


class ChildProductSerializer(serializers.ModelSerializer):
    """ Serializer for Product"""
    product_pro_image = ProductImageSerializer(read_only=True, many=True)

    class Meta:
        model = Product
        fields = ('product_sku', 'product_name', 'product_mrp', 'product_pro_image')


class ZoneCrudSerializers(serializers.ModelSerializer):
    warehouse = WarehouseSerializer(read_only=True)
    supervisor = UserSerializers(read_only=True)
    coordinator = UserSerializers(read_only=True)
    putaway_users = UserSerializers(read_only=True, many=True)
    picker_users = UserSerializers(read_only=True, many=True)

    class Meta:
        model = Zone
        fields = ('id', 'zone_number', 'name', 'warehouse', 'supervisor', 'coordinator', 'putaway_users', 'picker_users',
                  'created_at', 'updated_at')

    def validate(self, data):

        if 'name' in self.initial_data and self.initial_data['name']:
            data['name'] = self.initial_data['name']
        else:
            raise serializers.ValidationError("'name' | This is mandatory")

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

        if self.initial_data['warehouse'] and self.initial_data['supervisor'] and self.initial_data['coordinator']:
            if Zone.objects.filter(warehouse=self.initial_data['warehouse'], supervisor=self.initial_data['supervisor'],
                                   coordinator=self.initial_data['coordinator']).exists():
                raise serializers.ValidationError(
                    "Zone already exist for selected 'warehouse', 'supervisor' and 'coordinator'")

        if 'putaway_users' in self.initial_data and self.initial_data['putaway_users']:
            if len(self.initial_data['putaway_users']) > get_config('MAX_PUTAWAY_USERS_PER_ZONE'):
                raise serializers.ValidationError(
                    "Maximum " + str(get_config('MAX_PUTAWAY_USERS_PER_ZONE')) + " putaway users are allowed.")
            putaway_users = get_validate_putaway_users(
                self.initial_data['putaway_users'], self.initial_data['warehouse'])
            if 'error' in putaway_users:
                raise serializers.ValidationError((putaway_users["error"]))
            data['putaway_users'] = putaway_users['putaway_users']
        else:
            raise serializers.ValidationError("'putaway_users' | This is mandatory")

        if 'picker_users' in self.initial_data and self.initial_data['picker_users']:
            if len(self.initial_data['picker_users']) > get_config('MAX_PICKER_USERS_PER_ZONE'):
                raise serializers.ValidationError(
                    "Maximum " + str(get_config('MAX_PICKER_USERS_PER_ZONE')) + " putaway users are allowed.")
            picker_users = get_validate_picker_users(self.initial_data['picker_users'], self.initial_data['warehouse'])
            if 'error' in picker_users:
                raise serializers.ValidationError((picker_users["error"]))
            data['picker_users'] = picker_users['picker_users']
        else:
            raise serializers.ValidationError("'picker_users' | This is mandatory")

        if 'id' in self.initial_data and self.initial_data['id']:
            if not Zone.objects.filter(id=self.initial_data['id'], warehouse=warehouse).exists():
                raise serializers.ValidationError("Warehouse updation is not allowed.")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new Zone with Putaway Users"""
        putaway_users = validated_data.pop('putaway_users', None)
        picker_users = validated_data.pop('picker_users', None)

        try:
            zone_instance = Zone.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        ZoneCommonFunction.update_putaway_users(zone_instance, putaway_users)
        ZoneCommonFunction.update_picker_users(zone_instance, picker_users)
        return zone_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update Zone with Putaway Users"""
        putaway_users = validated_data.pop('putaway_users', None)
        picker_users = validated_data.pop('picker_users', None)

        try:
            zone_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        ZoneCommonFunction.update_putaway_users(zone_instance, putaway_users)
        ZoneCommonFunction.update_picker_users(zone_instance, picker_users)
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
    picker_users = UserSerializers(read_only=True, many=True)

    class Meta:
        model = Zone
        fields = ('id', 'zone_number', 'name', 'warehouse', 'supervisor', 'coordinator', 'putaway_users',
                  'picker_users')

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
                 'product__parent_id', 'product__name', 'created_at', 'updated_at', )
        for row in queryset:
            writer.writerow([row.warehouse.id, row.warehouse, row.product.parent_id, row.product.name, row.zone.id,
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


class BinCrudSerializers(serializers.ModelSerializer):
    warehouse = WarehouseSerializer(read_only=True)
    zone = ZoneSerializer(read_only=True)

    class Meta:
        model = Bin
        fields = ('id', 'warehouse', 'bin_id', 'bin_type', 'is_active', 'bin_barcode_txt', 'bin_barcode', 'zone',
                  'created_at', 'modified_at')

    def bin_id_validation(self, bin_id, bin_type):
        if not bin_id:
            return False, "Bin ID must not be empty."

        if not len(bin_id) == 16:
            return False, 'Bin Id min and max char limit is 16.Example:-B2BZ01SR001-0001'

        if not bin_id[0:3] in ['B2B', 'B2C']:
            return False, 'First three letter should be start with either B2B and B2C.Example:-B2BZ01SR001-0001'

        if not bin_id[3] in ['Z']:
            return False, 'Zone should be start with char Z.Example:-B2BZ01SR001-0001'

        if not bool(re.match('^[0-9]+$', bin_id[4:6]) and not bin_id[4:6] == '00'):
            return False, 'Zone number should be start in between 01 to 99.Example:-B2BZ01SR001-0001'

        if not bin_id[6:8] in ['SR', 'PA', 'HD']:
            return False, 'Rack type should be start with either SR, PA and HD only.Example:-B2BZ01SR001-0001'

        else:
            if not bin_id[6:8] == bin_type:
                return False, 'Type of Rack and Bin type should be same.'

        if not bool(re.match('^[0-9]+$', bin_id[8:11]) and not bin_id[8:11] == '000'):
            return False, 'Rack number should be start in between 000 to 999.Example:- B2BZ01SR001-0001'

        if not bin_id[11] in ['-']:
            return False, 'Only - allowed in between Rack number and Bin Number.Example:-B2BZ01SR001-0001'

        if not bool(re.match('^[0-9]+$', bin_id[12:16]) and not bin_id[12:16] == '0000'):
            return False, 'Bin number should be start in between 0000 to 9999. Example:-B2BZ01SR001-0001'

        return True, "Bin Id validation successfully passed."

    def validate(self, data):

        if 'warehouse' in self.initial_data and self.initial_data['warehouse']:
            try:
                warehouse = Shop.objects.get(id=self.initial_data['warehouse'], shop_type__shop_type='sp')
                data['warehouse'] = warehouse
            except:
                raise serializers.ValidationError("Invalid warehouse")
        else:
            raise serializers.ValidationError("'warehouse' | This is mandatory")

        if 'bin_type' in self.initial_data and self.initial_data['bin_type']:
            bin_type = self.initial_data['bin_type']
            if not (any(bin_type in i for i in BIN_TYPE_CHOICES)):
                raise serializers.ValidationError('Invalid bin_type')
            data['bin_type'] = bin_type
        else:
            raise serializers.ValidationError("'bin_type' | This is mandatory")

        if 'is_active' in self.initial_data and self.initial_data['is_active']:
            is_active = self.initial_data['is_active']
            if is_active not in [True, False]:
                raise serializers.ValidationError('Invalid is_active')
            data['is_active'] = is_active
        else:
            raise serializers.ValidationError("'is_active' | This is mandatory")

        if 'bin_id' in self.initial_data and self.initial_data['bin_id']:
            try:
                bin_id = self.initial_data['bin_id']
                bin_validation, message = self.bin_id_validation(bin_id, bin_type)
                if not bin_validation:
                    raise serializers.ValidationError(message)
            except:
                raise serializers.ValidationError("Invalid bin_id")
            data['bin_id'] = bin_id
        else:
            raise serializers.ValidationError("'bin_id' | This is mandatory")

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

        if Bin.objects.filter(warehouse=warehouse, bin_id=bin_id, zone=zone).exists():
            raise serializers.ValidationError(
                "Bin already exist for selected 'warehouse', 'bin' and 'zone'")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new Bin"""

        try:
            bin_instance = Bin.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return bin_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update WarehouseAssortment"""

        try:
            bin_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return bin_instance


class BinExportAsCSVSerializers(serializers.ModelSerializer):
    bin_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = Bin
        fields = ('bin_id_list',)

    def validate(self, data):

        if len(data.get('bin_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one bin id must be selected '))

        for c_id in data.get('bin_id_list'):
            try:
                Bin.objects.get(id=c_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'bin not found for id {c_id}')
        return data

    def create(self, validated_data):
        meta = Bin._meta
        field_names = ["Warehouse ID", "Warehouse", "Zone ID", "Zone Supervisor (Number - Name)",
                       "Zone Coordinator (Number - Name)", "Bin ID", "Bin Type", "Bin Barcode Text", "Bin Barcode Url",
                       "Active", "Created Datetime", "Updated Datetime"]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)

        queryset = Bin.objects.filter(id__in=validated_data['bin_id_list']). \
            select_related('warehouse', 'warehouse__shop_owner', 'warehouse__shop_type',
                           'warehouse__shop_type__shop_sub_type',
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
                 'bin_id', 'bin_type', 'is_active', 'bin_barcode_txt', 'bin_barcode', 'created_at', 'modified_at', ). \
            order_by('-id')
        for row in queryset:
            writer.writerow([row.warehouse.id, row.warehouse, row.zone.id if row.zone else None, (str(
                row.zone.supervisor.phone_number) + " - " + str(row.zone.supervisor.first_name)) if row.zone else None,
                             (str(row.zone.coordinator.phone_number) + " - " + str(
                                 row.zone.coordinator.first_name)) if row.zone else None,
                             row.bin_id, row.bin_type, row.bin_barcode_txt, row.bin_barcode.url, row.is_active,
                             row.created_at.strftime('%b %d,%Y %H:%M:%S'),
                             row.modified_at.strftime('%b %d,%Y %H:%M:%S')])
        return response


class BinExportBarcodeSerializers(serializers.ModelSerializer):
    bin_id_list = serializers.ListField(
        child=serializers.IntegerField(required=True)
    )

    class Meta:
        model = Bin
        fields = ('bin_id_list',)

    def validate(self, data):

        if len(data.get('bin_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one bin id must be selected '))

        for c_id in data.get('bin_id_list'):
            try:
                Bin.objects.get(id=c_id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'bin not found for id {c_id}')
        return data

    def create(self, validated_data):
        bin_id_list = {}
        for obj in validated_data['bin_id_list']:
            bin_obj = Bin.objects.get(id=obj)
            bin_barcode_txt = bin_obj.bin_barcode_txt
            if bin_barcode_txt is None:
                bin_barcode_txt = '1' + str(getattr(obj, 'id')).zfill(11)
            bin_id_list[bin_barcode_txt] = {"qty": 1, "data": {"Bin": bin_obj.bin_id}}
        return merged_barcode_gen(bin_id_list)


class ZonePutawayAssignmentsCrudSerializers(serializers.ModelSerializer):
    zone = ZoneSerializer(read_only=True)
    user = UserSerializers(read_only=True)

    class Meta:
        model = ZonePutawayUserAssignmentMapping
        fields = ('id', 'last_assigned_at', 'zone', 'user',)


class ZonePickerAssignmentsCrudSerializers(serializers.ModelSerializer):
    zone = ZoneSerializer(read_only=True)
    user = UserSerializers(read_only=True)

    class Meta:
        model = ZonePickerUserAssignmentMapping
        fields = ('id', 'last_assigned_at', 'zone', 'user',)


class PutawayModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Putaway
        fields = "__all__"


class InventoryTypeSerializers(serializers.ModelSerializer):

    class Meta:
        model = InventoryType
        fields = ('id', 'inventory_type',)


class StatusSerializer(serializers.ChoiceField):

    def to_representation(self, obj):
        if obj == '' and self.allow_blank:
            return obj
        return {'id': obj, 'status': self._choices[obj]}


class CancelPutawayCrudSerializers(serializers.ModelSerializer):
    warehouse = WarehouseSerializer(read_only=True)
    putaway_user = UserSerializers(read_only=True)
    inventory_type = InventoryTypeSerializers(read_only=True)
    status = StatusSerializer(choices=Putaway.PUTAWAY_STATUS_CHOICE, required=True)

    class Meta:
        model = Putaway
        fields = ('id', 'warehouse', 'putaway_user', 'putaway_type', 'putaway_type_id', 'sku', 'batch_id',
                  'inventory_type', 'quantity', 'putaway_quantity', 'status', 'created_at', 'modified_at',)

    @transaction.atomic
    def update(self, instance, validated_data):
        """Cancel Putaway"""
        try:
            validated_data["status"] = Putaway.PUTAWAY_STATUS_CHOICE.CANCELLED
            validated_data["putaway_user"] = None
            putaway_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return putaway_instance


class PutawaySerializers(serializers.ModelSerializer):
    """ Serializer for Putaway Model"""
    warehouse = WarehouseSerializer(read_only=True)
    putaway_user = UserSerializers(read_only=True)
    sku = ChildProductSerializer(read_only=True)
    inventory_type = InventoryTypeSerializers(read_only=True)
    status = StatusSerializer(choices=Putaway.PUTAWAY_STATUS_CHOICE, required=True)
    token_id = serializers.CharField(required=False)
    zone_id = serializers.CharField(required=False)

    class Meta:
        model = Putaway
        fields = ('id', 'token_id', 'zone_id', 'putaway_user', 'status', 'putaway_type', 'putaway_type_id', 'warehouse',
                  'sku', 'batch_id', 'inventory_type', 'quantity', 'putaway_quantity', 'created_at', 'modified_at',)


class UpdateZoneForCancelledPutawaySerializers(serializers.Serializer):
    putaway = PutawaySerializers(read_only=True)
    warehouse = WarehouseSerializer(read_only=True)
    product = ProductSerializer(read_only=True)
    zone = ZoneSerializer(read_only=True)

    def validate(self, data):

        if 'putaway' in self.initial_data and self.initial_data['putaway']:
            try:
                putaway = Putaway.objects.get(
                    id=self.initial_data['putaway'], status=Putaway.PUTAWAY_STATUS_CHOICE.CANCELLED)
                data['putaway'] = putaway
            except:
                raise serializers.ValidationError("Invalid putaway")
        else:
            raise serializers.ValidationError("'putaway' | This is mandatory")

        if 'warehouse' in self.initial_data and self.initial_data['warehouse']:
            try:
                warehouse = Shop.objects.get(id=self.initial_data['warehouse'], shop_type__shop_type='sp')
                data['warehouse'] = warehouse
            except:
                raise serializers.ValidationError("Invalid warehouse")
        else:
            raise serializers.ValidationError("'warehouse' | This is mandatory")

        if 'sku' in self.initial_data and self.initial_data['sku']:
            try:
                sku = Product.objects.get(product_sku=self.initial_data['sku'])
            except:
                raise serializers.ValidationError("Invalid sku")
            data['sku'] = sku
            data['product'] = sku.parent_product
        else:
            raise serializers.ValidationError("'sku' | This is mandatory")

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

        if WarehouseAssortment.objects.filter(warehouse=warehouse, product=sku.parent_product, zone=zone).exists():
            raise serializers.ValidationError(
                "Warehouse assortment already exist for selected 'warehouse', 'product' and 'zone'")

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        @param instance: WarehouseAssortment model instance
        @param validated_data: dict object
        @return: PutawaySerializers serializer object

        Reason: Update zone in WarehouseAssortment for selected warehouse and product and update status to NEW
                for mapped cancelled putaways
        """
        putaway = validated_data.pop('putaway')
        sku = validated_data.pop('sku')
        zone = validated_data.pop('zone')
        try:
            instance.zone = zone
            instance.save()
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return PutawaySerializers(self.update_all_existing_cancelled_putaways(instance.warehouse, sku), many=True)


    def update_all_existing_cancelled_putaways(self, warehouse, product):
        """
        @param warehouse: Shop model instance
        @param product: Product model instance
        @return: Putaway model instances

        Reason: update status to NEW for filtered putaways
        """
        putaway_instances = Putaway.objects.filter(
            warehouse=warehouse, sku=product.product_sku, status=Putaway.PUTAWAY_STATUS_CHOICE.CANCELLED)
        resp = copy.copy(putaway_instances)
        if putaway_instances.exists():
            putaway_instances.update(status=Putaway.PUTAWAY_STATUS_CHOICE.NEW)
        return resp


class GroupedByGRNPutawaysSerializers(serializers.Serializer):
    token_id = serializers.CharField()
    zone = serializers.IntegerField()
    total_items = serializers.IntegerField()
    putaway_user = serializers.SerializerMethodField()
    status = serializers.CharField()
    putaway_type = serializers.CharField()
    created_at__date = serializers.DateField()

    def get_putaway_user(self, obj):
        if obj['putaway_user']:
            return UserSerializers(User.objects.get(id=obj['putaway_user']), read_only=True).data
        return None


class StatusCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    status = serializers.CharField()


class POSummarySerializers(serializers.Serializer):
    po_no = serializers.CharField()
    putaway_type = serializers.CharField()
    status_count = serializers.SerializerMethodField()
    total_items = serializers.IntegerField()

    def get_status_count(self, obj):
        if obj['po_no']:
            status_data = Putaway.objects.filter(putaway_type='GRN'). \
                annotate(putaway_type_id_key=Cast('putaway_type_id', models.IntegerField()),
                         po_no=Subquery(GRNOrder.objects.filter(grn_id=Subquery(In.objects.filter(
                             id=OuterRef(OuterRef('putaway_type_id_key'))).order_by(
                             '-in_type_id').values('in_type_id')[:1])).order_by('-order__order_no').values(
                             'order__order_no')[:1])
                         ). \
                exclude(status__isnull=True). \
                filter(po_no=obj['po_no']). \
                values('status').annotate(count=Count('status')).order_by('-status')
            return StatusCountSerializer(status_data, read_only=True, many=True).data
        return []

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        status_list = []
        pending = 0
        completed = 0
        cancelled = 0
        if representation['status_count']:
            for obj in representation['status_count']:
                if obj['status'] in [Putaway.COMPLETED]:
                    completed += obj['count']
                elif obj['status'] in [Putaway.NEW, Putaway.ASSIGNED, Putaway.INITIATED]:
                    pending += obj['count']
                elif obj['status'] in [Putaway.CANCELLED]:
                    cancelled += obj['count']
        status_list.append(StatusCountSerializer({"count": completed, "status": "COMPLETED"}, read_only=True).data)
        status_list.append(StatusCountSerializer({"count": pending, "status": "PENDING"}, read_only=True).data)
        status_list.append(StatusCountSerializer({"count": cancelled, "status": "CANCELLED"}, read_only=True).data)
        representation['status_count'] = status_list
        return representation


class PutawaySummarySerializers(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()


class SummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()


class ZonewiseSummarySerializers(serializers.Serializer):
    status_count = SummarySerializer(read_only=True)
    zone = serializers.SerializerMethodField()

    def get_zone(self, obj):
        if obj['zone']:
            return ZoneSerializer(Zone.objects.get(id=obj['zone']), read_only=True).data
        return None


class PutawayItemsCrudSerializer(serializers.ModelSerializer):
    """ Serializer for Putaway CRUD API"""
    warehouse = WarehouseSerializer(read_only=True)
    sku = ChildProductSerializer(read_only=True)
    quantity = serializers.IntegerField(required=False)
    putaway_quantity = serializers.IntegerField(required=False)
    batch_id = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    suggested_bins = serializers.SerializerMethodField()
    putaway_done = serializers.SerializerMethodField()

    def get_suggested_bins(self, obj):
        """ Returns the suggested bins for a pending Putaway"""
        if obj.status in ['ASSIGNED', 'INITIATED']:
            return PutawayCommonFunctions.get_suggested_bins_for_putaway(obj.warehouse, obj.sku, obj.batch_id,
                                                                         obj.inventory_type)

    def get_putaway_done(self, obj):
        """ Returns Putaway bins along with respective quantity"""
        if obj.status in ['INITIATED', 'COMPLETED']:
            return PutawayBinInventory.objects.filter(putaway=obj).values('bin__bin__bin_id')\
                .annotate(putaway_bin=F('bin__bin__bin_id'), putaway_quantity=Sum('putaway_quantity'))\
                .values('putaway_bin', 'putaway_quantity')

    class Meta:
        model = Putaway
        fields = ('id', 'warehouse', 'sku', 'batch_id', 'putaway_type', 'quantity', 'putaway_quantity', 'status',
                  'suggested_bins', 'putaway_done', 'created_at', 'modified_at')

    def validate(self, data):
        """Validates the Putaway requests"""

        if 'id' in self.initial_data and self.initial_data['id']:
            if 'status' in self.initial_data and self.initial_data['status']:
                try:
                    putaway = Putaway.objects.get(id=self.initial_data['id'])
                    putaway_status = putaway.status
                    putaway_quantity = putaway.putaway_quantity
                    quantity = putaway.quantity
                except Exception as e:
                    raise serializers.ValidationError("Invalid Putaway")
                status = self.initial_data['status']
                if status == putaway_status:
                    raise serializers.ValidationError(f'Putaway already {status}')
                elif status in [Putaway.PUTAWAY_STATUS_CHOICE.NEW, Putaway.PUTAWAY_STATUS_CHOICE.ASSIGNED,
                                Putaway.PUTAWAY_STATUS_CHOICE.CANCELLED] \
                        or (status == Putaway.PUTAWAY_STATUS_CHOICE.INITIATED
                            and putaway_status != Putaway.PUTAWAY_STATUS_CHOICE.ASSIGNED)\
                        or (status == Putaway.PUTAWAY_STATUS_CHOICE.COMPLETED
                            and putaway_status != Putaway.PUTAWAY_STATUS_CHOICE.INITIATED):
                    raise serializers.ValidationError(f'Invalid status | {putaway_status}-->{status} not allowed')
                # elif status == Putaway.PUTAWAY_STATUS_CHOICE.COMPLETED \
                #     and putaway_status == Putaway.PUTAWAY_STATUS_CHOICE.INITIATED \
                #         and putaway_quantity != quantity:
                #     raise serializers.ValidationError(f'Putaway cannot be completed. '
                #                                       f'Remaining putaway_quantity-{quantity-putaway_quantity}')
                data['status'] = status
            else:
                raise serializers.ValidationError("Only status update is allowed")
        else:
            raise serializers.ValidationError("Putaway creation is not allowed.")

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            putaway_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return putaway_instance


class ZoneFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ('id', '__str__')

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['name'] = response['__str__']
        response.pop('__str__')
        return response


class PostLoginUserSerializers(serializers.ModelSerializer):

    is_warehouse_manager = serializers.SerializerMethodField()
    is_zone_supervisor = serializers.SerializerMethodField()
    is_zone_coordinator = serializers.SerializerMethodField()
    is_putaway_user = serializers.SerializerMethodField()
    is_picker = serializers.SerializerMethodField()
    user_warehouse = serializers.SerializerMethodField()

    def get_is_warehouse_manager(self, obj):
        """Check if user has warehouse manager permission"""
        if obj.has_perm('wms.can_have_zone_warehouse_permission'):
            return True
        return False

    def get_is_zone_supervisor(self, obj):
        """Check if user has Zone Supervisor permission"""
        if obj.has_perm('wms.can_have_zone_supervisor_permission'):
            return True
        return False

    def get_is_zone_coordinator(self, obj):
        """Check if user has Zone Coordinator permission"""
        if obj.has_perm('wms.can_have_zone_coordinator_permission'):
            return True
        return False

    def get_is_putaway_user(self, obj):
        """Check if user is Putaway User"""
        if obj.groups.filter(name='Putaway').exists():
            return True
        return False

    def get_is_picker(self, obj):
        """Check if user is Picker"""
        if obj.groups.filter(name='Picker Boy').exists():
            return True
        return False


    def get_user_warehouse(self, obj):
        """Get user's associated warehouse"""
        return WarehouseSerializer(obj.shop_employee.last().shop).data if obj.shop_employee.exists() else None

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'phone_number', 'is_warehouse_manager', 'is_zone_supervisor',
                  'is_zone_coordinator', 'is_putaway_user', 'user_warehouse', 'is_picker')


class BinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bin
        fields = ('id', 'bin_id', 'warehouse_id')


class InventoryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryType
        fields = ('id', 'inventory_type')


class BinInventorySerializer(serializers.ModelSerializer):
    warehouse = WarehouseSerializer()
    bin = BinSerializer()
    inventory_type = InventoryTypeSerializer()
    sku = ChildProductSerializer()
    bin_quantity = serializers.SerializerMethodField()

    def get_bin_quantity(self, obj):
        return obj.quantity+obj.to_be_picked_qty

    class Meta:
        model = BinInventory
        fields = ('warehouse', 'bin', 'sku', 'batch_id', 'inventory_type', 'bin_quantity')

class BinShiftPostSerializer(serializers.ModelSerializer):
    s_bin = serializers.IntegerField()
    t_bin = serializers.IntegerField()
    batch_id = serializers.CharField()
    qty = serializers.IntegerField()
    inventory_type = serializers.IntegerField()

    class Meta:
        model = BinInventory
        fields = ('s_bin', 't_bin', 'batch_id', 'qty', 'inventory_type')



    def validate(self, data):
        data['warehouse'] = self.initial_data['warehouse']
        try:
            s_bin = Bin.objects.get(id=self.initial_data['s_bin'])
        except Exception as e:
            raise serializers.ValidationError("Invalid source Bin")
        data['s_bin'] = s_bin

        try:
            t_bin = Bin.objects.get(id=self.initial_data['t_bin'])
        except Exception as e:
            raise serializers.ValidationError("Invalid target Bin")
        if s_bin == t_bin:
            raise serializers.ValidationError("Source and target bins are same.")
        data['t_bin'] = t_bin
        data['batch_id'] = self.initial_data['batch_id']


        if self.initial_data['qty'] <= 0:
            raise serializers.ValidationError(f"Invalid Quantity {self.initial_data['qty']}")
        data['qty'] = self.initial_data['qty']

        try:
            inventory_type = InventoryType.objects.get(id=self.initial_data['inventory_type'])
        except Exception as e:
            raise serializers.ValidationError("Invalid Inventory Type")
        data['inventory_type'] = inventory_type

        bin_inv = BinInventory.objects.filter(bin=s_bin, batch_id=self.initial_data['batch_id'],
                                              inventory_type=inventory_type).last()
        if bin_inv:
            if bin_inv.quantity+bin_inv.to_be_picked_qty < self.initial_data['qty']:
                raise serializers.ValidationError(f"Invalid Quantity to move | "
                                                  f"Available Quantity {bin_inv.quantity+bin_inv.to_be_picked_qty}")
        else:
            raise serializers.ValidationError("Invalid s_bin or batch_id")
        sku = get_sku_from_batch(self.initial_data['batch_id'])
        if BinInventory.objects.filter(~Q(batch_id=self.initial_data['batch_id']),
                                    Q(quantity__gt=0)|Q(to_be_picked_qty__gt=0), bin=t_bin, sku=sku).exists():
            raise serializers.ValidationError("Invalid Movement | "
                                              "Target bin already has same product with different batch ID")
        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            CommonBinInventoryFunctions.product_shift_across_bins(validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return validated_data


class PutawayActionSerializer(PutawayItemsCrudSerializer):
    """Serializer for PerformPutawayView"""

    def validate(self, data):
        if 'id' in self.initial_data and self.initial_data['id']:
            try:
                putaway_instance = Putaway.objects.get(id=self.initial_data['id'])
            except Exception as e:
                raise serializers.ValidationError("Invalid Putaway")
            data['putaway'] = putaway_instance
            if 'batch' in self.initial_data and self.initial_data['batch']:
                if self.initial_data['batch'] != putaway_instance.batch_id:
                    raise serializers.ValidationError('Invalid Batch')
                batch = self.initial_data['batch']
                data['batch'] = batch
            else:
                raise serializers.ValidationError("'batch' | This is mandatory")
            if 'putaway_bin_data' in self.initial_data and self.initial_data['putaway_bin_data']:
                putaway_quantity = putaway_instance.putaway_quantity
                zone = WarehouseAssortmentCommonFunction.get_product_zone(putaway_instance.warehouse, putaway_instance.sku)
                for item in self.initial_data['putaway_bin_data']:

                    bin = Bin.objects.filter(bin_id=item['bin'], warehouse=putaway_instance.warehouse,
                                             zone=zone, is_active=True).last()
                    if BinInventory.objects.filter(~Q(batch_id=putaway_instance.batch_id), warehouse=putaway_instance.warehouse,
                                                bin=bin, sku=putaway_instance.sku, quantity__gt=0).exists():
                        raise serializers.ValidationError(f"Invalid bin {item['bin']}| This product with different expiry date "
                                                          f"already present in bin")
                    if bin:
                        item['bin'] = bin
                    else:
                        raise serializers.ValidationError(f"Invalid Bin {item['bin']}")

                    if PutawayBinInventory.REMARK_CHOICE.__contains__(item['remark']):
                        item['remark'] = PutawayBinInventory.REMARK_CHOICE.__getitem__(item['remark'])
                    else:
                        raise serializers.ValidationError('Invalid reason')
                    
                    if item['qty'] <= 0 or putaway_quantity+item['qty'] > putaway_instance.quantity:
                        raise serializers.ValidationError(f'Invalid quantity')
                    if putaway_quantity+item['qty']<putaway_instance.quantity and (not item['remark'] or item['remark'] == ''):
                        raise serializers.ValidationError(f'Reason is required for partial putaway')
                    putaway_quantity += item['qty']
                data['putaway_bin_data'] = self.initial_data['putaway_bin_data']
            else:
                raise serializers.ValidationError("'putaway_bin_data' | This is mandatory")
        else:
            raise serializers.ValidationError("'putaway' | This is mandatory")
        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        @param instance: Putaway model instance
        @param validated_data: dict object
        @return: PutawayActionSerializer serializer object
        """
        try:
            putaway_instance = validated_data.pop('putaway')
            putaway_bin_data = validated_data.pop('putaway_bin_data')
            putaway_instance = self.post_putaway_data_update(putaway_instance, putaway_bin_data)
            validated_data['putaway_quantity'] = putaway_instance.putaway_quantity
            if putaway_instance.quantity == putaway_instance.putaway_quantity:
                validated_data['status'] = Putaway.PUTAWAY_STATUS_CHOICE.COMPLETED
            putaway_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return putaway_instance

    def post_putaway_data_update(self, putaway_instance, putaway_bin_data):
        """
        Updates following tables post putaway quantity update:
        1. Make entries in PutawayBinInventory
        2. Update BinInventory and BinInternalInventoryChange
        3. Update WarehouseInventory and WarehouseInternalInventoryChange
        """

        transaction_type = 'put_away_type'
        transaction_id = putaway_instance.id
        warehouse = putaway_instance.warehouse
        sku = putaway_instance.sku
        zone = WarehouseAssortmentCommonFunction.get_product_zone(warehouse, sku)

        initial_inv_type = InventoryType.objects.filter(inventory_type='new').last()
        final_inv_type = putaway_instance.inventory_type
        state_available = InventoryState.objects.filter(inventory_state='total_available').last()
        putaway_quantity = putaway_instance.putaway_quantity
        for item in putaway_bin_data:
            putaway_quantity += item['qty']
            # Get Bin Object
            bin = Bin.objects.filter(bin_id=item['bin'], warehouse=warehouse, zone=zone).last()
            weight = sku.weight_value * item['qty'] \
                            if sku.repackaging_type == 'packing_material' else 0

            # Update BinInventory
            bin_inventory_obj = CommonBinInventoryFunctions.update_bin_inventory_with_transaction_log(
                warehouse, bin, sku, putaway_instance.batch_id, initial_inv_type,
                final_inv_type, item['qty'], True, transaction_type, transaction_id, weight)

            # Create PutawayBinInventory
            PutawayBinInventory.objects.create(warehouse=warehouse, putaway=putaway_instance,
                                               bin=bin_inventory_obj, putaway_quantity=item['qty'], putaway_status=True,
                                               sku=sku, batch_id=putaway_instance.batch_id,
                                               putaway_type=putaway_instance.putaway_type, remark=item['remark'])

            # Update WarehouseInventory
            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                warehouse, sku, final_inv_type, state_available, item['qty'], transaction_type, transaction_id,
                                                        True,  weight)
        putaway_instance.putaway_quantity = putaway_quantity
        return putaway_instance


class QCAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = QCArea
        fields = ('id', 'area_id', 'area_type')


class PicklistSerializer(serializers.ModelSerializer):

    picker_status = serializers.SerializerMethodField('picker_status_dt')
    order_create_date = serializers.SerializerMethodField()
    delivery_location = serializers.SerializerMethodField('m_delivery_location')
    picking_assigned_time = serializers.SerializerMethodField('get_assigned_time')
    picking_completed_time = serializers.SerializerMethodField('get_completed_time')
    order_no = serializers.SerializerMethodField()
    qc_area = serializers.SerializerMethodField()
    zone = ZoneSerializer(read_only=True)
    picker_boy = UserSerializers(read_only=True)


    def picker_status_dt(self, obj):
        return str(obj.picking_status).lower()

    def get_order_create_date(self, obj):
        return obj.order.created_at.strftime("%d-%m-%Y")

    def m_delivery_location(self, obj):
        return obj.order.shipping_address.city.city_name

    def get_assigned_time(self, obj):
        try:
            return obj.picker_assigned_date.strftime('%b %d, %H:%M')
        except:
            return None

    def get_completed_time(self, obj):
        return obj.completed_at.strftime('%b %d, %H:%M') if obj.completed_at else None

    def get_order_no(self, obj):
        return obj.order.order_no

    def get_qc_area(self, obj):
        qc_area = obj.qc_area.area_id if obj.qc_area else None
        if not qc_area:
            qc_area = obj.order.picker_order.filter(qc_area__isnull=False).last().qc_area.area_id \
                if obj.order.picker_order.filter(qc_area__isnull=False).exists() else None
        return qc_area

    class Meta:
        model = PickerDashboard
        fields = ('id', 'order_no', 'picker_status', 'order_create_date', 'delivery_location', 'picking_assigned_time',
                  'picking_completed_time', 'moved_to_qc_at', 'qc_area', 'zone', 'picker_boy')


class AllocateQCAreaSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PickerDashboard
        fields = ('id', 'picking_status', 'qc_area_id')

    def validate(self, data):
        if 'id' in self.initial_data and self.initial_data['id']:
            try:
                picker_dashboard_instance = PickerDashboard.objects.get(id=self.initial_data['id'])
            except Exception as e:
                raise serializers.ValidationError("Invalid Picking Entry")
            if picker_dashboard_instance.picking_status not in ['picking_complete', 'moved_to_qc']:
                raise serializers.ValidationError('This picking is not yet completed')

            data['picking_entry'] = picker_dashboard_instance

            if 'qc_area' in self.initial_data and self.initial_data['qc_area']:
                qc_area = QCArea.objects.filter(area_id=self.initial_data['qc_area'],
                                                warehouse_id=self.initial_data['warehouse']).last()
                if not qc_area:
                    raise serializers.ValidationError('Invalid QC Area')

                qc_area_alloted = PickerDashboard.objects.filter(qc_area__isnull=False,
                                                                 order=picker_dashboard_instance.order)\
                                                         .exclude(id=picker_dashboard_instance.id).last()
                if qc_area_alloted and qc_area_alloted.qc_area.area_id != self.initial_data['qc_area']:
                    raise serializers.ValidationError(f"Invalid QC Area| QcArea allotted for this order is"
                                                      f" {qc_area_alloted.qc_area}")
                elif self.initial_data['qc_area'] and PickerDashboard.objects.filter(
                        qc_area__warehouse__id=self.initial_data['warehouse'],
                        qc_area__area_id=self.initial_data['qc_area'],
                        order__order_status=Order.MOVED_TO_QC,
                        order__rt_order_order_product__isnull=True).exists():
                    raise serializers.ValidationError(f"Invalid QC Area| QcArea {self.initial_data['qc_area']} "
                                                      f"allotted for another order.")
                data['qc_area'] = qc_area
            else:
                raise serializers.ValidationError("'qc_area' | This is mandatory")
        else:
            raise serializers.ValidationError("'id' | This is mandatory")
        return data


    @transaction.atomic
    def update(self, instance, validated_data):
        """
        @param instance: PickerDashboard model instance
        @param validated_data: dict object
        @return: AllocateQCAreaSerializer serializer object
        """
        try:
            validated_data['picking_status'] = 'moved_to_qc'
            picker_dashboard_instance = super().update(instance, validated_data)
            post_picking_order_update(instance)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return picker_dashboard_instance


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('id', 'order_no', )


class RepackagingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repackaging
        fields = ('id', 'repackaging_no', 'source_picking_status', 'created_at',)


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderedProduct
        fields = ('id', 'invoice_number', 'no_of_crates', 'no_of_packets', 'no_of_sacks', 'no_of_crates_check',
                  'no_of_packets_check', 'no_of_sacks_check', )


class PickerDashboardSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    repackaging = RepackagingSerializer(read_only=True)
    shipment = ShipmentSerializer(read_only=True)
    picker_boy = UserSerializers(read_only=True)
    qc_area = QCAreaSerializer(read_only=True)
    zone = ZoneSerializer(read_only=True)

    class Meta:
        model = PickerDashboard
        fields = ('id', 'order', 'repackaging', 'shipment', 'picking_status', 'picklist_id', 'picker_boy',
                  'pick_list_pdf', 'picker_assigned_date', 'zone', 'qc_area', 'is_valid', 'refreshed_at', 'created_at',
                  'modified_at', 'completed_at', 'moved_to_qc_at', )

    def validate(self, data):
        """Validates the PickerDashboard requests"""

        if 'id' in self.initial_data and self.initial_data['id']:
            if 'picker_boy' in self.initial_data and self.initial_data['picker_boy']:
                try:
                    picker_dashboard_obj = PickerDashboard.objects.get(id=self.initial_data['id'])
                    existing_picker_boy = picker_dashboard_obj.picker_boy
                except Exception as e:
                    raise serializers.ValidationError("Invalid Putaway")
                try:
                    picker_boy = User.objects.get(id=self.initial_data['picker_boy'], groups__name='Picker Boy')
                except Exception:
                    raise serializers.ValidationError("Invalid picker boy | user not found / not a picker boy.")
                if picker_boy == existing_picker_boy:
                    raise serializers.ValidationError(f'Picker Boy {picker_boy} is already assigned.')
                elif picker_dashboard_obj.zone is None:
                    raise serializers.ValidationError(f'Zone not mapped to the selected entry.')
                elif picker_boy not in picker_dashboard_obj.zone.picker_users.all():
                    raise serializers.ValidationError(f'Invalid picker_boy | {picker_boy} is not mapped to the zone.')
                data['picker_boy'] = picker_boy
            else:
                raise serializers.ValidationError(f"Invalid Picker boy | 'picker_boy' can't be empty.")
        else:
            raise serializers.ValidationError("PickerDashboard creation is not allowed.")

        if sorted(list(self.initial_data.keys())) != ['id', 'picker_boy']:
            raise serializers.ValidationError("Only Picker boy update is allowed")

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            picker_dashboard_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return picker_dashboard_instance


class PickerSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    completed = serializers.IntegerField()
    moved_to_qc = serializers.IntegerField()


class ZonewisePickerSummarySerializers(serializers.Serializer):
    status_count = PickerSummarySerializer(read_only=True)
    zone = ZoneSerializer(read_only=True)


class OrderStatusSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    completed = serializers.IntegerField()
    moved_to_qc = serializers.IntegerField()

