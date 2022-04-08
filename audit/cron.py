import logging

from audit.models import AUDIT_DETAIL_STATE_CHOICES, AuditProduct, AUDIT_PRODUCT_STATUS, AuditDetail, \
    AUDIT_RUN_TYPE_CHOICES
from audit.views import BlockUnblockProduct, create_audit_tickets_by_audit

cron_logger = logging.getLogger('cron_log')


def release_products_from_audit():
    cron_logger.info('release_products_from_audit|started')
    audit_product_list = AuditProduct.objects.filter(status=AUDIT_PRODUCT_STATUS.BLOCKED)\
                                             .exclude(audit__state__in=[AUDIT_DETAIL_STATE_CHOICES.CREATED,
                                                                        AUDIT_DETAIL_STATE_CHOICES.INITIATED])
    cron_logger.info('release_products_from_audit| product count {}'.format(len(audit_product_list)))
    for audit_product in audit_product_list:
        BlockUnblockProduct.unblock_product_after_audit(audit_product.audit,
                                                        audit_product.sku, audit_product.warehouse)
        cron_logger.info('release_products_from_audit| product unblocked | audit {}, SKU {}'
                         .format(audit_product.audit_id, audit_product.sku_id))
    cron_logger.info('release_products_from_audit|completed')


def create_audit_tickets_cron():
    cron_logger.info('create_audit_tickets|started')
    audit_id_list = AuditDetail.objects.filter(audit_run_type=AUDIT_RUN_TYPE_CHOICES.MANUAL,
                                               state=AUDIT_DETAIL_STATE_CHOICES.FAIL).values_list('pk', flat=True)
    cron_logger.info('create_audit_tickets|failed audit count {}'.format(len(audit_id_list)))
    for audit_id in audit_id_list:
        create_audit_tickets_by_audit(audit_id)
        cron_logger.info('create_audit_tickets| audit ticket created | audit {}'.format(audit_id))
    cron_logger.info('create_audit_tickets|completed')