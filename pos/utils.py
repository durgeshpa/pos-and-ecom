import csv
import datetime
from io import StringIO

from django.db.models import Sum, F, FloatField
from django.http import HttpResponse

from retailer_to_sp.models import ReturnItems, RoundAmount, Invoice, Order
from retailer_to_sp.utils import round_half_down
from .models import PAYMENT_MODE_POS, RetailerProduct, Payment, PaymentType
from .views import get_product_details, get_tax_details


def create_order_data_excel(queryset, request=None):
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
        'Purchased Product SKU', 'Linked Sku', 'Purchased Product Name', 'Purchased Product Ean Code',
        'B2B Category', 'B2B Sub Category', 'B2C Category', 'B2C Sub Category', 'Quantity', 'Invoice Quantity',
        'Product Type', 'MRP', 'Selling Price', 'Item wise Amount', 'Offer Applied', 'Offer Discount',
        'Spot Discount', 'Order Amount', 'Invoice Amount', 'Parent Id', 'Parent Name', 'Child Name', 'Brand',
        'Tax Slab(GST)', 'Tax Slab(Cess)', 'Tax Slab(Surcharge)', 'Tax Slab(TCS)', 'Redeemed Points',
        'Redeemed Points Value'])

    orders = queryset \
        .prefetch_related('order', 'invoice', 'order__seller_shop', 'order__seller_shop__shop_owner',
                          'order__seller_shop__shop_type__shop_sub_type', 'order__buyer',
                          'rt_order_product_order_product_mapping',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__product_sku',
                          'rt_order_product_order_product_mapping__retailer_product',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_parent',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_b2c_category__category__category_parent',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_b2c_category__category',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_parent',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand',
                          'order__rt_payment_retailer_order__payment_type', 'order__ordered_cart', 'order__ordered_cart__rt_cart_list'
                          )\
        .annotate(
            purchased_subtotal=RoundAmount(Sum(F('order__ordered_cart__rt_cart_list__qty') * F('order__ordered_cart__rt_cart_list__selling_price'),output_field=FloatField())),
            ) \
        .values('id', 'rt_order_product_order_product_mapping__retailer_product__linked_product',
                'rt_order_product_order_product_mapping__retailer_product__linked_product__product_sku',
                'order__order_no', 'invoice', 'invoice__invoice_no', 'order__order_status', 'order__created_at',
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
                'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_b2c_category__category__category_parent__category_name',
                'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_b2c_category__category__category_name',
                'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_parent__brand_name',
                'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_name',
                'purchased_subtotal', 'order__order_amount', 'invoice__shipment',
                'order__rt_payment_retailer_order__payment_type__type', 'order__ordered_cart__offers',
                'order__ordered_cart__redeem_points')

    for order in orders.iterator():
        redeem_points_value = None
        shipment = Invoice.objects.filter(id=order.get('invoice')).last().shipment
        if shipment:
            redeem_points_value = shipment.order.ordered_cart.redeem_points_value
        try:
            inv_amount = round_half_down(shipment.invoice_amount_final)
        except:
            inv_amount = shipment.invoice_amount

        order_product_mapping = shipment.rt_order_product_order_product_mapping.\
            filter(retailer_product_id=order.get('rt_order_product_order_product_mapping__retailer_product__id')).\
            last()
        inv_qty = order_product_mapping.shipped_qty
        product_inv_price = order_product_mapping.product_total_price

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

        b2c_category = order[
            'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_b2c_category__category__category_parent__category_name']
        b2c_sub_category = order[
            'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_b2c_category__category__category_name']
        if not b2c_category:
            b2c_category = b2c_sub_category
            b2c_sub_category = None

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
            order.get('rt_order_product_order_product_mapping__retailer_product__linked_product__product_sku'),
            order.get('rt_order_product_order_product_mapping__retailer_product__name'),
            order.get('rt_order_product_order_product_mapping__retailer_product__product_ean_code'),
            category,
            sub_category,
            b2c_category,
            b2c_sub_category,
            order.get('rt_order_product_order_product_mapping__shipped_qty'),
            inv_qty,
            retailer_product_type.get(product_type, product_type),
            order.get('rt_order_product_order_product_mapping__retailer_product__mrp'),
            order.get('rt_order_product_order_product_mapping__selling_price'),
            product_inv_price,
            offers[0].get('coupon_description', None) if len(offers) else None,
            offers[0].get('discount_value', None) if offers and offers[0].get('sub_type') != "spot_discount" else None,
            offers[0].get('discount_value', None) if offers and offers[0].get('sub_type') == "spot_discount" else None,
            order.get('order__order_amount'),
            inv_amount,
            order.get('rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_id'),
            order.get('rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__name'),
            brand,
            sub_brand,
            tax_details[0],
            tax_details[1],
            tax_details[2],
            tax_details[3],
            order.get('order__ordered_cart__redeem_points'),
            redeem_points_value
        ])

    return response

