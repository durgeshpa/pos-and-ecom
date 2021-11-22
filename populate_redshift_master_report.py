import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()

from services.views import MasterReport
from services.models import MasterReports

def populate_product(shop_id):
    master_report = MasterReport()
    master_report.get_master_report(shop_id)
    return "done"
if __name__=='__main__':
  shop_id=sys.argv[1]
  populate_product(shop_id)