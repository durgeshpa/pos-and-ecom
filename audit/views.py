import json
from collections import defaultdict
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q, F
from django.http import HttpResponse
import logging
from django.shortcuts import render, redirect
from django.utils import timezone
from rest_framework import status, authentication, permissions
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from shops.models import Shop
import csv
import codecs
from wms.models import Bin
from accounts.models import User
from retailer_to_sp.models import Order, Trip, PickerDashboard
from wms.views import commit_updates_to_es, PicklistRefresh
from .models import (AuditRun, AuditRunItem, AuditDetail,
                     AUDIT_DETAIL_STATUS_CHOICES, AUDIT_RUN_STATUS_CHOICES, AUDIT_INVENTORY_CHOICES,
                     AUDIT_RUN_TYPE_CHOICES, AUDIT_STATUS_CHOICES, AuditTicket, AUDIT_TICKET_STATUS_CHOICES,
                     AuditProduct,
                     AUDIT_PRODUCT_STATUS, AUDIT_DETAIL_STATE_CHOICES, AuditCancelledPicklist, AuditTicketManual,
                     AUDIT_LEVEL_CHOICES
                     )
from services.models import WarehouseInventoryHistoric, BinInventoryHistoric, InventoryArchiveMaster
from wms.models import WarehouseInventory, WarehouseInternalInventoryChange, InventoryType, InventoryState, \
    BinInventory, BinInternalInventoryChange, Putaway, OrderReserveRelease, Pickup, PickupBinInventory, \
    PutawayBinInventory
from products.models import Product
import datetime
from audit.forms import UploadBulkAuditAdminForm
from .serializers import WarehouseInventoryTransactionSerializer, WarehouseInventorySerializer, \
    BinInventoryTransactionSerializer, BinInventorySerializer, PickupBlockedQuantitySerializer
from .utils import get_products_by_audit

from audit.serializers import AuditBulkCreation
info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')


def initialize_dict():
    nested_dict = lambda: defaultdict(nested_dict)
    sku_dict = nested_dict()
    return sku_dict


def run_warehouse_level_audit(audit_run):
    audit_started = audit_run.created_at
    inventory_calculated = initialize_dict()

    current_inventory = WarehouseInventory.objects.filter(warehouse=audit_run.warehouse)\
                                                  .values('sku_id', 'inventory_type_id',
                                                          'inventory_state_id', 'quantity')

    last_archived = get_archive_entry(audit_run, InventoryArchiveMaster.ARCHIVE_INVENTORY_CHOICES.WAREHOUSE)

    if last_archived is None:
        return
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
        if tr.transaction_type in ['stock_correction_in_type', 'stock_correction_out_type']:
            inventory_calculated[tr.sku.product_sku][tr.final_type_id][tr.final_stage_id] = tr.quantity
        elif tr.transaction_type in ['manual_audit_add', 'audit_correction_add']:
            inventory_calculated[tr.sku.product_sku][tr.final_type_id][tr.final_stage_id] += tr.quantity
        elif tr.transaction_type in ['manual_audit_deduct', 'audit_correction_deduct']:
            inventory_calculated[tr.sku.product_sku][tr.final_type_id][tr.final_stage_id] -= tr.quantity
        else:
            inventory_calculated[tr.sku.product_sku][tr.initial_type_id][tr.initial_stage_id] -= tr.quantity
            inventory_calculated[tr.sku.product_sku][tr.final_type_id][tr.final_stage_id] += tr.quantity

    for item in current_inventory:
        if isinstance(inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']], dict):
            inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']] = 0
        qty_calculated = inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']]
        audit_status = AUDIT_STATUS_CHOICES.DIRTY
        if item['quantity'] == qty_calculated:
            audit_status = AUDIT_STATUS_CHOICES.CLEAN
        AuditRunItem.objects.create(warehouse=audit_run.warehouse,
                                    audit_run=audit_run,
                                    sku_id=item['sku_id'],
                                    inventory_type_id=item['inventory_type_id'],
                                    inventory_state_id=item['inventory_state_id'],
                                    qty_expected=item['quantity'],
                                    qty_calculated=qty_calculated,
                                    status=audit_status)
        if audit_status == AUDIT_STATUS_CHOICES.DIRTY:
            ticket = AuditTicket.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                sku_id=item['sku_id'],
                                                inventory_type_id=item['inventory_type_id'],
                                                inventory_state_id=item['inventory_state_id'],
                                                qty_expected_type=AuditTicket.QTY_TYPE_IDENTIFIER.WAREHOUSE,
                                                qty_calculated_type=AuditTicket.QTY_TYPE_IDENTIFIER.WAREHOUSE_CALCULATED,
                                                qty_expected=item['quantity'],
                                                qty_calculated=qty_calculated,
                                                status=AUDIT_TICKET_STATUS_CHOICES.OPEN)
            # AuditTicketHistory.objects.create(audit_ticket=ticket, comment="Created")


