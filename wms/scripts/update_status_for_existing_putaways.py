from django.db.models import Q, F

from wms.models import Putaway


def run():
    print('update_status_for_existing_putaways | STARTED')

    # Case 1
    putaways_qs_1 = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        filter(Q(status=Putaway.NEW) | Q(status=None)).filter(putaway_quantity=0). \
        exclude(putaway_user=None)
    print("Putaways having status is Null or New with putaway_quantity as 0 and putaway_user not Null, Count: " + str(
        putaways_qs_1.count()))
    if putaways_qs_1:
        putaways_qs_1.update(status=Putaway.ASSIGNED)
        print("Set status is ASSIGNED for putaways having status is Null or New with putaway_quantity as 0 and "
              "putaway_user not Null")

    # Case 2
    putaways_qs_2 = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        filter(Q(status=Putaway.NEW) | Q(status=None)). \
        filter(putaway_quantity=F("quantity")).exclude(putaway_user=None)
    print("Putaways having status is Null or New with putaway_quantity is equal to quantity and putaway_user not Null, "
          "Count: " + str(putaways_qs_2.count()))
    if putaways_qs_2:
        putaways_qs_2.update(status=Putaway.COMPLETED)
        print("Set status is COMPLETED for putaways having status is Null or New with "
              "putaway_quantity is equal to quantity and putaway_user not Null")

    # Case 3
    putaways_qs_3 = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        filter(Q(status=Putaway.NEW) | Q(status=None)).filter(putaway_quantity__gt=0). \
        filter(~Q(putaway_quantity=F("quantity"))).exclude(putaway_user=None)
    print("Putaways having status is Null or New with putaway_quantity is lesser than quantity and "
          "putaway_quantity is greater than 0 and putaway_user not Null, Count: " + str(putaways_qs_3.count()))
    if putaways_qs_3:
        putaways_qs_3.update(status=Putaway.ASSIGNED)
        print("Set status is COMPLETED for putaways having status is Null or New with putaway_quantity is lesser than "
              "quantity and putaway_quantity is greater than 0 and putaway_user not Null")

    # Case 4
    putaways_qs_4 = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        filter(status=None, putaway_user=None, putaway_quantity=0)
    print("Putaways having status is Null with putaway_quantity 0 and putaway_user is Null, Count: " + str(
        putaways_qs_4.count()))
    if putaways_qs_4:
        putaways_qs_4.update(status=Putaway.NEW)
        print("Set status is NEW for putaways having status is Null with putaway_quantity 0 and putaway_user is Null")

    # Case 5
    putaways_qs_5 = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        filter(status=Putaway.ASSIGNED, putaway_user__isnull=False, putaway_quantity=F("quantity"))
    print("Putaways having status is ASSIGNED with putaway_quantity is equal to quantity and putaway_user not Null, "
          "Count: " + str(putaways_qs_5.count()))
    if putaways_qs_5:
        putaways_qs_5.update(status=Putaway.COMPLETED)
        print("Set status is COMPLETED for putaways having status is ASSIGNED with putaway_quantity is equal to "
              "quantity and putaway_user not Null")

