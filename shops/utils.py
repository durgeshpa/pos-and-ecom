import io
import xlsxwriter

from django.http import HttpResponse

from addresses.models import Address, City, State, Shop


def create_shops_excel(queryset):
    cities_list = City.objects.values_list('city_name', flat=True)
    states_list = State.objects.values_list('state_name', flat=True)

    output = io.BytesIO()
    data = Shop.objects.values_list(
        'id', 'shop_name', 'shop_type__shop_type',
        'shop_owner__phone_number', 'status', 'shop_name_address_mapping__id',
        'shop_name_address_mapping__nick_name', 'shop_name_address_mapping__address_line1',
        'shop_name_address_mapping__address_contact_name', 'shop_name_address_mapping__address_contact_number',
        'shop_name_address_mapping__pincode', 'shop_name_address_mapping__state__state_name',
        'shop_name_address_mapping__city__city_name', 'shop_name_address_mapping__address_type'
    ).filter(id__in=queryset)

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