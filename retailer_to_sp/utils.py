import io
import logging

import xlsxwriter
import csv
import codecs
import datetime

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from django.utils.html import format_html_join, format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.http import HttpResponse
from django.db.models import Sum, F, FloatField, OuterRef, Subquery

from marketing.sms import SendSms
from products.models import Product
from retailer_backend.messages import NOTIFICATIONS
from retailer_backend.utils import time_diff_days_hours_mins_secs

# Logger
info_logger = logging.getLogger('file-info')

def add_cart_user(form, request):
	cart = form.save(commit=False)
	cart.last_modified_by = request.user
	cart.cart_status = 'ordered'
	cart.save()


def create_order_from_cart(form, formsets, request, Order):
    cart_data = get_cart_seller_buyer_shop_address(form)
    order_amounts = get_order_mrp_tax_discount_final_amount(formsets)

    order, _ = Order.objects.get_or_create(
    	ordered_cart=cart_data.get('cart'))

    order.seller_shop = cart_data.get('seller_shop')
    order.buyer_shop = cart_data.get('buyer_shop')
    order.billing_address = cart_data.get('billing_address')
    order.shipping_address = cart_data.get('shipping_address')
    order.total_mrp = order_amounts.get('total_mrp')
    order.total_discount_amount = order_amounts.get('total_discount_amount')
    order.total_tax_amount = order_amounts.get('total_tax_amount')
    #order.total_final_amount = order_amounts.get('total_final_amount')
    order.ordered_by = request.user
    order.order_status = Order.ORDERED
    order.last_modified_by = request.user
    order.save()


def get_product_tax_amount(product, ptr, ordered_no_of_pieces):
	tax_sum = 0
	product_tax = product.product_pro_tax
	if product_tax.exists():
		for tax in product_tax.all():
			tax_sum = float(tax_sum) + float(tax.tax.tax_percentage)
		tax_sum = round(tax_sum, 2)
		get_tax_val = tax_sum / 100
		basic_rate = (float(ptr)) / (float(get_tax_val) + 1)
		base_price = (
			(float(ptr) * float(ordered_no_of_pieces)) /
			(float(get_tax_val) + 1)
			)
		product_tax_amount = float(base_price) * float(get_tax_val)
		product_tax_amount = round(product_tax_amount, 2)
		return product_tax_amount
	return 0


def get_order_mrp_tax_discount_final_amount(formsets):
	total_mrp = []
	total_tax_amount = []
	total_discount_amount = []
	total_final_amount = []
	for forms in formsets:
		for form in forms:
			if form.instance:
				product = form.instance.cart_product
				ordered_no_of_pieces = float(form.instance.no_of_pieces)
				ptr = float(form.instance.cart_product_price.selling_price)
				mrp = float(form.instance.cart_product_price.mrp)
			else:
				product = form.cleaned_data.get('cart_product')
				ordered_no_of_pieces = float(form.cleaned_data.get('no_of_pieces'))
				ptr = float(form.cleaned_data.get('cart_product_price').selling_price)
				mrp = float(form.cleaned_data.get('cart_product_price').mrp)
			tax_amount = get_product_tax_amount(product, ptr, ordered_no_of_pieces)

			total_mrp.append(mrp * ordered_no_of_pieces)
			total_tax_amount.append(tax_amount)
			total_discount_amount.append((mrp - ptr) * ordered_no_of_pieces)
			total_final_amount.append(ptr * ordered_no_of_pieces)

	data = {
		'total_mrp': sum(total_mrp), 'total_tax_amount': sum(total_tax_amount),
		'total_discount_amount': sum(total_discount_amount),
		'total_final_amount': sum(total_final_amount)
		}

	return data


def get_cart_seller_buyer_shop_address(form):
	cart = form.instance
	data = {
		'cart': cart, 'order_id': cart.order_id,
		'seller_shop': cart.seller_shop, 'buyer_shop': cart.buyer_shop,
		'shipping_address': cart.buyer_shop.shop_name_address_mapping.filter(
			address_type='shipping').last(),
		'billing_address': cart.buyer_shop.shop_name_address_mapping.filter(
			address_type='billing').last()
		}

	return data