from retailer_to_sp.models import CartProductMapping
def create_cancel_order_csv(request, queryset):
    """creat csv file cancel order """
    filename = "cancel order{}.csv".format(datetime.date.today())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow([
        'Order No', 'Order Status', 'Order Created At', 'Seller Shop ID',
        'Seller Shop Name', 'Seller Shop Owner Id', 'Seller Shop Owner Name', 'Mobile No.(Seller Shop)',
        'Seller Shop Type', 'Buyer Id', 'Buyer Name', 'Mobile No(Buyer)', 'Purchased Product Id',
        'Purchased Product SKU', 'Linked Sku', 'Purchased Product Name', 'Purchased Product Ean Code',
        'Quantity', 'MRP', 'Selling Price',
        'Total price'])


    orders = queryset.prefetch_related('order', 'invoice', 'seller_shop', 'seller_shop__shop_owner',
                          'seller_shop__shop_type__shop_sub_type', 'buyer',
                          'rt_order_cart_mapping',
                          'rt_cart_product_mapping',
                          'rt_cart_product_mapping__retailer_product__linked_product__product_sku',
                          'rt_cart_product_mapping__retailer_product',
                          'rt_cart_product_mapping__retailer_product__linked_product',
                          'rt_cart_product_mapping__retailer_product__linked_product__parent_product',
                          'rt_cart_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_parent',
                          'rt_cart_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category',
                          'rt_cart_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_parent',
                          'rt_cart_product_mapping__retailer_product__linked_product__parent_product__parent_brand',
                          )\
        .annotate(
            purchased_subtotal=RoundAmount(Sum(F('rt_cart_list__qty') * F('rt_cart_list__selling_price'),output_field=FloatField())),
            )
    for order in orders.iterator():
        products = CartProductMapping.objects.filter(cart=order)

        for product in products:
            try:
                writer.writerow([
                        order.order_id,
                        order.rt_order_cart_mapping.order_status if order.rt_order_cart_mapping.order_status else '',
                        order.rt_order_cart_mapping.created_at if order.rt_order_cart_mapping.order_status else '' ,
                        order.seller_shop.id if order.seller_shop else '',
                        order.seller_shop.shop_name if order.seller_shop else '',
                        order.seller_shop.shop_owner.id if order.seller_shop.shop_owner else '',
                        order.seller_shop.shop_owner.first_name if order.seller_shop.shop_owner else '',
                        order.seller_shop.shop_owner.phone_number if order.seller_shop.shop_owner else '',
                        order.seller_shop.shop_type.shop_sub_type.retailer_type_name if  order.seller_shop.shop_type.shop_sub_type else '',
                        order.buyer.id if order.buyer.id else '',
                        order.buyer.first_name if order.buyer else '',
                        order.buyer.phone_number if order.buyer else '',

                        product.retailer_product.id if product.retailer_product else '',
                        product.retailer_product.sku if product.retailer_product else '',
                        product.retailer_product.linked_product.product_sku if product.retailer_product.linked_product else '',
                        product.retailer_product.name if product.retailer_product else "",
                        product.retailer_product.product_ean_code if product.retailer_product else '',

                        product.qty ,
                        product.retailer_product.mrp if product.retailer_product else '',
                        product.retailer_product.selling_price,
                        product.qty*product.retailer_product.selling_price
                    ])
            except:
                pass
    return response







