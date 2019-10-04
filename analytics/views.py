from django.shortcuts import render

# Create your views here.
from services.views import CategoryProductReport
from services.views import GRNReport
from services.views import MasterReport
from services.views import OrderReport

def populate_category_product():
    cat_prod_report = CategoryProductReport()
    cat_prod_report.get_category_product_report(None)
    return "done"

def populate_grn(shop_id,start_date):
    grn_report = GRNReport()
    grn_report.get_grn_report(shop_id,start_date,None)
    return "done"

def populate_product(shop_id):
    master_report = MasterReport()
    master_report.get_master_report(shop_id)
    return "done"

def populate_order(shop_id,start_date):
    order_report = OrderReport()
    order_report.get_order_report(shop_id,start_date,None)
    return "done"