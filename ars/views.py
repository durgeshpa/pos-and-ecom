import datetime
import math

from django.db.models import Sum, Count, F, Q
from django.shortcuts import render

# Create your views here.
from global_config.views import get_config
from gram_to_brand.models import Cart
from products.models import ProductVendorMapping
from retailer_to_sp.models import Order
from services.models import WarehouseInventoryHistoric
from shops.models import ParentRetailerMapping
from wms.common_functions import get_inventory_in_stock
from wms.models import Putaway


def get_daily_average(warehouse, parent_product):
    rolling_avg_days = get_config('ROLLING_AVG_DAYS', 30)
    starting_avg_from = datetime.datetime.today().date() - datetime.timedelta(days=rolling_avg_days)
    avg_days = WarehouseInventoryHistoric.objects.filter(warehouse=warehouse,
                                                         sku__parent_product=parent_product, visible=True,
                                                         archived_at__gte=starting_avg_from)\
                                                 .values('sku__parent_product')\
                                                 .annotate(days=Count(distinct='sku__parent_product'))
    products_ordered = get_total_products_ordered(warehouse, parent_product, starting_avg_from)
    rolling_avg = products_ordered/avg_days
    return math.ceil(rolling_avg)

def get_inventory_in_process(warehouse, parent_product):
    gf_shop = ParentRetailerMapping.objects.filter(retailer_id=warehouse, status=True, parent__shop_type__shop_type='gf')
    inventory_in_process = Cart.objects.filter(gf_billing_address__shop_name=gf_shop,
                                               po_status__in=[Cart.OPEN, Cart.APPROVAL_AWAITED],
                                               cart_list__cart_product__parent_product=parent_product)\
                                       .values('cart_list__cart_product__parent_product')\
                                       .annotate(no_of_pieces=Sum('cart_list__cart_product__no_of_pieces'))['no_of_pieces']
    return inventory_in_process if inventory_in_process else 0


def get_inventory_pending_for_putaway(warehouse, parent_product):
    pending_putaway_qty = Putaway.objects.filter(~Q(quantity=F('putaway_quantity')), warehouse=warehouse,
                                                 sku__parent_product=parent_product)\
                                         .values('sku__parent_product')\
                                         .annotate(pending_qty=Sum('sku__parent_product'))['pending_qty']
    return pending_putaway_qty if pending_putaway_qty else 0


def get_demand_by_parent_product(parent_product):
    daily_average = get_daily_average(parent_product)
    current_inventory = get_inventory_in_stock(parent_product)
    inventory_in_process = get_inventory_in_process(parent_product)
    putaway_inventory = get_inventory_pending_for_putaway(parent_product)
    max_inventory_in_days = get_config('ARS_MAX_INVENTORY_IN_DAYS', 7)
    demand = (daily_average * max_inventory_in_days) - current_inventory - inventory_in_process - putaway_inventory
    return math.ceil(demand) if demand else 0


def get_total_products_ordered(warehouse, parent_product, starting_from_date):
    no_of_pieces_ordered = Order.objects.filter(seller_shop=warehouse,
                                                ordered_cart__rt_cart_list__cart_product__parent_product=parent_product,
                                                created_at__gte=starting_from_date)\
                                         .values('ordered_cart__rt_cart_list__cart_product__parent_product')\
                                         .annotate(ordered_pieces=Sum('ordered_cart__rt_cart_list__no_of_pieces'))['ordered_pieces']
    return no_of_pieces_ordered if no_of_pieces_ordered else 0


def initiate_ars():
    product_vendor_mappings = ProductVendorMapping.objects.filter(
                                                            product__parent_product__is_ars_applicable=True,
                                                            vendors__ordering_days__contains=datetime.date.isoweekday(),
                                                            is_default=True)
    product_demand_dict = {}
    for item in product_vendor_mappings:
        if product_demand_dict.get(item.product.parent_product.parent_brand) is None:
            product_demand_dict[item.product.parent_product.parent_brand] = {item.product.parent_product:0}
        product_demand_dict[item.product.parent_product.parent_brand][item.product.parent_product] \
                                                            = get_demand_by_parent_product(item.product.parent_product)