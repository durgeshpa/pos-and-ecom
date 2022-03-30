import csv
import codecs


def zoho_credit_note_data_upload(credit_note_file):
    pass


def zoho_invoice_data_upload(invoice_file):
    reader = csv.reader(codecs.iterdecode(invoice_file, 'utf-8'))
    next(reader)
    for row in reader:
        pass


def zoho_customers_file_upload(request, customer_file):
    reader = csv.reader(codecs.iterdecode(invoice_file, 'utf-8'))
    next(reader)
    for row in reader:
        pass
