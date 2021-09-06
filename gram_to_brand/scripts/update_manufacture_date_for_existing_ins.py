from django.db import transaction
from gram_to_brand.models import GRNOrderProductMapping
from wms.models import In


def run():
    print("Started updating manufacturing date for existing GRN type Ins.")
    update_existing_ins()
    print("Task completed")

@transaction.atomic
def update_existing_ins():
    """
    Update Manufacturing date for existing GRN type Ins.
    """
    ins_objects = get_all_non_manufacturing_date_ins(in_type='GRN')
    print("Working for In objects, Count: ", ins_objects.count())
    for cnt, ins_obj in enumerate(ins_objects):
        mapping = get_grn_order_product_mapping(ins_obj.in_type_id, ins_obj.sku, ins_obj.batch_id, ins_obj.quantity)
        if mapping is not None and mapping.manufacture_date:
            ins_obj.manufacturing_date = mapping.manufacture_date
            ins_obj.save()
            print(cnt, "Updated manufactured date:", mapping.manufacture_date, " for In id: ", ins_obj.id)
        else:
            print(cnt, "No manufacture_date exist for GRN id: ", mapping)

def get_all_non_manufacturing_date_ins(in_type):
    """
    To get all In objects where no manufacturing date exists for corresponding type
    """
    return In.objects.filter(manufacturing_date=None, in_type=in_type)


def get_grn_order_product_mapping(in_type_id, sku, batch_id, quantity):
    """
    To get GRNOrderProductMapping object where some conditions matched
    """
    print("inside get_grn_order_product_mapping, in_type_id = ", in_type_id, ", sku = ", sku,
          ", batch_id = ", batch_id, ", quantity = ", quantity)
    objs = GRNOrderProductMapping.objects.filter(
        product=sku, grn_order__grn_id=in_type_id, delivered_qty=quantity, batch_id=batch_id)
    if objs.count() > 1:
        print("Multiple GRNOrderProductMapping exists for in_type_id = ", in_type_id, ", sku = ", sku,
              ", batch_id = ", batch_id, ", quantity = ", quantity)
    return objs.last()
