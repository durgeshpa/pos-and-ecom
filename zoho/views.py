import logging

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect

# Create your views here.
from zoho.common_function import ZohoInvoiceCls, error_invoice_credit_note_csv_file
from zoho.common_validators import bulk_invoice_data_validation
from zoho.forms import ZohoInvoiceFileUploadForm, ZohoCreditNoteFileUploadForm
# Logger
from zoho.models import ZohoFileUpload

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def bulk_zoho_invoice_file_upload(request):
    if request.method == 'POST':
        info_logger.info("POST request while bulk zoho invoice file upload.")
        form = ZohoInvoiceFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            info_logger.info("Data validation has been successfully done.")
            try:
                invoice_file = form.cleaned_data['file']
                invoice_file_obj = ZohoFileUpload.objects.create(file=invoice_file, upload_type=ZohoFileUpload.INVOICE,
                                                                 created_by=request.user, updated_by=request.user)
                response = pos_save_invoice_file(invoice_file_obj)
                info_logger.info("Invoice File uploaded")
                if isinstance(response, HttpResponse):
                    return response

                return redirect('/admin/zoho/zohofileupload/')
            except Exception as e:
                error_logger.error(e)
        else:
            return render(request, 'admin/zoho/bulk-upload-invoices.html', {'form': form})
    else:
        form = ZohoInvoiceFileUploadForm()
    return render(request, 'admin/zoho/bulk-upload-invoices.html', {'form': form})


def bulk_zoho_credit_note_file_upload(request):
    if request.method == 'POST':
        info_logger.info("POST request while bulk zoho credit file upload.")
        form = ZohoCreditNoteFileUploadForm(request.POST)
        if form.is_valid():
            info_logger.info("Data validation has been successfully done.")
            try:
                credit_note_file = form.cleaned_data['file']
                ZohoFileUpload.objects.create(file=credit_note_file, upload_type=ZohoFileUpload.CREDIT_NOTE,
                                              created_by=request.user, updated_by=request.user)
                info_logger.info("Credit Note File uploaded")
                with transaction.atomic():
                    pos_save_credit_note_file(credit_note_file)
                return redirect('/admin/zoho/zohofileupload/')

            except Exception as e:
                error_logger.error(e)
        else:
            return render(request, 'admin/zoho/bulk-upload-credit-note.html', {'form': form})
    else:
        form = ZohoCreditNoteFileUploadForm()
    return render(request, 'admin/zoho/bulk-upload-credit-note.html', {'form': form})


def pos_save_invoice_file(bulk_invoice_obj):
    response_file = None
    if bulk_invoice_obj:
        if bulk_invoice_obj.file:
            error_list, validated_rows = bulk_invoice_data_validation(bulk_invoice_obj.file)
            if validated_rows:
                ZohoInvoiceCls.create_zoho_invoice(validated_rows, bulk_invoice_obj.created_by)
            if len(error_list) > 1:
                response_file = error_invoice_credit_note_csv_file(error_list, 'zoho_invoice_error')
    return response_file


def pos_save_credit_note_file(bulk_invoice_obj):
    response_file = None
    if bulk_invoice_obj:
        if bulk_invoice_obj.file:
            error_list, validated_rows = bulk_invoice_data_validation(bulk_invoice_obj.file)
            if validated_rows:
                ZohoInvoiceCls.create_zoho_invoice(validated_rows, bulk_invoice_obj.created_by)
            if len(error_list) > 1:
                response_file = error_invoice_credit_note_csv_file(error_list, 'zoho_credit_note_error')
    return response_file
