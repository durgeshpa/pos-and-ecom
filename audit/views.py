from collections import defaultdict

from django.http import HttpResponse
from django.shortcuts import render
import logging
from shops.models import Shop
from .models import (AuditRun, AuditRunItems, AuditDetails,
                     AUDIT_DETAIL_STATUS_CHOICES, AUDIT_RUN_STATUS_CHOICES, AUDIT_INVENTORY_CHOICES,
                     AUDIT_RUN_TYPE_CHOICES, AUDIT_STATUS_CHOICES)
from services.models import WarehouseInventoryHistoric, BinInventoryHistoric
from wms.models import WarehouseInventory, WarehouseInternalInventoryChange, InventoryType, InventoryState, \
    BinInventory, BinInternalInventoryChange
from products.models import Product
import datetime

info_logger = logging.getLogger('file-info')


def index(request):
    return HttpResponse(start_automated_inventory_audit())


def initialize_dict():
    nested_dict = lambda: defaultdict(nested_dict)
    sku_dict = nested_dict()
    return sku_dict


def run_warehouse_level_audit(audit_run):
    audit_started = audit_run.started_at
    prev_day = audit_started.date() - datetime.timedelta(1)
    inventory_calculated = initialize_dict()

    current_inventory = WarehouseInventory.objects.filter(
        warehouse=audit_run.warehouse).values('sku_id', 'inventory_type_id', 'inventory_state_id', 'quantity')

    last_day_inventory = WarehouseInventoryHistoric.objects.filter(warehouse=audit_run.warehouse,
                                                                   archived_at__gte=prev_day,
                                                                   archived_at__lte=audit_started).values('sku_id',
                                                                                                          'inventory_type_id',
                                                                                                          'inventory_state_id',
                                                                                                          'quantity')
    info_logger.debug(
        "Audit run {} : Fetched last days snapshot, total rows {}".format(audit_run, last_day_inventory.count()))
    for item in last_day_inventory:
        inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']] = item['quantity']

    last_day_transactions = WarehouseInternalInventoryChange.objects.filter(warehouse=audit_run.warehouse,
                                                                            created_at__gte=prev_day,
                                                                            created_at__lte=audit_started)

    info_logger.debug(
        "Audit run {} : Fetched last days transactions, total rows {}".format(audit_run, last_day_transactions.count()))

    for tr in last_day_transactions:
        if isinstance(inventory_calculated[tr.sku.product_sku][tr.initial_type_id][tr.initial_stage_id], dict):
            inventory_calculated[tr.sku.product_sku][tr.initial_type_id][tr.initial_stage_id] = 0

        if isinstance(inventory_calculated[tr.sku.product_sku][tr.final_type_id][tr.final_stage_id], dict):
            inventory_calculated[tr.sku.product_sku][tr.final_type_id][tr.final_stage_id] = 0

        inventory_calculated[tr.sku.product_sku][tr.initial_type_id][tr.initial_stage_id] -= tr.quantity
        inventory_calculated[tr.sku.product_sku][tr.final_type_id][tr.final_stage_id] += tr.quantity

    for item in current_inventory:
        qty_calculated = inventory_calculated[item['sku_id']][item['inventory_type_id']][item['inventory_state_id']]
        status = AUDIT_RUN_STATUS_CHOICES.DIRTY
        if item['quantity'] == qty_calculated:
            status = AUDIT_RUN_STATUS_CHOICES.CLEAN
        AuditRunItems.objects.create(warehouse=audit_run.warehouse,
                                     audit_run=audit_run,
                                     sku_id=item['sku_id'],
                                     inventory_type_id=item['inventory_type_id'],
                                     inventory_state_id=item['inventory_state_id'],
                                     qty_expected=item['quantity'],
                                     qty_calculated=qty_calculated,
                                     status=status)


