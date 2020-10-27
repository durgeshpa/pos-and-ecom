from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from audit.models import AuditDetail, AUDIT_TYPE_CHOICES, AUDIT_DETAIL_STATUS_CHOICES
from audit.views import BlockUnblockProduct


@receiver(post_save, sender=AuditDetail)
def enable_disable_audit_product_on_save(sender, instance=None, created=False, **kwargs):
    if instance.audit_type == AUDIT_TYPE_CHOICES.AUTOMATED:
        return
    if instance.status == AUDIT_DETAIL_STATUS_CHOICES.INACTIVE:
        BlockUnblockProduct.enable_products(instance)
        return
    # BlockUnblockProduct.disable_products(instance)


def disable_bin_audit_products(sender, instance, action, *args, **kwargs):
    if action != 'post_add':
        return
    if instance.audit_type == AUDIT_TYPE_CHOICES.AUTOMATED:
        return
    if instance.status == AUDIT_DETAIL_STATUS_CHOICES.INACTIVE:
        return
    BlockUnblockProduct.disable_products(instance)


m2m_changed.connect(disable_bin_audit_products, sender=AuditDetail.bin.through)
m2m_changed.connect(disable_bin_audit_products, sender=AuditDetail.sku.through)
