import logging

from celery.task import task

from audit.models import AuditRun, AuditRunItem, AUDIT_DETAIL_STATE_CHOICES, AuditDetail, AuditCancelledPicklist
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
    orders_to_generate_picklists = AuditCancelledPicklist.object.filter(audit_id=audit_id, is_picklist_refreshed=False)\
                                                                .values_list('order_no', flat=True)
    for o in orders_to_generate_picklists:
        try:
            PicklistRefresh.create_picklist_by_order(o)
        except Exception as e:
            info_logger.error(e)
            info_logger.error('task|generate_pick_list|Exception while generating picklist for order {}'.format(o))
    info_logger.info('task | generate_pick_list | completed | audit no {}'.format(audit_id))



