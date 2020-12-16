# Create your models here.

from wms.models import Bin
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