# Create your models here.
from django.db.models.signals import post_save
from django.db import models

from wms.models import Bin, create_order_id
from audit.models import AuditDetail

class Fbin(Bin):
    class Meta:
        proxy = True
        verbose_name = 'Bin'


class Faudit(AuditDetail):
    class Meta:
        proxy = True
        verbose_name = 'Audit'

def get_default_virtual_bin_id():
    return 'V2VZ01SR001-0001'

class FranchiseSales(models.Model):
    bl_id = models.CharField(max_length=255, unique=True, null=True)
    shop_name = models.CharField(max_length=255)
    invoice_date = models.DateTimeField()
    invoice_number = models.CharField(max_length=255)
    quantity = models.FloatField(default = 0, null=True, blank=True)
    amount = models.FloatField(default = 0, null=True, blank=True)
    category_name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=255)
    status = models.BooleanField(default=False)

# Fbin proxy model for Bin - Signals need to be connected separately (again) for proxy model (if required)
post_save.connect(create_order_id, sender=Fbin)