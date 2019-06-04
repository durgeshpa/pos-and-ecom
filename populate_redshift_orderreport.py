import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()

from services.views import OrderReport
from services.models import OrderReports

def populate_order(shop_id):
    order_report = OrderReport()
    order_report.get_order_report(shop_id,None,None)
    return "done"
if __name__=='__main__':
  shop_id=sys.argv[1]
  populate_order(shop_id)
