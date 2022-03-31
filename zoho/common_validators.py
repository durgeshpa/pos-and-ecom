import csv
import codecs


# validation of uploaded invoice file
from zoho.utils import get_field_name_by_file_field_name, get_csv_file_data_as_dict


def bulk_invoice_data_validation(invoice_file):
    error_file_list = []
    validated_rows = []
    reader = csv.reader(codecs.iterdecode(invoice_file, 'utf-8', errors='ignore'))
    header = next(reader)
    error_file_list.append(list(header) + ["status"])
    header_list = []
    headers_map = {}
    headers_rev_map = {}
    for file_field_name in header:
        field_name = get_field_name_by_file_field_name(file_field_name)
        header_list.append(field_name)
        headers_map[file_field_name] = field_name
        headers_rev_map[field_name] = file_field_name

    uploaded_data_by_user_list = get_csv_file_data_as_dict(reader, header_list)
    for row in uploaded_data_by_user_list:
        error_msg = []
        if not 'invoice_id' in row:
            error_msg.append("invoice_id field is mandatory ")

        if not 'product_id' in row:
            error_msg.append("product_id field is mandatory ")

        if 'invoice_id' in row and not row.get('invoice_id', None):
            error_msg.append(f"{headers_rev_map['invoice_id']} cant be blank")

        if 'product_id' in row and not row.get('product_id', None):
            error_msg.append(f"{headers_rev_map['product_id']} cant be blank")

        if error_msg:
            msg = ", "
            msg = msg.join(map(str, error_msg))
            row_list = [row[headers_map[x]] for x in header]
            error_file_list.append(row_list + [msg])
        else:
            validated_rows.append(row)

    return error_file_list, validated_rows


def bulk_credit_note_data_validation(credit_note_file):
    error_file_list = []
    validated_rows = []
    reader = csv.reader(codecs.iterdecode(credit_note_file, 'utf-8', errors='ignore'))
    header = next(reader)
    error_file_list.append(list(header) + ["status"])
    header_list = []
    headers_map = {}
    headers_rev_map = {}
    for file_field_name in header:
        field_name = get_field_name_by_file_field_name(file_field_name)
        header_list.append(field_name)
        headers_map[file_field_name] = field_name
        headers_rev_map[field_name] = file_field_name

    uploaded_data_by_user_list = get_csv_file_data_as_dict(reader, header_list)
    for row in uploaded_data_by_user_list:
        error_msg = []

        if not 'creditnotes_id' in row:
            error_msg.append("creditnotes_id field is mandatory ")

        if not 'product_id' in row:
            error_msg.append("product_id field is mandatory ")

        if 'creditnotes_id' in row and not row.get('creditnotes_id', None):
            error_msg.append(f"{headers_rev_map['creditnotes_id']} cant be blank")

        if 'product_id' in row and not row.get('product_id', None):
            error_msg.append(f"{headers_rev_map['product_id']} cant be blank")

        if error_msg:
            msg = ", "
            msg = msg.join(map(str, error_msg))
            row_list = [row[headers_map[x]] for x in header]
            error_file_list.append(row_list + [msg])
        else:
            validated_rows.append(row)

    return error_file_list, validated_rows