class GetPcsFromQty(APIView):
	permission_classes = (AllowAny,)

	def get(self, *args, **kwargs):
		cart_product_id = self.request.GET.get('cart_product_id')
		if cart_product_id:
			product = Product.objects.values(
				'product_case_size', 'product_inner_case_size').get(pk=cart_product_id)
			case_size = product.get('product_case_size')
			inner_case_size = product.get('product_inner_case_size')
			return Response({
				"case_size": case_size,
				"inner_case_size": inner_case_size,
				"success": True
			})
		return Response({
			"success": False
		})

def order_invoices(shipments):
    return format_html_join(
    "","<a href='/admin/retailer_to_sp/shipment/{}/change/' target='blank'>{}</a><br><br>",
            ((s.pk,
            s.invoice_no,
            ) for s in shipments)
    )

def picking_statuses(picker_dashboards):
    return format_html_join(
    "","{}<br><br>",
            ((s.get_picking_status_display(),
            ) for s in picker_dashboards)
    )


def picklist_refreshed_at(picker_dashboards):
    return format_html_join(
    "","{}<br><br>",
            ((s.refreshed_at,
            ) for s in picker_dashboards)
    )

def picker_boys(picker_dashboards):
    return format_html_join(
    "","{}<br><br>",
            ((s.picker_boy, #get_picker_boy_display(),
            ) for s in picker_dashboards)
    )

def picklist_ids(picker_dashboards):
    return format_html_join(
    "","{}<br><br>",
            ((s.picklist_id, #get_picklist_id_display(),
            ) for s in picker_dashboards)
    )

def qc_areas(picker_dashboards):
    return format_html_join(
    "","{}<br><br>",
            ((s.qc_area, #get_qc_area_display(),
            ) for s in picker_dashboards)
    )

def zones(picker_dashboards):
    return format_html_join(
    "","{}<br><br>",
            ((s.zone, #get_zone_display(),
            ) for s in picker_dashboards)
    )


def order_shipment_status(shipments):
    return format_html_join(
    "","{}<br><br>",
            ((s.get_shipment_status_display(),
            ) for s in shipments)
    )



def order_shipment_status_reason(shipments):
    return format_html_join(
    "","{}<br><br>",
            ((s.get_return_reason_display(),
            ) for s in shipments)
    )


def order_shipment_amount(shipments):
    return format_html_join(
    "","{}<br><br>",
            ((s.invoice_amount,
            ) for s in shipments)
    )

def order_shipment_date(shipments):
    return format_html_join(
    "","{}<br><br>",
            ((s.created_at.strftime('%Y-%m-%d %H:%M:%S') if s.created_at else '-',
            ) for s in shipments)
    )

def order_delivery_date(shipments):
	return format_html_join(
		"", "{}<br><br>",
		((s.trip.completed_at.strftime('%Y-%m-%d %H:%M:%S') if s.trip and s.trip.completed_at else '-',) for s in shipments)
	)

def order_cash_to_be_collected(shipments):
	return format_html_join(
		"", "{}<br><br>",
		((s.cash_to_be_collected() if s.trip else '',) for s in shipments)
	)

def order_cn_amount(shipments):
	return format_html_join(
		"", "{}<br><br>",
		((s.credit_note.aggregate(Sum('amount')).get('amount__sum') if s.credit_note.exists() else '',) for s in shipments)
	)

def order_damaged_amount(shipments):
	return format_html_join(
		"", "{}<br><br>",
		((s.damaged_amount(),) for s in shipments)
	)

def order_delivered_value(shipments):
	return format_html_join(
		"", "{}<br><br>",
		((s.delivered_value(),) for s in shipments)
	)

