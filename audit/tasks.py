import logging

from celery.task import task
from audit.views import create_pick_list_by_audit, create_audit_tickets_by_audit, update_audit_status_by_audit

info_logger = logging.getLogger('file-info')

@task
def update_audit_status(audit_id):
    info_logger.info('task |update_audit_status| audit no {}'.format(audit_id))
    update_audit_status_by_audit(audit_id)
    info_logger.info('task |update_audit_status| audit no {} updated'.format([audit_id]))


@task
def generate_pick_list(audit_id):
    info_logger.info('task |generate_pick_list| started | audit no {}'.format(audit_id))
    create_pick_list_by_audit(audit_id)
    info_logger.info('task | generate_pick_list | completed | audit no {}'.format(audit_id))


@task
def create_audit_tickets(audit_id):
    info_logger.info('tasks|create_audit_tickets|started for audit {}'.format(audit_id))
    create_audit_tickets_by_audit(audit_id)
    info_logger.info('tasks|create_audit_tickets|completed for audit {}'.format(audit_id))

