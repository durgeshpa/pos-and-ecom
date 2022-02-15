from django.db.models import Q, F, Subquery

from retailer_to_sp.models import Order
from wms.models import Putaway, QCDeskQCAreaAssignmentMapping


def run():
    release_stucked_qc_areas_by_cron()


def release_stucked_qc_areas_by_cron():
    print('release_stucked_qc_areas | STARTED')

    query = """
    select * from retailer_to_sp_order where order_no in (
        select token_id from wms_qcdeskqcareaassignmentmapping where qc_done is false and token_id not in (
            select order_no from retailer_to_sp_order where order_status in 
            ('PICKING_PARTIAL_COMPLETE', 'picking_complete', 'MOVED_TO_QC', 'PARTIAL_MOVED_TO_QC')
        )
    )
    """

    orders = Order.objects.raw(query)
    order_nos = [x.order_no for x in orders]
    print(f"Releasing QC Areas against orders, Count {len(order_nos)}, List {order_nos}")
    mappings = QCDeskQCAreaAssignmentMapping.objects.filter(token_id__in=order_nos, qc_done=False)
    released_qc_areas = mappings.values_list("qc_area__area_id", flat=True)
    print(f"Released QC Areas, Count {len(released_qc_areas)}, List {released_qc_areas}")
    mappings.update(qc_done=True)

    print('release_stucked_qc_areas | ENDED')
