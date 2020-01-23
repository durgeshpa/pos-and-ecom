import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()

from services.views import GRNReport
from services.models import GRNReports

def populate_grn(shop_id,start_date):
    grn_report = GRNReport()
    grn_report.get_grn_report(shop_id,start_date,None)
    return "done"
if __name__=='__main__':
  shop_id=sys.argv[1]
  start_date=sys.argv[2]
  populate_grn(shop_id,start_date)