def get_archive_entry(audit_run, inventory_type):
    last_archived_qs = InventoryArchiveMaster.objects.filter(inventory_type=inventory_type)
    if audit_run.audit.is_historic:
        audit_from = audit_run.audit.audit_from
        last_archived_qs.filter(archive_date__gte=audit_from)
        last_archived = last_archived_qs.earliest('archive_date')
    else:
        last_archived = last_archived_qs.latest('archive_date')
    return last_archived


def bin_transaction_type_switch(tr_type):
    tr_type_in_out = {
        'audit_adjustment': 1,
        'put_away_type': 1,
        'pickup_created': -1,
        'pickup_complete': 1,
        'picking_cancelled': 1,
        'manual_audit_add': 1,
        'manual_audit_deduct': -1,
        'audit_correction_add': 1,
        'audit_correction_deduct': -1
    }
    return tr_type_in_out.get(tr_type, 1)


def run_bin_level_audit(audit_run):
    audit_started = audit_run.created_at
    inventory_calculated = initialize_dict()

    current_inventory = BinInventory.objects.filter(warehouse=audit_run.warehouse).values('sku_id', 'batch_id',
                                                                                          'bin_id', 'inventory_type_id',
                                                                                          'quantity')

    last_archived = get_archive_entry(audit_run, InventoryArchiveMaster.ARCHIVE_INVENTORY_CHOICES.BIN)

    if last_archived is None:
        return

    audit_run.archive_entry = last_archived
    last_day_inventory = BinInventoryHistoric.objects.filter(archive_entry=last_archived,
                                                             warehouse=audit_run.warehouse) \
                                                     .values('sku_id',
                                                             'batch_id',
                                                             'bin_id',
                                                             'inventory_type_id',
                                                             'quantity')

    for item in last_day_inventory:
        inventory_calculated[item['sku_id']][item['batch_id']][item['bin_id']][item['inventory_type_id']] = item[
            'quantity']

    last_day_transactions = BinInternalInventoryChange.objects.filter(warehouse=audit_run.warehouse,
                                                                      created_at__gte=last_archived.created_at,
                                                                      created_at__lte=audit_started)

    for tr in last_day_transactions:
        if isinstance(inventory_calculated[tr.sku_id][tr.batch_id][tr.final_bin_id][tr.final_inventory_type_id], dict):
            inventory_calculated[tr.sku_id][tr.batch_id][tr.final_bin_id][tr.final_inventory_type_id] = 0
        if tr.transaction_type in ['stock_correction_in_type','stock_correction_out_type']:
            inventory_calculated[tr.sku_id][tr.batch_id][tr.final_bin_id][tr.final_inventory_type_id] = tr.quantity
        else:
            quantity = bin_transaction_type_switch(tr.transaction_type)*tr.quantity
            inventory_calculated[tr.sku_id][tr.batch_id][tr.final_bin_id][tr.final_inventory_type_id] += quantity

    for item in current_inventory:
        if isinstance(inventory_calculated[item['sku_id']][item['batch_id']][item['bin_id']][item['inventory_type_id']], dict):
            inventory_calculated[item['sku_id']][item['batch_id']][item['bin_id']][item['inventory_type_id']] = 0
        qty_calculated = inventory_calculated[item['sku_id']][item['batch_id']][item['bin_id']][item['inventory_type_id']]
        audit_item_status = AUDIT_STATUS_CHOICES.DIRTY
        if item['quantity'] == qty_calculated:
            audit_item_status = AUDIT_STATUS_CHOICES.CLEAN
        audit_item = AuditRunItem.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                 sku_id=item['sku_id'],
                                                 batch_id=item['batch_id'],
                                                 bin_id=item['bin_id'],
                                                 inventory_type_id=item['inventory_type_id'],
                                                 qty_expected=item['quantity'],
                                                 qty_calculated=qty_calculated,
                                                 status=audit_item_status)
        if audit_item_status == AUDIT_STATUS_CHOICES.DIRTY:
            ticket = AuditTicket.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                sku_id=item['sku_id'],
                                                batch_id=item['batch_id'],
                                                bin_id=item['bin_id'],
                                                inventory_type_id=item['inventory_type_id'],
                                                qty_expected_type=AuditTicket.QTY_TYPE_IDENTIFIER.BIN,
                                                qty_calculated_type=AuditTicket.QTY_TYPE_IDENTIFIER.BIN_CALCULATED,
                                                qty_expected=item['quantity'],
                                                qty_calculated=qty_calculated,
                                                status=AUDIT_TICKET_STATUS_CHOICES.OPEN)
            # AuditTicketHistory.objects.create(audit_ticket=ticket, comment="Created")


