import io
import xlsxwriter

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from django.utils.html import format_html_join, format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.http import HttpResponse

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

def create_order_data_excel(queryset):
    worksheet.write('A1', 'Order No.', header_format)
    worksheet.write('A1', 'Seller Shop ID', header_format)
    worksheet.write('A1', 'Seller Shop Name', header_format)
    worksheet.write('A1', 'Buyer Shop ID', header_format)
    worksheet.write('A1', 'Buyer Shop Name', header_format)
    worksheet.write('A1', 'Mobile No.(Buyer Shop)', header_format)
    worksheet.write('A1', 'Pincode', header_format)
    worksheet.write('A1', 'City', header_format)
    worksheet.write('A1', 'Total Final Amount', header_format)
    worksheet.write('A1', 'Order Status', header_format)
    worksheet.write('A1', 'Order Created At', header_format)
    worksheet.write('A1', 'Payment Mode', header_format)
    worksheet.write('A1', 'Paid Amount', header_format)
    worksheet.write('A1', 'Total Paid Amount', header_format)
    worksheet.write('A1', 'Invoice No', header_format)
    worksheet.write('A1', 'Shipment Status', header_format)
    worksheet.write('A1', 'Shipment Amount', header_format)
    worksheet.write('A1', 'Trip Completed At', header_format)
    worksheet.write('A1', 'Picking Status', header_format)
    worksheet.write('A1', 'Picker Boy Name', header_format)
    worksheet.write('A1', 'Picker Boy Mobile No', header_format)
    worksheet.write('A1', 'Picklist ID', header_format)





order_no    seller_shop buyer_shop_id   buyer_shop_with_mobile  pincode city
total_final_amount  order_status    created_at  payment_mode    paid_amount total_paid_amount   invoice_no
shipment_status shipment_status_reason  order_shipment_amount   trip_completed_at   picking_status  picker_boy  picklist_id
    cities_list = City.objects.values_list('city_name', flat=True)
    states_list = State.objects.values_list('state_name', flat=True)
    output = io.BytesIO()
    data = Address.objects.values_list(
        'shop_name__id', 'shop_name__shop_name', 'shop_name__shop_type__shop_type',
        'shop_name__shop_owner__phone_number', 'shop_name__status', 'id', 'nick_name',
        'address_line1', 'address_contact_name', 'address_contact_number',
        'pincode_link__pincode', 'state__state_name', 'city__city_name', 'address_type',
        'shop_name__imei_no', 'shop_name__retiler_mapping__parent__shop_name',
        'shop_name__created_at').filter(shop_name__in=queryset)
    data_rows = data.count()
    workbook = xlsxwriter.Workbook(output, {'default_date_format':
                                            'dd/mm/yy hh:mm:ss'})
    worksheet = workbook.add_worksheet()
    unlocked = workbook.add_format({'locked': 0})

    header_format = workbook.add_format({
        'border': 1,
        'bg_color': '#C6EFCE',
        'bold': True,
        'text_wrap': True,
        'valign': 'vcenter',
        'indent': 1,
    })

    format1 = workbook.add_format({'bg_color': '#FFC7CE',
                               'font_color': '#9C0006'})

    # to set the width of column
    worksheet.set_column('A:A', 10)
    worksheet.set_column('B:B', 100)
    worksheet.set_column('C:C', 10)
    worksheet.set_column('D:D', 15)
    worksheet.set_column('E:E', 10)
    worksheet.set_column('F:F', 10)
    worksheet.set_column('G:G', 50)
    worksheet.set_column('H:H', 100)
    worksheet.set_column('I:I', 20)
    worksheet.set_column('J:J', 15)
    worksheet.set_column('K:K', 10)
    worksheet.set_column('L:L', 20)
    worksheet.set_column('M:M', 20)
    worksheet.set_column('N:N', 10)
    worksheet.set_column('O:O', 20)
    worksheet.set_column('P:P', 40)
    worksheet.set_column('Q:Q', 20)

    # to set the hieght of row
    worksheet.set_row(0, 36)

    # column headings
    worksheet.write('A1', 'Shop ID', header_format)
    worksheet.write('B1', 'Shop Name', header_format)
    worksheet.write('C1', 'Shop Type', header_format)
    worksheet.write('D1', 'Shop Owner', header_format)
    worksheet.write('E1', 'Shop Activated', header_format)
    worksheet.write('F1', 'Address ID', header_format)
    worksheet.write('G1', 'Address Name', header_format)
    worksheet.write('H1', 'Address', header_format)
    worksheet.write('I1', "Contact Person", header_format)
    worksheet.write('J1', 'Contact Number', header_format)
    worksheet.write('K1', 'Pincode', header_format)
    worksheet.write('L1', 'State', header_format)
    worksheet.write('M1', 'City', header_format)
    worksheet.write('N1', 'Address Type', header_format)
    worksheet.write('O1', 'IMEI', header_format)
    worksheet.write('P1', 'Parent Shop Name', header_format)
    worksheet.write('Q1', 'Shop created at', header_format)


    for row_num, columns in enumerate(data):
        for col_num, cell_data in enumerate(columns):
            if cell_data and col_num == 16:
                worksheet.write_datetime(row_num + 1, col_num, cell_data)
            elif cell_data and col_num == 4:
                worksheet.write_boolean(row_num + 1, col_num, cell_data)
            else:
                worksheet.write(row_num + 1, col_num, cell_data)

    worksheet.data_validation(
        'L2:L{}'.format(data_rows + 1),
        {'validate': 'list',
         'source': list(states_list)})

    worksheet.data_validation(
        'M2:M{}'.format(data_rows + 1),
        {'validate': 'list',
         'source': list(cities_list)})

    worksheet.data_validation(
        'E2:E{}'.format(data_rows + 1),
        {'validate': 'list',
         'source': [True, False]})

    worksheet.data_validation(
        'N2:N{}'.format(data_rows + 1),
        {'validate': 'list',
         'source': ['billing', 'shipping']})

    workbook.close()

    # Rewind the buffer.
    output.seek(0)

    # Set up the Http response.
    filename = 'Shops_sheet.xlsx'
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=%s' % filename

    return response
