from gram_to_brand.models import GRNOrder
from wms.models import Putaway, WarehouseAssortment, In


def run():
    print('update_zone_reference_id_in_putaway | STARTED')
    # Zone updation
    putaways = Putaway.objects.filter(zone__isnull=True)
    for p in putaways:
        zone = WarehouseAssortment.objects.filter(warehouse=p.warehouse, product=sku.parent_product).zone
        p.zone = zone
        p.save()
    # Zone updation
    # assortments = WarehouseAssortment.objects.all()
    # total_assortments = assortments.count()
    # for cnt, assortment in enumerate(assortments):
    #     Putaway.objects.filter(warehouse=assortment.warehouse, sku__parent_product=assortment.product).\
    #         update(zone=assortment.zone)
    #     print(f"{cnt + 1} / {total_assortments} | Updated zone {assortment.zone} for warehouse {assortment.warehouse}"
    #           f" & all products under parent product {assortment.product}")
    #
    # # Reference id updation
    # putaways = Putaway.objects.filter(
    #     putaway_type='GRN', status__in=[Putaway.NEW, Putaway.ASSIGNED, Putaway.INITIATED]).order_by('-id')
    # total_putaways = putaways.count()
    # for cn, putaway in enumerate(putaways):
    #     in_instance = In.objects.filter(id=putaway.putaway_type_id).last()
    #     if in_instance and in_instance.in_type_id:
    #         grn_order = GRNOrder.objects.filter(grn_id=in_instance.in_type_id).last()
    #         if grn_order:
    #             putaway.reference_id = grn_order.id
    #             putaway.save()
    #             print(f"{cn + 1} / {total_putaways} | Reference id {grn_order.id} for GRN {in_instance.in_type_id} "
    #                   f"updated for putaway id {putaway}")
    #
    # print('update_zone_reference_id_in_putaway | ENDED')
