from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from django.utils.html import format_html_join, format_html
from django.utils.safestring import mark_safe
from django.urls import reverse

from products.models import Product


def add_cart_user(form, request):
	cart = form.save(commit=False)
	cart.last_modified_by = request.user
	cart.cart_status = 'ordered'
	cart.save()


def create_order_from_cart(form, formsets, request, order):
	cart_data = get_cart_seller_buyer_shop_address(form)
	order_amounts = get_order_mrp_tax_discount_final_amount(formsets)

	order, _ = order.objects.get_or_create(
		ordered_cart=cart_data.get('cart'), order_no=cart_data.get('order_id'))

	order.seller_shop = cart_data.get('seller_shop')
	order.buyer_shop = cart_data.get('buyer_shop')
	order.billing_address = cart_data.get('billing_address')
	order.shipping_address = cart_data.get('shipping_address')
	order.total_mrp = order_amounts.get('total_mrp')
	order.total_discount_amount = order_amounts.get('total_discount_amount')
	order.total_tax_amount = order_amounts.get('total_tax_amount')
	#order.total_final_amount = order_amounts.get('total_final_amount')
	order.ordered_by = request.user
	order.order_status = order.ORDER_PLACED_DISPATCH_PENDING
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
		((s.credit_note_amount,) for s in shipments)
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
