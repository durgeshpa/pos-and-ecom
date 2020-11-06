import json
from collections import defaultdict

from django.db import transaction
from django.db.models import Sum, Q, F
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.http import HttpResponse
import logging

from django.utils import timezone
from rest_framework import status, authentication, permissions
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response

from sp_to_gram.tasks import update_product_es, es_mget_by_ids
from retailer_to_sp.models import Order, Trip, PickerDashboard
from wms.views import PicklistRefresh
from .models import (AuditRun, AuditRunItem, AuditDetail,
                     AUDIT_DETAIL_STATUS_CHOICES, AUDIT_RUN_STATUS_CHOICES, AUDIT_INVENTORY_CHOICES,
                     AUDIT_TYPE_CHOICES, AUDIT_STATUS_CHOICES, AuditTicket, AUDIT_TICKET_STATUS_CHOICES, AuditProduct,
                     AUDIT_PRODUCT_STATUS, AUDIT_DETAIL_STATE_CHOICES, AuditCancelledPicklist, AuditTicketManual
                     )
from services.models import WarehouseInventoryHistoric, BinInventoryHistoric, InventoryArchiveMaster
from wms.models import WarehouseInventory, WarehouseInternalInventoryChange, InventoryType, InventoryState, \
    BinInventory, BinInternalInventoryChange, Putaway, OrderReserveRelease, Pickup, PickupBinInventory
from products.models import Product
import datetime

from .serializers import WarehouseInventoryTransactionSerializer, WarehouseInventorySerializer, \
    BinInventoryTransactionSerializer, BinInventorySerializer, PickupBlockedQuantitySerializer
from .utils import get_es_status, get_products_by_audit

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


def bin_transaction_type_switch(tr_type):
    tr_type_in_out = {
        'audit_adjustment': 1,
        'put_away_type': 1,
        'pickup_created': -1,
        'pickup_complete': 1,
        'stock_correction_in_type': 1,
        'stock_correction_out_type': -1
    }
    return tr_type_in_out.get(tr_type, 1)


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

    for item in last_day_inventory:
        inventory_calculated[item['sku_id']][item['batch_id']][item['bin_id']][item['inventory_type_id']] = item[
            'quantity']

    last_day_transactions = BinInternalInventoryChange.objects.filter(warehouse=audit_run.warehouse,
                                                                      created_at__gte=last_archived.created_at,
                                                                      created_at__lte=audit_started)

    for tr in last_day_transactions:
        if isinstance(inventory_calculated[tr.sku_id][tr.batch_id][tr.final_bin_id][tr.final_inventory_type_id], dict):
            inventory_calculated[tr.sku_id][tr.batch_id][tr.final_bin_id][tr.final_inventory_type_id] = 0
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
                                                     status__in=['pickup_creation','pickup_assigned'])\
                                             .values('sku_id').annotate(qty=Sum('quantity'))

    pickup_dict = {g['sku_id']: g['qty'] for g in pickup_blocked_inventory}
    pickup_cancelled_inventory = Putaway.objects.filter(status__in=['pickup_cancelled'],
                                                       putaway_quantity=0)\
                                               .values('sku_id').annotate(qty=Sum('quantity'))

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
    audit_started = audit_run.created_at
    prev_day = audit_started.date() - datetime.timedelta(1)
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


def start_automated_inventory_audit():
    audits_to_perform = AuditDetail.objects.filter(audit_type=AUDIT_TYPE_CHOICES.AUTOMATED,
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
        # es_product_status = get_es_status(product_list, warehouse)
        for p in product_list:
            update_product_es.delay(warehouse.id, p.id, status=False)
            # AuditProduct.objects.update_or_create(audit=audit, warehouse=warehouse, sku=p,
            #                                       defaults={'status': AUDIT_PRODUCT_STATUS.BLOCKED,
            #                                                 'es_status': es_product_status[p.id]})
            AuditProduct.objects.update_or_create(audit=audit, warehouse=warehouse, sku=p,
                                                  defaults={'status': AUDIT_PRODUCT_STATUS.BLOCKED})

    @staticmethod
    def unblock_product_after_audit(audit, product, warehouse):
        audit_product = AuditProduct.objects.filter(audit=audit, warehouse=warehouse, sku=product).last()
        if audit_product:
            audit_product.status = AUDIT_PRODUCT_STATUS.RELEASED
            audit_product.save()
        is_products_still_blocked = AuditProduct.objects.filter(warehouse=warehouse, sku=product,
                                                                status=AUDIT_PRODUCT_STATUS.BLOCKED).exists()
        if not is_products_still_blocked:
            update_product_es.delay(warehouse.id, product.id, status=True)


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
    orders_to_generate_picklists = AuditCancelledPicklist.objects.filter(audit=audit_id, is_picklist_refreshed=False)
    for o in orders_to_generate_picklists:
        order = Order.objects.filter(order_no=o.order_no).last()
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
            info_logger.error('generate_pick_list|Exception while generating picklist for order {}'.format(o))


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


def get_existing_audit_for_product(warehouse, sku):
    return sku.audit_product_mapping.filter(warehouse=warehouse,
                                            state__in=[AUDIT_DETAIL_STATE_CHOICES.CREATED,
                                                       AUDIT_DETAIL_STATE_CHOICES.INITIATED]).order_by('pk')


def get_existing_audit_for_bin(warehouse, bin):
    return bin.audit_bin_mapping.filter(warehouse=warehouse,
                                        state__in=[AUDIT_DETAIL_STATE_CHOICES.CREATED,
                                                   AUDIT_DETAIL_STATE_CHOICES.INITIATED]).order_by('pk')
