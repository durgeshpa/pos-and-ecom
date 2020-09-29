import json
from collections import defaultdict

from django.db.models import Sum, Q
from django.http import HttpResponse
from django.shortcuts import render
import logging

from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, authentication, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from retailer_to_sp.models import Order, CartProductMapping, OrderedProduct, Trip
from shops.models import Shop
from .models import (AuditRun, AuditRunItem, AuditDetail,
                     AUDIT_DETAIL_STATUS_CHOICES, AUDIT_RUN_STATUS_CHOICES, AUDIT_INVENTORY_CHOICES,
                     AUDIT_RUN_TYPE_CHOICES, AUDIT_STATUS_CHOICES, AuditTicket, AUDIT_TICKET_STATUS_CHOICES,
                     AuditTicketHistory)
from services.models import WarehouseInventoryHistoric, BinInventoryHistoric, InventoryArchiveMaster
from wms.models import WarehouseInventory, WarehouseInternalInventoryChange, InventoryType, InventoryState, \
    BinInventory, BinInternalInventoryChange, Putaway, OrderReserveRelease, Pickup, PickupBinInventory
from products.models import Product
import datetime

from .serializers import WarehouseInventoryTransactionSerializer, WarehouseInventorySerializer, \
    BinInventoryTransactionSerializer, BinInventorySerializer

info_logger = logging.getLogger('file-info')


def initialize_dict():
    nested_dict = lambda: defaultdict(nested_dict)
    sku_dict = nested_dict()
    return sku_dict


def run_warehouse_level_audit(audit_run):
    audit_started = audit_run.created_at
    prev_day = audit_started.date() - datetime.timedelta(1)
    inventory_calculated = initialize_dict()

    current_inventory = WarehouseInventory.objects.filter(warehouse=audit_run.warehouse)\
                                                  .values('sku_id', 'inventory_type_id',
                                                          'inventory_state_id', 'quantity')


    last_archived = InventoryArchiveMaster.objects.filter(
                        inventory_type=InventoryArchiveMaster.ARCHIVE_INVENTORY_CHOICES.WAREHOUSE).latest('archive_date')
    audit_run.archive_entry = last_archived
    last_day_inventory = WarehouseInventoryHistoric.objects.filter(archive_entry=last_archived,
                                                                   warehouse=audit_run.warehouse) \
                                                           .values('sku_id',
                                                                   'inventory_type_id',
                                                                   'inventory_state_id',
                                                                   'quantity')
    for item in last_day_inventory:
        inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']] = item['quantity']

    last_day_transactions = WarehouseInternalInventoryChange.objects.filter(warehouse=audit_run.warehouse,
                                                                            created_at__gte=last_archived.created_at,
                                                                            created_at__lte=audit_started)

    for tr in last_day_transactions:
        if isinstance(inventory_calculated[tr.sku.product_sku][tr.initial_type_id][tr.initial_stage_id], dict):
            inventory_calculated[tr.sku.product_sku][tr.initial_type_id][tr.initial_stage_id] = 0

        if isinstance(inventory_calculated[tr.sku.product_sku][tr.final_type_id][tr.final_stage_id], dict):
            inventory_calculated[tr.sku.product_sku][tr.final_type_id][tr.final_stage_id] = 0

        inventory_calculated[tr.sku.product_sku][tr.initial_type_id][tr.initial_stage_id] -= tr.quantity
        inventory_calculated[tr.sku.product_sku][tr.final_type_id][tr.final_stage_id] += tr.quantity

    for item in current_inventory:
        if isinstance(inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']], dict):
            inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']] = 0
        qty_calculated = inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']]
        audit_status = AUDIT_STATUS_CHOICES.DIRTY
        if item['quantity'] == qty_calculated:
            audit_status = AUDIT_STATUS_CHOICES.CLEAN
        audit_item = AuditRunItem.objects.create(warehouse=audit_run.warehouse,
                                                 audit_run=audit_run,
                                                 sku_id=item['sku_id'],
                                                 inventory_type_id=item['inventory_type_id'],
                                                 inventory_state_id=item['inventory_state_id'],
                                                 qty_expected=item['quantity'],
                                                 qty_calculated=qty_calculated,
                                                 status=audit_status)
        if audit_status == AUDIT_STATUS_CHOICES.DIRTY:
            ticket = AuditTicket.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                # audit_type=audit_run.audit.audit_type,
                                                # audit_inventory_type=audit_run.audit.audit_inventory_type,
                                                sku_id=item['sku_id'],
                                                inventory_type_id=item['inventory_type_id'],
                                                inventory_state_id=item['inventory_state_id'],
                                                qty_expected_type=AuditTicket.QTY_TYPE_IDENTIFIER.WAREHOUSE,
                                                qty_calculated_type=AuditTicket.QTY_TYPE_IDENTIFIER.WAREHOUSE_CALCULATED,
                                                qty_expected=item['quantity'],
                                                qty_calculated=qty_calculated,
                                                status=AUDIT_TICKET_STATUS_CHOICES.OPENED)
            # AuditTicketHistory.objects.create(audit_ticket=ticket, comment="Created")


