
from django.db import models
from model_utils import Choices

from shops.models import Shop
from categories.models import Category
from wms.models import Bin, InventoryState, InventoryType
from django.contrib.auth import get_user_model
from products.models import Product
# Create your models here.

AUDIT_DETAIL_STATUS_CHOICES = Choices((0, 'INACTIVE', 'inactive'), (1, 'ACTIVE', 'active'))
AUDIT_INVENTORY_CHOICES = Choices((1, 'WAREHOUSE', 'warehouse'), (2, 'BIN', 'bin'), (3, 'INTEGRATED', 'bin-warehouse'))
AUDIT_SCHEDULE_STATUS_CHOICES = Choices((0, 'CREATED', 'created'), (1, 'ACTIVE', 'active'), (2, 'QUEUED', 'queued'), (3, 'DISABLED', 'disabled'))
AUDIT_RUN_TYPE_CHOICES = Choices((0, 'MANUAL', 'manual'), (1, 'SCHEDULED', 'scheduled'), (2, 'AUTOMATED', 'automated'))
AUDIT_RUN_STATUS_CHOICES = Choices((0, 'IN_PROGRESS', 'in_progress'), (1, 'ABORTED', 'aborted'), (2, 'COMPLETED', 'completed'))
AUDIT_STATUS_CHOICES = Choices((0, 'DIRTY', 'dirty'), (1, 'CLEAN', 'clean'))


class AuditDetails(models.Model):
    audit_type = models.PositiveSmallIntegerField(choices=AUDIT_RUN_TYPE_CHOICES)
    audit_inventory_type = models.PositiveSmallIntegerField(choices=AUDIT_INVENTORY_CHOICES)
    warehouse = models.ForeignKey(Shop, null=False, blank=False, on_delete=models.DO_NOTHING)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    bin = models.ForeignKey(Bin, null=True, blank=True, on_delete=models.DO_NOTHING)
    status = models.PositiveSmallIntegerField(choices=AUDIT_DETAIL_STATUS_CHOICES)
    user = models.ForeignKey(get_user_model(), related_name='created_by', on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wms_audit_details"


class AuditSchedule(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    audit = models.ForeignKey(AuditDetails, null=False, blank=False, on_delete=models.CASCADE)
    user_id = models.ForeignKey(get_user_model(), related_name='scheduled_by', on_delete=models.DO_NOTHING)
    status = models.PositiveSmallIntegerField(choices=AUDIT_SCHEDULE_STATUS_CHOICES)
    scheduled_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wms_audit_schedule"


class AuditRun(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    audit = models.ForeignKey(AuditDetails, null=False, blank=False, on_delete=models.CASCADE)
    schedule = models.ForeignKey(AuditSchedule, null=True, blank=True, on_delete=models.DO_NOTHING)
    status = models.PositiveSmallIntegerField(choices=AUDIT_RUN_STATUS_CHOICES)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wms_audit_run_log"


class AuditRunItems(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    audit_run = models.ForeignKey(AuditRun, null=False, blank=False, on_delete=models.CASCADE)
    sku = models.ForeignKey(Product, null=True, blank=True, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    bin = models.ForeignKey(Bin, null=True, blank=True, on_delete=models.DO_NOTHING)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    inventory_state = models.ForeignKey(InventoryState, null=True, blank=True, on_delete=models.DO_NOTHING)
    qty_expected = models.PositiveIntegerField()
    qty_calculated = models.PositiveIntegerField()
    status = models.PositiveSmallIntegerField(choices=AUDIT_STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wms_audit_run_items"
