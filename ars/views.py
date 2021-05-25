import csv
import datetime
import logging
import math
from io import StringIO

from dal import autocomplete
from django.db import transaction
from django.db.models import Sum, Count, F, Q

from accounts.models import User
from addresses.models import Address
from ars.models import ProductDemand, VendorDemand, VendorDemandProducts
from global_config.views import get_config
from gram_to_brand.models import Cart, CartProductMapping, GRNOrderProductMapping
from products.models import ProductVendorMapping, ParentProduct
from retailer_backend.common_function import bulk_create, send_mail
from retailer_backend.messages import SUCCESS_MESSAGES
from retailer_to_sp.models import Order
from services.models import WarehouseInventoryHistoric
from shops.models import ParentRetailerMapping, Shop
from wms.common_functions import get_inventory_in_stock
from wms.models import Putaway

info_logger = logging.getLogger('file-info')


def product_demand_data_generator(warehouse_list, parent_product_list):
    """
    Generates data to be populated into ProductDemand table.
    This function calculates the daily average, current inventory,
    current demand for all the parent products for all the given warehouses and stores this in ProductDemand table.
    """
    for warehouse in warehouse_list:
        for product in parent_product_list:
            active_child_product = get_child_product_with_latest_grn(product)
            if active_child_product is None:
                continue
            rolling_avg = get_daily_average(warehouse, product)
            if rolling_avg is None or rolling_avg == 0:
                continue
            current_inventory = get_inventory_in_stock(warehouse, product)
            inventory_in_process = get_inventory_in_process(warehouse, product)
            putaway_inventory = get_inventory_pending_for_putaway(warehouse, product)
            demand = (rolling_avg * product.max_inventory) - current_inventory - inventory_in_process - putaway_inventory
            demand = math.ceil(demand) if demand > 0 else 0
            product_demand = ProductDemand(warehouse=warehouse, parent_product=product,
                                           active_child_product=active_child_product,
                                           average_daily_sales=rolling_avg, current_inventory=current_inventory,
                                           demand=demand)
            info_logger.info('product_demand_data_generator|product demand {}'.format(product_demand))
            yield product_demand


def populate_daily_average():
    """
    Generate and saves the daily sales average for all the active parent products in the system.
    """
    warehouse_ids_as_string = get_config('ARS_WAREHOUSES')
    if warehouse_ids_as_string is None or len(warehouse_ids_as_string) == 0:
        return
    warehouse_ids = warehouse_ids_as_string.split(",")
    warehouse_list = [(Shop.objects.filter(id=id).last() if Shop.objects.filter(id=id).last() else None) for id in warehouse_ids]
    parent_product_list = ParentProduct.objects.filter(status=True)
    bulk_create(ProductDemand, product_demand_data_generator(warehouse_list, parent_product_list))

def get_daily_average(warehouse, parent_product):
    """
    Returns average no of pieces sold per day of all the children based on the data of last 30 days
    for given parent product and warehouse,
    only the days where product is available and visible on app are to be considered in calculating the average
    """
    rolling_avg_days = get_config('ROLLING_AVG_DAYS', 30)
    starting_avg_from = datetime.datetime.today().date() - datetime.timedelta(days=rolling_avg_days)
    query = WarehouseInventoryHistoric.objects.filter(warehouse=warehouse,
                                                         sku__parent_product=parent_product, visible=True,
                                                         archived_at__gte=starting_avg_from)\
                                                 .values('sku__parent_product')\
                                                 .annotate(days=Count('sku__parent_product', distinct=True))
    avg_days = query.last()['days'] if query.exists() else 0
    products_ordered = get_total_products_ordered(warehouse, parent_product, starting_avg_from)
    rolling_avg = products_ordered/avg_days if avg_days else 0
    return math.ceil(rolling_avg)

def get_inventory_in_process(warehouse, parent_product):
    """
    Returns total no of pieces of all the children for a given parent for which purchase order has been generated
    and it is either OPEN or Waiting for Approval.
    """
    shop_mapping = ParentRetailerMapping.objects.filter(retailer_id=warehouse, status=True,
                                                        parent__shop_type__shop_type='gf')
    gf_shop = shop_mapping.last().parent
    inventory_in_process = Cart.objects.filter(gf_billing_address__shop_name=gf_shop,
                                               po_status__in=[Cart.OPEN, Cart.APPROVAL_AWAITED],
                                               cart_list__cart_product__parent_product=parent_product)\
                                       .values('cart_list__cart_product__parent_product')\
                                       .annotate(no_of_pieces=Sum('cart_list__cart_product__no_of_pieces')).last()
    return inventory_in_process['no_of_pieces'] if inventory_in_process else 0


