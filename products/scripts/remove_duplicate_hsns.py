import logging

from django.db.models import Count, F
from django.db.models.functions import Substr

from products.models import ParentProduct, ProductHsnGst, ProductHsnCess, ProductHSN

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')


def run():
    trim_zero()
    remove_duplicate_hsns()
    remove_unmapped_hsns()


def trim_zero():
    print(f"trim_zero | Started")
    info_logger.info(f"trim_zero | Started")
    hsns = ProductHSN.objects.filter(product_hsn_code__startswith='0')
    hsns_list = list(hsns.values_list('product_hsn_code', flat=True))
    print(f"HSN to be trimmed count: {len(hsns_list)}, List {hsns_list}")
    info_logger.info(f"HSN to be trimmed count: {len(hsns_list)}, List {hsns_list}")
    hsns.update(product_hsn_code=Substr('product_hsn_code', 2, 15))
    print(f"trim_zero | Ended")
    info_logger.info(f"trim_zero | Ended")


def remove_unmapped_hsns():
    print('remove_unmapped_hsns | STARTED')
    info_logger.info('remove_unmapped_hsns | STARTED')
    hsns = ProductHSN.objects.filter(parent_hsn__isnull=True)
    for hsn in hsns:
        print(f"Deleted Unmapped HSN {hsn.pk} -> {hsn.product_hsn_code}")
        info_logger.info(f"Deleted Unmapped HSN {hsn.pk} -> {hsn.product_hsn_code}")
        delete_hsn(hsn)
    print(f"remove_unmapped_hsns | Ended")
    info_logger.info(f"remove_unmapped_hsns | Ended")


def remove_duplicate_hsns():
    print('remove_duplicate_hsns | STARTED')
    info_logger.info('remove_duplicate_hsns | STARTED')
    dup_hsns = ProductHSN.objects.values('product_hsn_code').annotate(Count('id')).order_by().filter(id__count__gt=1)
    total = dup_hsns.count()
    for cnt, code in enumerate(dup_hsns):
        print(f"\n\n{cnt+1}/{total}|HSN {code['product_hsn_code']} | Duplicate count {code['id__count']}")
        info_logger.info(f"\n\n{cnt+1}/{total}|HSN {code['product_hsn_code']} | Duplicate count {code['id__count']}")
        hsn_instances = ProductHSN.objects.filter(product_hsn_code=code['product_hsn_code'])
        gst_taxes = list(hsn_instances.filter(hsn_gst__isnull=False).values_list('hsn_gst__gst', flat=True).distinct())
        cess_taxes = list(hsn_instances.filter(hsn_cess__isnull=False).values_list('hsn_cess__cess', flat=True).distinct())
        hsn_ins = hsn_instances.first()
        print(f"HSN {code['product_hsn_code']} | GSTs {gst_taxes}")
        info_logger.info(f"HSN {code['product_hsn_code']} | GSTs {gst_taxes}")
        print(f"HSN {code['product_hsn_code']} | CESSs {cess_taxes}")
        info_logger.info(f"HSN {code['product_hsn_code']} | CESSs {cess_taxes}")
        print(f"HSN {code['product_hsn_code']} | Selected HSN ID {hsn_ins.pk}")
        info_logger.info(f"HSN {code['product_hsn_code']} | Selected HSN ID {hsn_ins.pk}")
        if gst_taxes:
            for gst_tax in gst_taxes:
                if not ProductHsnGst.objects.filter(product_hsn=hsn_ins, gst=gst_tax).exists():
                    print(f"HSN {code['product_hsn_code']} | GST {gst_tax}")
                    info_logger.info(f"HSN {code['product_hsn_code']} | GST {gst_tax}")
                    ProductHsnGst.objects.create(product_hsn=hsn_ins, gst=gst_tax, created_by_id=9)
        if cess_taxes:
            for cess_tax in cess_taxes:
                if not ProductHsnCess.objects.filter(product_hsn=hsn_ins, cess=cess_tax).exists():
                    print(f"HSN {code['product_hsn_code']} | CESS {cess_tax}")
                    info_logger.info(f"HSN {code['product_hsn_code']} | CESS {cess_tax}")
                    ProductHsnCess.objects.create(product_hsn=hsn_ins, cess=cess_tax, created_by_id=9)

        mapped_products = ParentProduct.objects.filter(product_hsn__product_hsn_code=code['product_hsn_code'])
        print(f"HSN {code['product_hsn_code']} | Product count {mapped_products.count()} | "
              f"Products {list(mapped_products.values_list('id', flat=True))}")
        info_logger.info(f"HSN {code['product_hsn_code']} | Product count {mapped_products.count()} | "
                         f"Products {list(mapped_products.values_list('id', flat=True))}")
        mapped_products.update(product_hsn=hsn_ins, tax_status=ParentProduct.APPROVED, tax_remark=None)

        to_be_removed_hsns = ProductHSN.objects.filter(product_hsn_code=code['product_hsn_code']).exclude(id=hsn_ins.pk)
        for removed_hsn in to_be_removed_hsns:
            delete_hsn(removed_hsn)
    print('remove_duplicate_hsns | ENDED')
    info_logger.info('remove_duplicate_hsns | ENDED')


def delete_hsn(hsn_instance):
    if hsn_instance.hsn_gst.all().exists():
        hsn_instance.hsn_gst.all().delete()
        print(f"HSN {hsn_instance.product_hsn_code} | All GST mapped deleted.")
        info_logger.info(f"HSN {hsn_instance.product_hsn_code} | All GST mapped deleted.")
    if hsn_instance.hsn_cess.all().exists():
        hsn_instance.hsn_cess.all().delete()
        print(f"HSN {hsn_instance.product_hsn_code} | All CESS mapped deleted.")
        info_logger.info(f"HSN {hsn_instance.product_hsn_code} | All CESS mapped deleted.")
    hsn_instance.delete()
    print(f"HSN {hsn_instance.product_hsn_code} | Deleted.")
    info_logger.info(f"HSN {hsn_instance.product_hsn_code} | Deleted.")