def run_bin_level_audit(audit_run):
    audit_started = audit_run.created_at
    prev_day = audit_started.date() - datetime.timedelta(1)
    inventory_calculated = initialize_dict()

    current_inventory = BinInventory.objects.filter(warehouse=audit_run.warehouse).values('sku_id', 'batch_id',
                                                                                          'bin_id', 'inventory_type_id',
                                                                                          'quantity')

    last_archived = InventoryArchiveMaster.objects.filter(
                        inventory_type=InventoryArchiveMaster.ARCHIVE_INVENTORY_CHOICES.BIN).latest('archive_date')
    audit_run.archive_entry = last_archived
    last_day_inventory = BinInventoryHistoric.objects.filter(archive_entry=last_archived,
                                                             warehouse=audit_run.warehouse) \
                                                     .values('sku_id',
                                                             'batch_id',
                                                             'bin_id',
                                                             'inventory_type_id',
                                                             'quantity')

    last_archived_at = WarehouseInventoryHistoric.objects.latest('archived_at').archived_at
    for item in last_day_inventory:
        inventory_calculated[item['sku_id']][item['batch_id']][item['bin_id']][item['inventory_type_id']] = item[
            'quantity']

    last_day_transactions = BinInternalInventoryChange.objects.filter(warehouse=audit_run.warehouse,
                                                                      created_at__gte=last_archived.created_at,
                                                                      created_at__lte=audit_started)

    for tr in last_day_transactions:
        if isinstance(inventory_calculated[tr.sku][tr.batch_id][tr.initial_bin_id][tr.initial_type_id], dict):
            inventory_calculated[tr.sku][tr.batch_id][tr.initial_bin_id][tr.initial_type_id] = 0

        if isinstance(inventory_calculated[tr.sku][tr.batch_id][tr.final_bin_id][tr.final_type_id], dict):
            inventory_calculated[tr.sku][tr.batch_id][tr.final_bin_id][tr.final_type_id] = 0

        inventory_calculated[tr.sku][tr.batch_id][tr.initial_bin_id][tr.initial_type_id] -= tr.quantity
        inventory_calculated[tr.sku][tr.batch_id][tr.final_bin_id][tr.final_type_id] += tr.quantity

    for item in current_inventory:
        if isinstance(inventory_calculated[item['sku_id']][item['batch_id']][item['bin_id']][item['inventory_type_id']], dict):
            inventory_calculated[item['sku_id']][item['batch_id']][item['bin_id']][item['inventory_type_id']] = 0
        qty_calculated = inventory_calculated[item['sku_id']][item['batch_id']][item['bin_id']][item['inventory_type_id']]
        status = AUDIT_STATUS_CHOICES.DIRTY
        if item['quantity'] == qty_calculated:
            status = AUDIT_STATUS_CHOICES.CLEAN
        audit_item = AuditRunItem.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                 sku_id=item['sku_id'],
                                                 batch_id=item['batch_id'],
                                                 bin_id=item['bin_id'],
                                                 inventory_type_id=item['inventory_type_id'],
                                                 qty_expected=item['quantity'],
                                                 qty_calculated=qty_calculated,
                                                 status=status)
        if status == AUDIT_STATUS_CHOICES.DIRTY:
            ticket = AuditTicket.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                # audit_type=audit_run.audit.audit_type,
                                                # audit_inventory_type=audit_run.audit.audit_inventory_type,
                                                sku_id=item['sku_id'],
                                                batch_id=item['batch_id'],
                                                bin_id=item['bin_id'],
                                                inventory_type_id=item['inventory_type_id'],
                                                qty_expected_type=AuditTicket.QTY_TYPE_IDENTIFIER.BIN,
                                                qty_calculated_type=AuditTicket.QTY_TYPE_IDENTIFIER.BIN_CALCULATED,
                                                qty_expected=item['quantity'],
                                                qty_calculated=qty_calculated,
                                                status=AUDIT_TICKET_STATUS_CHOICES.OPENED)
            # AuditTicketHistory.objects.create(audit_ticket=ticket, comment="Created")


