# python imports
import csv
from io import StringIO

import openpyxl
import re
import logging

# django imports
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.http import JsonResponse

# app imports
from .models import Bin
from shops.models import Shop

# third party imports
from wkhtmltopdf.views import PDFTemplateResponse
from .forms import BulkBinUpdation, BinForm, StockMovementCsvViewForm
from .models import Pickup, BinInventory, Putaway

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


def update_bin_inventory(id, quantity=0):
    """
    :param id:
    :param quantity:
    :return:
    """
    info_logger.info(quantity, "Bin Inventory quantity update function has been started.")
    try:
        BinInventory.objects.filter(id=id).update(quantity=quantity)
    except Exception as e:
        error_logger.error(e.message)
    info_logger.info(quantity, "Bin Inventory quantity updated successfully.")


def update_pickup_inventory(id, pickup_quantity=0):
    """
    :param id:
    :param pickup_quantity:
    :return:
    """
    info_logger.info(pickup_quantity, "Pick up quantity update function has started.")
    try:
        Pickup.objects.filter(id=id).update(pickup_quantity=pickup_quantity)
    except Exception as e:
        error_logger.error(e.message)
    info_logger.info(pickup_quantity, "Pick up quantity updated successfully.")


put_quantity = 0


def update_putaway(id, batch_id, warehouse, put_quantity):
    """
    :param id:
    :param batch_id:
    :param warehouse:
    :return:
    """
    try:
        info_logger.info("Put away quantity update function has started.")
        pu = Putaway.objects.filter(id=id, batch_id=batch_id, warehouse=warehouse)
        put_away_new = put_quantity if pu.last().quantity >= put_quantity else put_quantity -(put_quantity - pu.last().quantity)
        updated_putaway=pu.last().putaway_quantity
        if updated_putaway==pu.last().quantity:
            return put_quantity
        pu.update(putaway_quantity=updated_putaway+put_away_new)
        put_quantity = put_quantity - put_away_new
        info_logger.info(put_quantity, "Put away quantity updated successfully.")
        return put_quantity
    except Exception as e:
        error_logger.error(e.message)


def bins_upload(request):
    if request.method == 'POST':
        info_logger.info("POST request while upload the .xls file for Bin generation.")
        form = BulkBinUpdation(request.POST, request.FILES)
        if form.is_valid():
            info_logger.info("File format validation has been successfully done.")
            try:
                with transaction.atomic():
                    wb_obj = openpyxl.load_workbook(form.cleaned_data.get('file'))
                    sheet_obj = wb_obj.active
                    for row in sheet_obj.iter_rows(
                            min_row=2, max_row=None, min_col=None, max_col=None,
                            values_only=True
                    ):
                        info_logger.info("xls data validation has been started.")
                        if not row[0]:
                            raise ValidationError("warehouse field must not be empty. It should be Integer.")

                        if not row[2]:
                            raise ValidationError("Bin Type must not be empty.")

                        if not row[2] in ['p', 'sr']:
                            raise ValidationError("Bin Type must be start with either p or sr.")

                        if not row[3]:
                            raise ValidationError("Is Active field must not be empty.")

                        if not row[3] in ['t']:
                            raise ValidationError("Active field should be start with t char only.")

                        if not row[1]:
                            raise ValidationError("Bin ID must not be empty.")

                        if len(row[1]) < 14:
                            raise ValidationError('Bin Id min and max char limit is 14.Example:-B2BZ01SR01-001')

                        if not row[1][0:3] in ['B2B', 'B2C']:
                            raise ValidationError('First three letter should be start with either B2B and B2C.'
                                                  'Example:-B2BZ01SR01-001')
                        if not row[1][3] in ['Z']:
                            raise ValidationError('Zone should be start with char Z.Example:-B2BZ01SR01-001')
                        if not bool(re.match('^[0-9]+$', row[1][4:6]
                                             ) and not row[1][4:6] == '00'):
                            raise ValidationError(
                                'Zone number should be start in between 01 to 99.Example:-B2BZ01SR01-001')
                        if not row[1][6:8] in ['SR', 'PA']:
                            raise ValidationError('Rack type should be start with either SR and RA char only. '
                                                  'Example:-B2BZ01SR01-001')
                        if not bool(re.match('^[0-9]+$', row[1][8:10]
                                             ) and not row[1][8:10] == '00'):
                            raise ValidationError('Rack number should be start in between 01 to 99.'
                                                  'Example:- B2BZ01SR01-001')
                        if not row[1][10] in ['-']:
                            raise ValidationError('Only - allowed in between Rack number and Bin Number.'
                                                  'Example:-B2BZ01SR01-001')
                        if not bool(re.match('^[0-9]+$', row[1][11:14]
                                             ) and not row[1][11:14] == '000'):
                            raise ValidationError('Bin number should be start in between 001 to 999.'
                                                  'Example:-B2BZ01SR01-001')

                        info_logger.info("xls data validation has been passed.")
                        warehouse = Shop.objects.filter(id=int(row[0]))
                        if warehouse.exists():
                            bin_obj, created = Bin.objects.update_or_create(warehouse=warehouse.last(),
                                                        bin_id=row[1],
                                                        bin_type=row[2],
                                                        is_active=row[3],
                                                        )
                            if not created:
                                raise Exception(row[1], 'Bin with same data is already exist in the database.')
                        else:
                            raise Exception(row[0], "Warehouse id does not exist in the system.")

                return redirect('/admin/wms/bin/')

            except Exception as e:
                error_logger.error(e.message)
                messages.error(request, '{} (Shop: {})'.format(e.message, row[0]))
        else:
            raise Exception(form.errors['file'][0])
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


