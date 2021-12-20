import csv
import datetime

from django.db.models import Sum, F, FloatField
from django.http import HttpResponse

from retailer_to_sp.models import ReturnItems, RoundAmount, Invoice
from .models import PAYMENT_MODE_POS, RetailerProduct
from .views import get_product_details, get_tax_details


def create_order_data_excel(request, queryset):
    retailer_product_type = dict(((0, 'Free'),
                                  (1, 'Purchased')))

    filename = "Orders_data_{}.csv".format(datetime.date.today())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow([

        'Order No', 'Invoice No', 'Order Status', 'Order Created At', 'Invoice Date ', 'Seller Shop ID',
        'Seller Shop Name', 'Seller Shop Owner Id', 'Seller Shop Owner Name', 'Mobile No.(Seller Shop)',
        'Seller Shop Type', 'Buyer Id', 'Buyer Name', 'Mobile No(Buyer)', 'Purchased Product Id',
        'Purchased Product SKU', 'Purchased Product Name', 'Purchased Product Ean Code', 'Product Category',
        'Product SubCategory', 'Quantity', 'Invoice Quantity', 'Product Type', 'MRP', 'Selling Price',
        'Offer Applied', 'Offer Discount', 'Spot Discount', 'Order Amount', 'Invoice Amount',
        'Parent Id', 'Parent Name', 'Child Name', 'Brand', 'Tax Slab(GST)', 'Tax Slab(Cess)',
        'Tax Slab(Surcharge)', 'Tax Slab(TCS)'])

    orders = queryset \
        .prefetch_related('order', 'invoice', 'order__seller_shop', 'order__seller_shop__shop_owner',
                          'order__seller_shop__shop_type__shop_sub_type', 'order__buyer',
                          'rt_order_product_order_product_mapping',
                          'rt_order_product_order_product_mapping__retailer_product',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_parent',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_parent',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand',
                          'order__rt_payment_retailer_order__payment_type', 'order__ordered_cart', 'order__ordered_cart__rt_cart_list'
                          )\
        .annotate(
            purchased_subtotal=RoundAmount(Sum(F('order__ordered_cart__rt_cart_list__qty') * F('order__ordered_cart__rt_cart_list__selling_price'),output_field=FloatField())),
            ) \
        .values('id', 'order__order_no', 'invoice', 'invoice__invoice_no', 'order__order_status', 'order__created_at',
                'invoice__created_at', 'order__seller_shop__id', 'order__seller_shop__shop_name',
                'order__seller_shop__shop_owner__id', 'order__seller_shop__shop_owner__first_name',
                'order__seller_shop__shop_owner__phone_number',
                'order__seller_shop__shop_type__shop_sub_type__retailer_type_name',
                'order__buyer__id', 'order__buyer__first_name', 'order__buyer__phone_number',
                'rt_order_product_order_product_mapping__shipped_qty',
                'rt_order_product_order_product_mapping__product_type',
                'rt_order_product_order_product_mapping__selling_price',
                'rt_order_product_order_product_mapping__retailer_product__id',
                'rt_order_product_order_product_mapping__retailer_product__sku',
                'rt_order_product_order_product_mapping__retailer_product__name',
                'rt_order_product_order_product_mapping__retailer_product__mrp',
                'rt_order_product_order_product_mapping__retailer_product__selling_price',
                'rt_order_product_order_product_mapping__retailer_product__product_ean_code',
                'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_id',
                'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__name',
                'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_parent__category_name',
                'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_name',
                'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_parent__brand_name',
                'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_name',
                'purchased_subtotal', 'order__order_amount', 'invoice__shipment',
                'order__rt_payment_retailer_order__payment_type__type', 'order__ordered_cart__offers')

    for order in orders.iterator():
        shipment = Invoice.objects.filter(id=order.get('invoice')).last().shipment
        # try:
        #     inv_amount = shipment.rt_order_product_order_product_mapping.annotate(
        #         item_amount=F('effective_price') * F('shipped_qty')).aggregate(invoice_amount=Sum('item_amount')).get(
        #         'invoice_amount')
        # except:
        #     inv_amount = shipment.invoice_amount

        # inv_amount = shipment.rt_order_product_order_product_mapping. \
        #     filter(retailer_product_id=order.get('rt_order_product_order_product_mapping__retailer_product__id')).\
        #     annotate(item_amount=F('effective_price') * F('shipped_qty')).last().item_amount

        inv_qty = shipment.rt_order_product_order_product_mapping.\
            filter(retailer_product_id=order.get('rt_order_product_order_product_mapping__retailer_product__id')).last().shipped_qty

        retailer_product_id = order.get('rt_order_product_order_product_mapping__retailer_product__id')
        retailer_product = RetailerProduct.objects.get(id=retailer_product_id)
        tax_details = get_tax_details(retailer_product)
        product_type = order.get('rt_order_product_order_product_mapping__product_type')
        cart_offers = order['order__ordered_cart__offers']
        offers = list(filter(lambda d: d['type'] in 'discount', cart_offers))
        category = order[
            'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_parent__category_name']
        sub_category = order[
            'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_name']
        if not category:
            category = sub_category
            sub_category = None

        brand = order[
            'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_parent__brand_name']
        sub_brand = order[
            'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_name']
        if not brand:
            brand = sub_brand
            sub_brand = None
        writer.writerow([
            order.get('order__order_no'),
            order.get('invoice__invoice_no'),
            order.get('order__order_status'),
            order.get('order__created_at'),
            order.get('invoice__created_at'),
            order.get('order__seller_shop__id'),
            order.get('order__seller_shop__shop_name'),
            order.get('order__seller_shop__shop_owner__id'),
            order.get('order__seller_shop__shop_owner__first_name'),
            order.get('order__seller_shop__shop_owner__phone_number'),
            order.get('order__seller_shop__shop_type__shop_sub_type__retailer_type_name'),
            order.get('order__buyer__id'),
            order.get('order__buyer__first_name'),
            order.get('order__buyer__phone_number'),
            order.get('rt_order_product_order_product_mapping__retailer_product__id'),
            order.get('rt_order_product_order_product_mapping__retailer_product__sku'),
            order.get('rt_order_product_order_product_mapping__retailer_product__name'),
            order.get('rt_order_product_order_product_mapping__retailer_product__product_ean_code'),
            category,
            sub_category,
            order.get('rt_order_product_order_product_mapping__shipped_qty'),
            inv_qty,
            retailer_product_type.get(product_type, product_type),
            order.get('rt_order_product_order_product_mapping__retailer_product__mrp'),
            order.get('rt_order_product_order_product_mapping__selling_price'),
            offers[0].get('coupon_description', None) if len(offers) else None,
            offers[0].get('discount_value', None) if len(offers) else None,
            offers[0].get('spot_discount', None)
            if len(offers) else None,
            order.get('order__order_amount'),
            order.get('purchased_subtotal'),
            # inv_amount,
            order.get('rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_id'),
            order.get('rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__name'),
            brand,
            sub_brand,
            tax_details[0],
            tax_details[1],
            tax_details[2],
            tax_details[3]
        ])

    return response