def create_order_return_excel(queryset):
    filename = "Buyer_Return_sheet_{}.csv".format(datetime.date.today())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['Order No', 'Order Status', 'Order date', 'Credit Inv#', 'Sales Inv#', 'Store ID', 'Store Name',
                     'User', "Buyer", 'Buyer Mobile Number', 'EAN code', 'Item Name', 'Returned Qty', 'Selling Price',
                     'Returned Amount', 'MRP', 'Payment Mode', 'Parent ID', 'SKU ID', 'Parent Name', 'Child Name',
                     'B2B Category', 'B2B Sub Category', 'B2C Category', 'B2C Sub Category', 'Brand', 'Cart_Type'])

    returns = queryset. \
        prefetch_related('credit_note_order_return_mapping', 'credit_note_order_return_mapping__credit_note_id'). \
        values('order__order_no', 'order__order_status', 'order__created_at', 'order__seller_shop__id',
               'order__seller_shop__shop_name', 'processed_by__first_name', 'processed_by__last_name',
               'order__buyer__first_name', 'order__buyer__last_name', 'order__buyer__phone_number',
               'refund_amount', 'refund_mode', 'id', 'credit_note_order_return_mapping',
               'credit_note_order_return_mapping__credit_note_id', 'order__ordered_cart__cart_type')

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
            parent_id, category, sub_category, b2c_category, b2c_sub_category, brand, sub_brand = get_product_details(
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
                parent_id,  # Parent ID
                sku,  # SKU ID
                product_name,  # Parent Name
                retailer_product_name,  # Child Name
                category,  # Product Category
                sub_category,  # Sub Category
                b2c_category,
                b2c_sub_category,
                brand,  # Brand
                order_rtn.get('order__ordered_cart__cart_type'),
            ])

    return response


