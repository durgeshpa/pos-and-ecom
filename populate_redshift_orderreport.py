import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()

from services.views import OrderReport
from services.models import OrderReports

def populate_order(shop_id,start_date):
    order_report = OrderReport()
    order_report.get_order_report(shop_id,start_date,None)
    return "done"
if __name__=='__main__':
  shop_id=sys.argv[1]
  start_date=sys.argv[2]
  populate_order(shop_id,start_date)
