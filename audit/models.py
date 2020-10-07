from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from model_utils import Choices

from accounts.middlewares import get_current_user
from services.models import InventoryArchiveMaster
from shops.models import Shop
from categories.models import Category
from wms.models import Bin, InventoryState, InventoryType
from django.contrib.auth import get_user_model
from products.models import Product

# Create your models here.

AUDIT_DETAIL_STATUS_CHOICES = Choices((0, 'INACTIVE', 'inactive'), (1, 'ACTIVE', 'active'))
AUDIT_DETAIL_STATE_CHOICES = Choices((1, 'CREATED', 'created'), (2, 'INITIATED', 'initiated'),
                                     (3, 'PASS', 'pass'), (4, 'FAIL', 'fail'),
                                     (5, 'TICKET_RAISED', 'ticket_raised'),(6, 'TICKET_CLOSED', 'ticket_closed'))
AUDIT_INVENTORY_CHOICES = Choices((1, 'WAREHOUSE', 'warehouse'), (2, 'BIN', 'bin'), (3, 'INTEGRATED', 'bin-warehouse'),
                                  (4, 'DAILY_OPERATIONS', 'daily operations'))
AUDIT_TYPE_CHOICES = Choices((0, 'MANUAL', 'manual'),  #(1, 'SCHEDULED', 'scheduled'),
                             (2, 'AUTOMATED', 'automated'))
AUDIT_RUN_STATUS_CHOICES = Choices((0, 'IN_PROGRESS', 'in_progress'), (1, 'ABORTED', 'aborted'),
                                   (2, 'COMPLETED', 'completed'))
AUDIT_STATUS_CHOICES = Choices((0, 'DIRTY', 'dirty'), (1, 'CLEAN', 'clean'))
AUDIT_TICKET_STATUS_CHOICES = Choices((0, 'OPENED', 'opened'), (1, 'ASSIGNED', 'assigned'), (2, 'CLOSED', 'closed'))
AUDIT_LEVEL_CHOICES = Choices((0, 'BIN', 'bin'), (1, 'PRODUCT', 'product'))


class BaseTimestampModel(models.Model):
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)

    class Meta:
        abstract = True


class AuditDetail(BaseTimestampModel):
    # audit_no = models.CharField(max_length=10)
    audit_type = models.PositiveSmallIntegerField(choices=AUDIT_TYPE_CHOICES)
    audit_inventory_type = models.PositiveSmallIntegerField(choices=AUDIT_INVENTORY_CHOICES, null=True, blank=True,)
    audit_level = models.PositiveSmallIntegerField(choices=AUDIT_LEVEL_CHOICES, null=True, blank=True,)
    warehouse = models.ForeignKey(Shop, null=False, blank=False, on_delete=models.DO_NOTHING)
    bin = models.ManyToManyField(Bin, null=True, blank=True, related_name='audit_bin_mapping')
    sku = models.ManyToManyField(Product, null=True, blank=True, related_name='audit_product_mapping')
    status = models.PositiveSmallIntegerField(choices=AUDIT_DETAIL_STATUS_CHOICES)
    state = models.PositiveSmallIntegerField(choices=AUDIT_DETAIL_STATE_CHOICES,
                                             default=AUDIT_DETAIL_STATE_CHOICES.CREATED)
    user = models.ForeignKey(get_user_model(), related_name='audits_created', on_delete=models.DO_NOTHING)
    auditor = models.ForeignKey(get_user_model(), related_name='audits_assigned', null=True, on_delete=models.DO_NOTHING)

    def save(self, *args, **kwargs):
        if not self.id:
            self.user = get_current_user()
        super(AuditDetail, self).save(*args, **kwargs)

    def __str__(self):
        return self.id

    class Meta:
        db_table = "wms_audit_details"
        verbose_name_plural = "Audit Details"

#
# @receiver(post_save, sender=AuditDetail)
# def create_audit_no(sender, instance=None, created=False, **kwargs):
#     if created:
#         audit_no = "A"
#         if instance.audit_type == AUDIT_TYPE_CHOICES.MANUAL:
#             audit_no = audit_no + 'M'
#             if instance.audit_level == AUDIT_LEVEL_CHOICES.BIN:
#                 audit_no = audit_no + 'B'
#             elif instance.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
#                 audit_no = audit_no + 'P'
#         elif instance.audit_type == AUDIT_TYPE_CHOICES.AUTOMATED:
#             audit_no = audit_no + 'A'
#             if instance.audit_inventory_type == AUDIT_INVENTORY_CHOICES.BIN:
#                 audit_no = audit_no + 'B'
#             elif instance.audit_inventory_type == AUDIT_INVENTORY_CHOICES.WAREHOUSE:
#                 audit_no = audit_no + 'W'
#             elif instance.audit_inventory_type == AUDIT_INVENTORY_CHOICES.INTEGRATED:
#                 audit_no = audit_no + 'I'
#             elif instance.audit_inventory_type == AUDIT_INVENTORY_CHOICES.DAILY_OPERATIONS:
#                 audit_no = audit_no + 'O'
#         audit_no = audit_no + str(instance.id)
#         instance.audit_no = audit_no
#         instance.save()