def run_bin_warehouse_integrated_audit(audit_run):
    type_normal = InventoryType.objects.only('id').get(inventory_type='normal').id
    stage_available = InventoryState.objects.filter(inventory_state='available').last()
    stage_reserved = InventoryState.objects.filter(inventory_state='reserved').last()
    stage_ordered = InventoryState.objects.filter(inventory_state='ordered').last()

    current_bin_inventory = BinInventory.objects.values('sku_id', 'inventory_type_id') \
                                                .filter(warehouse=audit_run.warehouse) \
                                                .annotate(quantity=Sum('quantity'))
    pickup_blocked_inventory = Pickup.objects.filter(warehouse=audit_run.warehouse,
                                                     status__in=['pickup_creation', 'picking_assigned'])\
                                             .values('sku_id').annotate(qty=Sum('quantity'))

    pickup_dict = {g['sku_id']: g['qty'] for g in pickup_blocked_inventory}
    pickup_cancelled_inventory = PutawayBinInventory.objects.filter(warehouse=audit_run.warehouse,
                                                                    putaway_status=False,
                                                                    putaway__putaway_type='CANCELLED')\
                                                            .values('sku_id').annotate(qty=Sum('putaway_quantity'))
    pickup_cancelled_dict = {g['sku_id']: g['qty'] for g in pickup_cancelled_inventory}
    for item in current_bin_inventory:
        warehouse_quantity = WarehouseInventory.objects.filter(Q(warehouse__id=audit_run.warehouse.id),
                                                               Q(sku_id=item['sku_id']),
                                                               Q(inventory_type_id=item['inventory_type_id']),
                                                               Q(inventory_state_id__in=[stage_available,
                                                                                         stage_reserved,
                                                                                         stage_ordered])) \
                                                       .aggregate(total=Sum('quantity')).get('total')
        if not warehouse_quantity:
            warehouse_quantity = 0
        bin_quantity = item['quantity']
        if item['inventory_type_id'] == type_normal:
            bin_quantity += (pickup_dict[item['sku_id']] if pickup_dict.get(item['sku_id']) else 0)
            bin_quantity += (pickup_cancelled_dict[item['sku_id']] if pickup_cancelled_dict.get(item['sku_id']) else 0)
        audit_item_status = AUDIT_STATUS_CHOICES.DIRTY
        if warehouse_quantity == bin_quantity:
            audit_item_status = AUDIT_STATUS_CHOICES.CLEAN
        audit_item = AuditRunItem.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                 sku_id=item['sku_id'],
                                                 inventory_type_id=item['inventory_type_id'],
                                                 qty_expected=bin_quantity,
                                                 qty_calculated=warehouse_quantity,
                                                 status=audit_item_status)
        if audit_item_status == AUDIT_STATUS_CHOICES.DIRTY:
            ticket = AuditTicket.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                # audit_type=audit_run.audit.audit_type,
                                                # audit_inventory_type=audit_run.audit.audit_inventory_type,
                                                sku_id=item['sku_id'],
                                                inventory_type_id=item['inventory_type_id'],
                                                qty_expected_type=AuditTicket.QTY_TYPE_IDENTIFIER.BIN,
                                                qty_calculated_type=AuditTicket.QTY_TYPE_IDENTIFIER.WAREHOUSE,
                                                qty_expected=bin_quantity,
                                                qty_calculated=warehouse_quantity,
                                                status=AUDIT_TICKET_STATUS_CHOICES.OPEN)
            # AuditTicketHistory.objects.create(audit_ticket=ticket, comment="Created")


