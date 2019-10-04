from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F,Sum, Q
from shops.models import Shop
from gram_to_brand.models import Order as PurchaseOrder, GRNOrder
import requests
from decouple import config
from  services.models import RetailerReports, OrderReports,GRNReports, MasterReports, OrderGrnReports, OrderDetailReports, CategoryProductReports
from products.models import Product

@receiver(post_save, sender=Product)
def get_category_product_report(sender, instance=None, created=False, **kwargs):
    print("hit")
    requests.post(config('REDSHIFT_URL')+'/analytics/api/v1/product-category-report/', data={'id':instance.id})


@receiver(post_save, sender=GRNOrder)
def get_grn_report(sender, instance=None, created=False, **kwargs):
    if instance:
        for products in instance.grn_order_grn_order_product.all():
            try:
                product_id = products.product.id
                product_name = products.product.product_name
                product_brand = products.product.product_brand
                product_mrp = products.product.product_vendor_mapping.filter(product=products.product).last().product_mrp
                gram_to_brand_price = instance.grn_order_grn_order_product.filter(
                    product=products.product).last().po_product_price

                if products.product.product_pro_tax.filter(tax__tax_type='gst').exists():
                    product_gst = products.product.product_pro_tax.filter(tax__tax_type='gst').last()
                if instance.order.ordered_cart.supplier_state == instance.ordered_cart.gf_shipping_address.state:
                    product_cgst = (float(product_gst.tax.tax_percentage) / 2.0)
                    product_sgst = (float(product_gst.tax.tax_percentage) / 2.0)
                    product_igst = ''
                else:
                    product_cgst = ''
                    product_sgst = ''
                    product_igst = (float(product_gst.tax.tax_percentage))
                if products.product.product_pro_tax.filter(tax__tax_type='cess').exists():
                    product_cess = products.product.product_pro_tax.filter(tax__tax_type='cess').last().tax.tax_percentage
                else:
                    product_cess = ''
                po_no = instance.order.order_no
                po_date = instance.order.created_at
                po_status = instance.order.ordered_cart.get_po_status_display()
                vendor_name = instance.order.ordered_cart.supplier_name
                vendor_id = instance.order.ordered_cart.supplier_name.id
                buyer_shop = instance.order.ordered_cart.gf_shipping_address.shop_name
                shipping_address = instance.order.ordered_cart.gf_shipping_address.address_line1
                category_manager = ''
                manufacture_date = instance.grn_order_grn_order_product.get(product=products.product).manufacture_date
                expiry_date = instance.grn_order_grn_order_product.get(product=products.product).expiry_date
                po_sku_pieces = instance.grn_order_grn_order_product.get(
                    product=products.product).po_product_quantity if products.product else ''
                discount = ''
                grn_id = instance.grn_id
                grn_date = instance.created_at
                grn_sku_pieces = instance.grn_order_grn_order_product.get(
                    product=products.product).product_invoice_qty if products.product else ''
                invoice_item_gross_value = (instance.grn_order_grn_order_product.get(
                    product=products.product).product_invoice_qty) * (gram_to_brand_price)
                delivered_sku_pieces = instance.grn_order_grn_order_product.get(
                    product=products.product).delivered_qty if products.product else ''
                returned_sku_pieces = instance.grn_order_grn_order_product.get(
                    product=products.product).returned_qty if products.product else ''
                dn_number = ''
                dn_value_basic = ''
                GRNReports.objects.using('gfanalytics').create(po_no=po_no, po_date=po_date, po_status=po_status,
                                                               vendor_name=vendor_name, vendor_id=vendor_id,
                                                               buyer_shop=buyer_shop, shipping_address=shipping_address,
                                                               category_manager=category_manager, product_id=product_id,
                                                               product_name=product_name, product_brand=product_brand,
                                                               manufacture_date=manufacture_date, expiry_date=expiry_date,
                                                               po_sku_pieces=po_sku_pieces, product_mrp=product_mrp,
                                                               discount=discount, gram_to_brand_price=gram_to_brand_price,
                                                               grn_id=grn_id, grn_date=grn_date,
                                                               grn_sku_pieces=grn_sku_pieces, product_cgst=product_cgst,
                                                               product_sgst=product_sgst, product_igst=product_igst,
                                                               product_cess=product_cess,
                                                               invoice_item_gross_value=invoice_item_gross_value,
                                                               delivered_sku_pieces=delivered_sku_pieces,
                                                               returned_sku_pieces=returned_sku_pieces, dn_number=dn_number,
                                                               dn_value_basic=dn_value_basic)

            except:
                pass