class UpdateCashToBeCollected(object):
	"""Update trip's cash to be collected amount"""
	def __init__(self, form, formset):
		super(UpdateCashToBeCollected, self).__init__()
		self.shipment = form
		self.shipment_products = formset

	def deduct_amount(self):
		for inline_forms in self.shipment_products:
			for inline_form in inline_forms:
				instance = getattr(inline_form, 'instance', None)
				update_delivered_qty(instance, inline_form)
				shipped_qty_list.append(instance.shipped_qty if instance else 0)
				returned_qty_list.append(inline_form.cleaned_data.get('returned_qty', 0))
				damaged_qty_list.append(inline_form.cleaned_data.get('damaged_qty', 0))


def order_shipment_details_util(shipments):
    return format_html_join(
    "","{}-{}-{}<br><br>",
            ((s.invoice_amount,s.get_shipment_status_display(),s.trip.completed_at if s.trip else '--'
            ) for s in shipments)
    )


def reschedule_shipment_button(obj):
    return format_html(
        "<a class='related-widget-wrapper-link-custom add-related' id='shipment_reshcedule' href='%s?&_to_field=id&_popup=1&shipment_id=%s' target='_blank'>Reschedule the Shipment</a>" %
        (reverse('admin:retailer_to_sp_shipmentrescheduling_add'),
         obj.id)
    )


