import csv, io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Bin
from shops.models import Shop
from django.core.exceptions import ValidationError
from wkhtmltopdf.views import PDFTemplateResponse
from .forms import BulkBinUpdation, BinForm, OutForm, PickupForm
from .models import Out, Pickup, BinInventory
from retailer_to_sp.models import Order
from django.db import transaction
from django.http import HttpResponse
import openpyxl
import re
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response


def bins_upload(request):
    if request.method == 'POST':
        form = BulkBinUpdation(request.POST, request.FILES)
        print(request.FILES)
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


def put_away(request):
    form = BinForm
    bin_id = request.POST.get('bin_id')
    return render(request, 'admin/wms/putaway.html', {'form':form})


class CreatePickList(APIView):
    permission_classes = (AllowAny,)
    filename = 'picklist.pdf'
    template_name = 'admin/wms/picklist.html'
    new_list = []

    def get(self, request, *args, **kwargs):
        pick_list = get_object_or_404(Pickup, pk=self.kwargs.get('pk'))
        pu = Pickup.objects.filter(pickup_type_id=pick_list.pickup_type_id)
        data_list=[]
        product, sku, bin_id, batch_id, pickup_type_id = '', '', '', '', ''
        mrp, already_picked, remaining_qty, pickup_id, qty, qty_in_bin, ids = 0, 0, 0, 0, 0, 0, 0
        for i in pu:
            qty = i.pickup_quantity
            pikachu = i.sku.rt_product_sku.filter(quantity__gt=0).order_by('-batch_id', '-quantity').last()
            pickup_id = i.id
            pickup_type_id = i.pickup_type_id
            product = i.sku.product_name
            sku = i.sku.product_sku
            mrp = i.sku.rt_cart_product_mapping.all().last().cart_product_price.mrp if i.sku.rt_cart_product_mapping.all().last().cart_product_price else None
            batch_id = pikachu.batch_id if pikachu else None
            qty_in_bin = pikachu.quantity if pikachu else 0
            ids = pikachu.id if pikachu else None
            bin_id = pikachu.bin.bin_id if pikachu else None

        if qty - already_picked <= qty_in_bin:
            already_picked += qty
            remaining_qty = qty_in_bin - already_picked
            BinInventory.objects.filter(batch_id=batch_id, id=ids).update(quantity=remaining_qty)
            Pickup.objects.filter(pickup_type_id=pickup_type_id, id=pickup_id).update(pickup_quantity=0)
            prod_list = {"product": product, "sku": sku, "mrp": mrp, "qty": qty, "batch_id": batch_id, "bin": bin_id}
            data_list.append(prod_list)
        else:
            already_picked = qty_in_bin
            remaining_qty = qty - already_picked
            BinInventory.objects.filter(batch_id=batch_id, id=ids).update(quantity=0)
            Pickup.objects.filter(pickup_type_id=pickup_type_id, id=pickup_id).update(pickup_quantity=remaining_qty)
            prod_list = {"product": product, "sku": sku, "mrp": mrp, "qty": qty_in_bin, "batch_id": batch_id,"bin": bin_id}
            data_list.append(prod_list)
            self.get(request, *args, **kwargs)
        self.new_list.append(data_list[0])
        print(self.new_list)
        data = {
                "object": pu, "data_list":self.new_list[::-1]
                 }
        cmd_option = {
            "margin-top": 10,
            "zoom": 1,
            "javascript-delay": 1000,
            "footer-center": "[page]/[topage]",
            "no-stop-slow-scripts": True,
            "quiet": True
        }
        response = PDFTemplateResponse(
            request=request, template=self.template_name,
            filename=self.filename, context=data,
            show_content_in_browser=False, cmd_options=cmd_option
        )
        return response