class PickupInventoryManagement:

    def __init__(self):
        self.count = 0
        self.qty, self.qty_in_pickup, self.picked_p = 0, 0, 0
        self.pickup_quantity = 0
        self.binid, self.id = 0, 0

    def pickup_bin_inventory(self, bin_id, order_no, pickup_quantity_new, sku):
        try:
            info_logger.info("Pickup bin inventory quantity API method has been started.")
            lis_data, data = [], {}
            """
            :param bin_id:
            :param order_no:
            :param pickup_quantity_new:
            :param sku:
            :return:
            """
            self.count += 1
            diction = {i[1]:i[0] for i in zip(pickup_quantity_new, sku)}
            for value, i in diction.items():
                self.pickup_quantity = i
                binInv = BinInventory.objects.filter(bin__bin_id=bin_id, quantity__gt=0, sku__id=value).order_by('-batch_id', 'quantity')
                if len(binInv) == 0:
                    return 1
                for b in binInv:
                    if len(b.sku.rt_product_pickup.filter(pickup_type_id=order_no)) == 0:
                        return 0
                    for c in b.sku.rt_product_pickup.filter(pickup_type_id=order_no):
                        already_picked = 0
                        remaining_qty = 0
                        self.qty = c.pickup_quantity if c.pickup_quantity else 0
                        self.id = c.id
                        qty_in_pickup = c.quantity
                        # if i == self.qty:
                        #     msg = {'is_success': False,
                        #            'Pickup': 'pickup complete for {}'.format(value), 'sku_id':value}
                        #     # lis_data.append(msg)
                        #     continue

                        if self.pickup_quantity > c.quantity - self.qty:
                            msg = {'is_success': False,
                                   'Pickup':"Can add only {} more items for {}".format((c.quantity-c.pickup_quantity), value),'sku_id':value}
                            lis_data.append(msg)
                            continue
                        else:
                            if self.pickup_quantity - already_picked <= b.quantity:
                                already_picked += self.pickup_quantity
                                remaining_qty = b.quantity - already_picked
                                update_bin_inventory(b.id, remaining_qty)
                                updated_pickup = self.qty+already_picked
                                update_pickup_inventory(self.id, updated_pickup)
                            else:
                                already_picked = b.quantity
                                self.picked_p += already_picked
                                remaining_qty = self.pickup_quantity - already_picked
                                update_bin_inventory(b.id)
                                update_pickup_inventory(self.id, self.picked_p)
                                if b.value in [d.value for d in BinInventory.objects.filter(bin__bin_id=bin_id, quantity__gt=0).order_by('-batch_id', 'quantity')]:
                                    self.pickup_quantity -= b.quantity
                                else:
                                    self.pickup_quantity = i
                                self.pickup_bin_inventory(bin_id, order_no, self.pickup_quantity, sku=value)
            data.update({'data':lis_data})
            return lis_data
        except Exception as e:
            error_logger.error(e.message)


