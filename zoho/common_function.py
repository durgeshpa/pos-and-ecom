import csv
from django.http import HttpResponse

from zoho.models import ZohoInvoice, ZohoInvoiceItem, ZohoCreditNoteItem, ZohoCreditNote
from zoho.utils import get_invoice_and_items_dict, get_credit_note_and_items_dict


class ZohoInvoiceCls:
    @classmethod
    def create_zoho_invoice(cls, validated_rows, created_by):
        try:
            for row in validated_rows:
                invoice_kwargs, items_kwargs = get_invoice_and_items_dict(row)
                # Store Invoices in db
                invoice_id = invoice_kwargs.pop('invoice_id', None)
                zoho_invoice_obj, created = ZohoInvoice.objects.update_or_create(
                    invoice_id=invoice_id, defaults=invoice_kwargs)
                # Store Items in db
                product_id = items_kwargs.pop('product_id', None)
                ZohoInvoiceItem.objects.update_or_create(
                    product_id=product_id, zoho_invoice=zoho_invoice_obj, defaults=items_kwargs)

        except Exception as e:
            print(e)

    @classmethod
    def create_zoho_credit_note(cls, validated_rows, created_by):
        try:
            for row in validated_rows:
                credit_note_kwargs, credit_note_items_kwargs = get_credit_note_and_items_dict(row)
                # Store Invoices in db
                creditnotes_id = credit_note_kwargs.pop('creditnotes_id', None)
                credit_note_obj, created = ZohoCreditNote.objects.update_or_create(
                    creditnotes_id=creditnotes_id, defaults=credit_note_kwargs)
                # Store Items in db
                product_id = credit_note_items_kwargs.pop('product_id', None)
                ZohoCreditNoteItem.objects.update_or_create(
                    product_id=product_id, zoho_credit_note=credit_note_obj, defaults=credit_note_items_kwargs)

        except Exception as e:
            print(e)


def error_invoice_credit_note_csv_file(data_list, file_name):
    # Write error msg in csv sheet.
    filename = file_name.csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachement; filename="{}"'.format(filename)

    writer = csv.writer(response)
    for row in data_list:
        writer.writerow(row)

    return response
