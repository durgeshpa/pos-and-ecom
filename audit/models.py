from django.db import models
from model_utils import Choices

from accounts.middlewares import get_current_user
from services.models import InventoryArchiveMaster
from shops.models import Shop
from wms.models import Bin, InventoryState, InventoryType
from django.contrib.auth import get_user_model
from products.models import Product

# Create your models here.

AUDIT_DETAIL_STATUS_CHOICES = Choices((0, 'INACTIVE', 'Inactive'), (1, 'ACTIVE', 'Active'))
AUDIT_DETAIL_STATE_CHOICES = Choices((1, 'CREATED', 'Created'), (2, 'INITIATED', 'Initiated'),(3, 'ENDED', 'Ended'),
                                     (4, 'PASS', 'Pass'), (5, 'FAIL', 'Fail'),
                                     (6, 'TICKET_RAISED', 'Ticket Raised'),(7, 'TICKET_CLOSED', 'Ticket Closed'))
AUDIT_INVENTORY_CHOICES = Choices((1, 'WAREHOUSE', 'warehouse'), (2, 'BIN', 'bin'), (3, 'INTEGRATED', 'bin-warehouse'),
                                  (4, 'DAILY_OPERATIONS', 'daily operations'))
AUDIT_RUN_TYPE_CHOICES = Choices((0, 'MANUAL', 'Manual'),  #(1, 'SCHEDULED', 'scheduled'),
                                 (2, 'AUTOMATED', 'Automated'))
AUDIT_RUN_STATUS_CHOICES = Choices((0, 'IN_PROGRESS', 'In Progress'), (1, 'ABORTED', 'Aborted'),
                                   (2, 'COMPLETED', 'Completed'))
AUDIT_STATUS_CHOICES = Choices((0, 'DIRTY', 'Dirty'), (1, 'CLEAN', 'Clean'))
AUDIT_TICKET_STATUS_CHOICES = Choices((0, 'OPEN', 'Open'), (1, 'ASSIGNED', 'Assigned'), (2, 'CLOSED', 'Closed'))
AUDIT_LEVEL_CHOICES = Choices((0, 'BIN', 'Bin Wise'), (1, 'PRODUCT', 'Product Wise'))
AUDIT_PRODUCT_STATUS = Choices((0, 'RELEASED', 'Released'), (1, 'BLOCKED', 'Blocked'), )


class BaseTimestampModel(models.Model):
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)

    class Meta:
        abstract = True

class AuditNumberGenerator(BaseTimestampModel):
    audit_run_type = models.PositiveSmallIntegerField(choices=AUDIT_RUN_TYPE_CHOICES)
    audit_level = models.PositiveSmallIntegerField(choices=AUDIT_LEVEL_CHOICES, null=True)
    current_number = models.IntegerField()

class AuditDetail(BaseTimestampModel):
    audit_no = models.CharField(max_length=10, null=True)
    audit_run_type = models.PositiveSmallIntegerField(choices=AUDIT_RUN_TYPE_CHOICES,
                                                      verbose_name='Audit Run Type')
    audit_inventory_type = models.PositiveSmallIntegerField(choices=AUDIT_INVENTORY_CHOICES, null=True,
                                                            blank=True,verbose_name='Audit Inventory Type')
    audit_level = models.PositiveSmallIntegerField(choices=AUDIT_LEVEL_CHOICES, null=True, blank=True,
                                                   verbose_name='Audit Type')
    warehouse = models.ForeignKey(Shop, null=False, blank=False, on_delete=models.DO_NOTHING)
    bin = models.ManyToManyField(Bin, null=True, blank=True, related_name='audit_bin_mapping')
    sku = models.ManyToManyField(Product, null=True, blank=True, related_name='audit_product_mapping')
    status = models.PositiveSmallIntegerField(choices=AUDIT_DETAIL_STATUS_CHOICES,
                                              default=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE, verbose_name='Audit Status')
    state = models.PositiveSmallIntegerField(choices=AUDIT_DETAIL_STATE_CHOICES,
                                             default=AUDIT_DETAIL_STATE_CHOICES.CREATED,
                                             verbose_name='Audit State')
    user = models.ForeignKey(get_user_model(), related_name='audits_created', on_delete=models.DO_NOTHING,
                             verbose_name='Created By')
    auditor = models.ForeignKey(get_user_model(), related_name='audits_assigned', null=True, on_delete=models.DO_NOTHING)
    is_historic = models.BooleanField(default=False)
    audit_from = models.DateField(null=True, blank=True, verbose_name='Start Audit From')
    pbi = models.PositiveIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.user = get_current_user()
        super(AuditDetail, self).save(*args, **kwargs)

    def __str__(self):
        return "Audit ID - {}".format(self.id)

    class Meta:
        db_table = "wms_audit_details"
        verbose_name_plural = "Audit Tasks"


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
    qty_calculated = models.IntegerField()
    status = models.PositiveSmallIntegerField(choices=AUDIT_STATUS_CHOICES)

    class Meta:
        db_table = "wms_audit_run_items"


