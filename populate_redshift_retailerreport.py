import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()

from services.views import RetailerProfileReport
from services.models import RetailerReports

def populate_retailer(shop_id):
    retailer_report = RetailerProfileReport()
    retailer_report.get_retailer_report(shop_id)
    return "done"
if __name__=='__main__':
  shop_id=sys.argv[1]
  populate_retailer(shop_id)