def create_order_return_excel(queryset):
    filename = "Buyer_Return_sheet_{}.csv".format(datetime.date.today())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['Order No', 'Order Status', 'Order date', 'Credit Inv#', 'Sales Inv#', 'Store ID', 'Store Name',
                     'User', "Buyer", 'Buyer Mobile Number', 'EAN code', 'Item Name', 'Returned Qty', 'Selling Price',
                     'Returned Amount', 'MRP', 'Payment Mode', 'Product Category', 'Parent ID', 'SKU ID', 'Parent Name',
                     'Child Name', 'Sub Category', 'Brand'])

    returns = queryset. \
        prefetch_related('credit_note_order_return_mapping', 'credit_note_order_return_mapping__credit_note_id'). \
        values('order__order_no', 'order__order_status', 'order__created_at', 'order__seller_shop__id',
               'order__seller_shop__shop_name', 'processed_by__first_name', 'processed_by__last_name',
               'order__buyer__first_name', 'order__buyer__last_name', 'order__buyer__phone_number',
               'refund_amount', 'refund_mode', 'id', 'credit_note_order_return_mapping',
               'credit_note_order_return_mapping__credit_note_id', )

    return_mode_choice = dict(PAYMENT_MODE_POS)

    for order_rtn in returns.iterator():
        return_items = ReturnItems.objects.filter(return_id=order_rtn['id']). \
            select_related(
            'ordered_product', 'ordered_product__retailer_product', 'ordered_product__ordered_product',
            'ordered_product__ordered_product__invoice', 'ordered_product__retailer_product__linked_product'). \
            only('ordered_product__selling_price', 'return_qty', 'ordered_product__retailer_product__mrp',
                 'ordered_product__retailer_product__sku', 'ordered_product__retailer_product__name',
                 'ordered_product__retailer_product__product_ean_code', 'ordered_product__ordered_product__invoice',
                 'ordered_product__retailer_product__linked_product__product_name', )

        for item in return_items:
            refund_amt = item.return_qty * item.ordered_product.selling_price
            parent_id, category, sub_category, brand, sub_brand = get_product_details(
                item.ordered_product.retailer_product)
            selling_price, invoice_number, retailer_product_name, mrp, sku, name = None, None, None, None, None, None
            ean, product_name = None, None
            if item.ordered_product:
                selling_price = item.ordered_product.selling_price
                if item.ordered_product.ordered_product:
                    sales_invoice_number = item.ordered_product.ordered_product.invoice_no
                if item.ordered_product.retailer_product:
                    retailer_product_name = item.ordered_product.retailer_product.name
                    mrp = item.ordered_product.retailer_product.mrp
                    sku = item.ordered_product.retailer_product.sku
                    ean = item.ordered_product.retailer_product.product_ean_code
                    if item.ordered_product.retailer_product.linked_product:
                        product_name = item.ordered_product.retailer_product.linked_product.product_name
            writer.writerow([
                order_rtn.get('order__order_no'),  # Order No
                order_rtn.get('order__order_status'),  # Order Status
                order_rtn.get('order__created_at'),  # Order date
                order_rtn.get('credit_note_order_return_mapping__credit_note_id'),  # Credit Inv#
                sales_invoice_number,  # Sales Inv#
                order_rtn.get('order__seller_shop__id'),  # Store ID
                order_rtn.get('order__seller_shop__shop_name'),  # Store Name
                str(str(order_rtn.get('processed_by__first_name')) + " " + str(
                    order_rtn.get('processed_by__last_name'))).strip(),  # User
                str(str(order_rtn.get('order__buyer__first_name')) + " " + str(
                    order_rtn.get('order__buyer__last_name'))).strip(),  # Buyer
                order_rtn.get('order__buyer__phone_number'),  # Buyer Mobile Number
                ean,  # EAN code
                retailer_product_name,  # Item Name
                item.return_qty,  # Returned Qty
                selling_price,  # Selling Price
                refund_amt,  # Returned Amount
                mrp,  # MRP
                return_mode_choice.get(order_rtn.get('refund_mode')),  # Payment Mode
                category,  # Product Category
                parent_id,  # Parent ID
                sku,  # SKU ID
                product_name,  # Parent Name
                retailer_product_name,  # Child Name
                sub_category,  # Sub Category
                brand,  # Brand
            ])

    return response