def get_inventory_pending_for_putaway(warehouse, parent_product):
    """
    Returns total no of pieces  of all the children for a given parent and given warehouse which are pending for putaway.
    """
    pending_putaway = Putaway.objects.filter(~Q(quantity=F('putaway_quantity')), warehouse=warehouse,
                                                 sku__parent_product=parent_product)\
                                         .values('sku__parent_product')\
                                         .annotate(pending_qty=Sum(F('quantity')-F('putaway_quantity'))).last()
    return pending_putaway['pending_qty'] if pending_putaway else 0


def get_demand_by_parent_product(warehouse, parent_product):
    """
    Return the current demand for a given parent product and warehouse.
    Demand is calcuated as follows :
        Pending Demand = (MAX_INVENTORY_DAYS * Daily Average)
                                - Current Inventory - Pending Putaway Inventory - Inventory in Process
    """
    daily_average = get_daily_average(warehouse, parent_product)
    if daily_average <= 0:
        return 0
    current_inventory = get_current_inventory(warehouse, parent_product)
    max_inventory_in_days = parent_product.max_inventory
    demand = (daily_average * max_inventory_in_days) - current_inventory
    return math.ceil(demand) if demand > 0 else 0


def get_current_inventory(warehouse, parent_product):
    """
    Returns the inventory available in stock + inventory for which PO is already raised + inventory pending for putaway
    """
    inventory_in_stock = get_inventory_in_stock(warehouse, parent_product)
    inventory_in_process = get_inventory_in_process(warehouse, parent_product)
    putaway_inventory = get_inventory_pending_for_putaway(warehouse, parent_product)
    current_inventory = inventory_in_stock + inventory_in_process + putaway_inventory
    return current_inventory


def get_total_products_ordered(warehouse, parent_product, starting_from_date):
    """
    Returns total no of peices ordered of all the children for a given parent product and warehouse
    starting from the given date.
    """
    query = Order.objects.filter(seller_shop=warehouse,
                                                ordered_cart__rt_cart_list__cart_product__parent_product=parent_product,
                                                created_at__gte=starting_from_date)\
                                         .values('ordered_cart__rt_cart_list__cart_product__parent_product')\
                                         .annotate(ordered_pieces=Sum('ordered_cart__rt_cart_list__no_of_pieces'))
    no_of_pieces_ordered = query.last()['ordered_pieces'] if query.exists() else 0
    return no_of_pieces_ordered

def initiate_ars():
    """
    Initiates the process of ARS.
    Select the vendors eligible for the current order cycle i.e. whose “Ordering Day” = Today.
    In case of multiple brands for a vendor separate PO will be created for each brand.
    Only products for which vendor is default vendor the PO will be created
    """
    info_logger.info("initiate_ars|Started| Day of Week {} ".datetime.date.isoweekday())
    product_vendor_mappings = ProductVendorMapping.objects.filter(
                                                            product__parent_product__is_ars_applicable=True,
                                                            vendors__ordering_days__contains=datetime.date.isoweekday(),
                                                            is_default=True)
    brand_product_dict = {}
    for item in product_vendor_mappings:
        parent_product = item.product.parent_product
        brand = parent_product.parent_brand

        warehouse_ids = get_config('ARS_WAREHOUSES', '600, 1393')
        warehouse_list = [Shop.objects.filter(id=id).last() if Shop.objects.filter(id=id).last() else id in warehouse_ids]

        for warehouse in warehouse_list:
            if brand_product_dict.get(brand) is None:
                brand_product_dict[brand] = {'vendor':item.vendor, 'warehouse':warehouse, 'products':{}}
            if parent_product not in brand_product_dict[brand]['products'].keys():

                is_eligible_to_raise_demand = True
                demand = get_demand_by_parent_product(warehouse, parent_product)
                daily_average = get_daily_average(warehouse, parent_product)
                max_inventory_in_days = parent_product.max_inventory
                if parent_product.is_lead_time_applicable:
                    max_inventory_in_days = max_inventory_in_days + item.vendor.lead_time

                min_inventory_factor = get_config('ARS_MIN_INVENTORY_FACTOR', 70)
                min_inventory_in_days = max_inventory_in_days * min_inventory_factor / 100
                max_inventory = max_inventory_in_days * daily_average
                min_inventory = min_inventory_in_days * daily_average
                if demand < (max_inventory - min_inventory):
                    is_eligible_to_raise_demand = False

                if is_eligible_to_raise_demand:
                    brand_product_dict[brand]['products'] = {parent_product : demand}
        else:
            info_logger.info("create_po_from_demand|No valid warehouse configured")


    for brand, product_demand_dict in brand_product_dict.items():
        po = VendorDemand.objects.create(brand=brand, vendor=product_demand_dict['vendor'],
                                   warehouse=product_demand_dict['warehouse'])
        for product, demand in product_demand_dict['products'].items():
            VendorDemandProducts.objects.create(po=po, product=product, demand=demand)

        info_logger.info("initiate_ars|Demand generated| brand-{}, vendor-{}, warehouse-{} "
                         .format(brand, product_demand_dict['vendor'], product_demand_dict['warehouse']))