def get_grn_report(self, shop_id, start_date, end_date):

    buyer_shop = Shop.objects.get(pk=shop_id)
    orders = PurchaseOrder.objects.filter(ordered_cart__gf_shipping_address__shop_name = buyer_shop)
    if start_date:
        orders = orders.filter(created_at__gte = start_date)
    if end_date:
        orders = orders.filter(created_at__lte = end_date)
    grn_details = {}
    i=0
    for order in orders:
        for grns in order.order_grn_order.all():
            for products in grns.grn_order_grn_order_product.all():
                i += 1
                try:
                    product_id = products.product.id
                    product_name = products.product.product_name
                    product_brand = products.product.product_brand
                    product_mrp = products.product.product_vendor_mapping.filter(product = products.product).last().product_mrp
                    gram_to_brand_price = grns.grn_order_grn_order_product.filter(product = products.product).last().po_product_price
                    #product_value_tax_included = products.product.product_pro_price.get(status=True, shop = buyer_shop).price_to_retailer
                    if products.product.product_pro_tax.filter(tax__tax_type ='gst').exists():
                        product_gst = products.product.product_pro_tax.filter(tax__tax_type ='gst').last()
                    if order.ordered_cart.supplier_state == order.ordered_cart.gf_shipping_address.state:
                        product_cgst = (float(product_gst.tax.tax_percentage)/2.0)
                        product_sgst = (float(product_gst.tax.tax_percentage)/2.0)
                        product_igst = ''
                    else:
                        product_cgst = ''
                        product_sgst = ''
                        product_igst = (float(product_gst.tax.tax_percentage))
                    if products.product.product_pro_tax.filter(tax__tax_type ='cess').exists():
                        product_cess = products.product.product_pro_tax.filter(tax__tax_type ='cess').last().tax.tax_percentage
                    else:
                        product_cess = ''
                    po_no = order.order_no
                    po_date = order.created_at
                    po_status = order.ordered_cart.get_po_status_display()
                    vendor_name = order.ordered_cart.supplier_name
                    vendor_id = order.ordered_cart.supplier_name.id
                    buyer_shop = order.ordered_cart.gf_shipping_address.shop_name
                    shipping_address = order.ordered_cart.gf_shipping_address.address_line1
                    category_manager = ''
                    manufacture_date = grns.grn_order_grn_order_product.get(product = products.product).manufacture_date
                    expiry_date = grns.grn_order_grn_order_product.get(product = products.product).expiry_date
                    po_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).po_product_quantity if products.product else ''
                    discount = ''
                    grn_id = grns.grn_id
                    grn_date = grns.created_at
                    grn_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).product_invoice_qty if products.product else ''
                    invoice_item_gross_value = (grns.grn_order_grn_order_product.get(product = products.product).product_invoice_qty) * (gram_to_brand_price)
                    delivered_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).delivered_qty if products.product else ''
                    returned_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).returned_qty if products.product else ''
                    dn_number = ''
                    dn_value_basic =''
                    GRNReports.objects.using('gfanalytics').create(po_no = po_no, po_date = po_date, po_status = po_status, vendor_name = vendor_name,  vendor_id = vendor_id, buyer_shop=buyer_shop, shipping_address = shipping_address, category_manager = category_manager, product_id = product_id, product_name = product_name, product_brand = product_brand, manufacture_date = manufacture_date, expiry_date = expiry_date, po_sku_pieces = po_sku_pieces, product_mrp = product_mrp, discount = discount,  gram_to_brand_price = gram_to_brand_price, grn_id = grn_id, grn_date = grn_date, grn_sku_pieces = grn_sku_pieces, product_cgst = product_cgst, product_sgst = product_sgst, product_igst = product_igst, product_cess = product_cess, invoice_item_gross_value = invoice_item_gross_value, delivered_sku_pieces = delivered_sku_pieces, returned_sku_pieces = returned_sku_pieces, dn_number = dn_number, dn_value_basic = dn_value_basic)
                    grn_details[i] = { 'po_no':po_no, 'po_date':po_date, 'po_status':po_status, 'vendor_name':vendor_name, 'vendor_id':vendor_id, 'buyer_shop':buyer_shop, 'shipping_address':shipping_address, 'category_manager':category_manager, 'product_id':product_id, 'product_name':product_name, 'product_brand':product_brand, 'manufacture_date':manufacture_date, 'expiry_date':expiry_date, 'po_sku_pieces':po_sku_pieces, 'product_mrp':product_mrp, 'discount':discount, 'gram_to_brand_price':gram_to_brand_price, 'grn_id':grn_id, 'grn_date':grn_date, 'grn_sku_pieces':grn_sku_pieces, 'product_cgst':product_cgst, 'product_sgst':product_sgst, 'product_igst':product_igst, 'product_cess':product_cess, 'invoice_item_gross_value':invoice_item_gross_value, 'delivered_sku_pieces':delivered_sku_pieces, 'returned_sku_pieces':returned_sku_pieces, 'dn_number':dn_number, 'dn_value_basic':dn_value_basic}
                except:
                    pass
    data = grn_details
    return data