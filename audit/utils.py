from audit.models import AuditRun, AUDIT_RUN_STATUS_CHOICES, AUDIT_RUN_TYPE_CHOICES, AUDIT_LEVEL_CHOICES
from sp_to_gram.tasks import es_mget_by_ids
from wms.models import BinInventory


def create_audit_no(audit):
    if audit.audit_run_type == AUDIT_RUN_TYPE_CHOICES.AUTOMATED:
        audit_no = audit.id
    else:
        audit_no = 'A_'
        if audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
            audit_no += 'B'
        elif audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
            audit_no += 'P'
        audit_id_str = str(audit.id)
        audit_id_str.zfill(3)
        audit_no += audit_id_str
    return audit_no


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