def run_bin_warehouse_integrated_audit(audit_run):
    stage_available = InventoryState.objects.filter(inventory_state='available').last()
    stage_reserved = InventoryState.objects.filter(inventory_state='reserved').last()
    stage_ordered = InventoryState.objects.filter(inventory_state='ordered').last()

    current_bin_inventory = BinInventory.objects.values('sku_id', 'inventory_type_id') \
        .filter(warehouse=audit_run.warehouse) \
        .annotate(quantity=Sum('quantity'))

    for item in current_bin_inventory:
        warehouse_quantity = WarehouseInventory.objects.filter(Q(warehouse__id=audit_run.warehouse.id),
                                                               Q(sku_id=item['sku_id']),
                                                               Q(inventory_type_id=item['inventory_type_id']),
                                                               Q(inventory_state_id__in=[stage_available,
                                                                                         stage_reserved,
                                                                                         stage_ordered])) \
                                                       .aggregate(total=Sum('quantity')).get('total')
        status = AUDIT_STATUS_CHOICES.DIRTY
        if warehouse_quantity == item['quantity']:
            status = AUDIT_STATUS_CHOICES.CLEAN
        audit_item = AuditRunItem.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                 sku_id=item['sku_id'],
                                                 inventory_type_id=item['inventory_type_id'],
                                                 qty_expected=item['quantity'],
                                                 qty_calculated=warehouse_quantity,
                                                 status=status)
        if status == AUDIT_STATUS_CHOICES.DIRTY:
            ticket = AuditTicket.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                # audit_type=audit_run.audit.audit_type,
                                                # audit_inventory_type=audit_run.audit.audit_inventory_type,
                                                sku_id=item['sku_id'],
                                                inventory_type_id=item['inventory_type_id'],
                                                qty_expected_type=AuditTicket.QTY_TYPE_IDENTIFIER.BIN,
                                                qty_calculated_type=AuditTicket.QTY_TYPE_IDENTIFIER.WAREHOUSE,
                                                qty_expected=item['quantity'],
                                                qty_calculated=warehouse_quantity,
                                                status=AUDIT_TICKET_STATUS_CHOICES.OPENED)
            # AuditTicketHistory.objects.create(audit_ticket=ticket, comment="Created")