from django.views.generic import View, FormView


class StockMovementCsvSample(View):
    """
    This class is used to download the sample file for different stock movement
    """
    def get(self, request, *args, **kwargs):
        """

        :param request: GET request
        :param args: non keyword argument
        :param kwargs: keyword argument
        :return: csv file
        """
        try:
            if request.GET['inventory_movement_type'] == '2':
                # name of the csv file
                filename = 'bin_stock_movement' + ".csv"
                f = StringIO()
                writer = csv.writer(f)
                # header of csv file
                writer.writerow(['Warehouse ID', 'SKU', 'Batch ID ', 'Initial Type', 'Final Type', 'Initial Bin ID',
                                 'Final Bin ID', 'Quantity'])
                writer.writerow(['88', 'ORCPCRTOY00000002', 'ORCPCRTOY000000020820', 'normal', 'damaged',
                                 'B2BZ01SR01-001', 'B2BZ01SR01-002', '100'])
            elif request.GET['inventory_movement_type'] == '3':
                filename = 'stock_correction' + ".csv"
                f = StringIO()
                writer = csv.writer(f)
                # header of csv file
                writer.writerow(['Warehouse ID', 'SKU', 'Bin ID', 'Batch ID', 'Expiry Date(MM-YYYY)', 'In/Out',
                                 'Quantity'])
                writer.writerow(['88', 'ORCPCRTOY00000002', 'B2BZ01SR01-001', 'ORCPCRTOY000000020820', '02-2020', 'In',
                                 '100'])

            elif request.GET['inventory_movement_type'] == '4':
                filename = 'warehouse_inventory_change' + ".csv"
                f = StringIO()
                writer = csv.writer(f)
                # header of csv file
                writer.writerow(['Warehouse ID', 'SKU', 'Initial Stage', 'Final Stage', 'Quantity', 'Inventory Type'])
                writer.writerow(['88', 'ORCPCRTOY00000002', 'available', 'reserved', '100', 'normal'])

            f.seek(0)
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            return response
        except Exception as e:
            error_logger.error(e.message)


class StockMovementCsvView(FormView):
    """
    This class is used to upload csv file for different stock movement
    """
    form_class = StockMovementCsvViewForm

    def post(self, request, *args, **kwarg):
        """

        :param request: POST or ajax call
        :param args: non keyword argument
        :param kwarg: keyword argument
        :return: success and error message based on the logical condition
        """
        if request.method == 'POST' and request.is_ajax():
            form_class = self.get_form_class()
            form = self.get_form(form_class)
            # to verify the form
            try:
                if form.is_valid():
                    result = {'message': 'CSV uploaded successfully.'}
                    status = '200'
                # return validation error message while uploading csv file
                else:
                    result = {'message': form.errors['file'][0]}
                    status = '400'

                return JsonResponse(result, status=status)
            # exception block
            except Exception as e:
                error_logger.exception(e)
                result = {'message': "Issue in file"}
                status = '400'
                return JsonResponse(result, status)
        else:
            result = {'message': "This method is not allowed"}
            status = '400'
        return JsonResponse(result, status)
