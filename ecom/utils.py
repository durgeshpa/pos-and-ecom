import datetime
import csv
from functools import wraps
from decimal import Decimal

from django.db.models import Sum, F, FloatField
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework import status

from shops.models import Shop
from wms.models import PosInventory, PosInventoryState
from retailer_to_sp.models import RoundAmount, OrderedProduct
from .models import Address
from pos.models import RetailerProduct


def api_response(msg, data=None, status_code=status.HTTP_406_NOT_ACCEPTABLE, success=False, extra_params=None):
    ret = {"is_success": success, "message": msg, "response_data": data}
    if extra_params:
        ret.update(extra_params)
    return Response(ret, status=status_code)


def check_ecom_user(view_func):
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        if not request.user.is_ecom_user:
            return api_response("User Not Registered For E-commerce!")
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


def check_ecom_user_shop(view_func):
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        if not request.user.is_ecom_user:
            return api_response("User Not Registered For E-commerce!")
        try:
            shop = Shop.objects.get(id=request.META.get('HTTP_SHOP_ID', None), shop_type__shop_type='f', status=True,
                                    approval_status=2, pos_enabled=1)
        except:
            return api_response("Shop not available!")
        kwargs['shop'] = shop
        kwargs['app_type'] = request.META.get('HTTP_APP_TYPE', None)
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


def nearby_shops(lat, lng, radius=10, limit=1):
    """
    Returns shop(s) within radius from lat,lng point
    lat: latitude
    lng: longitude
    radius: distance in km from latitude,longitude point
    """

    query = """SELECT * from (
               SELECT shops_shop.id, (6367*acos(cos(radians(%2f))
               *cos(radians(latitude))*cos(radians(longitude)-radians(%2f))
               +sin(radians(%2f))*sin(radians(latitude))))
               AS distance FROM shops_shop 
               left join shops_shoptype on shops_shoptype.id=shops_shop.shop_type_id
               where shops_shoptype.shop_type='f' and shops_shop.status=True and shops_shop.approval_status=2
               and shops_shop.pos_enabled=True and shops_shop.online_inventory_enabled=True) as shop_loc
               where distance < %2f ORDER BY distance LIMIT %d OFFSET 0""" % (float(lat), float(lng), float(lat),
                                                                              radius, limit)

    queryset = Shop.objects.raw(query)
    return queryset[0] if queryset else None


def validate_address_id(func):
    @wraps(func)
    def _wrapped_view_func(self, request, pk):
        user_address = Address.objects.filter(user=request.user, id=pk).last()
        if not user_address:
            return api_response("Invalid Address Id")
        return func(self, request, pk)

    return _wrapped_view_func


def get_categories_with_products(shop):
    query_set = PosInventory.objects.filter(product__shop=shop, product__status='active', quantity__gt=0,
                                            inventory_state=PosInventoryState.objects.filter(
                                                inventory_state='available').last())
    return query_set.values_list(
        'product__linked_product__parent_product__parent_product_pro_category__category', flat=True).distinct()


def get_ecom_tax_details(product):
    gst_amount = 0
    if product.linked_product:
        tax_details = product.linked_product.product_pro_tax
        if tax_details.filter(tax__tax_type='gst').last():
            gst_amount = tax_details.filter(tax__tax_type='gst').last().tax.tax_percentage
    return gst_amount