def run_bin_level_audit(audit_run):
    audit_started = audit_run.started_at
    prev_day = audit_started.date() - datetime.timedelta(1)
    inventory_calculated = initialize_dict()

    current_inventory = BinInventory.objects.filter(warehouse=audit_run.warehouse).values('sku_id', 'batch_id',
                                                                                          'bin_id', 'inventory_type_id',
                                                                                          'quantity')
    last_day_inventory = BinInventoryHistoric.objects.filter(warehouse=audit_run.warehouse,
                                                             archived_at__gte=prev_day,
                                                             archived_at__lte=audit_started).values('sku_id',
                                                                                                    'batch_id',
                                                                                                    'bin_id',
                                                                                                    'inventory_type_id',
                                                                                                    'quantity')
    for item in last_day_inventory:
        inventory_calculated[item['sku_id']][item['batch_id']][item['bin_id']][item['inventory_type_id']] = item[
            'quantity']

    last_day_transactions = BinInternalInventoryChange.objects.filter(warehouse=audit_run.warehouse,
                                                                      created_at__gte=prev_day,
                                                                      created_at__lte=audit_started)

    for tr in last_day_transactions:
        if isinstance(inventory_calculated[tr.sku][tr.batch_id][tr.initial_bin_id][tr.initial_type_id], dict):
            inventory_calculated[tr.sku][tr.batch_id][tr.initial_bin_id][tr.initial_type_id] = 0

        if isinstance(inventory_calculated[tr.sku][tr.batch_id][tr.final_bin_id][tr.final_type_id], dict):
            inventory_calculated[tr.sku][tr.batch_id][tr.final_bin_id][tr.final_type_id] = 0

        inventory_calculated[tr.sku][tr.batch_id][tr.initial_bin_id][tr.initial_type_id] -= tr.quantity
        inventory_calculated[tr.sku][tr.batch_id][tr.final_bin_id][tr.final_type_id] += tr.quantity

    for item in current_inventory:
        qty_calculated = inventory_calculated[item['sku_id']][item['batch_id']][item['bin_id']][
            item['inventory_type_id']]
        status = AUDIT_STATUS_CHOICES.DIRTY
        if item['quantity'] == qty_calculated:
            status = AUDIT_STATUS_CHOICES.CLEAN
        audit_run_item = AuditRunItems.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                                      sku_id=item['sku_id'],
                                                      batch_id=item['batch_id'],
                                                      bin_id=item['bin_id'],
                                                      inventory_type_id=item['inventory_type_id'],
                                                      qty_expected=item['quantity'],
                                                      qty_calculated=qty_calculated,
                                                      status=status)


def run_bin_warehouse_integrated_audit(audit_run):
    current_warehouse_inventory = WarehouseInventory.objects.filter(
        warehouse=audit_run.warehouse).values('sku_id', 'inventory_type_id', 'quantity')
    for item in current_warehouse_inventory:
        bin_quantity = BinInventory.available_qty_with_inventory_type(audit_run.warehouse.id,
                                                                      Product.objects.filter(
                                                                          product_sku=item['sku_id']).last().id,
                                                                      item['inventory_type_id'])
        status = AUDIT_STATUS_CHOICES.DIRTY
        if bin_quantity == item['quantity']:
            status = AUDIT_STATUS_CHOICES.CLEAN
        AuditRunItems.objects.create(warehouse=audit_run.warehouse, audit_run=audit_run,
                                     sku_id=item['sku_id'],
                                     inventory_type_id=item['inventory_type_id'],
                                     qty_expected=item['quantity'],
                                     qty_calculated=bin_quantity,
                                     status=status)


def run_audit(audit_run, inventory_choice):
    if inventory_choice == AUDIT_INVENTORY_CHOICES.WAREHOUSE:
        run_warehouse_level_audit(audit_run)
    if inventory_choice == AUDIT_INVENTORY_CHOICES.BIN:
        run_bin_level_audit(audit_run)
    if inventory_choice == AUDIT_INVENTORY_CHOICES.INTEGRATED:
        run_bin_warehouse_integrated_audit(audit_run)


def start_automated_inventory_audit():
    audits_to_perform = AuditDetails.objects.filter(audit_type=AUDIT_RUN_TYPE_CHOICES.AUTOMATED,
                                                    status=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE)
    for audit in audits_to_perform:
        audit_run = AuditRun.objects.filter(audit=audit, status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS)
        if audit_run:
            info_logger.debug("Audit run already in progress for AuditDetails {} ".format(audit))
            continue
        audit_run = AuditRun.objects.create(warehouse=audit.warehouse, audit=audit,
                                            status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS)
        info_logger.debug("Audit run started AuditDetails {} at {} ".format(audit, audit_run.started_at))
        try:
            run_audit(audit_run, audit.audit_inventory_type)
        except Exception as e:
            info_logger.error("Audit run aborted with Exception ")
            audit_run.status = AUDIT_RUN_STATUS_CHOICES.ABORTED
        else:
            audit_run.status = AUDIT_RUN_STATUS_CHOICES.COMPLETED
            audit_run.completed_at = datetime.datetime.now()
        info_logger.debug("Audit run completed AuditDetails {} at {} ".format(audit, audit_run.completed_at))
        audit_run.save()