class AuditRun(BaseTimestampModel):
    warehouse = models.ForeignKey(Shop, null=False, blank=False, on_delete=models.DO_NOTHING)
    audit = models.ForeignKey(AuditDetail, null=False, blank=False, on_delete=models.CASCADE)
    archive_entry = models.ForeignKey(InventoryArchiveMaster, null=True, on_delete=models.DO_NOTHING)
    status = models.PositiveSmallIntegerField(choices=AUDIT_RUN_STATUS_CHOICES)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "wms_audit_run_log"
        verbose_name_plural = "Audits Performed"


class AuditRunItem(BaseTimestampModel):
    warehouse = models.ForeignKey(Shop, null=False, blank=False, on_delete=models.DO_NOTHING)
    audit_run = models.ForeignKey(AuditRun, null=False, blank=False, on_delete=models.CASCADE)
    sku = models.ForeignKey(Product, null=True, blank=True, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    bin = models.ForeignKey(Bin, null=True, blank=True, on_delete=models.DO_NOTHING)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    inventory_state = models.ForeignKey(InventoryState, null=True, blank=True, on_delete=models.DO_NOTHING)
    qty_expected = models.PositiveIntegerField()
    qty_calculated = models.PositiveIntegerField()
    status = models.PositiveSmallIntegerField(choices=AUDIT_STATUS_CHOICES)

    class Meta:
        db_table = "wms_audit_run_items"


class AuditTicket(BaseTimestampModel):
    QTY_TYPE_IDENTIFIER = Choices((0, 'BIN', 'bin'),
                                  (1, 'BIN_CALCULATED', 'bin-calculated'),
                                  (2, 'WAREHOUSE', 'warehouse'),
                                  (3, 'WAREHOUSE_CALCULATED', 'warehouse-calculated'))
    warehouse = models.ForeignKey(Shop, null=False, on_delete=models.DO_NOTHING)
    # audit_type = models.PositiveSmallIntegerField(choices=AUDIT_RUN_TYPE_CHOICES)
    # audit_inventory_type = models.PositiveSmallIntegerField(choices=AUDIT_INVENTORY_CHOICES)
    audit_run = models.ForeignKey(AuditRun, null=False, on_delete=models.CASCADE)
    sku = models.ForeignKey(Product, null=False, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True)
    bin = models.ForeignKey(Bin, null=True, on_delete=models.DO_NOTHING)
    inventory_type = models.ForeignKey(InventoryType, null=True, on_delete=models.DO_NOTHING)
    inventory_state = models.ForeignKey(InventoryState, null=True, on_delete=models.DO_NOTHING)
    qty_expected_type = models.PositiveIntegerField(choices=QTY_TYPE_IDENTIFIER)
    qty_calculated_type = models.PositiveIntegerField(choices=QTY_TYPE_IDENTIFIER)
    qty_expected = models.PositiveIntegerField()
    qty_calculated = models.PositiveIntegerField()
    status = models.PositiveSmallIntegerField(choices=AUDIT_TICKET_STATUS_CHOICES)
    assigned_user = models.ForeignKey(get_user_model(), related_name='audit_tickets_assigned',
                                      null=True, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "wms_audit_tickets"

    def audit_inventory_type(self):
        return AUDIT_INVENTORY_CHOICES[self.audit_run.audit.audit_inventory_type]

    def audit_type(self):
        return AUDIT_TYPE_CHOICES[self.audit_run.audit.audit_type]

#
# class AuditTicketHistory(models.Model):
#     audit_ticket = models.ForeignKey(AuditTicket, null=False, on_delete=models.CASCADE)
#     comment = models.CharField(max_length=255, null=False, blank=False)
#     assigned_to = models.PositiveSmallIntegerField(null=True)
#     user = models.ForeignKey(get_user_model(), related_name='audit_ticket_comments', null=True, on_delete=models.DO_NOTHING)
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     class Meta:
#         db_table = "wms_audit_tickets_history"
