import csv
import datetime

from django.db.models import Sum, F, FloatField
from django.http import HttpResponse

from retailer_to_sp.models import ReturnItems
from .models import PAYMENT_MODE_POS
from .views import get_product_details


def create_order_data_excel(request, queryset, RetailerOrderedProduct,
                            RetailerOrderedProductMapping, Order, RetailerOrderReturn,
                            RoundAmount, RetailerReturnItems, Shop):
    retailer_product_type = dict(((0, 'Free'),
                                  (1, 'Purchased')))

    filename = "Orders_data_{}.csv".format(datetime.date.today())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow([
        'Order No', 'Invoice No', 'Order Status', 'Order Created At', 'Seller Shop ID',
        'Seller Shop Name', 'Seller Shop Owner Name', 'Mobile No.(Seller Shop)', 'Seller Shop Type', 'Buyer Name',
        'Mobile No(Buyer)', 'Purchased Product Id', 'Purchased Product SKU', 'Purchased Product Name', 'Quantity',
        'Product Type', 'Selling Price', 'Subtotal', 'Order Amount',
        # 'Return Id', 'Return Status', 'Return Processed By', 
        # 'Return Product Id', 'Return Product SKU', 'Return Product Name', 'Quantity','Product Type', 'Selling Price', 
        'Return Quantity', 'Return Amount'])

    orders = queryset \
        .annotate(
        purchased_subtotal=RoundAmount(
            Sum(F('order__ordered_cart__rt_cart_list__qty') * F('order__ordered_cart__rt_cart_list__selling_price'),
                output_field=FloatField())),
        # purchased_reward_point = Case(
        #                             When(order__ordered_cart__redeem_factor = 0, then = Value(0.0)),
        #                             default=Value(F('order__rt_order_cart_mapping__redeem_points') / F('order__rt_order_cart_mapping__redeem_factor')),
        #                             output_field=FloatField(),
        #                         )
    ) \
        .values('order__order_no', 'invoice__invoice_no', 'order__order_status', 'order__created_at',
                'order__seller_shop__id', 'order__seller_shop__shop_name',
                'order__seller_shop__shop_owner__first_name', 'order__seller_shop__shop_owner__phone_number',
                'order__seller_shop__shop_type__shop_type',
                'order__buyer__first_name', 'order__buyer__phone_number',
                "rt_order_product_order_product_mapping__id",
                'purchased_subtotal', 'order__order_amount', )

    for order in orders.iterator():
        order_prod_mapping = RetailerOrderedProductMapping.objects.get(
            id=order.get('rt_order_product_order_product_mapping__id'))
        return_item = order_prod_mapping.rt_return_ordered_product.all()

        no_of_product_return = 0
        cost = 0

        for item in return_item:
            no_of_product_return += item.return_qty

        if order_prod_mapping.product_type:
            cost = (no_of_product_return * order_prod_mapping.retailer_product.selling_price)

        if no_of_product_return:
            order.update({'return_qty': no_of_product_return, 'refund_amount': cost})

        writer.writerow([
            order.get('order__order_no'),
            order.get('invoice__invoice_no'),
            order.get('order__order_status'),
            order.get('order__created_at'),
            order.get('order__seller_shop__id'),
            order.get('order__seller_shop__shop_name'),
            order.get('order__seller_shop__shop_owner__first_name'),
            order.get('order__seller_shop__shop_owner__phone_number'),
            order.get('order__seller_shop__shop_type__shop_type'),
            order.get('order__buyer__first_name'),
            order.get('order__buyer__phone_number'),
            order_prod_mapping.retailer_product.id,
            order_prod_mapping.retailer_product.sku,
            order_prod_mapping.retailer_product.name,
            # order.get('rt_order_product_order_product_mapping__shipped_qty'),
            # retailer_product_type.get(
            #     order.get('rt_order_product_order_product_mapping__product_type'),
            #     order.get('rt_order_product_order_product_mapping__product_type')),
            order_prod_mapping.shipped_qty,
            retailer_product_type.get(
                order_prod_mapping.product_type,
                order_prod_mapping.product_type),
            order_prod_mapping.retailer_product.selling_price,
            order.get('purchased_subtotal'),
            order.get('order__order_amount'),
            order.get('return_qty', None),
            order.get('refund_amount', None)
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
