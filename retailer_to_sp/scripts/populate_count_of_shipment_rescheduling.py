from django.db.models import F

from retailer_to_sp.models import ShipmentRescheduling


def run():
    print('populate_rescheduling_count_for_existing_data | STARTED')

    ship_rescheduling = ShipmentRescheduling.objects.filter(rescheduled_count=0)
    print(ship_rescheduling.count())
    ship_rescheduling.update(rescheduled_count=1)
    print("ship_rescheduling updation completed")
    print("Task completed")