def run_stock_audit(audit_run):
    audit_started = audit_run.created_at
    prev_day = audit_started.date() - datetime.timedelta(1)
    type_normal = InventoryType.objects.only('id').get(inventory_type='normal').id
    stage_available = InventoryState.objects.only('id').get(inventory_state='available').id
    stage_reserved = InventoryState.objects.only('id').get(inventory_state='reserved').id
    stage_ordered = InventoryState.objects.only('id').get(inventory_state='ordered').id
    stage_picked = InventoryState.objects.only('id').get(inventory_state='picked').id
    stage_shipped = InventoryState.objects.only('id').get(inventory_state='shipped').id

    inventory_calculated = initialize_dict()

    last_archived = InventoryArchiveMaster.objects.filter(
                        inventory_type=InventoryArchiveMaster.ARCHIVE_INVENTORY_CHOICES.WAREHOUSE).latest('archive_date')
    audit_run.archive_entry = last_archived

    current_inventory = WarehouseInventory.objects.filter(warehouse=audit_run.warehouse) \
                                                  .values('sku_id', 'inventory_type_id',
                                                          'inventory_state_id', 'quantity')

    last_day_inventory = WarehouseInventoryHistoric.objects.filter(archive_entry=last_archived,
                                                                   warehouse=audit_run.warehouse) \
                                                           .values('sku_id',
                                                                   'inventory_state_id',
                                                                   'inventory_type_id',
                                                                   'quantity')

    inventory_calculated = initialize_dict()
    for item in last_day_inventory:
        inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']] = item['quantity']

    putaway_sku = Putaway.objects.filter(warehouse=audit_run.warehouse,
                                         created_at__gte=last_archived.created_at)\
                                 .values('sku_id').annotate(qty=Sum('putaway_quantity'))

    for item in putaway_sku:
        if isinstance(inventory_calculated[item['sku_id']][type_normal][stage_available], dict):
            inventory_calculated[item['sku_id']][type_normal][stage_available] = 0
        inventory_calculated[item['sku_id']][type_normal][stage_available] += item['qty']

    reserved_sku = OrderReserveRelease.objects.filter(warehouse__id=audit_run.warehouse.id,
                                                      warehouse_internal_inventory_release=None,
                                                      reserved_time__gte=last_archived.created_at).values('sku_id') \
                                              .annotate(qty=Sum('warehouse_internal_inventory_reserve__quantity'))

    for item in reserved_sku:
        if isinstance(inventory_calculated[item['sku_id']][type_normal][stage_reserved], dict):
            inventory_calculated[item['sku_id']][type_normal][stage_reserved] = 0

        inventory_calculated[item['sku_id']][type_normal][stage_reserved] += item['qty']
        inventory_calculated[item['sku_id']][type_normal][stage_available] -= item['qty']

    orders_placed = Order.objects.filter(~Q(order_status=Order.CANCELLED), created_at__gte=last_archived.created_at)
    for o in orders_placed:
        ordered_sku = o.ordered_cart.rt_cart_list.values('cart_product__product_sku').annotate(qty=Sum('no_of_pieces'))
        for item in ordered_sku:
            if isinstance(inventory_calculated[item['cart_product__product_sku']][type_normal][stage_ordered], dict):
                inventory_calculated[item['cart_product__product_sku']][type_normal][stage_ordered] = 0

            inventory_calculated[item['cart_product__product_sku']][type_normal][stage_ordered] += item['qty']
            inventory_calculated[item['cart_product__product_sku']][type_normal][stage_available] -= item['qty']

    pickups = PickupBinInventory.objects.filter(pickup__status='picking_complete',
                                                pickup__modified_at__gte=last_archived.created_at).values('pickup__sku_id') \
                                        .annotate(pickup_qty=Sum('pickup_quantity'), qty=Sum('quantity'))
    for item in pickups:
        if isinstance(inventory_calculated[item['pickup__sku_id']][type_normal][stage_picked], dict):
            inventory_calculated[item['pickup__sku_id']][type_normal][stage_picked] = 0

        inventory_calculated[item['pickup__sku_id']][type_normal][stage_picked] += item['pickup_qty']
        inventory_calculated[item['pickup__sku_id']][type_normal][stage_ordered] -= item['qty']
        inventory_calculated[item['pickup__sku_id']][type_normal][stage_available] += item['qty'] - item['pickup_qty']

    trips_started = Trip.objects.filter(starts_at__gte=last_archived.created_at).all()
    for t in trips_started:
        shipments = t.rt_invoice_trip.all()
        for s in shipments:
            shipment_sku = s.rt_order_product_order_product_mapping.values('product__product_sku').annotate(
                qty=Sum('shipped_qty'))
            for item in shipment_sku:
                if isinstance(inventory_calculated[item['product__product_sku']][type_normal][stage_shipped], dict):
                    inventory_calculated[item['product__product_sku']][type_normal][stage_shipped] = 0
                inventory_calculated[item['product__product_sku']][type_normal][stage_shipped] += item['qty']
                inventory_calculated[item['product__product_sku']][type_normal][stage_picked] -= item['qty']

    for item in current_inventory:
        if isinstance(inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']], dict):
            inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']] = 0
        calculated_quantity = inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']]

        status = AUDIT_STATUS_CHOICES.DIRTY
        if calculated_quantity == item['quantity']:
            status = AUDIT_STATUS_CHOICES.CLEAN

        audit_item = AuditRunItem.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                 sku_id=item['sku_id'],
                                                 inventory_type_id=item['inventory_type_id'],
                                                 inventory_state_id=item['inventory_state_id'],
                                                 qty_expected=item['quantity'],
                                                 qty_calculated=calculated_quantity,
                                                 status=status)
        if status == AUDIT_STATUS_CHOICES.DIRTY:
            ticket = AuditTicket.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                # audit_type=audit_run.audit.audit_type,
                                                # audit_inventory_type=audit_run.audit.audit_inventory_type,
                                                sku_id=item['sku_id'],
                                                inventory_type_id=item['inventory_type_id'],
                                                inventory_state_id=item['inventory_state_id'],
                                                qty_expected_type=AuditTicket.QTY_TYPE_IDENTIFIER.WAREHOUSE,
                                                qty_calculated_type=AuditTicket.QTY_TYPE_IDENTIFIER.WAREHOUSE_CALCULATED,
                                                qty_expected=item['quantity'],
                                                qty_calculated=calculated_quantity,
                                                status=AUDIT_TICKET_STATUS_CHOICES.OPENED)
            # AuditTicketHistory.objects.create(audit_ticket=ticket, comment="Created")


