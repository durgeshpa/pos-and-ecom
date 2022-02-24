from retailer_to_sp.models import OrderedProductMapping, OrderedProduct, Order
from services.models import OrderDetailReportsData
import xlrd

def update_redshift_data(lst):
        wb = xlrd.open_workbook('missing_redshift.xlsx')
        sheet = wb.sheet_by_index(0)
        sheet.cell_value(0, 0)
        for k in range(sheet.nrows - 1):
            lst.append(sheet.cell_value(k+1, 0))
        orders = Order.objects.filter(rt_order_order_product__invoice_no__in=lst)
        order_details = {}
        i = 0
        for order in orders:
            seller_shop = order.seller_shop
            for shipment in order.rt_order_order_product.all():
                for products in shipment.rt_order_product_order_product_mapping.all():
                    i += 1
                    product_id = products.product.id
                    product_name = products.product.product_name
                    product_brand = products.product.product_brand
                    # product_mrp = products.product.product_pro_price.get(status=True, shop = seller_shop).mrp
                    # product_value_tax_included = products.product.product_pro_price.get(status=True, shop = seller_shop).price_to_retailer
                    # New Price Logic
                    product_mrp = products.product.product_pro_price.filter(status=True,
                                                                            seller_shop=seller_shop).last().mrp
                    product_value_tax_included = products.product.product_pro_price.filter(status=True,
                                                                                           seller_shop=seller_shop).last().price_to_retailer
                    for price in order.ordered_cart.rt_cart_list.all():
                        selling_price = price.cart_product_price.selling_price
                        item_effective_price = price.item_effective_prices

                    if products.product.product_pro_tax.filter(tax__tax_type='gst').exists():
                        product_gst = products.product.product_pro_tax.filter(tax__tax_type='gst').last()
                    if order.shipping_address.state == order.seller_shop.shop_name_address_mapping.filter(
                            address_type='shipping').last().state:
                        product_cgst = (float(product_gst.tax.tax_percentage) / 2.0)
                        product_sgst = (float(product_gst.tax.tax_percentage) / 2.0)
                        product_igst = ''
                    else:
                        product_cgst = ''
                        product_sgst = ''
                        product_igst = (float(product_gst.tax.tax_percentage))
                    if products.product.product_pro_tax.filter(tax__tax_type='cess').exists():
                        product_cess = products.product.product_pro_tax.filter(
                            tax__tax_type='cess').last().tax.tax_percentage
                    else:
                        product_cess = ''
                    invoice_id = shipment.id
                    invoice_modified_at = shipment.modified_at
                    order_modified_at = order.modified_at
                    shipment_last_modified_by = shipment.last_modified_by
                    seller_shop = order.seller_shop
                    order_id = order.order_no
                    pin_code = order.shipping_address.pincode
                    order_status = order.get_order_status_display()
                    order_date = order.created_at
                    order_by = order.ordered_by
                    retailer_id = order.buyer_shop.id
                    retailer_name = order.buyer_shop
                    order_invoice = shipment.invoice_no
                    invoice_date = shipment.created_at
                    invoice_status = shipment.get_shipment_status_display()
                    ordered_sku_pieces = products.ordered_qty
                    shipped_sku_pieces = products.shipped_qty
                    delivered_sku_pieces = products.delivered_qty
                    returned_sku_pieces = products.returned_qty
                    damaged_sku_pieces = products.damaged_qty
                    sales_person_name = "{} {}".format(order.ordered_by.first_name, order.ordered_by.last_name)
                    order_type = ''
                    campaign_name = ''
                    discount = ''
                    trip = ''
                    trip_id = ''
                    trip_status = ''
                    delivery_boy = ''
                    trip_created_at = None
                    if shipment and shipment.trip:
                        trip = shipment.trip.dispatch_no
                        trip_id = shipment.trip.id
                        trip_status = shipment.trip.trip_status
                        delivery_boy = shipment.trip.delivery_boy
                        trip_created_at = shipment.trip.created_at
                    OrderDetailReportsData.objects.using('gfanalytics').create(invoice_id=invoice_id,
                                                                               order_invoice=order_invoice,
                                                                               invoice_date=invoice_date,
                                                                               invoice_modified_at=invoice_modified_at,
                                                                               invoice_last_modified_by=shipment_last_modified_by,
                                                                               invoice_status=invoice_status,
                                                                               order_id=order_id,
                                                                               seller_shop=seller_shop,
                                                                               order_status=order_status,
                                                                               order_date=order_date,
                                                                               order_modified_at=order_modified_at,
                                                                               order_by=order_by,
                                                                               retailer_id=retailer_id,
                                                                               retailer_name=retailer_name,
                                                                               pin_code=pin_code, product_id=product_id,
                                                                               product_name=product_name,
                                                                               product_brand=product_brand,
                                                                               product_mrp=product_mrp,
                                                                               product_value_tax_included=product_value_tax_included,
                                                                               ordered_sku_pieces=ordered_sku_pieces,
                                                                               shipped_sku_pieces=shipped_sku_pieces,
                                                                               delivered_sku_pieces=delivered_sku_pieces,
                                                                               returned_sku_pieces=returned_sku_pieces,
                                                                               damaged_sku_pieces=damaged_sku_pieces,
                                                                               product_cgst=product_cgst,
                                                                               product_sgst=product_sgst,
                                                                               product_igst=product_igst,
                                                                               product_cess=product_cess,
                                                                               sales_person_name=sales_person_name,
                                                                               order_type=order_type,
                                                                               campaign_name=campaign_name,
                                                                               discount=discount, trip=trip,
                                                                               trip_id=trip_id, trip_status=trip_status,
                                                                               delivery_boy=delivery_boy,
                                                                               trip_created_at=trip_created_at,
                                                                               selling_price=selling_price,
                                                                               item_effective_price=item_effective_price)
                    order_details[i] = {'invoice_id': invoice_id, 'order_invoice': order_invoice,
                                        'invoice_date': invoice_date, 'invoice_modified_at': invoice_modified_at,
                                        'shipment_last_modified_by': shipment_last_modified_by,
                                        'invoice_status': invoice_status, 'order_id': order_id,
                                        'seller_shop': seller_shop, 'order_status': order_status,
                                        'order_date': order_date, 'order_modified_at': order_modified_at,
                                        'order_by': order_by, 'retailer_id': retailer_id,
                                        'retailer_name': retailer_name, 'pin_code': pin_code, 'product_id': product_id,
                                        'product_name': product_name, 'product_brand': product_brand,
                                        'product_mrp': product_mrp,
                                        'product_value_tax_included': product_value_tax_included,
                                        'ordered_sku_pieces': ordered_sku_pieces,
                                        'shipped_sku_pieces': shipped_sku_pieces,
                                        'delivered_sku_pieces': delivered_sku_pieces,
                                        'returned_sku_pieces': returned_sku_pieces,
                                        'damaged_sku_pieces': damaged_sku_pieces, 'product_cgst': product_cgst,
                                        'product_sgst': product_sgst, 'product_igst': product_igst,
                                        'product_cess': product_cess, 'sales_person_name': sales_person_name,
                                        'order_type': order_type, 'campaign_name': campaign_name, 'discount': discount,
                                        'trip': trip, 'trip_id': trip_id, 'trip_status': trip_status,
                                        'delivery_boy': delivery_boy, 'trip_created_at': trip_created_at,
                                        'selling_price': selling_price, 'item_effective_price': item_effective_price}

        data = order_details
        return data

lst=[]

def update_missing_data():
    update_redshift_data(lst)
