from django.core.exceptions import ValidationError

from zoho.models import ZohoInvoice, ZohoInvoiceItem, ZohoCreditNote, ZohoCreditNoteItem

zoho_id_fields = ['invoice_id', 'customer_id', 'branch_id', 'product_id', 'e-invoice_ack_number', 'tax_id',
                     'creditnotes_id', 'tax1_id']

def get_field_name_by_file_field_name(file_field_name):
    return str(file_field_name).strip().lower().replace(' ', '_').replace('(', '_').replace(')', ''). \
        replace('_&_', '_').replace('_%', '_percentage').replace('-', '_').replace('#', '').replace('2c', 'c'). \
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


def get_invoice_and_items_dict(data_row):
    invoice_fields = [f.name for f in ZohoInvoice._meta.get_fields()]
    items_fields = [f.name for f in ZohoInvoiceItem._meta.get_fields()]
    invoice_kwargs = {}
    items_kwargs = {}
    for field_name, value in data_row.items():
        if field_name in invoice_fields:
            invoice_kwargs[field_name] = value
        if field_name in items_fields:
            items_kwargs[field_name] = value
    return invoice_kwargs, items_kwargs


def get_credit_note_and_items_dict(data_row):
    credit_note_fields = [f.name for f in ZohoCreditNote._meta.get_fields()]
    items_fields = [f.name for f in ZohoCreditNoteItem._meta.get_fields()]
    credit_note_kwargs = {}
    credit_note_items_kwargs = {}
    for field_name, value in data_row.items():
        if field_name in credit_note_fields:
            credit_note_kwargs[field_name] = value
        if field_name in items_fields:
            credit_note_items_kwargs[field_name] = value
    return credit_note_kwargs, credit_note_items_kwargs
