from datetime import datetime, timedelta

from django.db.models import F

from retailer_to_sp.models import Order, ShopCrate, Trip, LastMileTripShipmentMapping, OrderedProduct, \
    LastMileTripShipmentPackages, ShipmentPackaging
from wms.models import Crate


def run():
    print('create_last_mile_trip_shipment_mapping_for_existing_data | STARTED')

    # Update source shop as seller shop where source shop is empty
    Trip.objects.filter(source_shop__isnull=True).update(source_shop=F('seller_shop'))

    # create last mile trip shipment mapping for existing data
    shipments = OrderedProduct.objects.filter(trip__isnull=False, trip__last_mile_trip_shipments_details__isnull=True,
                                              trip__trip_status__in=['READY', 'STARTED', 'COMPLETED'],
                                              trip__created_at__gte='2022-02-01')

    for shipment in shipments:
        trip_shipment, created = LastMileTripShipmentMapping.objects.update_or_create(
            trip=shipment.trip, shipment=shipment,
            defaults={'shipment_status': LastMileTripShipmentMapping.LOADED_FOR_DC})
        LastMileTripShipmentPackages.objects.filter(trip_shipment=trip_shipment).delete()
        for package in ShipmentPackaging.objects.filter(
                shipment=trip_shipment.shipment, status=ShipmentPackaging.DISPATCH_STATUS_CHOICES.READY_TO_DISPATCH):
            LastMileTripShipmentPackages.objects.create(trip_shipment=trip_shipment, shipment_packaging=package,
                                                        package_status=LastMileTripShipmentPackages.LOADED)

        print(f"LastMileTripShipmentMapping entry {'created' if created else 'updated'}, Instance " + str(trip_shipment))