def create_order_data_excel(request, queryset, OrderPayment, ShipmentPayment,
                            OrderedProduct, Order, Trip, PickerDashboard,
                            RoundAmount):
    shipment_status_dict = dict(OrderedProduct.SHIPMENT_STATUS)
    order_status_dict = dict(Order.ORDER_STATUS)
    trip_status_dict = dict(Trip.TRIP_STATUS)
    picking_status_dict = dict(PickerDashboard.PICKING_STATUS)
    return_reason_dict = dict(OrderedProduct.RETURN_REASON)

    filename = "Orders_data_{}.csv".format(datetime.date.today())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow([
        'Order No', 'Order Status', 'Order Created At', 'Seller Shop ID',
        'Seller Shop Name', 'Buyer Shop ID',
        'Buyer Shop Name', 'Buyer Shop Type', 'Buyer Shop SubType', 'Mobie No.(Buyer Shop)', 'City(Buyer Shop)',
        'Pincode(Buyer Shop)', 'Order MRP Amount', 'Order Amount',
        'Order Paid Amount', 'Invoice No', 'Invoice Amount', 'Shipment Status', 'Trip Id',
        'Shipment Return Reason', 'Shipment Created At', 'Shipment Delivered At',
        'Shipment Paid Amount', 'Picking Status', 'Picklist ID', 'QC Area', 'Picker Boy', 'Picker Boy Name',
        'Picking Completed At', 'Picking Completion Time'])

    order_payments = OrderPayment.objects.filter(order=OuterRef('pk')).order_by().values('order')
    order_paid_amount = order_payments.annotate(sum=Sum('paid_amount')).values('sum')

    shipment_payments = ShipmentPayment.objects.filter(parent_order_payment__order=OuterRef('pk')).order_by().values('parent_order_payment__order')
    shipment_paid_amount = shipment_payments.annotate(sum=Sum('paid_amount')).values('sum')

    orders = queryset\
        .annotate(
            # total_mrp_amount=RoundAmount(Sum(F('ordered_cart__rt_cart_list__no_of_pieces') * F('ordered_cart__rt_cart_list__cart_product_price__mrp'), output_field=FloatField())),
            # total_final_amount=RoundAmount(Sum(F('ordered_cart__rt_cart_list__no_of_pieces') * F('ordered_cart__rt_cart_list__cart_product_price__selling_price'), output_field=FloatField())),
            shipment_paid_amount=Subquery(shipment_paid_amount),
            order_paid_amount=Subquery(order_paid_amount),
            invoice_amount=Subquery(OrderedProduct.objects.filter(order=OuterRef('pk')).annotate(sum=RoundAmount(Sum(
                F('rt_order_product_order_product_mapping__effective_price') * 
                F('rt_order_product_order_product_mapping__shipped_qty'),
                output_field=FloatField()))).values('sum')[:1]))\
        .values('order_no', 'order_status', 'created_at', 'seller_shop_id',
                'seller_shop__shop_name', 'buyer_shop_id',
                'buyer_shop__shop_name', 'buyer_shop__shop_type__shop_type',
                'buyer_shop__shop_type__shop_sub_type__retailer_type_name',
                'buyer_shop__shop_owner__phone_number',
                'shipping_address__city__city_name',
                'shipping_address__pincode_link__pincode',
                'rt_order_order_product__invoice__invoice_no',
                'invoice_amount',
                'rt_order_order_product__shipment_status',
                'rt_order_order_product__rescheduling_shipment__trip__dispatch_no',
                'rt_order_order_product__trip__dispatch_no',
                'rt_order_order_product__return_reason',
                'rt_order_order_product__invoice__created_at',
                'rt_order_order_product__trip__completed_at',
                'picker_order__picking_status',
                'picker_order__picklist_id',
                'picker_order__qc_area__area_id',
                'picker_order__picker_boy__phone_number',
                'picker_order__picker_boy__first_name',
                'shipment_paid_amount',
                'order_paid_amount',
                'total_mrp', 'ordered_cart__offers',
                'order_amount',
                'picker_order__picker_assigned_date',
                'picker_order__completed_at')
    # print(orders)
    for order in orders.iterator():
        offers = order.get('ordered_cart__offers')
        if offers:
            total_final_amount = sum([i.get('discounted_product_subtotal', 0) for i in offers])
            total_final_amount = round(total_final_amount)
        else:
            total_final_amount = order.get('order_amount')

        trip = order.get('rt_order_order_product__trip__dispatch_no')
        trip_str = trip if trip else ''
        shipment_reschedule = order.get('rt_order_order_product__rescheduling_shipment__trip__dispatch_no')
        if shipment_reschedule:
            trip_str = trip_str + ', ' + shipment_reschedule if trip_str else shipment_reschedule

        writer.writerow([
            order.get('order_no'),
            order_status_dict.get(order.get('order_status'),
                                  order.get('order_status')),
            order.get('created_at'),
            order.get('seller_shop_id'),
            order.get('seller_shop__shop_name'),
            order.get('buyer_shop_id'),
            order.get('buyer_shop__shop_name'),
            order.get('buyer_shop__shop_type__shop_type'),
            order.get('buyer_shop__shop_type__shop_sub_type__retailer_type_name'),
            order.get('buyer_shop__shop_owner__phone_number'),
            order.get('shipping_address__city__city_name'),
            order.get('shipping_address__pincode_link__pincode'),
            order.get('total_mrp'),
            order.get('order_amount'),
            order.get('order_paid_amount'),
            order.get('rt_order_order_product__invoice__invoice_no'),
            order.get('invoice_amount'),
            shipment_status_dict.get(order.get('rt_order_order_product__shipment_status'),
                                     order.get('rt_order_order_product__shipment_status')),
            trip_str,
            return_reason_dict.get(order.get('rt_order_order_product__return_reason'),
                                   order.get('rt_order_order_product__return_reason')),
            order.get('rt_order_order_product__invoice__created_at'),
            order.get('rt_order_order_product__trip__completed_at'),
            order.get('shipment_paid_amount'),
            picking_status_dict.get(order.get('picker_order__picking_status'),
                                 order.get('picker_order__picking_status')),
            order.get('picker_order__picklist_id'),
            order.get('picker_order__qc_area__area_id'),
            order.get('picker_order__picker_boy__phone_number'),
            order.get('picker_order__picker_boy__first_name'),
            order.get('picker_order__completed_at'),
            time_diff_days_hours_mins_secs(order.get('picker_order__completed_at'),
                                           order.get('picker_order__picker_assigned_date'))
            if order.get('picker_order__completed_at') else None
        ])
    return response


