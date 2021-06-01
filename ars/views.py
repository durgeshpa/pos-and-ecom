import csv
import datetime
import logging
import math
from io import StringIO

from dal import autocomplete
from decouple import config
from django.db import transaction
from django.db.models import Sum, Count, F, Q
from django.http import HttpResponse

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
from wms.models import Putaway, WarehouseInventory, InventoryState, InventoryType

info_logger = logging.getLogger('file-info')


def product_demand_data_generator(master_data, retailer_parent_mapping_dict):
    """
    Generates data to be populated into ProductDemand table.
    This function calculates the daily average, current inventory,
    current demand for all the parent products for all the given warehouses and stores this in ProductDemand table.
    """
    for parent_product_id, item in master_data.items():
        for warehouse_id, data in item.items():
            if retailer_parent_mapping_dict.get(warehouse_id) is None:
                continue
            active_child_product = get_child_product_with_latest_grn(retailer_parent_mapping_dict[warehouse_id], parent_product_id)
            if active_child_product is None:
                continue

            rolling_avg = math.ceil(data['ordered_pieces']/data['visible_days']) if data.get('visible_days') else 0
            if rolling_avg is None or rolling_avg == 0:
                continue
            current_inventory = data['qty'] if data['qty'] > 0 else 0
            inventory_in_process = data['in_process_inventory'] if data.get('in_process_inventory') else 0
            putaway_inventory = data['pending_putaway'] if data.get('pending_putaway') else 0
            demand = (rolling_avg * data['max_inventory']) - current_inventory - inventory_in_process - putaway_inventory
            demand = math.ceil(demand) if demand > 0 else 0
            product_demand = ProductDemand(warehouse_id=warehouse_id, parent_product_id=parent_product_id,
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
    rolling_avg_days = get_config('ROLLING_AVG_DAYS', 30)
    starting_avg_from = datetime.datetime.today().date() - datetime.timedelta(days=rolling_avg_days)
    if warehouse_ids_as_string is None or len(warehouse_ids_as_string) == 0:
        return
    warehouse_ids = warehouse_ids_as_string.split(",")
    warehouse_list = Shop.objects.filter(id__in=warehouse_ids).values_list('pk', flat=True)

    type_normal = InventoryType.objects.filter(inventory_type='normal').last()
    inventory_data = WarehouseInventory.objects.filter(warehouse__id__in=warehouse_list,
                                                       inventory_type=type_normal,
                                                       inventory_state__inventory_state__in=['reserved', 'ordered',
                                                                                             'to_be_picked',
                                                                                             'total_available'])\
                                               .prefetch_related('sku__parent_product')
    master_data = {}
    for item in inventory_data:
        if master_data.get(item.sku.parent_product_id) is None:
            master_data[item.sku.parent_product_id] = {warehouse_id: {'qty': 0,
                                                                      'ordered_pieces': 0,
                                                                      'in_process_inventory': 0,
                                                                      'pending_putaway': 0,
                                                                      'max_inventory': item.sku.parent_product.max_inventory} for warehouse_id in warehouse_list}
        if item.inventory_state.inventory_state == 'total_available':
            master_data[item.sku.parent_product_id][item.warehouse_id]['qty'] += item.quantity
        elif item.inventory_state.inventory_state in ('reserved', 'ordered', 'to_be_picked'):
            master_data[item.sku.parent_product_id][item.warehouse_id]['qty'] -= item.quantity

    # From historic data, get the total number of days on which the product has been visible,
    # starting from starting_avg_from date
    historic_data = WarehouseInventoryHistoric.objects.filter(warehouse__id__in=warehouse_list, visible=True,
                                                              sku__parent_product_id__in=master_data.keys(),
                                                              archived_at__gte=starting_avg_from) \
                                                      .values('warehouse', 'sku__parent_product', 'archived_at__date') \
                                                      .annotate(days=Count('sku__parent_product', distinct=True))


    for item in historic_data:
        if master_data[item['sku__parent_product']][item['warehouse']].get('visible_days') is None:
            master_data[item['sku__parent_product']][item['warehouse']]['visible_days'] = 0

        master_data[item['sku__parent_product']][item['warehouse']]['visible_days'] += item['days']

    # Get total no of pieces ordered starting from starting_avg_from date
    total_products_ordered = Order.objects.filter(seller_shop__id__in=warehouse_list,
                                                  ordered_cart__rt_cart_list__cart_product__parent_product_id__in=master_data.keys(),
                                                  created_at__gte=starting_avg_from).order_by() \
                                          .values('seller_shop', 'ordered_cart__rt_cart_list__cart_product__parent_product') \
                                          .annotate(ordered_pieces=Sum('ordered_cart__rt_cart_list__no_of_pieces'))


    for item in total_products_ordered:
        master_data[item['ordered_cart__rt_cart_list__cart_product__parent_product']][item['seller_shop']]['ordered_pieces'] = item['ordered_pieces']


    # Get total no of pieces in process currently which are not yet added in warehouse inventory
    parent_retailer_mappings = ParentRetailerMapping.objects.filter(retailer__id__in=warehouse_list, status=True,
                                                        parent__shop_type__shop_type='gf').values('parent_id', 'retailer_id')
    parent_retailer_mapping_dict = {mapping['parent_id']:mapping['retailer_id'] for mapping in parent_retailer_mappings}
    inventory_in_process = Cart.objects.filter(gf_billing_address__shop_name__id__in=parent_retailer_mapping_dict.keys(),
                                               po_status__in=[Cart.OPEN, Cart.PENDING_APPROVAL],
                                               cart_list__cart_product__parent_product_id__in=master_data.keys())\
                                       .values('gf_billing_address__shop_name','cart_list__cart_product__parent_product')\
                                       .annotate(no_of_pieces=Sum('cart_list__no_of_pieces'))

    for item in inventory_in_process:
        if parent_retailer_mapping_dict.get(item['gf_billing_address__shop_name']):
            retailer_id = parent_retailer_mapping_dict[item['gf_billing_address__shop_name']]
            master_data[item['cart_list__cart_product__parent_product']][retailer_id]['in_process_inventory'] = item['no_of_pieces']

    # Get total no of pieces pending for putaway currently.
    pending_putaway = Putaway.objects.filter(~Q(quantity=F('putaway_quantity')), warehouse__id__in=warehouse_list,
                                             sku__parent_product_id__in=master_data.keys()) \
                                     .values('warehouse', 'sku__parent_product') \
                                     .annotate(pending_qty=Sum(F('quantity') - F('putaway_quantity')))
    for item in pending_putaway:
        master_data[item['sku__parent_product']][item['warehouse']]['pending_putaway'] = item['pending_qty']

    inv_parent_retailer_mapping_dict = {v: k for k, v in parent_retailer_mapping_dict.items()}
    bulk_create(ProductDemand, product_demand_data_generator(master_data, inv_parent_retailer_mapping_dict))

def get_daily_average(warehouse, parent_product):
    """
    Returns average no of pieces sold per day of all the children based on the data of last 30 days
    for given parent product and warehouse,
    only the days where product is available and visible on app are to be considered in calculating the average
    """
    rolling_avg_days = get_config('ROLLING_AVG_DAYS', 30)
    starting_avg_from = datetime.datetime.today().date() - datetime.timedelta(days=rolling_avg_days)
    avg_days = WarehouseInventoryHistoric.objects.filter(warehouse=warehouse,
                                                         sku__parent_product=parent_product, visible=True,
                                                         archived_at__gte=starting_avg_from) \
                                              .values('sku__parent_product', 'archived_at__date')\
                                              .distinct('sku__parent_product__id', 'archived_at__date').count()
    # avg_days = query.last()['days'] if query.exists() else 0
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
                                               po_status__in=[Cart.OPEN, Cart.PENDING_APPROVAL],
                                               cart_list__cart_product__parent_product=parent_product)\
                                       .values('cart_list__cart_product__parent_product')\
                                       .annotate(no_of_pieces=Sum('cart_list__no_of_pieces'))
    return inventory_in_process[0]['no_of_pieces'] if inventory_in_process.exists() else 0


