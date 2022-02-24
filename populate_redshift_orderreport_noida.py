import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()

from services.views import OrderReportData
from services.models import OrderDetailReportsData

def populate_order(shop_id,start_date=None, end_date=None):
    order_report = OrderReportData()
    order_report.get_order_report(shop_id,start_date,end_date)
    return "done"
if __name__=='__main__':
  shop_id=sys.argv[1]
  start_date=sys.argv[2]
  end_date = sys.argv[3]
  populate_order(shop_id, start_date, end_date)
