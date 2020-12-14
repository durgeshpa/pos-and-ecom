from django.db import transaction
from django.db.models import Count, Q

from audit.models import AuditRun, AUDIT_RUN_STATUS_CHOICES, AuditNumberGenerator, AuditDetail
from sp_to_gram.tasks import es_mget_by_ids
from wms.models import BinInventory


def get_next_audit_no(audit):
    audit_no_generator = AuditNumberGenerator.objects.filter(audit_run_type=audit.audit_run_type,
                                                             audit_level=audit.audit_level).last()
    if audit_no_generator:
        audit_no_generator.current_number = audit_no_generator.current_number + 1
        audit_no_generator.save()

    else:
        count = AuditDetail.objects.filter(audit_run_type=audit.audit_run_type,
                                           audit_level=audit.audit_level).count()
        audit_no_generator = AuditNumberGenerator.objects.create(audit_run_type=audit.audit_run_type,
                                                                 audit_level=audit.audit_level,
                                                                 current_number=count)
    return audit_no_generator.current_number




def get_products_by_audit(audit_detail):
    products_to_update = []
    if audit_detail.audit_level == 1:
        products_to_update.extend(audit_detail.sku.all())
    if audit_detail.audit_level == 0:
        if audit_detail.bin.count() != 0:
            products_to_update.extend(get_products_by_bin(audit_detail.warehouse, audit_detail.bin.all()))
    return products_to_update


def get_es_status(product_list, warehouse):
    es_products = es_mget_by_ids(warehouse.id, {'ids': get_product_ids_from_product_list(product_list)})
    es_product_status = {}
    for p in es_products['docs']:
        es_product_status[int(p['_id'])] = p['_source']['status'] if p['found'] else False
    return es_product_status


def get_product_ids_from_product_list(product_list):
    product_id_list = []
    for p in product_list:
        product_id_list.append(p.id)
    return product_id_list


def get_products_by_bin(warehouse, bins):
    bin_inventory = BinInventory.objects.filter(warehouse=warehouse, bin_id__in=bins)
    product_list = []
    for b in bin_inventory:
        product_list.append(b.sku)
    return product_list

def is_audit_started(audit):
    return AuditRun.objects.filter(audit=audit, status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS).exists()


def is_diff_batch_in_this_bin(warehouse, batch_id, bin, sku):
    return BinInventory.objects.filter(~Q(batch_id=batch_id),
                                       warehouse=warehouse,
                                       bin=bin,
                                       sku=sku,
                                       quantity__gt=0).exists()


def get_product_image(product):
    image_url = ''
    if product.product_pro_image.exists():
        image_url = product.product_pro_image.last().image.url
    return image_url

