import logging
from datetime import datetime

from django.db import transaction
from django.db.models import Sum
from products.models import Product

from wms.models import BinInventory
from gram_to_brand.models import (ProductCostPriceChangeLog, ProductGRNCostPriceMapping,
                                  GRNOrderProductMapping)
from services.models import BinInventoryHistoric


logger = logging.getLogger('django')

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


# def run():
#     months = int(get_config('last_grn_for_cp_series', 12))
#     days = 30 * months
#     start_date = datetime.now() - timedelta(days=days)
#     grns = GRNOrderProductMapping.objects.filter(product_invoice_qty__gt=0)\
#         .filter(product_invoice_price__gt=0, 
#                 created_at__gte=start_date).order_by('created_at')
#     print(f"Total GRN found :: {grns.count()}")
#     for grn in grns:
#         create_cost_price(grn)

def create_cost_price(instance):
    product = instance.product
    avail_qty = BinInventoryHistoric.objects.filter(sku=product, 
                                                    archived_at__date=instance.created_at.date(), 
                                                    inventory_type__inventory_type='normal')\
                                                    .aggregate(total=Sum('quantity')).get('total')
    avail_qty = avail_qty if avail_qty else 0
    cost_price_change_log = ProductCostPriceChangeLog()
    try:
        cost_price = ProductGRNCostPriceMapping.objects.get(product=product)
        last_cp = cost_price.cost_price
        cost_price_change_log.grn = cost_price.latest_grn
    except ProductGRNCostPriceMapping.DoesNotExist:
        cost_price = ProductGRNCostPriceMapping()
        grn = GRNOrderProductMapping.objects.filter(product=product, 
                                                    product_invoice_qty__gt=0)\
                                                        .filter(product_invoice_price__gt=0, 
                                                                id__lt=instance.pk)\
                                                            .exclude(id=instance.pk).last()
        last_cp = grn.product_invoice_price if grn else 0
        cost_price_change_log.grn = grn
        cost_price.product = product
    cost_price_change_log.cost_price_grn_mapping = cost_price
    cost_price_change_log.cost_price = last_cp
    current_purchase_price = instance.product_invoice_price
    current_purchase_qty = instance.product_invoice_qty
    total =  (avail_qty + current_purchase_qty) 
    if total:
        new_cost_price = (float((avail_qty * last_cp)) + (current_purchase_qty * current_purchase_price)) / total
    else:
        new_cost_price = last_cp
    ### updating cost price of product 
    cost_price.cost_price = new_cost_price
    cost_price.latest_grn = instance
    cost_price.modified_at = datetime.now()
    with transaction.atomic():
        cost_price.save()
        cost_price_change_log.cost_price_grn_mapping = cost_price
        cost_price_change_log.save()



def run():
    products = Product.objects.filter(status='active')
    print(f"Products found :: {products.count()}")
    for product in products:
        grns = GRNOrderProductMapping.objects.filter(product=product).filter(product_invoice_qty__gt=0)\
        .filter(product_invoice_price__gt=0).order_by('-created_at')[:4]
        if grns:
            total_price = sum([ grn.product_amount for grn in grns])
            total_qty = sum([ grn.product_invoice_qty for grn in grns])
            cp = total_price / total_qty
            ProductGRNCostPriceMapping.objects.create(
                product = product,
                cost_price = cp,
                latest_grn = grns[0]
            )