def generate_prn_csv_report(queryset):
    filename = 'PRN_Report_{}.csv'.format(datetime.datetime.now().strftime("%m/%d/%Y--%H-%M-%S"))
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    csv_writer = csv.writer(response)
    csv_writer.writerow(
        [
            'PR NO.', 'STATUS', 'PO NO', 'PO DATE', 'GRN DATE', 'Shop Name', 'PRN UNIT PRICE', 'GST Tax','Cess_Tax','Surcharge_Tax',
            'Total Tax',
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
            gst_tax, cess_tax, surcharge_tax = '', '', ''
            total_tax = 0
            if return_item.product.linked_product:
                if return_item.product.linked_product.product_pro_tax is not None:
                    for tax in return_item.product.linked_product.product_pro_tax.all():
                        if tax.tax.tax_type == 'gst':
                            gst_tax = tax.tax.tax_percentage
                            total_tax += tax.tax.tax_percentage
                        elif tax.tax.tax_type == 'cess':
                            cess_tax = tax.tax.tax_percentage
                            total_tax += tax.tax.tax_percentage
                        elif tax.tax.tax_type == 'surcharge':
                            surcharge_tax = tax.tax.tax_percentage
                            total_tax += tax.tax.tax_percentage

            rows.append(
                [
                    p_return.pr_number,
                    p_return.status,
                    p_return.po_no,
                    p_return.grn_ordered_id.order.ordered_cart.created_at.strftime("%m/%d/%Y--%H-%M-%S") if p_return.grn_ordered_id else '',
                    p_return.grn_ordered_id.created_at.strftime("%m/%d/%Y--%H-%M-%S") if p_return.grn_ordered_id else '',
                    shop if shop else return_item.product.shop,
                    return_item.product.product_price,
                    gst_tax,
                    cess_tax,
                    surcharge_tax,
                    total_tax,
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
                    p_return.vendor_id.vendor_name if p_return.vendor_id else p_return.grn_ordered_id.order.ordered_cart.vendor.vendor_name if p_return.grn_ordered_id else "",
                    p_return.vendor_id.address if p_return.vendor_id else p_return.grn_ordered_id.order.ordered_cart.vendor.address if p_return.grn_ordered_id else  "",
                    p_return.vendor_id.state if p_return.vendor_id else p_return.grn_ordered_id.order.ordered_cart.vendor.state if p_return.grn_ordered_id else "",
                    p_return.vendor_id.alternate_phone_number if p_return.vendor_id else p_return.grn_ordered_id.order.ordered_cart.vendor.alternate_phone_number if p_return.grn_ordered_id else  "",


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
        [
            'Order No',
            'Order Created At',
            'Delivery Option',
            'Invoice No',
            'Invoice Date',
            'ORDER STATUS',
            'BILLING ADDRESS',
            'SELLER SHOP',
            'PAYMENT TYPE',
            'TRANSACTION ID',
            'Point Redemption',
            'Point Redemption Value',
            'combo offer',
            'coupon discount',
            'coupon discount value',
            'Max coupon discount',
            'spot discount',
            'spot discount value',
            'Order Amount',
            'Invoice Amount',
            'PAID BY',
            'PROCCESSED BY',
            'PAID AT',
            'PickUp Time',
            'Delivery Start Time',
            'Delivery End Time'
        ]
    )
    rows = []
    for payment in payments:
        inv_amt = None
        payment_types = PaymentType.objects.filter(type__in=['cod', 'cash'])
        if payment and (payment.payment_type in payment_types or
                        payment.payment_status not in [Payment.PAYMENT_PENDING, Payment.PAYMENT_FAILED,
                                                       'payment_not_found']):
            if payment.order.order_app_type == Order.POS_WALKIN:
                inv_amt = payment.amount
            elif payment.order.order_app_type == Order.POS_ECOMM and payment.payment_type.type == 'cod' \
                    and payment.order.order_status in [Order.DELIVERED, Order.PARTIALLY_RETURNED, Order.FULLY_RETURNED]:
                inv_amt = payment.amount
            elif payment.order.order_app_type == Order.POS_ECOMM and payment.payment_type.type in ['cod_upi', 'credit',
                                                                                                   'online'] \
                    and payment.order.order_status in [Order.DELIVERED, Order.PARTIALLY_RETURNED, Order.FULLY_RETURNED,
                                                       Order.OUT_FOR_DELIVERY]:
                inv_amt = payment.amount

        row = []
        row.append(payment.order.order_no)
        row.append(payment.order.created_at.strftime('%m/%d/%Y-%H-%M-%S'))
        row.append(payment.order.get_delivery_option_display())
        row.append(getattr(payment.order.shipments()[0],'invoice','')  if payment.order.shipments() else '')
        row.append(payment.order.shipments()[0].created_at.strftime("%m/%d/%Y-%H:%M:%S") if payment.order.shipments() else '')
        row.append(payment.order.get_order_status_display())
        row.append(payment.order.billing_address)
        row.append(payment.order.seller_shop)
        row.append(payment.payment_type)
        row.append(payment.transaction_id)
        row.append(payment.order.ordered_cart.redeem_points)
        row.append(payment.order.ordered_cart.redeem_points_value)
        max_discount = ''
        combo_offer = ''
        coupon_discount = ''
        coupon_discount_v = ''
        spot_discount = ''
        spot_discount_v = ''
        if payment.order.ordered_cart.offers :
            for coupon in payment.order.ordered_cart.offers:
                if coupon.get('type') == 'combo':
                    combo_offer = coupon.get('coupon_name', '')
                if coupon.get('type') == 'discount' and coupon.get('sub_type') == 'set_discount':
                    coupon_discount = coupon.get('coupon_name', '')
                    coupon_discount_v = "Rs. " + str(coupon.get('discount_value'))
                    max_discount = "Maximum discount {}".format(coupon.get('max_discount')) if coupon.get('max_discount') else ''

                if coupon.get('type') == 'discount' and coupon.get('sub_type') == 'spot_discount':
                    spot_discount = (str(coupon.get('discount'))+" % ") if coupon.get('is_percentage') else 'Rs.' + str(coupon.get('discount'))
                    spot_discount_v = str(coupon.get('discount_value'))

        row.append(combo_offer)
        row.append(coupon_discount)
        row.append(coupon_discount_v)
        row.append(max_discount)
        row.append(spot_discount)
        row.append(spot_discount_v)
        row.append(payment.amount)
        row.append(inv_amt)
        row.append(payment.paid_by)
        row.append(payment.processed_by)
        row.append(payment.created_at.strftime("%m/%d/%Y-%H:%M:%S"))
        if payment.order.rt_order_order_product.last():
            if payment.order.rt_order_order_product.last().rt_order_product_order_product_mapping.last():
                pickup_time = payment.order.rt_order_order_product.last().rt_order_product_order_product_mapping.last().\
                    created_at.strftime('%m/%d/%Y-%H-%M-%S') if payment.order.rt_order_order_product.last().\
                    rt_order_product_order_product_mapping.last().\
                    created_at.strftime('%m/%d/%Y-%H-%M-%S') else ''
                row.append(pickup_time)

            if payment.order.rt_order_order_product.last().pos_trips.last():
                trip_start_at = payment.order.rt_order_order_product.last().pos_trips.last().\
                    trip_start_at.strftime('%m/%d/%Y-%H-%M-%S') if payment.order.rt_order_order_product.last().pos_trips.last().\
                    trip_start_at.strftime('%m/%d/%Y-%H-%M-%S') else ''
                row.append(trip_start_at)

                trip_end_at = payment.order.rt_order_order_product.last().pos_trips.last().\
                    trip_end_at.strftime('%m/%d/%Y-%H-%M-%S') if payment.order.rt_order_order_product.last().pos_trips.last().\
                    trip_end_at.strftime('%m/%d/%Y-%H-%M-%S') else ''
                row.append(trip_end_at)
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


def download_grn_cvs(queryset):
    f = StringIO()
    writer = csv.writer(f)
    writer.writerow(
        ['GRN Id', 'GRN DATE', 'PO No', 'PO DATE', 'PO Status', 'GRN Amount', 'Bill amount', 'Supplier Invoice No',
         'Invoice Date', 'Invoice Amount', 'Created At', 'Vendor', 'Vendor Address', 'Vendor State', 'Vendor GST NO.',
         'Store Id', 'Store Name', 'Shop User', 'SKU', 'Product Name', 'Parent Product', 'B2B Category',
         'B2B Sub Category', 'B2C Category', 'B2C Sub Category', 'Brand', 'Sub Brand', 'PO Qty', 'GST Tax',
         'Cess_Tax', 'Surcharge_Tax', 'Total Tax', 'Unit Price', 'Total Tax value', 'Recieved Quantity'])
    rows = []

    for obj in queryset:

        for p in obj.po_grn_products.all():
            parent_id, b2b_category, b2b_sub_category, b2c_category, b2c_sub_category, brand, sub_brand = get_product_details(p.product)
            gst_tax, cess_tax, surcharge_tax = '', '', ''
            total_tax = 0
            original_amount = 0

            if p.product.linked_product:
                if p.product.linked_product.product_pro_tax is not None:
                    for tax in p.product.linked_product.product_pro_tax.all():
                        if tax.tax.tax_type == 'gst':
                            gst_tax = tax.tax.tax_percentage
                            total_tax += tax.tax.tax_percentage
                        elif tax.tax.tax_type == 'cess':
                            cess_tax = tax.tax.tax_percentage
                            total_tax += tax.tax.tax_percentage
                        elif tax.tax.tax_type == 'surcharge':
                            surcharge_tax = tax.tax.tax_percentage
                            total_tax += tax.tax.tax_percentage
                if total_tax:
                    divisor = (1 + (total_tax / 100))
                    original_amount = round(float(p.grn_order.order.ordered_cart.po_products.filter(
                        product_id=p.product_id).first().total_price()) / float(divisor), 3)

            writer.writerow(
                [obj.grn_id, p.grn_order.created_at.strftime('%d-%m-%y  %I:%M %p'), obj.order.ordered_cart.po_no,
                 obj.order.ordered_cart.created_at.strftime('%d-%m-%y  %I:%M %p'),
                 obj.order.ordered_cart.status,
                 p.received_qty * p.product.product_price,
                 p.grn_order.order.ordered_cart.po_products.filter(product_id=p.product_id).first().total_price(),
                 obj.invoice_no, obj.invoice_date,
                 obj.invoice_amount, obj.created_at,
                 obj.order.ordered_cart.vendor, obj.order.ordered_cart.vendor.address,
                 obj.order.ordered_cart.vendor.state,
                 obj.order.ordered_cart.vendor.gst_number,
                 obj.order.ordered_cart.retailer_shop.id,
                 obj.order.ordered_cart.retailer_shop.shop_name,
                 obj.order.ordered_cart.retailer_shop.shop_owner,
                 p.product.sku, p.product.name, parent_id, b2b_category, b2b_sub_category, b2c_category,
                 b2c_sub_category, brand, sub_brand, p.grn_order.order.ordered_cart.po_products.filter(product_id=p.product_id).first().qty,
                 gst_tax, cess_tax, surcharge_tax, total_tax if total_tax else '',
                 p.grn_order.order.ordered_cart.po_products.filter(product_id=p.product_id).first().price,
                 round(((float(original_amount) * total_tax) / 100), 3) if total_tax else '',
                 p.received_qty])

    f.seek(0)
    response = HttpResponse(f, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=pos_grns_' + datetime.datetime.now().strftime("%m/%d/%Y--%H-%M-%S") + '.csv'
    return response