import logging

from django.db import transaction
from django.shortcuts import render, redirect

# Create your views here.
from .forms import ZohoInvoiceFileUploadForm, ZohoCreditNoteFileUploadForm, ZohoCustomerFileUploadForm
# Logger
from .models import ZohoFileUpload
from .services import zoho_credit_note_data_upload, zoho_invoice_data_upload, zoho_customers_file_upload

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def bulk_zoho_invoice_file_upload(request):
    if request.method == 'POST':
        info_logger.info("POST request while bulk zoho invoice file upload.")
        form = ZohoInvoiceFileUploadForm(request.POST)
        if form.is_valid():
            info_logger.info("Data validation has been successfully done.")
            try:
                invoice_file = form.cleaned_data['file']
                ZohoFileUpload.objects.create(file=invoice_file, upload_type='Invoice',
                                              created_by=request.user, updated_by=request.user)
                info_logger.info("Invoice File uploaded")
                with transaction.atomic():
                    zoho_invoice_data_upload(invoice_file)

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
                ZohoFileUpload.objects.create(file=credit_note_file, upload_type='Credit Note',
                                              created_by=request.user, updated_by=request.user)
                info_logger.info("Credit Note File uploaded")
                with transaction.atomic():
                    zoho_credit_note_data_upload(credit_note_file)
                return redirect('/admin/zoho/zohofileupload/')

            except Exception as e:
                error_logger.error(e)
        else:
            return render(request, 'admin/zoho/bulk-upload-credit-note.html', {'form': form})
    else:
        form = ZohoCreditNoteFileUploadForm()
    return render(request, 'admin/zoho/bulk-upload-credit-note.html', {'form': form})



def bulk_upload_zoho_customers_file_upload(request):
    if request.method == "POST":
        info_logger.info("POST request while bulk zoho Customers file upload.")
        form = ZohoCustomerFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            info_logger.info("Data validation has been successfully done.")
            try:
                credit_note_file = form.cleaned_data['file']
                info_logger.info("bulk zoho Customers file upload.")
                zoho_customers_file_upload(request, credit_note_file)

                ZohoFileUpload.objects.create(file=credit_note_file, upload_type='Credit Note',
                                              created_by=request.user, updated_by=request.user)
                return redirect('/admin/zoho/zohofileupload/')

            except Exception as e:
                error_logger.error(e)
        else:
            return render(request, 'admin/zoho/bulk-upload-credit-note.html', {'form': form})
    else:
        form = ZohoCustomerFileUploadForm()
    return render(request, 'admin/zoho/bulk-upload-credit-note.html', {'form': form})

        

