from django.db.models import Count

from products.models import ParentProduct, ProductHsnGst, ProductHsnCess, ProductHSN


#
def run():
    print('remove_duplicate_hsns | STARTED')

    dup_hsns = ProductHSN.objects.values('product_hsn_code').annotate(Count('id')).order_by().filter(id__count__gt=1)
    total = dup_hsns.count()
    for cnt, code in enumerate(dup_hsns):
        print(f"\n\n{cnt+1}/{total}|HSN {code['product_hsn_code']} | Duplicate count {code['id__count']}")
        hsn_instances = ProductHSN.objects.filter(product_hsn_code=code['product_hsn_code'])
        gst_taxes = list(hsn_instances.filter(hsn_gst__isnull=False).values_list('hsn_gst__gst', flat=True).distinct())
        cess_taxes = list(hsn_instances.filter(hsn_cess__isnull=False).values_list('hsn_cess__cess', flat=True).distinct())
        hsn_ins = hsn_instances.first()
        print(f"HSN {code['product_hsn_code']} | GSTs {gst_taxes}")
        print(f"HSN {code['product_hsn_code']} | CESSs {cess_taxes}")
        print(f"HSN {code['product_hsn_code']} | Selected HSN ID {hsn_ins.pk}")
        if gst_taxes:
            for gst_tax in gst_taxes:
                if not ProductHsnGst.objects.filter(product_hsn=hsn_ins, gst=gst_tax).exists():
                    print(f"HSN {code['product_hsn_code']} | GST {gst_tax}")
                    ProductHsnGst.objects.create(product_hsn=hsn_ins, gst=gst_tax, created_by_id=9)
        if cess_taxes:
            for cess_tax in cess_taxes:
                if not ProductHsnCess.objects.filter(product_hsn=hsn_ins, cess=cess_tax).exists():
                    print(f"HSN {code['product_hsn_code']} | CESS {cess_tax}")
                    ProductHsnCess.objects.create(product_hsn=hsn_ins, cess=cess_tax, created_by_id=9)

        mapped_products = ParentProduct.objects.filter(product_hsn__product_hsn_code=code['product_hsn_code'])
        print(f"HSN {code['product_hsn_code']} | Product count {mapped_products.count()} | "
              f"Products {list(mapped_products.values_list('id', flat=True))}")
        if mapped_products.count() > 0:
            break
        mapped_products.update(product_hsn=hsn_ins, tax_status=ParentProduct.APPROVED, tax_remark=None)

        to_be_removed_hsns = ProductHSN.objects.filter(product_hsn_code=code['product_hsn_code']).exclude(id=hsn_ins.pk)
        for removed_hsn in to_be_removed_hsns:
            delete_hsn(removed_hsn)

    print('remove_duplicate_hsns | ENDED')


def delete_hsn(hsn_instance):
    if hsn_instance.hsn_gst.all().exists():
        hsn_instance.hsn_gst.all().delete()
        print(f"HSN {hsn_instance.product_hsn_code} | All GST mapped deleted.")
    if hsn_instance.hsn_cess.all().exists():
        hsn_instance.hsn_cess.all().delete()
        print(f"HSN {hsn_instance.product_hsn_code} | All CESS mapped deleted.")
    hsn_instance.delete()
    print(f"HSN {hsn_instance.product_hsn_code} | Deleted.")