def run_audit_for_daily_operations(audit_run):
    type_normal = InventoryType.objects.only('id').get(inventory_type='normal').id
    stage_available = InventoryState.objects.only('id').get(inventory_state='available').id
    stage_reserved = InventoryState.objects.only('id').get(inventory_state='reserved').id
    stage_ordered = InventoryState.objects.only('id').get(inventory_state='ordered').id
    stage_picked = InventoryState.objects.only('id').get(inventory_state='picked').id
    stage_shipped = InventoryState.objects.only('id').get(inventory_state='shipped').id

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
        if isinstance(inventory_calculated[item['sku_id']][type_normal][stage_available], dict):
            inventory_calculated[item['sku_id']][type_normal][stage_available] = 0

        inventory_calculated[item['sku_id']][type_normal][stage_reserved] += item['qty']
        inventory_calculated[item['sku_id']][type_normal][stage_available] -= item['qty']

    orders_placed = Order.objects.filter(~Q(order_status=Order.CANCELLED), created_at__gte=last_archived.created_at)
    for o in orders_placed:
        ordered_sku = o.ordered_cart.rt_cart_list.values('cart_product__product_sku').annotate(qty=Sum('no_of_pieces'))
        for item in ordered_sku:
            if isinstance(inventory_calculated[item['cart_product__product_sku']][type_normal][stage_ordered], dict):
                inventory_calculated[item['cart_product__product_sku']][type_normal][stage_ordered] = 0
            if isinstance(inventory_calculated[item['cart_product__product_sku']][type_normal][stage_available], dict):
                inventory_calculated[item['cart_product__product_sku']][type_normal][stage_available] = 0

            inventory_calculated[item['cart_product__product_sku']][type_normal][stage_ordered] += item['qty']
            inventory_calculated[item['cart_product__product_sku']][type_normal][stage_available] -= item['qty']

    pickups = PickupBinInventory.objects.filter(pickup__status='picking_complete',
                                                pickup__modified_at__gte=last_archived.created_at).values('pickup__sku_id') \
                                        .annotate(pickup_qty=Sum('pickup_quantity'), qty=Sum('quantity'))
    for item in pickups:
        if isinstance(inventory_calculated[item['pickup__sku_id']][type_normal][stage_picked], dict):
            inventory_calculated[item['pickup__sku_id']][type_normal][stage_picked] = 0
        if isinstance(inventory_calculated[item['pickup__sku_id']][type_normal][stage_ordered], dict):
            inventory_calculated[item['pickup__sku_id']][type_normal][stage_ordered] = 0
        if isinstance(inventory_calculated[item['pickup__sku_id']][type_normal][stage_available], dict):
            inventory_calculated[item['pickup__sku_id']][type_normal][stage_available] = 0

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
                if isinstance(inventory_calculated[item['product__product_sku']][type_normal][stage_picked], dict):
                    inventory_calculated[item['product__product_sku']][type_normal][stage_picked] = 0

                inventory_calculated[item['product__product_sku']][type_normal][stage_shipped] += item['qty']
                inventory_calculated[item['product__product_sku']][type_normal][stage_picked] -= item['qty']

    for item in current_inventory:
        if isinstance(inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']], dict):
            inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']] = 0
        calculated_quantity = inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']]

        audit_item_status = AUDIT_STATUS_CHOICES.DIRTY
        if calculated_quantity == item['quantity']:
            audit_item_status = AUDIT_STATUS_CHOICES.CLEAN

        audit_item = AuditRunItem.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                 sku_id=item['sku_id'],
                                                 inventory_type_id=item['inventory_type_id'],
                                                 inventory_state_id=item['inventory_state_id'],
                                                 qty_expected=item['quantity'],
                                                 qty_calculated=calculated_quantity,
                                                 status=audit_item_status)
        if audit_item_status == AUDIT_STATUS_CHOICES.DIRTY:
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
                                                status=AUDIT_TICKET_STATUS_CHOICES.OPEN)
            # AuditTicketHistory.objects.create(audit_ticket=ticket, comment="Created")


