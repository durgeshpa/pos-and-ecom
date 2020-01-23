import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()

from services.views import CategoryProductReport
from services.models import CategoryProductReports

def populate_category_product():
    cat_prod_report = CategoryProductReport()
    cat_prod_report.get_category_product_report(None)
    return "done"
if __name__=='__main__':
  populate_category_product()