class AuditTicket(BaseTimestampModel):
    QTY_TYPE_IDENTIFIER = Choices((0, 'BIN', 'bin'),
                                  (1, 'BIN_CALCULATED', 'bin-calculated'),
                                  (2, 'WAREHOUSE', 'warehouse'),
                                  (3, 'WAREHOUSE_CALCULATED', 'warehouse-calculated'))
    warehouse = models.ForeignKey(Shop, null=False, on_delete=models.DO_NOTHING)
    audit_run = models.ForeignKey(AuditRun, null=False, on_delete=models.CASCADE)
    sku = models.ForeignKey(Product, null=False, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True)
    bin = models.ForeignKey(Bin, null=True, on_delete=models.DO_NOTHING)
    inventory_type = models.ForeignKey(InventoryType, null=True, on_delete=models.DO_NOTHING)
    inventory_state = models.ForeignKey(InventoryState, null=True, on_delete=models.DO_NOTHING)
    qty_expected_type = models.PositiveIntegerField(choices=QTY_TYPE_IDENTIFIER)
    qty_calculated_type = models.PositiveIntegerField(choices=QTY_TYPE_IDENTIFIER)
    qty_expected = models.PositiveIntegerField()
    qty_calculated = models.IntegerField()
    status = models.PositiveSmallIntegerField(choices=AUDIT_TICKET_STATUS_CHOICES)
    assigned_user = models.ForeignKey(get_user_model(), related_name='+',
                                      null=True, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "wms_audit_tickets"
        verbose_name = "Automated Audit Ticket"
        verbose_name_plural = "Automated Audit Tickets"

    def audit_inventory_type(self):
        return AUDIT_INVENTORY_CHOICES[self.audit_run.audit.audit_inventory_type]

    def audit_run_type(self):
        return AUDIT_RUN_TYPE_CHOICES[self.audit_run.audit.audit_run_type]


class AuditProduct(BaseTimestampModel):
    audit = models.ForeignKey(AuditDetail, null=False, related_name='+', on_delete=models.DO_NOTHING)
    warehouse = models.ForeignKey(Shop, null=False, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, null=False, to_field='product_sku',related_name='rt_audit_sku', on_delete=models.DO_NOTHING)
    status = models.PositiveSmallIntegerField(choices=AUDIT_PRODUCT_STATUS)
    # es_status = models.BooleanField(default=False)

    class Meta:
        db_table = "wms_audit_products"


class AuditCancelledPicklist(BaseTimestampModel):
    audit = models.ForeignKey(AuditDetail, null=False, on_delete=models.DO_NOTHING, related_name='+')
    order_no = models.CharField(max_length=20, null=False)
    is_picklist_refreshed = models.BooleanField(default=False, verbose_name='Picklist Refreshed')

    class Meta:
        db_table = "wms_audit_cancelled_picklists"
        verbose_name = "Audit Cancelled Picklist"
        verbose_name_plural = "Audit Cancelled Picklists"


class AuditUpdatedPickup(BaseTimestampModel):
    audit = models.ForeignKey(AuditDetail, null=False, on_delete=models.DO_NOTHING, related_name='+')
    order_no = models.CharField(max_length=20, null=False)
    batch_id = models.CharField(max_length=50, null=False)
    bin = models.ForeignKey(Bin, null=False,  on_delete=models.DO_NOTHING, related_name='+')

    class Meta:
        db_table = "wms_audit_updated_pickups"
        verbose_name = "Audit Updated Pickup"
        verbose_name_plural = "Audit Updated Pickups"

class AuditTicketManual(BaseTimestampModel):
    warehouse = models.ForeignKey(Shop, null=False, related_name='+', on_delete=models.DO_NOTHING)
    audit_run = models.ForeignKey(AuditRun, null=False, on_delete=models.CASCADE)
    sku = models.ForeignKey(Product, null=False, to_field='product_sku', related_name='+', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True)
    bin = models.ForeignKey(Bin, null=True, on_delete=models.DO_NOTHING)
    qty_normal_system = models.PositiveIntegerField(verbose_name='Normal System Qty')
    qty_normal_actual = models.PositiveIntegerField(verbose_name='Normal Physical Qty')
    qty_damaged_system = models.PositiveIntegerField(verbose_name='Damaged System Qty')
    qty_damaged_actual = models.PositiveIntegerField(verbose_name='Damaged Physical Qty')
    qty_expired_system = models.PositiveIntegerField(verbose_name='Expired System Qty')
    qty_expired_actual = models.PositiveIntegerField(verbose_name='Expired Physical Qty')
    status = models.PositiveSmallIntegerField(choices=AUDIT_TICKET_STATUS_CHOICES)
    assigned_user = models.ForeignKey(get_user_model(),verbose_name='Assigned To', related_name='+',
                                      null=True, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "wms_audit_tickets_manual"
        verbose_name = "Manual Audit Ticket"
        verbose_name_plural = "Manual Audit Tickets"


class AuditedBinRecord(models.Model):
    audit = models.ForeignKey(AuditDetail, null=False, related_name='+', on_delete=models.DO_NOTHING)
    bin = models.ForeignKey(Bin, null=True, related_name='+', on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    class Meta:
        db_table = "wms_audit_bin_record"

class AuditedProductRecord(models.Model):
    audit = models.ForeignKey(AuditDetail, null=False, related_name='+', on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, null=False, to_field='product_sku', related_name='+', on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    class Meta:
        db_table = "wms_audit_product_record"