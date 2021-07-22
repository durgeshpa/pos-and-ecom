
import csv
import datetime
import re

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
        'Return Id', 'Return Status', 'Return Processed By', 
        # 'Return Product Id', 'Return Product SKU', 'Return Product Name', 'Quantity','Product Type', 'Selling Price', 
        'Refunded amount', 'Discount Adjusted', 'Refund Point', 'Refund Mode', 'Return Created At'])

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
                'rt_order_product_order_product_mapping__retailer_product__id','rt_order_product_order_product_mapping__retailer_product__sku',
                'rt_order_product_order_product_mapping__retailer_product__name', 'rt_order_product_order_product_mapping__shipped_qty',
                'rt_order_product_order_product_mapping__product_type', 'rt_order_product_order_product_mapping__retailer_product__selling_price',
                'purchased_subtotal', 'order__order_amount',)

    
    count = 0
    prev_order_no = 0
    for order in orders.iterator():
        
        return_order = RetailerOrderReturn.objects.filter(order__order_no = order.get('order__order_no'))
        if len(return_order) > 0 and prev_order_no != order.get('order__order_no'):
            return_dict = return_order\
            .values('id','status', 'processed_by__first_name', 'refund_amount', 
                    'discount_adjusted', 'refund_points', 'refund_mode',
                    'created_at')
            count = 0

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
            order.get('rt_order_product_order_product_mapping__retailer_product__id'),
            order.get('rt_order_product_order_product_mapping__retailer_product__sku'),
            order.get('rt_order_product_order_product_mapping__retailer_product__name'),
            order.get('rt_order_product_order_product_mapping__shipped_qty'),
            retailer_product_type.get(
                order.get('rt_order_product_order_product_mapping__product_type'),
                order.get('rt_order_product_order_product_mapping__product_type')),
            order.get('rt_order_product_order_product_mapping__retailer_product__selling_price'),
            order.get('purchased_subtotal'),
            order.get('order__order_amount'),
            return_dict[count].get('id')
            if len(return_order) > 0 and count < len(return_dict) else None,
            return_dict[count].get('status')
            if len(return_order) > 0 and count < len(return_dict) else None,
            return_dict[count].get('processed_by__first_name')
            if len(return_order) > 0 and count < len(return_dict) else None,
            return_dict[count].get('refund_amount')
            if len(return_order) > 0 and count < len(return_dict) else None,
            return_dict[count].get('discount_adjusted')
            if len(return_order) > 0 and count < len(return_dict) else None,
            return_dict[count].get('refund_points')
            if len(return_order) > 0 and count < len(return_dict) else None,
            return_dict[count].get('refund_mode')
            if len(return_order) > 0 and count < len(return_dict) else None,
            return_dict[count].get('created_at')
            if len(return_order) > 0 and count < len(return_dict) else None,
        ])
        count += 1
        prev_order_no = order.get('order__order_no')
        
    return response