def get_inventory_pending_for_putaway(warehouse, parent_product):
    """
    Returns total no of pieces  of all the children for a given parent and given warehouse which are pending for putaway.
    """
    pending_putaway = Putaway.objects.filter(~Q(quantity=F('putaway_quantity')), warehouse=warehouse,
                                                 sku__parent_product=parent_product)\
                                         .values('sku__parent_product')\
                                         .annotate(pending_qty=Sum(F('quantity')-F('putaway_quantity')))
    return pending_putaway[0]['pending_qty'] if pending_putaway.exists() else 0


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
                                                created_at__gte=starting_from_date).order_by()\
                                         .values('ordered_cart__rt_cart_list__cart_product__parent_product')\
                                         .annotate(ordered_pieces=Sum('ordered_cart__rt_cart_list__no_of_pieces'))
    no_of_pieces_ordered = query[0]['ordered_pieces'] if query.exists() else 0
    return no_of_pieces_ordered


def initiate_ars():
    """
    Initiates the process of ARS.
    Select the vendors eligible for the current order cycle i.e. whose “Ordering Day” = Today.
    In case of multiple brands for a vendor separate PO will be created for each brand.
    Only products for which vendor is default vendor the PO will be created
    """
    info_logger.info("initiate_ars|Started| Day of Week {} ".format(datetime.date.today().isoweekday()))

    min_inventory_factor = get_config('ARS_MIN_INVENTORY_FACTOR', 70)
    warehouse_ids_as_string = get_config('ARS_WAREHOUSES')
    if warehouse_ids_as_string is None or len(warehouse_ids_as_string) == 0:
        return
    warehouse_ids = warehouse_ids_as_string.split(",")
    warehouse_list = Shop.objects.filter(id__in=warehouse_ids)

    product_vendor_mappings = ProductVendorMapping.objects.filter(
                                                            product__parent_product__is_ars_applicable=True,
                                                            vendor__ordering_days__contains=datetime.date.today().isoweekday(),
                                                            is_default=True, status=True)

    brand_product_dict = {}
    for item in product_vendor_mappings:
        parent_product = item.product.parent_product
        brand = parent_product.parent_brand_id

        for warehouse in warehouse_list:
            if brand_product_dict.get(brand) is None:
                brand_product_dict[brand] = {warehouse.id: {item.vendor_id: {}}}
            elif brand_product_dict[brand].get(warehouse.id) is None:
                brand_product_dict[brand][warehouse.id] = {item.vendor_id: {}}
            elif brand_product_dict[brand][warehouse.id].get(item.vendor_id) is None:
                brand_product_dict[brand][warehouse.id][item.vendor_id] = {}
            if parent_product not in brand_product_dict[brand][warehouse.id][item.vendor_id].keys():
                is_eligible_to_raise_demand = False
                daily_average = get_daily_average(warehouse, parent_product)
                if daily_average <= 0:
                    continue
                current_inventory = get_current_inventory(warehouse, parent_product)
                max_inventory_in_days = parent_product.max_inventory
                demand = (daily_average * max_inventory_in_days) - current_inventory
                if demand <= 0:
                    continue
                if parent_product.is_lead_time_applicable:
                    max_inventory_in_days = max_inventory_in_days + item.vendor.lead_time

                min_inventory_in_days = max_inventory_in_days * min_inventory_factor / 100
                max_inventory = max_inventory_in_days * daily_average
                min_inventory = min_inventory_in_days * daily_average
                if demand >= (max_inventory - min_inventory):
                    is_eligible_to_raise_demand = True

                if is_eligible_to_raise_demand:
                    brand_product_dict[brand][warehouse.id][item.vendor_id] = {parent_product.id : demand}

    for brand, warehouse_demand_dict in brand_product_dict.items():
        for wh, vendor_demand_dict in warehouse_demand_dict.items():
            for vendor, product_demand_dict in vendor_demand_dict.items():
                with transaction.atomic():
                    if len(product_demand_dict) > 0:

                        existing_demand_raised = VendorDemand.objects.filter(brand_id=brand,
                                                                             vendor_id=vendor,
                                                                             warehouse_id=wh,
                                                                             status=VendorDemand.STATUS_CHOICE.DEMAND_CREATED)
                        if existing_demand_raised.exists():
                            continue
                        po = VendorDemand.objects.create(brand_id=brand, vendor_id=vendor,
                                                         warehouse_id=wh,
                                                         status=VendorDemand.STATUS_CHOICE.DEMAND_CREATED)
                        for product, demand in product_demand_dict.items():
                            VendorDemandProducts.objects.create(demand=po, product_id=product, quantity=demand)

                        info_logger.info("initiate_ars|Demand generated| brand-{}, vendor-{}, warehouse-{} "
                                         .format(brand, vendor, wh))


