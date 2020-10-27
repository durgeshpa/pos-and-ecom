from celery.task import task

from audit.models import AuditRun, AuditRunItem, AUDIT_DETAIL_STATE_CHOICES, AuditDetail


@task
def update_audit_status(audit_id):
    audit = AuditDetail.objects.get(pk=audit_id)
    audit_run = AuditRun.objects.filter(audit=audit)
    audit_items = AuditRunItem.objects.filter(audit_run=audit_run)
    audit_state = AUDIT_DETAIL_STATE_CHOICES.PASS
    for i in audit_items:
        if i.expected_qty != i.calculated_qty:
            audit_state = AUDIT_DETAIL_STATE_CHOICES.FAIL
            break
    audit.update(audit_state)