def generate_prn_csv_report(queryset):
    filename = 'PRN_Report_{}.csv'.format(datetime.datetime.now().strftime("%m/%d/%Y--%H-%M-%S"))
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    csv_writer = csv.writer(response)
    csv_writer.writerow(
        [
            'PR NO.', 'STATUS', 'PO NO','PO DATE','GRN DATE','PRN UNIT PRICE', 'TAX TYPE','TAX RATE','STORE NAME',
            'PRODUCT', 'PRODUCT EAN CODE', 'PRODUCT SKU', 'PRODUCT TYPE', 'PRODUCT MRP',
            'PRODUCT PURCHASE PRICE', 'RETURN QTY', 'RETURN QTY UNIT',
            'GRN  QTY', 'GIVEN QTY UNIT', 'CREATED AT','Vendor Name', 'Vendor Address','Vendor State','phone_number'
        ]
    )
    rows = []
    for p_return in queryset:
        for return_item in p_return.grn_order_return.select_related('product').iterator():
            try:
                shop = p_return.grn_ordered_id.order.ordered_cart.retailer_shop
            except Exception:
                shop = None
            rows.append(
                [
                    p_return.pr_number,
                    p_return.status,
                    p_return.po_no,
                    p_return.grn_ordered_id.order.ordered_cart.created_at.strftime("%m/%d/%Y--%H-%M-%S") if p_return.grn_ordered_id else '',
                    p_return.grn_ordered_id.created_at.strftime("%m/%d/%Y--%H-%M-%S") if p_return.grn_ordered_id else '',
                    return_item.product.product_price,
                    return_item.product.product_tax.tax_type,
                    return_item.product.product_tax.tax_percentage,
                    shop,
                    return_item.product.name,
                    return_item.product.product_ean_code,
                    return_item.product.sku,
                    return_item.product.product_pack_type,
                    return_item.product.mrp,
                    return_item.selling_price,
                    return_item.return_qty,
                    return_item.given_qty_unit if return_item.given_qty_unit else 'PACK',
                    return_item.grn_received_qty if return_item.grn_return_id.grn_ordered_id else 0,
                    return_item.given_qty_unit if return_item.given_qty_unit else 'PACK',
                    p_return.created_at.strftime("%m/%d/%Y-%H:%M:%S"),
                    p_return.vendor_id.vendor_name if p_return.vendor_id else "",
                    p_return.vendor_id.address if p_return.vendor_id else '' ,
                    p_return.vendor_id.state if p_return.vendor_id else '' ,
                    p_return.vendor_id.alternate_phone_number if p_return.vendor_id else '' ,


                ]
            )
    csv_writer.writerows(rows)
    return response