def get_child_product_with_latest_grn(parent_product):
    """
    Returns the child product whose GRN is latest for any given parent product.
    In case there are more than one child products with same GRN time then it returns the child product with greater MRP
    """
    child_product_with_latest_grn = None
    products = GRNOrderProductMapping.objects.filter(product__parent_product=parent_product).order_by('-created_at')
    if products.exists():
        child_product_with_latest_grn = products[0].product
        created_at = child_product_with_latest_grn.created_at
        for p in products:
            if p.created_at != created_at:
                break
            if p.product_mrp > child_product_with_latest_grn.product_mrp:
                child_product_with_latest_grn = p

    if child_product_with_latest_grn is None:
        parent_product.product_parent_product.last()

    return child_product_with_latest_grn


def mail_category_manager_for_po_approval():
    """
    Generates and send mail to category managers the summary of all the PO's which are generated today through ARS
    and are pending for approval.
    """
    try:
        sender = get_config("ARS_MAIL_SENDER", "consultant1@gramfactory.com")
        recipient_list = get_config("ARS_MAIL_PO_ARROVAL_RECIEVER", "consultant1@gramfactory.com")
        today = datetime.datetime.today().date()
        subject = SUCCESS_MESSAGES['ARS_MAIL_PO_APPROVAL_SUBJECT'].format(today)
        body = SUCCESS_MESSAGES['ARS_MAIL_PO_APPROVAL_BODY'].format(today)
        f = StringIO()
        writer = csv.writer(f)
        filename = 'PO_pending_for_approval-{}.csv'.format(today)
        columns = ['PO Number', 'Brand', 'Supplier State', 'Supplier Name', 'PO Creation Date', 'PO Status',
                   'PO Delivery Date']
        writer.writerow(columns)
        po_to_send_mail_for = VendorDemand.objects.filter(status=VendorDemand.STATUS_CHOICE.CREATED,
                                                          created_at__date=today)
        for item in po_to_send_mail_for:
            writer.writerow([item.po.po_no, item.brand, item.vendor.state, item.vendor.vendor_name, item.created_at,
                            'Pending Approval', item.po.po_delivery_date])
        attachment = {'name' : filename, 'type' : 'text/csv', 'value' : writer.getvalue()}
        send_mail(sender, recipient_list, subject, body, [attachment])
        po_to_send_mail_for.update(status=VendorDemand.STATUS_CHOICE.MAIL_SENT)
    except Exception as e:
        info_logger.error("Exception|mail_category_manager_for_po_approval|{}".format(e))


def create_po():
    """
    Creates PurchaseOrder for all the demands created.
    """
    try:
        for demand in VendorDemand.objects.filter(Q(status=VendorDemand.STATUS_CHOICE.DEMAND_CREATED)):
            create_po_from_demand(demand)
    except Exception as e:
        info_logger.info("Exception | create_po | e-{}".format(e))


