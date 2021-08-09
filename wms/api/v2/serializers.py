import csv
from itertools import chain

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from products.models import Product
from shops.models import Shop
from wms.models import In, Out


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
        field_names = ['TIMESTAMP', 'SKU', 'WAREHOUSE', 'INVENTORY TYPE', 'IN TYPE', 'OUT TYPE', 'TRANSACTION ID',
                       'QUANTITY']

        data = sorted(chain(ins, outs), key=lambda instance: instance.created_at)

        # Sum of qty
        ins_qty = ins.aggregate(Sum('quantity'))['quantity__sum']
        outs_qty = outs.aggregate(Sum('quantity'))['quantity__sum']

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(['TOTAL IN QUANTITY', ins_qty if ins_qty else 0])
        writer.writerow(['TOTAL OUT QUANTITY', outs_qty if outs_qty else 0])
        writer.writerow([])
        writer.writerow(field_names)
        for obj in data:
            if obj.__class__.__name__ == 'In':
                writer.writerow([obj.created_at, obj.sku, obj.warehouse, obj.inventory_type, obj.in_type, None,
                                 obj.in_type_id, obj.quantity])
            elif obj.__class__.__name__ == 'Out':
                writer.writerow([obj.created_at, obj.sku, obj.warehouse, obj.inventory_type, None, obj.out_type,
                                 obj.out_type_id, obj.quantity])
            else:
                writer.writerow([obj.created_at, obj.sku, obj.warehouse, obj.inventory_type, None, None, None,
                                 obj.quantity])

        return response



