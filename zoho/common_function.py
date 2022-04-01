import csv
import logging
from django.http import HttpResponse

from zoho.models import ZohoInvoice, ZohoInvoiceItem, ZohoCreditNoteItem, ZohoCreditNote
from zoho.utils import get_invoice_and_items_dict, get_credit_note_and_items_dict

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


class ZohoInvoiceCls:
    @classmethod
    def create_zoho_invoice(cls, validated_rows, created_by):
        try:
            created_invoice = []
            for row in validated_rows:
                invoice_kwargs, items_kwargs = get_invoice_and_items_dict(row)
                # Store Invoices in db
                invoice_number = invoice_kwargs.pop('invoice_number', None)
                zoho_invoice_obj, created = ZohoInvoice.objects.update_or_create(
                    invoice_number=invoice_number, defaults=invoice_kwargs)
                if created:
                    created_invoice.append(zoho_invoice_obj)
                    zoho_invoice_obj.created_by = created_by
                else:
                    zoho_invoice_obj.updated_by = created_by
                zoho_invoice_obj.save()
                # Store Items in db
                if zoho_invoice_obj in created_invoice:
                    items_kwargs["zoho_invoice"] = zoho_invoice_obj
                    ZohoInvoiceItem.objects.create(**items_kwargs)
                    # product_id = items_kwargs.pop('product_id', None)
                    # ZohoInvoiceItem.objects.update_or_create(
                    #     product_id=product_id, zoho_invoice=zoho_invoice_obj, defaults=items_kwargs)

        except Exception as e:
            error_logger.error(e)
            print(e)

    @classmethod
    def create_zoho_credit_note(cls, validated_rows, created_by):
        try:
            created_credit_note = []
            for row in validated_rows:
                credit_note_kwargs, credit_note_items_kwargs = get_credit_note_and_items_dict(row)
                # Store Invoices in db
                credit_note_number = credit_note_kwargs.pop('credit_note_number', None)
                credit_note_obj, created = ZohoCreditNote.objects.update_or_create(
                    credit_note_number=credit_note_number, defaults=credit_note_kwargs)
                if created:
                    created_credit_note.append(credit_note_obj)
                    credit_note_obj.created_by = created_by
                else:
                    credit_note_obj.updated_by = created_by
                credit_note_obj.save()
                # Store Items in db
                if credit_note_obj in created_credit_note:
                    credit_note_items_kwargs["zoho_credit_note"] = credit_note_obj
                    ZohoCreditNoteItem.objects.create(**credit_note_items_kwargs)
                    # product_id = credit_note_items_kwargs.pop('product_id', None)
                    # ZohoCreditNoteItem.objects.update_or_create(
                    #     product_id=product_id, zoho_credit_note=credit_note_obj, defaults=credit_note_items_kwargs)

        except Exception as e:
            error_logger.error(e)
            print(e)


def error_invoice_credit_note_csv_file(data_list, file_name):
    # Write error msg in csv sheet.
    filename = file_name
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachement; filename="{}"'.format(filename)

    writer = csv.writer(response)
    for row in data_list:
        writer.writerow(row)

    return response
