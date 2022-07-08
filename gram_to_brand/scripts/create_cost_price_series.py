import logging
from datetime import datetime
from venv import create

from django.db import transaction
from django.db.models import Sum

from wms.models import BinInventory
from gram_to_brand.models import (ProductCostPriceChangeLog, ProductGRNCostPriceMapping,
                                  GRNOrderProductMapping)
from services.models import BinInventoryHistoric


logger = logging.getLogger('django')

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


def run():
    grns = GRNOrderProductMapping.objects.order_by('created_at')
    for grn in grns:
        create_cost_price(grn)

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
        grn = GRNOrderProductMapping.objects.filter(product=product).exclude(id=instance.pk).last()
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