def generate_ecom_order_csv_report(queryset):
    #queryset = OrderedProduct.objects.filter(order__in=queryset)
    retailer_product_type = dict(((0, 'Free'),
                                  (1, 'Purchased')))
    filename = 'ECOM_order_report_{}.csv'.format(datetime.datetime.now().strftime('%m/%d/%Y--%H-%M-%S'))
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachement; filename="{}"'.format(filename)
    csv_writer = csv.writer(response)
    csv_writer.writerow([
        'Order No', 'Invoice No', 'Order Status', 'Order Created At', 'Seller Shop ID',
        'Seller Shop Name', 'Seller Shop Owner Id', 'Seller Shop Owner Name', 'Mobile No.(Seller Shop)', 'Seller Shop Type', 
        'Buyer Id', 'Buyer Name','Mobile No(Buyer)',
        'Purchased Product Id', 'Purchased Product SKU', 'Purchased Product Name', 'Purchased Product Ean Code','Product Category',
        'Product SubCategory', 'Quantity',
        'Product Type', 'MRP', 'Selling Price' , 'Offer Applied' ,'Offer Discount',
        'Subtotal', 'Order Amount', 'Payment Mode',
        'Parent Id', 'Parent Name', 'Child Name', 'Brand', 
        'Tax Slab(GST)', 'Discount' ,'Delivered Quantity', 'Delivered Value', 'Delivery Start Time', 'Delivery End Time', 'PickUp Time' ,'Redeemed Points'
    ])
    orders = queryset \
        .prefetch_related('order', 'invoice','pos_trips', 'order__ordered_cart__seller_shop', 'order__ordered_cart__seller_shop__shop_owner',
                          'order__ordered_cart__seller_shop__shop_type__shop_sub_type', 'order__buyer', 'rt_order_product_order_product_mapping',
                          'rt_order_product_order_product_mapping__retailer_product',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_parent',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_parent',
                          'rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand',
                          'rt_payment_retailer_order__payment_type', 'ordered_cart', 'ordered_cart__rt_cart_list'
                          )\
        .annotate(
            purchased_subtotal=RoundAmount(Sum(F('ordered_cart__rt_cart_list__qty') * F('ordered_cart__rt_cart_list__selling_price'),output_field=FloatField())),
            ) \
        .values('id', 'order_no', 'rt_order_order_product__invoice__invoice_no', 'order_status', 'created_at','ordered_cart__seller_shop__id', 'ordered_cart__seller_shop__shop_name',
                'ordered_cart__seller_shop__shop_owner__id', 'ordered_cart__seller_shop__shop_owner__first_name',
                'ordered_cart__seller_shop__shop_owner__phone_number',
                'ordered_cart__seller_shop__shop_type__shop_sub_type__retailer_type_name',
                'buyer__id', 'buyer__first_name', 'buyer__phone_number',
                'rt_order_order_product__rt_order_product_order_product_mapping__shipped_qty',
                'rt_order_order_product__rt_order_product_order_product_mapping__product_type',
                'rt_order_order_product__rt_order_product_order_product_mapping__selling_price',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__id',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__sku',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__name',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__mrp',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__selling_price',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__product_ean_code',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_id',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__name',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_parent__category_name',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_name',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_parent__brand_name',
                'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_name',
                'purchased_subtotal', 'order_amount', 'rt_payment_retailer_order__payment_type__type',
                'ordered_cart__offers'
                ).iterator()
    for order in orders:
        retailer_product_id = order.get('rt_order_product_order_product_mapping__retailer_product__id')
        retailer_product = RetailerProduct.objects.filter(id=retailer_product_id)
        if retailer_product:
            tax_detail = get_ecom_tax_details(retailer_product.last())
        else:
            tax_detail = None
        product_type = order.get('rt_order_product_order_product_mapping__product_type')
        cart_offers = order['order__ordered_cart__offers']
        cart_offers = order['ordered_cart__offers']
        offers = list(filter(lambda d: d['type'] in 'discount', cart_offers))
        category = order[
            'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_parent__category_name']
        sub_category = order[
            'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_product_pro_category__category__category_name']
        if not category:
            category = sub_category
            sub_category = None

        brand = order[
            'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_parent__brand_name']
        sub_brand = order[
            'rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_brand__brand_name']
        if not brand:
            brand = sub_brand
            sub_brand = None
        discount = order.get('rt_order_product_order_product_mapping__selling_price') - order.get('rt_order_product_order_product_mapping__effective_price',
                                                                                      order.get('rt_order_product_order_product_mapping__selling_price'))
        try:
           sub_total = "{:.2f}".format(order.get(
                'rt_order_order_product__rt_order_product_order_product_mapping__shipped_qty') * order.get(
                'rt_order_order_product__rt_order_product_order_product_mapping__selling_price')),
        except:
            sub_total = float(0.0)
        csv_writer.writerow([
            order.get('order_no'),
            order.get('order__rt_order_order_product__invoice__invoice_no'),
            order.get('order_status'),
            order.get('created_at').strftime('%m/%d/%Y-%H-%M-%S'),
            order.get('ordered_cart__seller_shop__id'),
            order.get('ordered_cart__seller_shop__shop_name'),
            order.get('ordered_cart__seller_shop__shop_owner__id'),
            order.get('ordered_cart__seller_shop__shop_owner__first_name'),
            order.get('ordered_cart__seller_shop__shop_owner__phone_number'),
            order.get('ordered_cart__seller_shop__shop_type__shop_sub_type__retailer_type_name'),
            order.get('buyer__id'),
            order.get('buyer__first_name'),
            order.get('buyer__phone_number'),
            order.get('rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__id'),
            order.get('rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__sku'),
            order.get('rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__name'),
            order.get('rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__product_ean_code'),
            category,
            sub_category,
            order.get('rt_order_order_product__rt_order_product_order_product_mapping__shipped_qty'),
            retailer_product_type.get(product_type, product_type),
            order.get('rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__mrp'),
            order.get('rt_order_order_product__rt_order_product_order_product_mapping__selling_price'),
            offers[0].get('coupon_description', None) if len(offers) else None,
            offers[0].get('discount_value', None) if len(offers) else None
            if len(offers) else None,
            #order.get('purchased_subtotal'),
            sub_total,
            order.get('order_amount'),
            order.get('rt_payment_retailer_order__payment_type__type'),
            order.get('rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__parent_id'),
            order.get('rt_order_order_product__rt_order_product_order_product_mapping__retailer_product__linked_product__parent_product__name'),
            brand,
            sub_brand,
            tax_detail,
            discount,
            "{:.2f}".format(order.get('rt_order_product_order_product_mapping__delivered_qty')),
            "{:.2f}".format(order.get('rt_order_product_order_product_mapping__delivered_qty')*order.get('rt_order_product_order_product_mapping__selling_price')),
            order.get('pos_trips__trip_start_at').strftime('%m/%d/%Y-%H-%M-%S') \
                if order.get('pos_trips__trip_start_at') else '',
            order.get('pos_trips__trip_end_at').strftime('%m/%d/%Y-%H-%M-%S') \
                if order.get('pos_trips__trip_end_at') else '',
            order.get('created_at').strftime('%m/%d/%Y-%H-%M-%S'),
            order.get('order__ordered_cart__redeem_points'),
        ])

    return response
