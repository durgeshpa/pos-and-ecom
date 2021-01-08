from django.db import transaction
from django.db.models import Count, Q

from audit.models import AuditRun, AUDIT_RUN_STATUS_CHOICES, AuditNumberGenerator, AuditDetail, \
    AUDIT_DETAIL_STATUS_CHOICES, AUDIT_DETAIL_STATE_CHOICES
from sp_to_gram.tasks import es_mget_by_ids
from wms.models import BinInventory

def get_existing_audit_for_product(warehouse, sku):
    return sku.audit_product_mapping.filter(warehouse=warehouse,
                                            status=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE,
                                            state__in=[AUDIT_DETAIL_STATE_CHOICES.CREATED,
                                                       AUDIT_DETAIL_STATE_CHOICES.INITIATED]).order_by('pk')


def get_existing_audit_for_bin(warehouse, bin):
    return bin.audit_bin_mapping.filter(warehouse=warehouse,
                                        status=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE,
                                        state__in=[AUDIT_DETAIL_STATE_CHOICES.CREATED,
                                                   AUDIT_DETAIL_STATE_CHOICES.INITIATED]).order_by('pk')
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
    if product.use_parent_image and product.parent_product.parent_product_pro_image.exists():
        image_url = product.parent_product.parent_product_pro_image.last().image.url
    elif not product.use_parent_image and product.product_pro_image.exists():
        image_url = product.product_pro_image.last().image.url
    elif not product.use_parent_image and product.child_product_pro_image.exists():
        image_url = product.child_product_pro_image.last().image.url
    return image_url

def get_audit_start_time(audit_detail):
    '''
    Takes AuditDetail instance
    Returns audit start time if audit has been started else None
    '''
    if audit_detail.state > AUDIT_DETAIL_STATE_CHOICES.CREATED:
        return AuditRun.objects.filter(audit=audit_detail).last().created_at
    return None


def get_audit_complete_time(audit_detail):
    '''
    Takes AuditDetail instance
    Returns audit completion time if audit has been completed else None
    '''
    if audit_detail.state > AUDIT_DETAIL_STATE_CHOICES.INITIATED:
        return AuditRun.objects.filter(audit=audit_detail).last().completed_at
    return None

def time_diff_days_hours_mins_secs(dt2, dt1):
    diff_in_seconds = date_diff_in_seconds(dt2, dt1)
    days, hours, minutes, seconds = dhms_from_seconds(diff_in_seconds)
    time_string = ''
    if days > 0:
        time_string += '%d days' % days
    if hours > 0:
        time_string += ' %d hrs' % hours
    if minutes > 0:
        time_string += ' %d mins' % minutes
    if seconds > 0:
        time_string += ' %d secs' % seconds
    return time_string


def date_diff_in_seconds(dt2, dt1):
    timedelta = dt2 - dt1
    return timedelta.days * 24 * 3600 + timedelta.seconds


def dhms_from_seconds(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return (days, hours, minutes, seconds)


def get_audit_completion_time_string(audit_detail):
    '''
    Takes AuditDetail instance
    Returns audit duration if audit has been completed else None
    '''
    if audit_detail.state > AUDIT_DETAIL_STATE_CHOICES.INITIATED:
        audit_run = AuditRun.objects.filter(audit=audit_detail).last()
        return time_diff_days_hours_mins_secs(audit_run.completed_at, audit_run.created_at)
    return None