@transaction.atomic
def create_po_from_demand(demand):
    """
    Creates PurchaseOrder for any given demand.
    """
    info_logger.info("create_po_from_demand|Started|Brand-{}, Vendor-{}, Warehouse-{}"
                     .format(demand.brand, demand.vendor, demand.warehouse))

    user_id = get_config('ars_user')
    if user_id is None:
        info_logger.info("create_po_from_demand|user is not defined ")
        return

    system_user = User.objects.filter(pk=user_id).last()
    if system_user is None:
        info_logger.info("create_po_from_demand|no User found with id -{}".format(user_id))
        return

    shop_mapping = ParentRetailerMapping.objects.filter(retailer_id=demand.warehouse, status=True, parent__shop_type__shop_type='gf').last()
    if shop_mapping is None:
        info_logger.info("create_po_from_demand|No GF shop found|warehouse -{}".format(demand.warehouse))
        return

    gf_shop = shop_mapping.parent
    shipp_address = Address.objects.filter(shop_name=gf_shop, address_type='shipping').last()
    bill_address = Address.objects.filter(shop_name=gf_shop, address_type='billing').last()

    if shipp_address is None or bill_address is None:
        info_logger.info("create_po_from_demand|Address not found|shop -{}".format(gf_shop))
        return

    cart_instance = Cart.objects.create(brand=demand.brand, supplier_name=demand.vendor, supplier_state=demand.vendor.state,
                                        gf_shipping_address=shipp_address,
                                        gf_billing_address=bill_address,
                                        po_raised_by=system_user, last_modified_by=system_user,
                                        cart_type=Cart.CART_TYPE_CHOICE.AUTO,
                                        po_status=Cart.APPROVAL_AWAITED,
                                        po_delivery_date=datetime.datetime.today() +
                                                         datetime.timedelta(days=demand.vendor.lead_time))

    info_logger.info("create_po_from_demand|Cart created | Cart ID-{}".format(cart_instance.id))
    for demand_product in VendorDemandProducts.objects.filter(demand=demand):

        info_logger.info("create_po_from_demand|Parent Product-{}, Demand-{}"
                         .format(demand_product.product, demand_product.demand))
        product = get_child_product_with_latest_grn(demand_product.product)

        info_logger.info("create_po_from_demand|Parent Product-{}, Child Product to be added in PO-{}"
                         .format(demand_product.product, product))

        vendor_mapping = ProductVendorMapping.objects.filter(product=product, vendor=demand.vendor,
                                                             status=True, is_default=True)
        if vendor_mapping.exists():
            if vendor_mapping.last().product_price:
                vendor_product_price = vendor_mapping.last().product_price

            elif vendor_mapping.last().product_price_pack:
                vendor_product_price = vendor_mapping.last().product_price_pack

            product_case_size = vendor_mapping.last().case_size if vendor_mapping.last().case_size else product.product_case_size
            product_inner_case_size = product.product_inner_case_size

            taxes = ([field.tax.tax_percentage for field in vendor_mapping.last().product.product_pro_tax.all()])
            taxes = str(sum(taxes))

            no_of_cases = demand / product_case_size
            no_of_pieces = no_of_cases * product_case_size

            CartProductMapping.objects.create(cart=cart_instance, cart_parent_product=demand_product.parent_product,
                                          cart_product=product, _tax_percentage=taxes,
                                          inner_case_size=product_inner_case_size,
                                          case_size=product_case_size,
                                          number_of_cases=no_of_cases,
                                          no_of_pieces=no_of_pieces,
                                          vendor_product=vendor_mapping,
                                          price=vendor_product_price)

            info_logger.info("create_po_from_demand| Product added in PO | Child Product-{}, no_of_pieces-{}"
                             .format(product, no_of_pieces))
        else:
            info_logger.info("create_po_from_demand|Vendor Product Mapping does not exist | "
                             "vendor-{}, parent product-{}, product-{}"
                            .format(demand.vendor, demand_product.parent_product, product))
            demand.status = VendorDemand.STATUS_CHOICE.FAILED
            demand.save()
            raise Exception('Vendor Product Mapping does not exist| vendor-{}, parent product-{}, product-{}'
                            .format(demand.vendor, demand_product.parent_product, product))
    demand.status = VendorDemand.STATUS_CHOICE.CREATED
    demand.po_no = cart_instance.po_no
    demand.save()
    return cart_instance


class WareHouseComplete(autocomplete.Select2QuerySetView):

    def get_queryset(self, *args, **kwargs):
        """
        Returns queryset for Shop model where shop_name matches the given string to support autocomplete.
        """
        if not self.request.user.is_authenticated:
            return Shop.objects.none()

        qs = Shop.objects.filter(shop_type__shop_type__in=['sp', 'f'])

        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class ParentProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        """
        Returns queryset for ParentProduct model where parent_id or name matches the given string  to support autocomplete.
        """
        if not self.request.user.is_authenticated:
            return ParentProduct.objects.none()

        qs = ParentProduct.objects.all()

        if self.q:
            qs = qs.filter(Q(parent_id__icontains=self.q)|Q(name__icontains=self.q))
        return qs
