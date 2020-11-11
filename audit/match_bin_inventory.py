from audit.models import AuditDetail, AUDIT_TYPE_CHOICES, AuditRun, AUDIT_RUN_STATUS_CHOICES, AuditTicket, \
    AUDIT_INVENTORY_CHOICES
from wms.common_functions import WareHouseInternalInventoryChange
from wms.models import BinInternalInventoryChange

tr_add_type = 'audit_correction_add'
tr_deduct_type = 'audit_correction_deduct'
initial_inventory_type = None
initial_inventory_state = None



def correct_inventory_mismatches(warehouse, inventory_type):
    audit = AuditDetail.objects.filter(warehouse=warehouse,
                                       audit_type=AUDIT_TYPE_CHOICES.AUTOMATED,
                                       audit_inventory_type=inventory_type,
                                       is_historic=True).last()
    if not audit:
        return
    audit_run = AuditRun.objects.filter(audit=audit, status=AUDIT_RUN_STATUS_CHOICES.COMPLETED).last()
    if not audit_run:
        return
    tickets_qs = AuditTicket.objects.filter(audit_run=audit_run)
    for ticket in tickets_qs:
        qty_diff = ticket.qty_expected - ticket.qty_calculated
        tr_type = tr_add_type
        if qty_diff < 0:
            tr_type = tr_deduct_type
        if inventory_type == AUDIT_INVENTORY_CHOICES.BIN:
            BinInternalInventoryChange.objects.create(warehouse=warehouse, sku=ticket.sku,
                                                      batch_id=ticket.batch_id,
                                                      final_bin=ticket.bin,
                                                      initial_inventory_type=initial_inventory_type,
                                                      final_inventory_type=ticket.inventory_state,
                                                      transaction_type=tr_type,
                                                      transaction_id=ticket.id,
                                                      quantity=abs(qty_diff))

        if inventory_type == AUDIT_INVENTORY_CHOICES.WAREHOUSE:
            WareHouseInternalInventoryChange.create_warehouse_inventory_change(warehouse, ticket.sku,
                                                                               tr_type, ticket.id,
                                                                               initial_inventory_type,
                                                                               initial_inventory_state,
                                                                               ticket.inventory_type,
                                                                               ticket.inventory_state,
                                                                               abs(qty_diff))