def create_invoice_data_excel(request, queryset, RoundAmount, ShipmentPayment,
                              OrderedProduct, Trip, Order):
    shipment_status_dict = dict(OrderedProduct.SHIPMENT_STATUS)
    order_status_dict = dict(Order.ORDER_STATUS)
    trip_status_dict = dict(Trip.TRIP_STATUS)
    filename = "Invoice_data_{}.csv".format(datetime.date.today())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow([
        'Invoice No.', 'Created At', 'Invoice Amount',
        'Shipment Status', 'Order No.', 'Order Date', 'Order Status',
        'Trip No.', 'Trip Status', 'Delivery Started At',
        'Delivery Completed At', 'Paid Amount', 'CN Amount'])

    shipment_payments = ShipmentPayment.objects.filter(shipment__invoice__id=OuterRef('pk')).order_by().values('shipment__invoice__id')
    shipment_paid_amount = shipment_payments.annotate(sum=Sum('paid_amount')).values('sum')

    invoices = queryset\
        .annotate(
            get_order=F('shipment__order__order_no'), shipment_status=F('shipment__shipment_status'),
            trip_no=F('shipment__trip__dispatch_no'), trip_status=F('shipment__trip__trip_status'),
            order_date=F('shipment__order__created_at'), order_status=F('shipment__order__order_status'),
            trip_started_at=F('shipment__trip__starts_at'), trip_completed_at=F('shipment__trip__completed_at'),
            shipment_paid_amount=Subquery(shipment_paid_amount),
            cn_amount=F('shipment__credit_note__amount'),
            invoice_amount=RoundAmount(Sum(
                F('shipment__rt_order_product_order_product_mapping__effective_price') *
                F('shipment__rt_order_product_order_product_mapping__shipped_qty'),
                output_field=FloatField())))\
        .values(
            'invoice_no', 'created_at', 'invoice_amount', 'shipment_status',
            'get_order', 'order_date', 'order_status', 'trip_no',
            'trip_status', 'trip_started_at', 'trip_completed_at',
            'shipment_paid_amount', 'cn_amount'
        )
    for invoice in invoices.iterator():
        writer.writerow([
            invoice.get('invoice_no'),
            invoice.get('created_at'),
            invoice.get('invoice_amount'),
            shipment_status_dict.get(invoice.get('shipment_status'), invoice.get('shipment_status')),
            invoice.get('get_order'),
            invoice.get('order_date'),
            order_status_dict.get(invoice.get('order_status'), invoice.get('order_status')),
            invoice.get('trip_no'),
            trip_status_dict.get(invoice.get('trip_status'), invoice.get('trip_status')),
            invoice.get('trip_started_at'),
            invoice.get('trip_completed_at'),
            invoice.get('shipment_paid_amount'),
            invoice.get('cn_amount'),
        ])
    return response


def send_sms_on_trip_start(trip_instance):
    shipments = trip_instance.rt_invoice_trip.filter(is_customer_notified=False)
    if shipments.count() == 0:
        return
    delivery_boy_name = trip_instance.delivery_boy.first_name
    delivery_boy_number = trip_instance.delivery_boy.phone_number
    info_logger.info("send_sms_on_trip_start| trip{}".format(trip_instance))
    for shipment in shipments:
        if shipment.invoice_amount > 0:
            try:
                buyer_name = shipment.order.buyer_shop.shop_owner.first_name
                text = NOTIFICATIONS['TRIP_START_MSG'].format(buyer_name, delivery_boy_name, delivery_boy_number,
                                                                     shipment.invoice_amount)
                phone_no = shipment.order.buyer_shop.shop_owner.phone_number
                info_logger.info("send_sms_on_trip_start| message {}, phone no {} ".format(text, phone_no))
                message = SendSms(phone=phone_no, body=text)
                message.send()
                shipment.is_customer_notified = True
                shipment.save()
            except Exception as e:
                info_logger.info("Exception|send_sms_on_trip_start| e {} ".format(e))
                info_logger.error(e)
