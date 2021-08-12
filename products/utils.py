import io
import xlsxwriter

from django.http import QueryDict
import json
from rest_framework import parsers

from django.http import HttpResponse
from django.db.models import Q

from addresses.models import Address, City, State
from products.models import ProductVendorMapping
from .models import ProductHSN, ParentProduct
from django.db.models.functions import Length


def create_shops_excel(queryset):
    cities_list = City.objects.values_list('city_name', flat=True)
    states_list = State.objects.values_list('state_name', flat=True)

    output = io.BytesIO()
    data = Address.objects.values_list(
        'shop_name_id', 'shop_name__shop_name',
        'shop_name__shop_type__shop_type',
        'shop_name__shop_owner__phone_number',
        'shop_name__status', 'id', 'nick_name', 'address_line1',
        'address_contact_name', 'address_contact_number', 'pincode',
        'state__state_name', 'city__city_name', 'address_type'
    ).filter(shop_name__in=queryset)

    data_rows = data.count()
    workbook = xlsxwriter.Workbook(output)
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

    for row_num, columns in enumerate(data):
        for col_num, cell_data in enumerate(columns):
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


def products_price_excel(queryset):
    output = io.BytesIO()
    data = queryset

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
    worksheet.set_column('A:A', 20)
    worksheet.set_column('B:B', 50)
    worksheet.set_column('C:C', 20)
    worksheet.set_column('D:D', 50)
    worksheet.set_column('E:E', 20)
    worksheet.set_column('F:F', 20)
    worksheet.set_column('G:G', 20)
    worksheet.set_column('H:H', 30)
    worksheet.set_column('I:I', 20)
    worksheet.set_column('J:J', 20)
    worksheet.set_column('K:K', 50)
    worksheet.set_column('L:L', 20)
    worksheet.set_column('M:M', 20)
    worksheet.set_column('N:N', 20)

    # to set the hieght of row
    worksheet.set_row(0, 60)

    # column headings
    worksheet.write('A1', 'Product SKU\n(required)', header_format)
    worksheet.write('B1', 'Product Name', header_format)
    worksheet.write('C1', 'Seller Shop Name', header_format)
    worksheet.write('D1', 'MRP\n(Stored with Child Product. Do not update here.)', header_format)
    worksheet.write('E1', 'Selling Price\n(required)', header_format)
    worksheet.write('F1', 'City ID\n(optional)', header_format)
    worksheet.write('G1', 'City Name', header_format)
    worksheet.write('H1', 'Pincode\n(optional)', header_format)
    worksheet.write('I1', 'Buyer Shop ID\n(optional)', header_format)
    worksheet.write('J1', 'Buyer Shop Name', header_format)
    worksheet.write('K1', 'Price Start Date\n(dd/mm/yy hh:mm:ss)(required)', header_format)
    worksheet.write('L1', 'Price End Date\n(dd/mm/yy hh:mm:ss)(autoset)', header_format)
    worksheet.write('M1', 'Approval Status\n(autoset)', header_format)
    # worksheet.write('C1', 'Product GF Code', header_format)
    # worksheet.write('D1', 'Seller Shop Name', header_format)
    # worksheet.write('E1', 'MRP\n(required)', header_format)
    # worksheet.write('F1', 'Selling Price\n(required)', header_format)
    # worksheet.write('G1', 'City ID\n(optional)', header_format)
    # worksheet.write('H1', 'City Name', header_format)
    # worksheet.write('I1', 'Pincode\n(optional)', header_format)
    # worksheet.write('J1', 'Buyer Shop ID\n(optional)', header_format)
    # worksheet.write('K1', 'Buyer Shop Name', header_format)
    # worksheet.write('L1', 'Price Start Date\n(dd/mm/yy hh:mm:ss)(required)', header_format)
    # worksheet.write('M1', 'Price End Date\n(dd/mm/yy hh:mm:ss)(required)', header_format)
    # worksheet.write('N1', 'Approval Status', header_format)

    for row_num, columns in enumerate(data):
        for col_num, cell_data in enumerate(columns):
            # if cell_data and col_num in (11, 12):
            if cell_data and col_num in (10, 11):
                worksheet.write_datetime(row_num + 1, col_num, cell_data)
            else:
                worksheet.write(row_num + 1, col_num, cell_data)

    # worksheet.data_validation(
    #     'L2:L{}'.format(data_rows + 1),
    #     {'validate': 'list',
    #      'source': list(states_list)})

    # worksheet.data_validation(
    #     'M2:M{}'.format(data_rows + 1),
    #     {'validate': 'list',
    #      'source': list(cities_list)})

    # worksheet.data_validation(
    #     'E2:E{}'.format(data_rows + 1),
    #     {'validate': 'list',
    #      'source': [True, False]})

    # worksheet.data_validation(
    #     'N2:N{}'.format(data_rows + 1),
    #     {'validate': 'list',
    #      'source': ['billing', 'shipping']})

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


def vendor_product_mapping(supplier, product_id, price, mrp, case_size, unit):
    """
        Create vendor product mapping for product purchase price with case size
    """
    vendor_product_obj = None
    if unit.lower() == 'per piece':
        vendor_product_obj = ProductVendorMapping.objects.create(vendor=supplier, product_id=product_id,
                                                                 product_price=price, product_mrp=mrp,
                                                                 case_size=case_size, status=True)
    elif unit.lower() == 'per pack':
        vendor_product_obj = ProductVendorMapping.objects.create(vendor=supplier, product_id=product_id,
                                                                 product_price_pack=price, product_mrp=mrp,
                                                                 case_size=case_size, status=True)
    return vendor_product_obj


def hsn_queryset(self):
    """
    return query set from Product HSN which length is gte 6 and lte 8
    """

    qs = ProductHSN.objects.annotate(text_len=Length('product_hsn_code')).filter(text_len__gte=6,
                                                                                 text_len__lte=8,
                                                                                 product_hsn_code__icontains=self.q)
    return qs


def get_selling_price(def_product):
    selling_price = 0
    ptr_percent = def_product.parent_product.ptr_percent
    ptr_type = def_product.parent_product.ptr_type
    if ptr_type == ParentProduct.PTR_TYPE_CHOICES.MARK_UP:
        selling_price = def_product.product_mrp / (1 + (ptr_percent / 100))
    elif ptr_type == ParentProduct.PTR_TYPE_CHOICES.MARK_DOWN:
        selling_price = def_product.product_mrp * (1 - (ptr_percent / 100))
    return selling_price