import logging

from audit.models import AuditDetail, AUDIT_RUN_TYPE_CHOICES, AUDIT_DETAIL_STATE_CHOICES, AuditCancelledPicklist, \
    AuditProduct, AUDIT_PRODUCT_STATUS
from audit.views import update_audit_status_by_audit, create_audit_tickets_by_audit, create_pick_list_by_audit, \
    BlockUnblockProduct

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