def run_audit(audit_run, inventory_choice):
    if inventory_choice == AUDIT_INVENTORY_CHOICES.WAREHOUSE:
        run_warehouse_level_audit(audit_run)
    if inventory_choice == AUDIT_INVENTORY_CHOICES.BIN:
        run_bin_level_audit(audit_run)
    if inventory_choice == AUDIT_INVENTORY_CHOICES.INTEGRATED:
        run_bin_warehouse_integrated_audit(audit_run)
    if inventory_choice == AUDIT_INVENTORY_CHOICES.DAILY_OPERATIONS:
        run_audit_for_daily_operations(audit_run)


def get_last_historic_run(audit):
    return AuditRun.objects.filter(audit=audit, status=AUDIT_RUN_STATUS_CHOICES.COMPLETED).last()


def start_automated_inventory_audit():
    audits_to_perform = AuditDetail.objects.filter(audit_run_type=AUDIT_RUN_TYPE_CHOICES.AUTOMATED,
                                                   status=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE)
    for audit in audits_to_perform:
        if audit.is_historic:
            last_historic_run = get_last_historic_run(audit)
            if last_historic_run:
                diff_in_dates = (datetime.date.today() - last_historic_run.completed_at.date())
                if diff_in_dates.days < 30:
                    cron_logger.info('Audit Id-{}. last run was completed on {}, skipping this audit run for now.'
                                     .format(audit.id, last_historic_run.completed_at))
                    continue
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
        audit_run.status = AUDIT_RUN_STATUS_CHOICES.COMPLETED
        audit_run.completed_at = datetime.datetime.now()
        audit_run.save()


def run_audit_manually(request):
    return HttpResponse(start_automated_inventory_audit())


