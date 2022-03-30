from products.common_function import ParentProductCls
from products.models import ParentProduct, ProductHsnGst, ProductHsnCess

#
def run():
    print('tax_update_parent_product | STARTED')

    parent_products = ParentProduct.objects.filter(
        tax_status__isnull=True, product_hsn__isnull=False, parent_product_pro_tax__isnull=False,
        product_hsn__hsn_gst__isnull=True)
    total = parent_products.count()
    print(f"Total: {total}")

    for cnt, parent_product in enumerate(parent_products):
        print(f"{cnt}/{total} | {parent_product} | {parent_product.id}")
        gst_tax_map = parent_product.parent_product_pro_tax.filter(tax__tax_type="gst").last()
        gst_tax = gst_tax_map.tax.tax_percentage if gst_tax_map else None
        cess_tax_map = parent_product.parent_product_pro_tax.filter(tax__tax_type="cess").last()
        cess_tax = cess_tax_map.tax.tax_percentage if cess_tax_map else None
        product_hsn = parent_product.product_hsn
        if gst_tax is not None:
            hsn_gst = ProductHsnGst.objects.update_or_create(
                product_hsn=product_hsn, gst=int(gst_tax), defaults={"created_by": parent_product.updated_by})
            print(f"{parent_product} | {parent_product.id} | HSN GST {hsn_gst} created.")
        if cess_tax is not None:
            hsn_cess = ProductHsnCess.objects.update_or_create(
                product_hsn=product_hsn, cess=int(cess_tax), defaults={"created_by": parent_product.updated_by})
            print(f"{parent_product} | {parent_product.id} | HSN CESS {hsn_cess} created.")
        ParentProductCls.update_tax_status_and_remark(parent_product)

    print('tax_update_parent_product | ENDED')



