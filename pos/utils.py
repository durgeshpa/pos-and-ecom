
import csv
import datetime

from django.http import HttpResponse
from django.db.models import Sum, F, FloatField, OuterRef, Subquery, Case, Value, When, Q
from retailer_backend.utils import time_diff_days_hours_mins_secs


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

    orders = queryset\
        .annotate(
            purchased_subtotal=RoundAmount(Sum(F('order__ordered_cart__rt_cart_list__qty') * F('order__ordered_cart__rt_cart_list__selling_price'),output_field=FloatField())),
            # purchased_reward_point = Case(
            #                             When(order__ordered_cart__redeem_factor = 0, then = Value(0.0)),
            #                             default=Value(F('order__rt_order_cart_mapping__redeem_points') / F('order__rt_order_cart_mapping__redeem_factor')),
            #                             output_field=FloatField(),
            #                         )
            )\
        .values('order__order_no', 'invoice__invoice_no', 'order__order_status', 'order__created_at', 
                'order__seller_shop__id', 'order__seller_shop__shop_name' ,
                'order__seller_shop__shop_owner__first_name', 'order__seller_shop__shop_owner__phone_number',
                'order__seller_shop__shop_type__shop_type',
                'order__buyer__first_name', 'order__buyer__phone_number',
                "rt_order_product_order_product_mapping__id",
                'purchased_subtotal', 'order__order_amount',)
    print(orders)


    for order in orders.iterator():
        print(order)
        # order_prod = RetailerOrderedProduct.objects.get(order__order_no = order.get('order__order_no'))
        # print(order_prod.order.order_no)
        order_prod_mapping = RetailerOrderedProductMapping.objects.get(id = order.get('rt_order_product_order_product_mapping__id'))
        return_item = order_prod_mapping.rt_return_ordered_product.all()

        no_of_product_return = 0
        cost = 0

        for item in return_item:
            no_of_product_return += item.return_qty

        if order_prod_mapping.product_type:
            cost = (no_of_product_return * order_prod_mapping.retailer_product.selling_price)
        
        if no_of_product_return:
            order.update({'return_qty':no_of_product_return, 'refund_amount': cost})

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
