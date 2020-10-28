import logging

from celery.task import task

from audit.models import AuditRun, AuditRunItem, AUDIT_DETAIL_STATE_CHOICES, AuditDetail, AuditCancelledPicklist
from wms.views import PicklistRefresh

info_logger = logging.getLogger('file-info')

@task
def update_audit_status(audit_id):
    info_logger.info('task |update_audit_status| audit no {}'.format(audit_id))
    audit = AuditDetail.objects.get(pk=audit_id)
    audit_run = AuditRun.objects.filter(audit=audit)
    audit_items = AuditRunItem.objects.filter(audit_run=audit_run)
    audit_state = AUDIT_DETAIL_STATE_CHOICES.PASS
    for i in audit_items:
        if i.expected_qty != i.calculated_qty:
            audit_state = AUDIT_DETAIL_STATE_CHOICES.FAIL
            break
    audit.update(audit_state)
    info_logger.info('task |update_audit_status| audit status {}'.format(AUDIT_DETAIL_STATE_CHOICES[audit_state]))


@task
def generate_pick_list(audit_id):
    info_logger.info('task |generate_pick_list| started | audit no {}'.format(audit_id))
    orders_to_generate_picklists = AuditCancelledPicklist.object.filter(audit_id=audit_id)\
                                                                .values_list('order_no', flat=True)
    try:
        PicklistRefresh.create_picklist_by_order(orders_to_generate_picklists)
    except Exception as e:
        info_logger.error(e)
    info_logger.info('task | generate_pick_list | completed | audit no {}'.format(audit_id))



