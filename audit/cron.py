import logging

from audit.models import AuditDetail, AUDIT_TYPE_CHOICES, AUDIT_DETAIL_STATE_CHOICES
from audit.views import update_audit_status_by_audit, create_audit_tickets_by_audit, create_pick_list_by_audit

cron_logger = logging.getLogger('cron_log')


def update_audit_status_cron():
    cron_logger.info('update_audit_status|started')
    audit_id_list = AuditDetail.objects.filter(audit_type=AUDIT_TYPE_CHOICES.MANUAL,
                                               state=AUDIT_DETAIL_STATE_CHOICES.ENDED).values_list('pk', flat=True)
    cron_logger.info('update_audit_status| audit count {}'.format(len(audit_id_list)))
    for audit_id in audit_id_list:
        update_audit_status_by_audit(audit_id)
        cron_logger.info('update_audit_status|audit state updated | audit {}, state'.format(audit_id))
    cron_logger.info('update_audit_status|completed')


def create_audit_tickets_cron():
    cron_logger.info('create_audit_tickets|started')
    audit_id_list = AuditDetail.objects.filter(audit_type=AUDIT_TYPE_CHOICES.MANUAL,
                                               state=AUDIT_DETAIL_STATE_CHOICES.FAIL).values_list('pk', flat=True)
    cron_logger.info('create_audit_tickets|failed audit count {}'.format(len(audit_id_list)))
    for audit_id in audit_id_list:
        create_audit_tickets_by_audit(audit_id)
        cron_logger.info('create_audit_tickets| audit ticket created | audit {}'.format(audit_id))
    cron_logger.info('create_audit_tickets|completed')

def create_picklist_cron():
    cron_logger.info('create_picklist_cron|started')
    audit_id_list = AuditDetail.objects.filter(audit_type=AUDIT_TYPE_CHOICES.MANUAL,
                                               state__in=[AUDIT_DETAIL_STATE_CHOICES.FAIL,
                                                          AUDIT_DETAIL_STATE_CHOICES.TICKET_RAISED],
                                               is_picklist_refreshed=False)\
                                       .values_list('pk', flat=True)
    cron_logger.info('create_picklist_cron| Audit count to generate picklist for {}'.format(len(audit_id_list)))
    for audit_id in audit_id_list:
        create_pick_list_by_audit(audit_id)
        cron_logger.info('create_picklist_cron| picklist generated | audit {}'.format(audit_id))
    cron_logger.info('create_audit_tickets|completed')