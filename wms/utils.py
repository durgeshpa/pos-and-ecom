import csv
import datetime

from django.http import HttpResponse


def create_warehouse_assortment_excel(queryset):
    filename = "Warehouse_Assortment_sheet_{}.csv".format(datetime.date.today())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['warehouse_id', 'warehouse_name', 'product_id', 'product_name', 'zone_number', 'zone_supervisor',
                     'zone_coordinator'])

    assortments = queryset. \
        select_related('warehouse', 'product', 'zone'). \
        values('warehouse_id', 'warehouse__shop_name', 'product__parent_id', 'product__name', 'zone__zone_number',
               'zone__supervisor__phone_number', 'zone__supervisor__first_name',
               'zone__coordinator__phone_number', 'zone__coordinator__first_name',)

    for assortment in assortments.iterator():
        writer.writerow([
            assortment.get('warehouse_id'),  # Order No
            assortment.get('warehouse__shop_name'),  # Order Status
            assortment.get('product__parent_id'),  # Order date
            assortment.get('product__name'),  # Credit Inv#
            assortment.get('zone__zone_number'),  # Store ID
            str(str(assortment.get('zone__supervisor__phone_number')) + " - " + str(
                assortment.get('zone__supervisor__first_name'))).strip(),  # User
            str(str(assortment.get('zone__coordinator__phone_number')) + " - " + str(
                assortment.get('zone__coordinator__first_name'))).strip(),  # User
            # str(str(assortment.get('order__buyer__first_name')) + " " + str(
            #     assortment.get('order__buyer__last_name'))).strip(),  # Buyer
            # assortment.get('zone__coordinator'),  # Buyer Mobile Number
        ])

    return response


