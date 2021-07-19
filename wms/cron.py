import logging

from django.db.models import F, Subquery, OuterRef

from wms.models import BinInventory, In

cron_logger = logging.getLogger('cron_log')

def create_move_discounted_products():
    inventory = BinInventory.objects.filter(inventory_type__inventory_type='normal', quantity__gt=0)\
                                    .annotate(discounted_life='sku__parent_product__discounted_life_percent',
                                              manufacturing_date=Subquery(In.objects.filter(batch_id=OuterRef('batch_id')).last().manufacturing_date))
