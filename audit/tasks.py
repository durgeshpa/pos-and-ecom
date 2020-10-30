import logging

from celery.task import task
from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from audit.models import AuditRunItem, AUDIT_DETAIL_STATE_CHOICES, AuditDetail, AuditCancelledPicklist \
    , AUDIT_TICKET_STATUS_CHOICES, AuditRun, AuditTicketManual
from retailer_to_sp.models import PickerDashboard, Order
from wms.models import InventoryType
from wms.views import PicklistRefresh

info_logger = logging.getLogger('file-info')

@task
def update_audit_status(audit_id):
    info_logger.info('task |update_audit_status| audit no {}'.format(audit_id))
    audit = AuditDetail.objects.get(pk=audit_id)
    audit_items = AuditRunItem.objects.filter(audit_run__audit=audit)
    audit_state = AUDIT_DETAIL_STATE_CHOICES.PASS
    for i in audit_items:
        if i.qty_expected != i.qty_calculated:
            audit_state = AUDIT_DETAIL_STATE_CHOICES.FAIL
            break
    audit.state = audit_state
    audit.save()
    info_logger.info('task |update_audit_status| audit status {}'.format(AUDIT_DETAIL_STATE_CHOICES[audit_state]))


@task
def generate_pick_list(audit_id):
    info_logger.info('task |generate_pick_list| started | audit no {}'.format(audit_id))
    orders_to_generate_picklists = AuditCancelledPicklist.objects.filter(audit_id=audit_id, is_picklist_refreshed=False)
    for o in orders_to_generate_picklists:
        order = Order.objects.filter(order_no=o.order_no)
        try:
            pd_obj = PickerDashboard.objects.filter(order=order,
                                                    picking_status__in=['picking_pending', 'picking_assigned'],
                                                    is_valid=False).last()
            if pd_obj is None:
                info_logger.info("Picker Dashboard object does not exists for order {}".format(order.order_no))
                continue
            with transaction.atomic():
                PicklistRefresh.create_picklist_by_order(o.order_no, pd_obj)
                o.is_picklist_refreshed = True
                o.save()
                pd_obj.is_valid = True
                pd_obj.refreshed_at = timezone.now()
                pd_obj.save()
        except Exception as e:
            info_logger.error(e)
            info_logger.error('task|generate_pick_list|Exception while generating picklist for order {}'.format(o))
    info_logger.info('task | generate_pick_list | completed | audit no {}'.format(audit_id))


@task
def create_audit_tickets(audit_id):
    info_logger.info('tasks|create_audit_tickets|started for audit {}'.format(audit_id))
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
        if not AuditTicketManual.objects.filter(audit_run=audit_run, bin=i.bin, sku=i.sku, batch_id=i.batch_id).exists():
            agg_qty = AuditRunItem.objects.filter(audit_run=audit_run, bin=i.bin, sku=i.sku, batch_id=i.batch_id)\
                                          .aggregate(n_phy=Sum('qty_calculated', filter=Q(inventory_type=type_normal)),
                                                     n_sys=Sum('qty_expected', filter=Q(inventory_type=type_normal)),
                                                     e_phy=Sum('qty_calculated', filter=Q(inventory_type=type_expired)),
                                                     e_sys=Sum('qty_expected', filter=Q(inventory_type=type_expired)),
                                                     d_phy=Sum('qty_calculated', filter=Q(inventory_type=type_damaged)),
                                                     d_sys=Sum('qty_expected', filter=Q(inventory_type=type_damaged)))

            ticket = AuditTicketManual.objects.create(warehouse=audit_run.warehouse,
                                                      audit_run=audit_run, bin=i.bin, sku=i.sku, batch_id=i.batch_id,
                                                      qty_normal_system=agg_qty['n_sys'],
                                                      qty_normal_actual=agg_qty['n_phy'],
                                                      qty_damaged_system=agg_qty['d_sys'],
                                                      qty_damaged_actual=agg_qty['d_phy'],
                                                      qty_expired_system=agg_qty['e_sys'],
                                                      qty_expired_actual=agg_qty['e_phy'],
                                                      status=AUDIT_TICKET_STATUS_CHOICES.OPENED)
            info_logger.info('tasks|create_audit_tickets|created for audit run {}, bin {}, batch {}'
                             .format(audit_run.id, i.bin_id, i.batch_id))
    audit.state = AUDIT_DETAIL_STATE_CHOICES.TICKET_RAISED
    audit.save()
    info_logger.info('tasks|create_audit_tickets|completed for audit {}'.format(audit_id))

