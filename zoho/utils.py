from django.core.exceptions import ValidationError


def get_field_name_by_file_field_name(file_field_name):
    return str(file_field_name).strip().lower().replace(' ', '_').replace('(', '_').replace(')', '').\
        replace('_&_', '_').replace('_%', '_percentage').replace('-', '_').replace('#', '').replace('2c', 'c').\
        replace('/', '_').replace('.', '_').replace('__', '_')


def get_csv_file_data_as_dict(csv_file, csv_file_headers):
    uploaded_data_by_user_list = []
    csv_dict = {}
    count = 0
    row_num = 1
    for row in csv_file:
        row_num += 1
        for ele in row:
            if '#' in ele:
                raise ValidationError(f"Row {row_num} | column can not contain '#' ")
            csv_dict[csv_file_headers[count]] = ele
            count += 1
        uploaded_data_by_user_list.append(csv_dict)
        csv_dict = {}
        count = 0
    return uploaded_data_by_user_list