class BaseListAPIView(ListCreateAPIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
               'message': "%s records found" % (queryset.count()),
               'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class WarehouseInventoryHistoryView(BaseListAPIView):
    serializer_class = WarehouseInventorySerializer

    def get_queryset(self):
        return WarehouseInventoryHistoric.objects.filter(warehouse=self.request.data.get('shop_id'),
                                                         sku_id=self.request.data.get('sku_id'),
                                                         archived_at__date=self.request.data.get('archive_date'))


class WarehouseInventoryTransactionView(BaseListAPIView):
    serializer_class = WarehouseInventoryTransactionSerializer

    def get_queryset(self):
        data = self.request.data
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        sku_id = data.get('sku_id')
        return WarehouseInternalInventoryChange.objects.filter(warehouse=self.request.data.get('shop_id'),
                                                               sku_id=Product.objects.only('id').get(product_sku=sku_id).id,
                                                               created_at__gte=start_date,
                                                               created_at__lte=end_date)


class WarehouseInventoryView(BaseListAPIView):
    serializer_class = WarehouseInventorySerializer

    def get_queryset(self):
        return WarehouseInventory.objects.filter(warehouse=self.request.data.get('shop_id'),
                                                 sku_id=self.request.data.get('sku_id'))


class BinInventoryTransactionView(BaseListAPIView):
    serializer_class = BinInventoryTransactionSerializer

    def get_queryset(self):
        data = self.request.data
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        sku_id = data.get('sku_id')
        return BinInternalInventoryChange.objects.filter(warehouse=self.request.data.get('shop_id'),
                                                         sku_id=sku_id,
                                                         created_at__gte=start_date,
                                                         created_at__lte=end_date)


class BinInventoryView(BaseListAPIView):
    serializer_class = BinInventorySerializer

    def get_queryset(self):
        return BinInventory.objects.filter(warehouse=self.request.data.get('shop_id'),
                                           sku_id=self.request.data.get('sku_id'))


class BinInventoryHistoryView(BaseListAPIView):
    serializer_class = BinInventorySerializer

    def get_queryset(self):
        return BinInventoryHistoric.objects.filter(warehouse=self.request.data.get('shop_id'),
                                                   sku_id=self.request.data.get('sku_id'),
                                                   archived_at__date=self.request.data.get('archive_date')
                                                   )


class PickupBlockedQuantityView(BaseListAPIView):
    serializer_class = PickupBlockedQuantitySerializer
    def get_queryset(self):
        return Pickup.objects.filter(warehouse=self.request.data.get('shop_id'),
                                     sku_id=self.request.data.get('sku_id'),
                                     status__in=['pickup_creation', 'pickup_assigned'])

class BlockUnblockProduct(object):

    @staticmethod
    def is_product_blocked_for_audit(product, warehouse):
        return AuditProduct.objects.filter(warehouse=warehouse, sku=product, status=AUDIT_PRODUCT_STATUS.BLOCKED).exists()

    @staticmethod
    def block_product_during_audit(audit, product_list, warehouse):
        for p in product_list:
            AuditProduct.objects.update_or_create(audit=audit, warehouse=warehouse, sku=p,
                                                  defaults={'status': AUDIT_PRODUCT_STATUS.BLOCKED})
            commit_updates_to_es(warehouse, p)

    @staticmethod
    def unblock_product_after_audit(audit, product, warehouse):
        audit_product = AuditProduct.objects.filter(audit=audit, warehouse=warehouse, sku=product).last()
        if audit_product:
            audit_product.status = AUDIT_PRODUCT_STATUS.RELEASED
            audit_product.save()
        commit_updates_to_es(warehouse, product)


    @staticmethod
    def enable_products(audit_detail):
        products_to_update = get_products_by_audit(audit_detail)
        for p in products_to_update:
            BlockUnblockProduct.unblock_product_after_audit(audit_detail, p, audit_detail.warehouse)

    @staticmethod
    def disable_products(audit_detail):
        products_to_disable = get_products_by_audit(audit_detail)
        if len(products_to_disable) > 0:
            BlockUnblockProduct.block_product_during_audit(audit_detail, products_to_disable, audit_detail.warehouse)

    @staticmethod
    def release_product_from_audit(audit, audit_run, sku, warehouse):
        if audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
            remaining_products_to_audit = get_remaining_products_to_audit(audit, audit_run)
            if sku not in remaining_products_to_audit:
                BlockUnblockProduct.unblock_product_after_audit(audit, sku, warehouse)
        if audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
            remaining_bins_to_audit = get_remaining_bins_to_audit(audit, audit_run, sku)
            if len(remaining_bins_to_audit) == 0:
                BlockUnblockProduct.unblock_product_after_audit(audit, sku, warehouse)


def get_remaining_bins_to_audit(audit, audit_run, sku):
    bin_and_batches_to_audit = BinInventory.objects.filter(warehouse=audit.warehouse,
                                                           sku=sku)\
                                                   .values_list('bin_id', 'batch_id', 'sku_id')
    bin_batches_audited = AuditRunItem.objects.filter(audit_run=audit_run)\
                                              .values_list('bin_id', 'batch_id', 'sku_id')

    remaining_bin_batches_to_audit = list(set(bin_and_batches_to_audit) - set(bin_batches_audited))
    info_logger.info('AuditInventory|get_remaining_bins_to_audit|remaining_bin_batches_to_audit-{}'
                     .format(remaining_bin_batches_to_audit))
    return remaining_bin_batches_to_audit

def get_remaining_products_to_audit(audit, audit_run):
    all_bins_to_audit = audit.bin.all()
    bin_and_batches_to_audit = BinInventory.objects.filter(warehouse=audit.warehouse,
                                                           bin__in=all_bins_to_audit)\
                                                   .values_list('bin_id', 'batch_id', 'sku_id')

    bin_batches_audited = AuditRunItem.objects.filter(audit_run=audit_run)\
                                              .values_list('bin_id', 'batch_id', 'sku_id')
    remaining_bin_batches_to_audit = list(set(bin_and_batches_to_audit) - set(bin_batches_audited))
    remaining_skus_to_audit = [item[2] for item in remaining_bin_batches_to_audit]
    info_logger.info('AuditInventory|get_remaining_products_to_audit|remaining_skus_to_audit-{}'
                     .format(remaining_skus_to_audit))
    return remaining_skus_to_audit

def update_audit_status_by_audit(audit_id):
    audit = AuditDetail.objects.filter(id=audit_id).last()
    audit_items = AuditRunItem.objects.filter(audit_run__audit=audit)
    audit_state = AUDIT_DETAIL_STATE_CHOICES.PASS
    for i in audit_items:
        if i.qty_expected != i.qty_calculated:
            audit_state = AUDIT_DETAIL_STATE_CHOICES.FAIL
            break
    audit.state = audit_state
    audit.save()


def create_pick_list_by_audit(audit_id):
    orders_to_generate_picklists = AuditCancelledPicklist.objects.filter(audit=audit_id, is_picklist_refreshed=False)\
                                                                 .order_by('order_no')
    for o in orders_to_generate_picklists:
        info_logger.error('create_pick_list_by_audit|Starting for order {}'.format(o.order_no))
        order = Order.objects.filter(~Q(order_status='CANCELLED'), order_no=o.order_no).last()
        if order is None:
            info_logger.error('create_pick_list_by_audit| Order number-{}, No active order found'
                              .format(o.order_no))
            continue
        try:
            pd_obj = PickerDashboard.objects.filter(order=order,
                                                    picking_status__in=['picking_pending', 'picking_assigned'],
                                                    is_valid=False).last()
            if pd_obj is None:
                info_logger.info("Picker Dashboard object does not exists for order {}".format(order.order_no))
                continue
            with transaction.atomic():
                PicklistRefresh.create_picklist_by_order(order)
                o.is_picklist_refreshed = True
                o.save()
                pd_obj.is_valid = True
                pd_obj.refreshed_at = timezone.now()
                pd_obj.save()
        except Exception as e:
            info_logger.error(e)
            info_logger.error('create_pick_list_by_audit|Exception while generating picklist for order {}'.format(o.order_no))


def create_audit_tickets_by_audit(audit_id):
    audit = AuditDetail.objects.filter(id=audit_id).last()
    if audit.state != AUDIT_DETAIL_STATE_CHOICES.FAIL:
        info_logger.info('tasks|create_audit_tickets| ticked not generated, audit is in {} state'
                         .format(AUDIT_DETAIL_STATE_CHOICES[audit.state]))
        return
    audit_run = AuditRun.objects.filter(audit=audit).last()
    type_normal = InventoryType.objects.filter(inventory_type='normal').last()
    type_expired = InventoryType.objects.filter(inventory_type='expired').last()
    type_damaged = InventoryType.objects.filter(inventory_type='damaged').last()
    audit_items = AuditRunItem.objects.filter(~Q(qty_expected=F('qty_calculated')), audit_run=audit_run)
    for i in audit_items:
        if not AuditTicketManual.objects.filter(audit_run=audit_run, bin=i.bin, sku=i.sku,
                                                batch_id=i.batch_id).exists():
            agg_qty = AuditRunItem.objects.filter(audit_run=audit_run, bin=i.bin, sku=i.sku, batch_id=i.batch_id) \
                .aggregate(n_phy=Sum('qty_calculated', filter=Q(inventory_type=type_normal)),
                           n_sys=Sum('qty_expected', filter=Q(inventory_type=type_normal)),
                           e_phy=Sum('qty_calculated', filter=Q(inventory_type=type_expired)),
                           e_sys=Sum('qty_expected', filter=Q(inventory_type=type_expired)),
                           d_phy=Sum('qty_calculated', filter=Q(inventory_type=type_damaged)),
                           d_sys=Sum('qty_expected', filter=Q(inventory_type=type_damaged)))

            AuditTicketManual.objects.create(warehouse=audit_run.warehouse,
                                             audit_run=audit_run, bin=i.bin, sku=i.sku, batch_id=i.batch_id,
                                             qty_normal_system=agg_qty['n_sys'],
                                             qty_normal_actual=agg_qty['n_phy'],
                                             qty_damaged_system=0 if agg_qty['d_sys'] is None else agg_qty['d_sys'],
                                             qty_damaged_actual=0 if agg_qty['d_phy'] is None else agg_qty['d_phy'],
                                             qty_expired_system=0 if agg_qty['e_sys'] is None else agg_qty['e_sys'],
                                             qty_expired_actual=0 if agg_qty['e_phy'] is None else agg_qty['e_phy'],
                                             status=AUDIT_TICKET_STATUS_CHOICES.OPEN)
    info_logger.info('tasks|create_audit_tickets|created for audit run {}, bin {}, batch {}'
                     .format(audit_run.id, i.bin_id, i.batch_id))
    audit.state = AUDIT_DETAIL_STATE_CHOICES.TICKET_RAISED
    audit.save()


def bulk_audit_csv_upload_view(request):
    warehouse_choices = Shop.objects.filter(shop_type__shop_type='sp')

    if request.method == 'POST':
        form = UploadBulkAuditAdminForm(request.POST, request.FILES)
        
        if form.errors:
            return render(request, 'admin/audit/bulk-upload-audit-details.html', {'warehouses': warehouse_choices.values(),'form': form})

        if form.is_valid():
            upload_file = form.cleaned_data.get('file')
            warehouse_id = request.POST.get('select')
          
            reader = csv.reader(codecs.iterdecode(upload_file, 'utf-8', errors='ignore'))
            first_row = next(reader)
            try:
                for row_id, row in enumerate(reader):
                    if len(row) == 0:
                        continue
                    if '' in row:
                        if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' ):
                            continue
                    phone_number = row[1].split('-')[0].strip()
                    if row[0]=='Manual':
                        audit_run_type = 0
                    if row[2] == "Bin Wise":
                        audit_level = 0
                        bins = []
                        for row in row[3].split(","):
                            bin_value = Bin.objects.get(bin_id=row.strip())
                            obj = Bin.objects.filter(warehouse=warehouse_id,bin_id=bin_value).exists()
                            if obj == True:
                                bins.append(bin_value)
                            else:
                                return render(request, 'admin/audit/bulk-upload-audit-details.html', 
                                {
                                'form': form,
                                'warehouses': warehouse_choices.values(),
                                'error': f"Row {row_id + 1} | 'Invalid Bin IDs"
                                })
    
                        audit_item = AuditDetail.objects.create(
                            warehouse=Shop.objects.get(id=warehouse_id),
                            audit_run_type=audit_run_type,
                            auditor = User.objects.get(phone_number=phone_number),
                            audit_level=audit_level,
                        )
                        for bin_value in bins:
                            audit_item.bin.add(bin_value)
                        audit_item.save()       
                    elif row[2] == "Product Wise":
                        audit_level = 1
                        skus = []
                        for row in row[4].split(","):
                            if Product.objects.get(product_sku=row.strip()):
                                sku_obj = Product.objects.get(product_sku=row.strip())
                            obj = BinInventory.objects.filter(warehouse=warehouse_id,sku=sku_obj).exists()
                          
                            if obj == True:
                                skus.append(sku_obj)
                            else:
                                return render(request, 'admin/audit/bulk-upload-audit-details.html', 
                                {
                                'form': form,
                                'warehouses': warehouse_choices.values(),
                                'error': f"Row {row_id + 1} | 'Invalid SKU IDs"
                                })
                        audit_item = AuditDetail.objects.create(
                            warehouse=Shop.objects.get(id=warehouse_id),
                            audit_run_type=audit_run_type,
                            auditor = User.objects.get(phone_number=phone_number),
                            audit_level=audit_level,
                        )
                        for sku_value in skus:
                            audit_item.sku.add(sku_value)
                        audit_item.save()
            except Exception as e:
                print(e)
            return render(request, 'admin/audit/bulk-upload-audit-details.html', {
                'form': form,
                'warehouses': warehouse_choices.values(),
                'success': 'Audit CSV uploaded successfully !',
            })
    else:
        form = UploadBulkAuditAdminForm()
    return render(request, 'admin/audit/bulk-upload-audit-details.html', {'warehouses': warehouse_choices.values(),'form': form})

    
def AuditDownloadSampleCSV(request):
    filename = "audit_sample.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(["Audit Run Type", "Auditor", "Audit Level", "Bin ID", "SKU ID"])
    writer.writerow(["Manual", "7088491957 - Ankit", "Bin Wise", "B2BZ01SR001-0001,B2BZ01SR001-0002"," "])
    return response