def get_child_product_with_latest_grn(warehouse_id, parent_product_id):
    """
    Returns the child product whose GRN is latest for any given parent product.
    In case there are more than one child products with same GRN time then it returns the child product with greater MRP
    """
    child_product_with_latest_grn = None
    products = GRNOrderProductMapping.objects.filter(grn_order__order__ordered_cart__gf_billing_address__shop_name_id=warehouse_id,
                                                     product__parent_product_id=parent_product_id).order_by('-created_at')
    if products.exists():
        child_product_with_latest_grn = products[0].product
        created_at = child_product_with_latest_grn.created_at
        for p in products:
            if p.created_at != created_at:
                break
            if p.product.product_mrp > child_product_with_latest_grn.product.product_mrp:
                child_product_with_latest_grn = p
    return child_product_with_latest_grn


def mail_category_manager_for_po_approval():
    """
    Generates and send mail to category managers the summary of all the PO's which are generated today through ARS
    and are pending for approval.
    """
    try:

        today = datetime.datetime.today().date()
        po_to_send_mail_for = VendorDemand.objects.filter(status=VendorDemand.STATUS_CHOICE.PO_CREATED,
                                                          created_at__date=today)
        if po_to_send_mail_for.count() > 0:
            sender = get_config("ARS_MAIL_SENDER")
            recipient_list = get_config("MAIL_DEV")
            if config('OS_ENV') and config('OS_ENV') in ['Production']:
                recipient_list = get_config("ARS_MAIL_PO_ARROVAL_RECIEVER")
            subject = SUCCESS_MESSAGES['ARS_MAIL_PO_APPROVAL_SUBJECT'].format(today)
            body = SUCCESS_MESSAGES['ARS_MAIL_PO_APPROVAL_BODY'].format(today)
            f = StringIO()
            writer = csv.writer(f)
            filename = 'PO_pending_for_approval-{}.csv'.format(today)
            columns = ['PO Number', 'Brand', 'Supplier State', 'Supplier Name', 'PO Creation Date', 'PO Status',
                       'PO Delivery Date']
            writer.writerow(columns)
            for item in po_to_send_mail_for:
                writer.writerow([item.po.po_no, item.brand, item.vendor.state, item.vendor.vendor_name, item.created_at,
                                'Pending Approval', item.po.po_delivery_date])
            attachment = {'name' : filename, 'type' : 'text/csv', 'value' : f.getvalue()}
            send_mail(sender, recipient_list, subject, body, [attachment])
            po_to_send_mail_for.update(status=VendorDemand.STATUS_CHOICE.MAIL_SENT_FOR_APPROVAL)
    except Exception as e:
        info_logger.error("Exception|mail_category_manager_for_po_approval|{}".format(e))


