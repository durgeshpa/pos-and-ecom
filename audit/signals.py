from django.db import transaction
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from audit.models import AuditDetail, AUDIT_RUN_TYPE_CHOICES, AUDIT_DETAIL_STATUS_CHOICES, AUDIT_DETAIL_STATE_CHOICES, \
    AuditTicketManual, AUDIT_TICKET_STATUS_CHOICES, AUDIT_LEVEL_CHOICES
from audit.utils import get_next_audit_no
from audit.views import BlockUnblockProduct
from franchise.models import Faudit
from wms.models import PickupBinInventory


@receiver(post_save, sender=AuditDetail)
def save_audit_no(sender, instance=None, created=False, **kwargs):
    if created:
        with transaction.atomic():
            if instance.audit_run_type == AUDIT_RUN_TYPE_CHOICES.AUTOMATED:
                audit_no = 'AA_'
            elif instance.audit_run_type == AUDIT_RUN_TYPE_CHOICES.MANUAL:
                audit_no = 'MA_'
                if instance.audit_level == AUDIT_LEVEL_CHOICES.BIN:
                    audit_no += 'B'
                elif instance.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
                    audit_no += 'P'
            next_audit_no = get_next_audit_no(instance)
            audit_no += str(next_audit_no)
            instance.audit_no = audit_no
            if instance.pbi:
                pbi_obj = PickupBinInventory.objects.filter(id=instance.pbi).last()
                pbi_obj.audit_no = instance.audit_no
                pbi_obj.save()
            instance.save()

# Faudit proxy model for AuditDetail - Signals need to be connected separately (again) for proxy model (if required)
post_save.connect(save_audit_no, sender=Faudit)


@receiver(post_save, sender=AuditDetail)
def enable_disable_audit_product_on_save(sender, instance=None, created=False, **kwargs):
    if instance.audit_run_type == AUDIT_RUN_TYPE_CHOICES.AUTOMATED:
        return
    if instance.status == AUDIT_DETAIL_STATUS_CHOICES.INACTIVE:
        BlockUnblockProduct.enable_products(instance)
        return
    if instance.state == AUDIT_DETAIL_STATE_CHOICES.CREATED:
        BlockUnblockProduct.disable_products(instance)

# Faudit proxy model for AuditDetail - Signals need to be connected separately (again) for proxy model (if required)
post_save.connect(enable_disable_audit_product_on_save, sender=Faudit)


def disable_bin_audit_products(sender, instance, action, *args, **kwargs):
    if action != 'post_add':
        return
    if instance.audit_run_type == AUDIT_RUN_TYPE_CHOICES.AUTOMATED:
        return
    if instance.status == AUDIT_DETAIL_STATUS_CHOICES.INACTIVE:
        return
    BlockUnblockProduct.disable_products(instance)


m2m_changed.connect(disable_bin_audit_products, sender=AuditDetail.bin.through)
m2m_changed.connect(disable_bin_audit_products, sender=AuditDetail.sku.through)
# Faudit proxy model for AuditDetail - Signals need to be connected separately (again) for proxy model (if required)
m2m_changed.connect(disable_bin_audit_products, sender=Faudit.bin.through)
m2m_changed.connect(disable_bin_audit_products, sender=Faudit.sku.through)


@receiver(post_save, sender=AuditTicketManual)
def update_audit_ticket(sender, instance=None, created=False, **kwargs):
    if instance.status == AUDIT_TICKET_STATUS_CHOICES.CLOSED:
        open_ticket_count = AuditTicketManual.objects.filter(audit_run=instance.audit_run,
                                                             status=AUDIT_TICKET_STATUS_CHOICES.OPEN).count()
        if open_ticket_count == 0:
            audit = AuditDetail.objects.filter(id=instance.audit_run.audit_id).last()
            if audit:
                audit.state = AUDIT_DETAIL_STATE_CHOICES.TICKET_CLOSED
                audit.save()
