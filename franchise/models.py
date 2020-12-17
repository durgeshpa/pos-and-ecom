# Create your models here.
from django.db.models.signals import post_save

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

post_save.connect(create_order_id, sender=Fbin)