def create_po():
    """
    Creates PurchaseOrder for all the demands created.
    """
    for demand in VendorDemand.objects.filter(Q(status=VendorDemand.STATUS_CHOICE.DEMAND_CREATED)):
        try:
            create_po_from_demand(demand)
        except Exception as e:
            info_logger.info("Exception | create_po | demand-{}, e-{}".format(demand, e))


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
                                        po_status=Cart.PENDING_APPROVAL,
                                        po_validity_date=datetime.date.today() + datetime.timedelta(days=15),
                                        po_delivery_date=datetime.datetime.today() +
                                                         datetime.timedelta(days=demand.vendor.lead_time))

    info_logger.info("create_po_from_demand|Cart created | Cart ID-{}".format(cart_instance.id))
    for demand_product in VendorDemandProducts.objects.filter(demand=demand):

        info_logger.info("create_po_from_demand|Parent Product-{}, Demand-{}"
                         .format(demand_product.product, demand_product.quantity))
        parent_retailer_mapping = ParentRetailerMapping.objects.filter(retailer=demand.warehouse).last()

        product = get_child_product_with_latest_grn(parent_retailer_mapping.parent_id, demand_product.product_id)

        info_logger.info("create_po_from_demand|Parent Product-{}, Child Product to be added in PO-{}"
                         .format(demand_product.product, product))

        vendor_mapping = ProductVendorMapping.objects.filter(product=product, vendor=demand.vendor, status=True)
        if vendor_mapping.exists():
            if vendor_mapping.last().product_price:
                vendor_product_price = vendor_mapping.last().product_price

            elif vendor_mapping.last().product_price_pack:
                vendor_product_price = vendor_mapping.last().product_price_pack

            product_case_size = vendor_mapping.last().case_size if vendor_mapping.last().case_size else product.product_case_size
            product_inner_case_size = product.product_inner_case_size

            taxes = ([field.tax.tax_percentage for field in vendor_mapping.last().product.product_pro_tax.all()])
            taxes = str(sum(taxes))

            no_of_cases = demand_product.quantity / product_case_size
            no_of_pieces = no_of_cases * product_case_size

            CartProductMapping.objects.create(cart=cart_instance, cart_parent_product=demand_product.product,
                                          cart_product=product, _tax_percentage=taxes,
                                          inner_case_size=product_inner_case_size,
                                          case_size=product_case_size,
                                          number_of_cases=no_of_cases,
                                          no_of_pieces=no_of_pieces,
                                          vendor_product=vendor_mapping.last(),
                                          price=vendor_product_price)

            info_logger.info("create_po_from_demand| Product added in PO | Child Product-{}, no_of_pieces-{}"
                             .format(product, no_of_pieces))
        else:
            info_logger.info("create_po_from_demand|Vendor Product Mapping does not exist | "
                             "vendor-{}, parent product-{}, product-{}"
                            .format(demand.vendor, demand_product.product, product))
            demand.status = VendorDemand.STATUS_CHOICE.FAILED
            demand.comment = 'Vendor Product Mapping does not exist'
            demand.save()
            raise Exception('Vendor Product Mapping does not exist| vendor-{}, parent product-{}, product-{}'
                            .format(demand.vendor, demand_product.product, product))
    demand.status = VendorDemand.STATUS_CHOICE.DEMAND_CREATED
    demand.po = cart_instance
    demand.status = VendorDemand.STATUS_CHOICE.PO_CREATED
    demand.save()
    return cart_instance


class ARSWareHouseComplete(autocomplete.Select2QuerySetView):

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


class ARSParentProductAutocomplete(autocomplete.Select2QuerySetView):
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
