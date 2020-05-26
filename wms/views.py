import csv, io
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Bin
from shops.models import Shop
from django.core.exceptions import ValidationError
from .forms import BulkBinUpdation
from django.db import transaction
import openpyxl
import re



# def bins_upload(request):
#     template = "admin/wms/bulk-bin-updation.html"
#     data = Bin.objects.all()
#     prompt = {
#         'order': 'Order of the CSV should be warehouse, bin_id, bin_type, is_active',
#         'bins_data': data
#     }
#     if request.method == "GET":
#         return render(request, template, prompt)
#     if request.FILES:
#         csv_file = request.FILES['file']
#         print(csv_file.name.endswith('.csv'))
#         if csv_file.name.endswith('.csv'):
#             data_set = csv_file.read().decode('UTF-8')
#             io_string = io.StringIO(data_set)
#             next(io_string)
#             for column in csv.reader(io_string, delimiter=',', quotechar="|"):
#                 _, created = Bin.objects.update_or_create(
#                     warehouse=Shop.objects.get(id=int(column[0])),
#                     bin_id=column[1],
#                     bin_type=column[2],
#                     is_active=column[3],
#                 )
#         else:
#             messages.error(request, 'THIS IS NOT A CSV FILE')
#     context = {}
#     return render(request, template, context)

def bins_upload(request):
    if request.method == 'POST':
        form = BulkBinUpdation(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    wb_obj = openpyxl.load_workbook(form.cleaned_data.get('file'))
                    sheet_obj = wb_obj.active
                    for row in sheet_obj.iter_rows(
                            min_row=2, max_row=None, min_col=None, max_col=None,
                            values_only=True
                    ):

                        if not [0]:
                            raise ValidationError("warehouse field must not be empty. It should be Integer")

                        if not row[2]:
                            raise ValidationError("Bin Type must not be empty")

                        if not [3]:
                            raise ValidationError("Is Active field must not be empty")

                        if not [1]:
                            raise ValidationError("Bin ID must not be empty")

                        warehouse =Shop.objects.filter(id=int(row[0]))
                        if warehouse.exists():
                            Bin.objects.update_or_create(warehouse=warehouse.last(),
                                                        bin_id=row[1],
                                                        bin_type=row[2],
                                                        is_active=row[3],
                                                        )
                        else:
                            raise Exception('Warehouse Does"t Exists')

                return redirect('/admin/wms/bin/')

            except Exception as e:
                messages.error(request, '{} (Shop: {})'.format(e, row[0]))
    else:
        form = BulkBinUpdation()

    return render(
        request,
        'admin/wms/bulk-bin-updation.html',
        {'form': form}
    )