def run_audit(audit_run, inventory_choice):
    if inventory_choice == AUDIT_INVENTORY_CHOICES.WAREHOUSE:
        run_warehouse_level_audit(audit_run)
    if inventory_choice == AUDIT_INVENTORY_CHOICES.BIN:
        run_bin_level_audit(audit_run)
    if inventory_choice == AUDIT_INVENTORY_CHOICES.INTEGRATED:
        run_bin_warehouse_integrated_audit(audit_run)
    if inventory_choice == AUDIT_INVENTORY_CHOICES.STOCK:
        run_stock_audit(audit_run)


def start_automated_inventory_audit():
    audits_to_perform = AuditDetail.objects.filter(audit_type=AUDIT_RUN_TYPE_CHOICES.AUTOMATED,
                                                   status=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE)
    for audit in audits_to_perform:
        audit_run = AuditRun.objects.filter(audit=audit, status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS)
        if audit_run:
            continue
        audit_run = AuditRun.objects.create(warehouse=audit.warehouse, audit=audit,
                                            status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS)
        try:
            run_audit(audit_run, audit.audit_inventory_type)
        except Exception as e:
            info_logger.error("Audit run aborted with Exception ")
            info_logger.error(e)
            audit_run.status = AUDIT_RUN_STATUS_CHOICES.ABORTED
            audit_run.save()
            raise
        audit_run.status = AUDIT_RUN_STATUS_CHOICES.COMPLETED
        audit_run.completed_at = datetime.datetime.now()
        audit_run.save()


class WarehouseInventoryTransactionViewSet(APIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        audit_run_id = request.data.get('audit_run_id')
        sku_id = request.data.get('sku_id')
        audit_run = AuditRun.objects.get(pk=audit_run_id)
        inventory_transactions = WarehouseInternalInventoryChange.objects.filter(sku_id=Product.objects.only('id')
                                                                                 .get(product_sku=sku_id).id,
                                                                                 created_at__gte=audit_run.archive_entry.created_at,
                                                                                 created_at__lte=audit_run.created_at)
        serializer = WarehouseInventoryTransactionSerializer(inventory_transactions, many=True)
        return Response({"data": serializer.data, "message": "OK"}, status=status.HTTP_200_OK)


class WarehouseInventoryViewSet(APIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        sku_id = request.data.get('sku_id')
        inventory = WarehouseInventory.objects.filter(sku_id=sku_id)
        serializer = WarehouseInventorySerializer(inventory, many=True)
        return Response({"data": serializer.data, "message": "OK"}, status=status.HTTP_200_OK)


class BinInventoryTransactionViewSet(APIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        audit_run_id = request.data.get('audit_run_id')
        sku_id = request.data.get('sku_id')
        audit_run = AuditRun.objects.get(pk=audit_run_id)
        inventory_transactions = BinInternalInventoryChange.objects.filter(sku_id=sku_id,
                                                                           created_at__gte=audit_run.archive_entry.created_at,
                                                                           created_at__lte=audit_run.created_at)
        serializer = BinInventoryTransactionSerializer(inventory_transactions, many=True)
        return Response({"data": serializer.data, "message": "OK"}, status=status.HTTP_200_OK)


class BinInventoryViewSet(APIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        sku_id = request.data.get('sku_id')
        inventory_transactions = BinInventory.objects.filter(sku_id=sku_id)
        serializer = BinInventorySerializer(inventory_transactions, many=True)
        return Response({"data": serializer.data, "message": "OK"}, status=status.HTTP_200_OK)