def generate_csv_payment_report(payments):
    filename = "Buyer_payment_{}.csv".format(datetime.datetime.now().strftime("%m/%d/%Y--%H-%M-%S"))
    response = HttpResponse(content_type='text/csv')
    response["Content-Disposition"] = 'attachement; filename="{}"'.format(filename)
    csv_writer = csv.writer(response)
    csv_writer.writerow(
        [   'Order No',
            'Invoice No',
            'Invoice Date',
            'ORDER STATUS',
            'BILLING ADDRESS',
            'SELLER SHOP',
            'PAYMENT TYPE',
            'TRANSACTION ID',
            'Point Redemption',
            'Point Redemption Value',
            'Coupon NAME',
            'AMOUNT',
            'PAID BY',
            'PROCCESSED BY',
            'PAID AT'
        ]
    )
    rows = []
    for payment in payments:
        row = []
        row.append(payment.order.order_no)
        row.append(getattr(payment.order.shipments()[0],'invoice','')  if payment.order.shipments() else '')
        row.append(payment.order.shipments()[0].created_at.strftime("%m/%d/%Y-%H:%M:%S") if payment.order.shipments() else '')
        row.append(payment.order.get_order_status_display())
        row.append(payment.order.billing_address)
        row.append(payment.order.seller_shop)
        row.append(payment.payment_type)
        row.append(payment.transaction_id)
        row.append(payment.order.ordered_cart.redeem_points)
        row.append(payment.order.ordered_cart.redeem_points_value)
        offername = ''
        if payment.order.ordered_cart.offers :
            for coupon in payment.order.ordered_cart.offers:
                if coupon.get('type') == 'combo':
                    offername = offername + coupon.get('coupon_name', '')
                if coupon.get('type') == 'discount':
                    offername = offername +',' + coupon.get('coupon_name', '')
                if coupon.get('type') == 'discount' and coupon.get('sub_type') == 'spot_discount':
                    offername = offername +',' +  'spot_discount: {}'.format(coupon.get('discount'))+ " %" if coupon.get('is_percentage')==1 else ''
        row.append(offername.strip(','))
        row.append(payment.amount)
        row.append(payment.paid_by)
        row.append(payment.processed_by)
        row.append(payment.created_at.strftime("%m/%d/%Y-%H:%M:%S"))
        rows.append(row)





    # rows = [
    #     [
    #         payment.order.order_no,
    #         getattr(payment.order.shipments()[0],'invoice','')  if payment.order.shipments() else '',
    #         payment.order.shipments()[0].created_at.strftime("%m/%d/%Y-%H:%M:%S") if payment.order.shipments() else '',
    #         payment.order.get_order_status_display(),
    #         payment.order.billing_address,
    #         payment.order.seller_shop,
    #         payment.payment_type,
    #         payment.transaction_id,
    #         payment.order.ordered_cart.redeem_points,
    #         payment.order.ordered_cart.redeem_points_value,
    #         ",".join( coupon.get('coupon_name','') for coupon in  payment.order.ordered_cart.offers).strip(',') if payment.order.ordered_cart.offers else None ,
    #         payment.amount,
    #         payment.paid_by,
    #         payment.processed_by,
    #         payment.created_at.strftime("%m/%d/%Y-%H:%M:%S")
    #     ]
    #     for payment in payments
    # ]
    csv_writer.writerows(rows)
    return response

