# python imports
import csv
from io import StringIO
import codecs
import itertools
import openpyxl
import re
import logging

from django.db.models.functions import Length

from barCodeGenerator import barcodeGen
# django imports
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
from sp_to_gram.tasks import update_shop_product_es, update_product_es
from django.db.models.signals import post_save
from django.db.models import Sum
from django.dispatch import receiver
from django.db import transaction, DatabaseError
from datetime import datetime, timedelta
from .common_functions import CommonPickBinInvFunction, CommonPickupFunctions, \
    create_batch_id, set_expiry_date, CommonWarehouseInventoryFunctions, OutCommonFunctions, \
    common_release_for_inventory, cancel_shipment, cancel_ordered, cancel_returned, WareHouseInternalInventoryChange, \
    get_expiry_date_db
from .models import Bin, InventoryType, WarehouseInternalInventoryChange, WarehouseInventory, OrderReserveRelease, In, \
    BinInternalInventoryChange, ExpiredInventoryMovement, Putaway
from .models import Bin, WarehouseInventory, PickupBinInventory, Out, PutawayBinInventory
from shops.models import Shop
from retailer_to_sp.models import Cart, Order, generate_picklist_id, PickerDashboard, OrderedProductBatch, \
    OrderedProduct, OrderedProductMapping
from products.models import Product, ProductPrice
from gram_to_brand.models import GRNOrderProductMapping

# third party imports
from wkhtmltopdf.views import PDFTemplateResponse
from .forms import BulkBinUpdation, BinForm, StockMovementCsvViewForm, DownloadAuditAdminForm, UploadAuditAdminForm
from .models import Pickup, BinInventory, InventoryState
from .common_functions import InternalInventoryChange, CommonBinInventoryFunctions, PutawayCommonFunctions, \
    InCommonFunctions, WareHouseCommonFunction, InternalWarehouseChange, StockMovementCSV, \
    InternalStockCorrectionChange, get_product_stock, updating_tables_on_putaway, AuditInventory, inventory_in_and_out
from barCodeGenerator import barcodeGen, merged_barcode_gen
from services.models import WarehouseInventoryHistoric, BinInventoryHistoric, InventoryArchiveMaster

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


class MergeBarcode(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        bin = Bin.objects.filter(pk=self.kwargs.get('id')).last()
        bin_barcode_txt = bin.bin_barcode_txt
        if bin_barcode_txt is None:
            bin_barcode_txt = '1' + str(bin.id).zfill(11)
        bin_id_list = {bin_barcode_txt: {"qty": 1, "data": {"Bin": bin.bin_id}}}
        return merged_barcode_gen(bin_id_list)


def update_bin_inventory(id, quantity=0):
    """
    :param id:
    :param quantity:
    :return:
    """
    info_logger.info(quantity, "Bin Inventory quantity update function has been started.")
    try:
        CommonBinInventoryFunctions.get_filtered_bin_inventory(id=id).update(quantity=quantity)
    except Exception as e:
        error_logger.error(e)
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
        error_logger.error(e)
    info_logger.info(pickup_quantity, "Pick up quantity updated successfully.")


put_quantity = 0


def update_putaway(id, batch_id, warehouse, put_quantity, user):
    """
    :param id:
    :param batch_id:
    :param warehouse:
    :return:
    """
    try:
        info_logger.info("Put away quantity update function has started.")
        pu = PutawayCommonFunctions.get_filtered_putaways(id=id, batch_id=batch_id, warehouse=warehouse)
        put_away_new = put_quantity if pu.last().quantity >= put_quantity else put_quantity - (
                put_quantity - pu.last().quantity)
        updated_putaway = pu.last().putaway_quantity
        if updated_putaway == pu.last().quantity:
            return put_quantity
        pu.update(putaway_quantity=updated_putaway + put_away_new, putaway_user=user)
        put_quantity = put_quantity - put_away_new
        info_logger.info(put_quantity, "Put away quantity updated successfully.")
        return put_quantity
    except Exception as e:
        error_logger.error(e)


from django import forms


def bins_upload(request):
    if request.method == 'POST':
        info_logger.info("POST request while upload the .xls file for Bin generation.")
        form = BulkBinUpdation(request.POST, request.FILES)
        if form.is_valid():
            info_logger.info("File format validation has been successfully done.")
            try:
                upload_data = form.cleaned_data['file']
                for row_id, data in enumerate(upload_data):
                    with transaction.atomic():
                        info_logger.info("xls data validation has been passed.")
                        warehouse = Shop.objects.filter(id=int(data[1]))
                        if warehouse.exists():
                            if Bin.objects.filter(warehouse=warehouse.last(), bin_id=data[3]).exists():
                                return render(request, 'admin/wms/bulk-bin-updation.html',
                                              {'error': 'Row' + ' ' + str(row_id + 1) + ' ' + 'Duplicate Bin ID,'
                                                                                              ' Please verify at your end.',
                                               'form': form})
                            else:
                                bin_obj, created = Bin.objects.get_or_create(warehouse=warehouse.last(),
                                                                             bin_id=data[3],
                                                                             bin_type=data[2],
                                                                             is_active='t')
                                if not created:
                                    return render(request, 'admin/wms/bulk-bin-updation.html', {
                                        'error': 'Row' + ' ' + str(
                                            row_id + 1) + ' ' + 'Same Data is already exist in the system.'
                                                                'Please re-verify at your end.',
                                        'form': form})
                        else:
                            return render(request, 'admin/wms/bulk-bin-updation.html', {
                                'error': 'Row' + ' ' + str(
                                    row_id + 1) + ' ' + 'WareHouse ID is not exist in the system,'
                                                        ' Please re-verify at your end.',
                                'form': form})

                return redirect('/admin/wms/bin/')

            except Exception as e:
                error_logger.error(e)
        else:
            return render(request, 'admin/wms/bulk-bin-updation.html', {'form': form})
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
    return render(request, 'admin/wms/putaway.html', {'form': form})


class CreatePickList(APIView):
    permission_classes = (AllowAny,)
    filename = 'picklist.pdf'
    template_name = 'admin/wms/picklist.html'

    def get(self, request, *args, **kwargs):
        order = get_object_or_404(Order, pk=self.kwargs.get('pk'))
        barcode = barcodeGen(order.order_no)
        picku_bin_inv = PickupBinInventory.objects.filter(pickup__pickup_type_id=order.order_no)
        data_list = []
        new_list = []
        for i in picku_bin_inv:
            product = i.pickup.sku.product_name
            sku = i.pickup.sku.product_sku
            cart_product = order.ordered_cart.rt_cart_list.filter(cart_product=i.pickup.sku).last()
            mrp = cart_product.cart_product_price.mrp
            # mrp = i.pickup.sku.rt_cart_product_mapping.all().order_by('created_at')[0].cart_product_price.mrp
            qty = i.quantity
            batch_id = i.batch_id
            bin_id = i.bin.bin.bin_id
            prod_list = {"product": product, "sku": sku, "mrp": mrp, "qty": qty, "batch_id": batch_id, "bin": bin_id}
            data_list.append(prod_list)
        data = {"data_list": data_list,
                "buyer_shop": order.ordered_cart.buyer_shop.shop_name,
                "buyer_contact_no": order.ordered_cart.buyer_shop.shop_owner.phone_number,
                "buyer_shipping_address": order.shipping_address.address_line1,
                "buyer_shipping_city": order.shipping_address.city.city_name,
                "barcode": barcode,
                "order_obj": order,
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
            diction = {i[1]: i[0] for i in zip(pickup_quantity_new, sku)}
            for value, i in diction.items():
                self.pickup_quantity = i
                binInv = BinInventory.objects.filter(bin__bin_id=bin_id, quantity__gt=0, sku__id=value).order_by(
                    '-batch_id', 'quantity')
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
                                   'Pickup': "Can add only {} more items for {}".format(
                                       (c.quantity - c.pickup_quantity), value), 'sku_id': value}
                            lis_data.append(msg)
                            continue
                        else:
                            if self.pickup_quantity - already_picked <= b.quantity:
                                already_picked += self.pickup_quantity
                                remaining_qty = b.quantity - already_picked
                                update_bin_inventory(b.id, remaining_qty)
                                updated_pickup = self.qty + already_picked
                                update_pickup_inventory(self.id, updated_pickup)
                            else:
                                already_picked = b.quantity
                                self.picked_p += already_picked
                                remaining_qty = self.pickup_quantity - already_picked
                                update_bin_inventory(b.id)
                                update_pickup_inventory(self.id, self.picked_p)
                                if b.value in [d.value for d in
                                               BinInventory.objects.filter(bin__bin_id=bin_id, quantity__gt=0).order_by(
                                                   '-batch_id', 'quantity')]:
                                    self.pickup_quantity -= b.quantity
                                else:
                                    self.pickup_quantity = i
                                self.pickup_bin_inventory(bin_id, order_no, self.pickup_quantity, sku=value)
            data.update({'data': lis_data})
            return lis_data
        except Exception as e:
            error_logger.error(e)


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
                writer.writerow(['Warehouse ID', 'SKU', 'Batch ID ', 'Initial Bin ID',
                                 'Final Bin ID', 'Initial Type', 'Final Type', 'Quantity'])
                writer.writerow(
                    ['1393', 'ORCPCRTOY00000002', 'ORCPCRTOY000000020820', 'B2BZ01SR01-001', 'B2BZ01SR01-002',
                     'normal', 'damaged', '100'])
                f.seek(0)
                response = HttpResponse(f, content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
                return response
            elif request.GET['inventory_movement_type'] == '3':
                filename = 'stock_correction' + ".csv"
                f = StringIO()
                writer = csv.writer(f)
                # header of csv file
                writer.writerow(
                    ['Warehouse ID', 'Product Name', 'SKU', 'Expiry Date', 'Bin ID',
                     'Normal Quantity', 'Damaged Quantity', 'Expired Quantity', 'Missing Quantity'])
                writer.writerow(['88', 'Complan Kesar Badam Refill, 200 gm', 'HOKBACFRT00000021', '20/08/2020',
                                 'V2VZ01SR001-0001', '0', '0', '0', '0'])
                f.seek(0)
                response = HttpResponse(f, content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
                return response
            elif request.GET['inventory_movement_type'] == '4':
                filename = 'warehouse_inventory_change' + ".csv"
                f = StringIO()
                writer = csv.writer(f)
                # header of csv file
                writer.writerow(['Warehouse ID', 'SKU', 'Initial Stage', 'Final Stage', 'Inventory Type', 'Quantity'])
                writer.writerow(['1393', 'ORCPCRTOY00000002', 'available', 'reserved', 'normal', '100'])

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
                    upload_data = form.cleaned_data['file']
                    try:
                        # create date in Stock Movement Csv Upload Model
                        stock_movement_obj = StockMovementCSV.create_stock_movement_csv(request.user,
                                                                                        request.FILES['file'],
                                                                                        request.POST[
                                                                                            'inventory_movement_type'])
                        if request.POST['inventory_movement_type'] == '2':
                            bin_stock_movement_data(upload_data, stock_movement_obj)
                        elif request.POST['inventory_movement_type'] == '3':
                            stock_correction = stock_correction_data(upload_data, stock_movement_obj)
                            if stock_correction is True:
                                result = {'message': 'CSV uploaded successfully.'}
                                status = '200'
                            else:
                                result = {'message': stock_correction.args[0]}
                                status = '400'
                        else:
                            warehouse_inventory_change_data(upload_data, stock_movement_obj)
                    except Exception as e:
                        error_logger.exception(e)
                        result = {'message': 'Something went wrong! Please verify the data.'}
                        status = '400'
                        return JsonResponse(result, status)
                # return validation error message while uploading csv file
                else:
                    result = {'message': form.errors['file'][0]}
                    status = '400'
                return JsonResponse(result, status=status)
            # exception block
            except Exception as e:
                error_logger.exception(e)
                result = {'message': 'Something went wrong! Please verify the data.'}
                status = '400'
                return JsonResponse(result, status)
        else:
            result = {'message': "This method is not allowed."}
            status = '400'
        return JsonResponse(result, status)


def commit_updates_to_es(shop, product):
    """
    :param shop:
    :param product:
    :return:
    """
    status = True
    db_available_products = get_product_stock(shop, product)
    products_available = db_available_products.aggregate(Sum('quantity'))['quantity__sum']
    try:
        available_qty = int(int(products_available) / int(product.product_inner_case_size))
    except Exception as e:
        status = False
        update_product_es.delay(shop.id, product.id, available=0, status=status)
        return False
    if not available_qty:
        status = False
    info_logger.info("updating ES %s", available_qty)
    update_product_es.delay(shop.id, product.id, available=available_qty, status=status)


@receiver(post_save, sender=WarehouseInventory)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    info_logger.info("Post save called for Warehouse Inventory")
    if instance.inventory_type.inventory_type == 'normal' and instance.inventory_state.inventory_state == 'available':
        info_logger.info("Inside if condition of post save Warehouse Inventory")
        commit_updates_to_es(instance.warehouse, instance.sku)


def bin_stock_movement_data(upload_data, stock_movement_obj):
    """

        :param upload_data: Collection of csv data
        :param stock_movement_obj: object of CSV file
        :return: result
    """
    try:
        with transaction.atomic():
            for data in upload_data:
                # condition to get the queryset for Initial Bin ID
                initial_inventory_object = CommonBinInventoryFunctions.filter_bin_inventory(data[0], data[1], data[2],
                                                                                            Bin.objects.get(
                                                                                                bin_id=data[3]),
                                                                                            data[5])
                initial_quantity = initial_inventory_object[0].quantity

                # get the quantity of Initial bin
                quantity = initial_quantity - int(data[7])

                # update the quantity of Initial Bin ID
                CommonBinInventoryFunctions.update_or_create_bin_inventory(
                    data[0], Bin.objects.get(bin_id=data[3]), Product.objects.get(product_sku=data[1]),
                    data[2], InventoryType.objects.get(inventory_type=data[5]), quantity, True)

                # condition to get the queryset for Final Bin ID
                final_inventory_object = CommonBinInventoryFunctions.filter_bin_inventory(data[0], data[1], data[2],
                                                                                          Bin.objects.get(
                                                                                              bin_id=data[4]),
                                                                                          data[6])
                if not final_inventory_object:
                    final_quantity = int(data[7])
                else:
                    final_quantity = final_inventory_object[0].quantity + int(data[7])

                # update the quantity of Final Bin ID
                CommonBinInventoryFunctions.update_or_create_bin_inventory(
                    Shop.objects.get(id=data[0]), Bin.objects.get(bin_id=data[4]),
                    Product.objects.get(product_sku=data[1]), data[2],
                    InventoryType.objects.get(inventory_type=data[6]), final_quantity, True)

                # create data in Internal Inventory Change Model
                InternalInventoryChange.create_bin_internal_inventory_change(data[0], data[1], data[2],
                                                                             data[3], data[4], data[5],
                                                                             data[6], data[7], stock_movement_obj[0])
            return
    except Exception as e:
        error_logger.error(e)


def stock_correction_data(upload_data, stock_movement_obj):
    """

    :param upload_data: Collection of csv data
    :param stock_movement_obj: object of CSV file
    :return: result
    """
    try:
        with transaction.atomic():
            in_quantity = 0
            out_quantity = 0
            for data in upload_data:
                # get the type of stock
                stock_correction_type = 'stock_adjustment'
                # Create data in IN Model
                sku = data[2]
                expiry_date = data[3]
                # create batch id
                batch_id = create_batch_id(sku, expiry_date)

                # to check normal quantity is available or not in Bin Inventory object
                bin_inv_normal = BinInventory.objects.filter(warehouse=data[0],
                                            bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                            sku=Product.objects.filter(
                                                product_sku=data[2]).last(),
                                            batch_id=batch_id,
                                            inventory_type__id=InventoryType.objects.filter(inventory_type='normal')[
                                                0].id).last()

                # if exists
                if bin_inv_normal:
                    # check whether the given quantity is greater or lower than normal quantity
                    if bin_inv_normal.quantity <= int(data[5]):

                        # add into in in_quantity
                        in_quantity = in_quantity + int(data[5])
                    else:
                        # add into in out quantity
                        out_quantity = out_quantity + int(data[5])
                else:
                    # if Norma quanity is not available in Bin Inventory object then create the data into Bin Inventory
                    BinInventory.objects.get_or_create(warehouse=Shop.objects.filter(id=data[0])[0],
                                                       bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                                       batch_id=batch_id,
                                                       sku=Product.objects.filter(
                                                           product_sku=data[2]).last(),
                                                       in_stock=True, quantity=int(data[5]),
                                                       inventory_type=InventoryType.objects.filter(
                                                           inventory_type='normal').last())
                    in_quantity = in_quantity + int(data[5])

                # to check normal damaged is available or not in Bin Inventory object
                bin_inv_damaged = BinInventory.objects.filter(warehouse=data[0],
                                                          bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                                          sku=Product.objects.filter(
                                                              product_sku=data[2]).last(),
                                                          batch_id=batch_id,
                                                          inventory_type__id=
                                                          InventoryType.objects.filter(inventory_type='damaged')[
                                                              0].id).last()
                if bin_inv_damaged:
                    if bin_inv_damaged.quantity <= int(data[6]):
                        in_quantity = in_quantity + int(data[6])
                    else:
                        out_quantity = out_quantity + int(data[6])
                else:
                    BinInventory.objects.get_or_create(warehouse=Shop.objects.filter(id=data[0])[0],
                                                       bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                                       batch_id=batch_id,
                                                       sku=Product.objects.filter(product_sku=data[2]).last(),
                                                       in_stock=True, quantity=int(data[6]),
                                                       inventory_type=InventoryType.objects.filter(
                                                           inventory_type='damaged').last())

                    in_quantity = in_quantity + int(data[6])

                # to check expired quantity is available or not in Bin Inventory object
                bin_inv_expired = BinInventory.objects.filter(warehouse=data[0],
                                                          bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                                          sku=Product.objects.filter(
                                                              product_sku=data[2]).last(),
                                                          batch_id=batch_id,
                                                          inventory_type__id=
                                                          InventoryType.objects.filter(inventory_type='expired')[
                                                              0].id).last()
                if bin_inv_expired:
                    if bin_inv_expired.quantity <= int(data[7]):
                        in_quantity = in_quantity + int(data[7])
                    else:
                        out_quantity = out_quantity + int(data[7])
                else:
                    BinInventory.objects.get_or_create(
                        warehouse=Shop.objects.filter(id=data[0])[0],
                        bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                        batch_id=batch_id,
                        sku=Product.objects.filter(
                            product_sku=data[2]).last(),
                        in_stock=True, quantity=int(data[7]),
                        inventory_type=InventoryType.objects.filter(
                            inventory_type='expired').last())

                    in_quantity = in_quantity + int(data[7])

                # to check missing quantity is available or not in Bin Inventory object
                bin_inv_missing = BinInventory.objects.filter(warehouse=data[0],
                                                          bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                                          sku=Product.objects.filter(
                                                              product_sku=data[2]).last(),
                                                          batch_id=batch_id,
                                                          inventory_type__id=
                                                          InventoryType.objects.filter(inventory_type='missing')[
                                                              0].id).last()
                if bin_inv_missing:
                    if bin_inv_missing.quantity <= int(data[8]):
                        in_quantity = in_quantity + int(data[8])
                    else:
                        out_quantity = out_quantity + int(data[8])
                else:
                    BinInventory.objects.get_or_create(
                        warehouse=Shop.objects.filter(id=data[0])[0],
                        bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                        batch_id=batch_id,
                        sku=Product.objects.filter(
                            product_sku=data[2]).last(),
                        in_stock=True, quantity=int(data[8]),
                        inventory_type=InventoryType.objects.filter(
                            inventory_type='missing').last())
                    in_quantity = in_quantity + int(data[8])

                if in_quantity >= 0:
                    InCommonFunctions.create_in(Shop.objects.get(id=data[0]), stock_correction_type,
                                                         stock_movement_obj[0].id,
                                                         Product.objects.get(product_sku=data[2]),
                                                         batch_id, in_quantity, 0)
                    # Create data in Stock Correction change Model
                    InternalStockCorrectionChange.create_stock_inventory_change(Shop.objects.get(id=data[0]),
                                                                                Product.objects.get(
                                                                                    product_sku=data[2]),
                                                                                batch_id,
                                                                                Bin.objects.get(bin_id=data[4],
                                                                                                warehouse=Shop.objects.get(
                                                                                                    id=data[0])),
                                                                                'In', in_quantity,
                                                                                stock_movement_obj[0])
                if out_quantity >= 0:
                    Out.objects.create(warehouse=Shop.objects.get(id=data[0]),
                                       out_type='stock_correction_out_type',
                                       out_type_id=stock_movement_obj[0].id,
                                       sku=Product.objects.get(product_sku=data[2]),
                                       batch_id=batch_id, quantity=out_quantity)
                    # Create data in Stock Correction change Model
                    InternalStockCorrectionChange.create_stock_inventory_change(Shop.objects.get(id=data[0]),
                                                                                Product.objects.get(
                                                                                    product_sku=data[2]),
                                                                                batch_id,
                                                                                Bin.objects.get(bin_id=data[4],
                                                                                                warehouse=Shop.objects.get(
                                                                                                    id=data[0])),
                                                                                'Out', out_quantity,
                                                                                stock_movement_obj[0])
                # Create date in BinInventory, Put Away BinInventory and WarehouseInventory
                # inventory_type = 'normal'
                inventory_state = 'available'
                status = True
                iter_list = iterate_quantity_type(data)
                for key, value in iter_list.items():
                    transaction_type_obj, transaction_type = check_transaction_type(key, value, data,
                                                                                    stock_movement_obj,
                                                                                    stock_correction_type,
                                                                                    in_quantity, out_quantity)
                    inventory_in_and_out(Shop.objects.get(id=data[0]), data[4],
                                         Product.objects.get(product_sku=data[2]), batch_id, key,
                                         inventory_state, status, value, status, transaction_type_obj,
                                         transaction_type, data[5])

            return True
    except Exception as e:
        return e


def check_transaction_type(key, value, data, stock_movement_obj, stock_correction_type, in_quantity, out_quantity):
    """

    :param key:
    :param value:
    :param data:
    :param stock_movement_obj:
    :param stock_correction_type:
    :param in_quantity:
    :param out_quantity:
    :return:
    """
    sku = data[2]
    expiry_date = data[3]
    batch_id = create_batch_id(sku, expiry_date)
    bin_inv_normal = BinInventory.objects.filter(warehouse=data[0],
                                                 bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                                 sku=Product.objects.filter(
                                                     product_sku=data[2]).last(),
                                                 batch_id=batch_id,
                                                 inventory_type__id=
                                                 InventoryType.objects.filter(inventory_type=key)[
                                                     0].id).last()
    if bin_inv_normal:
        if bin_inv_normal.quantity <= int(value):
            in_obj = InCommonFunctions.get_filtered_in(warehouse=Shop.objects.get(id=data[0]),
                                                       in_type=stock_correction_type,
                                                       in_type_id=stock_movement_obj[0].id,
                                                       sku=Product.objects.get(product_sku=data[2]),
                                                       batch_id=batch_id, quantity=in_quantity).last()

            transaction_type_obj = PutawayCommonFunctions.get_filtered_putaways(warehouse=in_obj.warehouse,
                                                                                putaway_type=in_obj.in_type,
                                                                                putaway_type_id=in_obj.id,
                                                                                sku=in_obj.sku,
                                                                                batch_id=in_obj.batch_id,
                                                                                quantity=in_obj.quantity)
            transaction_type = 'stock_correction_in_type'
        else:
            # add into in out quantity
            transaction_type_obj = Out.objects.filter(batch_id=batch_id, warehouse=Shop.objects.get(
                id=data[0]), quantity=out_quantity)
            transaction_type = 'stock_correction_out_type'

        return transaction_type_obj, transaction_type


def iterate_quantity_type(data):
    """

    :param data:
    :return:
    """
    inventory_type = {}
    if int(data[5]) >= 0:
        inventory_type.update({'normal': int(data[5])})
    if int(data[6]) >= 0:
        inventory_type.update({'damaged': int(data[6])})
    if int(data[7]) >= 0:
        inventory_type.update({'expired': int(data[7])})
    if int(data[8]) >= 0:
        inventory_type.update({'missing': int(data[8])})
    return inventory_type


def warehouse_inventory_change_data(upload_data, stock_movement_obj):
    """

        :param upload_data: Collection of csv data
        :param stock_movement_obj: object of CSV file
        :return: result
    """
    try:
        with transaction.atomic():
            for data in upload_data:
                # condition to get the queryset for warehouse queryset
                initial_inventory_object = WareHouseCommonFunction.filter_warehouse_inventory(data[0], data[1], data[2],
                                                                                              data[4])
                # get the initial quantity of warehouse
                initial_quantity = initial_inventory_object[0].quantity

                # get the quantity from initial to updated quantity which comes from csv
                quantity = initial_quantity - int(data[5])

                # update the quantity of initial warehouse
                WareHouseCommonFunction.update_or_create_warehouse_inventory(
                    data[0], data[1], data[2], data[4], quantity, True)

                # condition to get the queryset for new warehouse id
                final_inventory_object = WareHouseCommonFunction.filter_warehouse_inventory(data[0], data[1], data[3],
                                                                                            data[4])
                if not final_inventory_object:
                    final_quantity = int(data[5])
                else:
                    final_quantity = final_inventory_object[0].quantity + int(data[5])

                # update the quantity of new warehouse id
                WareHouseCommonFunction.update_or_create_warehouse_inventory(
                    Shop.objects.get(id=data[0]), Product.objects.get(product_sku=data[1]), data[3], data[4],
                    final_quantity, True)

                # Create data in Internal Warehouse change Model
                transaction_type = 'war_house_adjustment'
                try:
                    transaction_id = 'war_' + data[0] + data[1][14:] + data[2][0:5] + data[3][0:4] + data[4][0:4] + \
                                     data[5]
                except Exception as e:
                    error_logger.error(e)
                    transaction_id = 'war_tran_' + '00001'
                InternalWarehouseChange.create_warehouse_inventory_change(Shop.objects.get(id=data[0]).id,
                                                                          Product.objects.get(product_sku=data[1]),
                                                                          transaction_type,
                                                                          transaction_id,
                                                                          InventoryState.objects.get(
                                                                              inventory_state=data[2]),
                                                                          InventoryState.objects.get(
                                                                              inventory_state=data[3]),
                                                                          InventoryType.objects.get(
                                                                              inventory_type=data[4]),
                                                                          int(data[5]), stock_movement_obj[0])
            return
    except Exception as e:
        error_logger.error(e)


def release_blocking_with_cron():
    """

    :return:
    """
    current_time = datetime.now() - timedelta(minutes=8)
    order_reserve_release = OrderReserveRelease.objects.filter(warehouse_internal_inventory_release_id=None,
                                                               created_at__lt=current_time)
    sku_id = [p.sku.id for p in order_reserve_release]
    for order_product in order_reserve_release:
        transaction_id = order_product.transaction_id
        shop_id = order_product.warehouse.id
        transaction_type = 'released'
        order_status = 'available'
        release_type = 'cron'
        common_release_for_inventory(sku_id, shop_id, transaction_type, transaction_id, order_status, order_product,
                                     release_type)


def pickup_entry_exists_for_order(order_id):
    pd_obj = PickerDashboard.objects.filter(order_id=order_id)
    if pd_obj.exists():
        return True
    return False


def pickup_entry_creation_with_cron():
    cron_logger.info("pickup_entry_creation_with_cron started")
    current_time = datetime.now() - timedelta(minutes=1)
    start_time = datetime.now() - timedelta(days=30)
    order_obj = Order.objects.filter(order_status='ordered',
                                     order_closed=False,
                                     created_at__lt=current_time,
                                     created_at__gt=start_time)
    type_normal = InventoryType.objects.filter(inventory_type="normal").last()
    data_list = []
    with transaction.atomic():
        if order_obj.exists():
            for order in order_obj:
                pincode = "00"
                if pickup_entry_exists_for_order(order.id):
                    cron_logger.info('pickup extry exists for order {}'.format(order.id))
                    continue
                PickerDashboard.objects.create(
                    order=order,
                    picking_status="picking_pending",
                    picklist_id=generate_picklist_id(pincode),
                )
                order_obj.update(order_status='PICKUP_CREATED')
                cron_logger.info('picker dashboard entry created for order {}, order status updated to {}'
                                 .format(order.id, order.PICKUP_CREATED))
                shop = Shop.objects.filter(id=order.seller_shop.id).last()
                for order_product in order.ordered_cart.rt_cart_list.all():
                    CommonPickupFunctions.create_pickup_entry(shop, 'Order', order.order_no, order_product.cart_product,
                                                              order_product.no_of_pieces,
                                                              'pickup_creation')
                    cron_logger.info('pickup entry created for order {}, order_product {}'
                                     .format(order.id, order_product.cart_product))
                pu = Pickup.objects.filter(pickup_type_id=order.order_no)

                for obj in pu:
                    bin_inv_dict = {}
                    pickup_obj = obj
                    qty = obj.quantity
                    bin_lists = obj.sku.rt_product_sku.filter(quantity__gt=0,
                                                              inventory_type__inventory_type='normal').order_by(
                        '-batch_id',
                        'quantity')
                    if bin_lists.exists():
                        for k in bin_lists:
                            if len(k.batch_id) == 23:
                                bin_inv_dict[k] = str(datetime.strptime(
                                    k.batch_id[17:19] + '-' + k.batch_id[19:21] + '-' + '20' + k.batch_id[21:23],
                                    "%d-%m-%Y"))
                            else:
                                bin_inv_dict[k] = str(
                                    datetime.strptime('30-' + k.batch_id[17:19] + '-20' + k.batch_id[19:21],
                                                      "%d-%m-%Y"))
                    else:
                        bin_lists = obj.sku.rt_product_sku.filter(quantity=0,
                                                                  inventory_type__inventory_type='normal').order_by(
                            '-batch_id',
                            'quantity').last()
                        if len(bin_lists.batch_id) == 23:
                            bin_inv_dict[bin_lists] = str(datetime.strptime(
                                    bin_lists.batch_id[17:19] + '-' + bin_lists.batch_id[19:21] + '-' + '20' + bin_lists.batch_id[21:23],
                                    "%d-%m-%Y"))
                        else:
                            bin_inv_dict[bin_lists] = str(
                                datetime.strptime('30-' + bin_lists.batch_id[17:19] + '-20' + bin_lists.batch_id[19:21],
                                                  "%d-%m-%Y"))

                    bin_inv_list = list(bin_inv_dict.items())
                    bin_inv_dict = dict(sorted(dict(bin_inv_list).items(), key=lambda x: x[1]))
                    product = obj.sku.product_name
                    sku = obj.sku.product_sku
                    mrp = obj.sku.rt_cart_product_mapping.all().last().cart_product_price.mrp if obj.sku.rt_cart_product_mapping.all().last().cart_product_price else None
                    for bin_inv in bin_inv_dict.keys():
                        if qty == 0:
                            break
                        already_picked = 0
                        batch_id = bin_inv.batch_id if bin_inv else None
                        qty_in_bin = bin_inv.quantity if bin_inv else 0
                        shops = bin_inv.warehouse
                        bin_id = bin_inv.bin.bin_id if bin_inv else None
                        if qty - already_picked <= qty_in_bin:
                            already_picked += qty
                            remaining_qty = qty_in_bin - already_picked
                            bin_inv.quantity = remaining_qty
                            bin_inv.save()
                            qty = 0
                            prod_list = {"product": product, "sku": sku, "mrp": mrp, "qty": already_picked,
                                         "batch_id": batch_id, "bin": bin_id}
                            data_list.append(prod_list)
                            CommonPickBinInvFunction.create_pick_bin_inventory(shops, pickup_obj, batch_id, bin_inv,
                                                                               quantity=already_picked,
                                                                               bin_quantity=qty_in_bin,
                                                                               pickup_quantity=None)
                            InternalInventoryChange.create_bin_internal_inventory_change(shops, obj.sku, batch_id,
                                                                                         bin_inv.bin,
                                                                                         type_normal, type_normal,
                                                                                         "pickup_created",
                                                                                         pickup_obj.pk,
                                                                                         already_picked)
                        else:
                            already_picked = qty_in_bin
                            remaining_qty = qty - already_picked
                            bin_inv.quantity = qty_in_bin - already_picked
                            bin_inv.save()
                            qty = remaining_qty
                            prod_list = {"product": product, "sku": sku, "mrp": mrp, "qty": already_picked,
                                         "batch_id": batch_id, "bin": bin_id}
                            data_list.append(prod_list)
                            CommonPickBinInvFunction.create_pick_bin_inventory(shops, pickup_obj, batch_id, bin_inv,
                                                                               quantity=already_picked,
                                                                               bin_quantity=qty_in_bin,
                                                                               pickup_quantity=None)
                            InternalInventoryChange.create_bin_internal_inventory_change(shops, obj.sku, batch_id,
                                                                                         bin_inv.bin,
                                                                                         type_normal, type_normal,
                                                                                         "pickup_created",
                                                                                         pickup_obj.pk,
                                                                                         already_picked)

                    cron_logger.info('pickup bin inventory created for order {}, sku {}, '.format(order.id, obj.sku))


class DownloadBinCSV(View):
    """
    This class is used to download the sample file for Bin CSV
    """

    def get(self, request, *args, **kwargs):
        """

        :param request: GET request
        :param args: non keyword argument
        :param kwargs: keyword argument
        :return: csv file
        """
        try:
            filename = 'sample_bin' + ".csv"
            f = StringIO()
            writer = csv.writer(f)
            # header of csv file
            writer.writerow(['Warehouse Name', 'Warehouse ID', 'BIN Type ', 'Bin ID'])
            writer.writerow(['GFDN Noida', '600', 'PA', 'B2BZ01SR001-0001'])
            f.seek(0)
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            return response
        except Exception as e:
            error_logger.error(e.message)


def audit_download(request):
    """

    :param request: POST request
    :return: CSV file for audit
    """
    if request.method == 'POST':
        info_logger.info("POST request while upload the .csv file for Audit file download.")
        form = DownloadAuditAdminForm(request.POST, request.FILES)
        if form.is_valid():
            info_logger.info("File format validation has been successfully done.")
            upload_data = form.cleaned_data['file']
            # define the file name
            filename = 'audit_download' + ".csv"
            f = StringIO()
            writer = csv.writer(f)
            # define the header name in csv
            writer.writerow(['Warehouse', 'SKU Name - ID', 'MRP', 'Expiry Date',
                             'Bin ID', 'Normal-Initial Qty', 'Damaged-Initial Qty', 'Expired-Initial Qty',
                             'Missing-Initial Qty', 'Normal-Final Qty', 'Damaged-Final Qty', 'Expired-Final Qty',
                             'Missing-Final Qty'])

            # fetch the inventory type in Inventory Type Model
            inventory_type_normal = InventoryType.objects.filter(inventory_type='normal')
            inventory_type_expired = InventoryType.objects.filter(inventory_type='expired')
            inventory_type_damaged = InventoryType.objects.filter(inventory_type='damaged')
            inventory_type_missing = InventoryType.objects.filter(inventory_type='missing')

            # list to store data from csv
            data_list = []
            for data in upload_data:
                # get product instance
                product = Product.objects.filter(product_sku=data[0])
                try:
                    product_price = ProductPrice.objects.filter(product=product[0])[0].mrp
                except:
                    product_price = ''
                # filter query for Bin Inventory model to get all Bin id which consists same warehouse and sku
                bin_inventory_obj = BinInventory.objects.filter(warehouse=request.POST['warehouse'],
                                                                sku=Product.objects.filter(product_sku=data[0])[0])
                # for loop for every bin inventory object
                for bin_inventory in bin_inventory_obj:
                    # condition to get those object which type is normal
                    bin_obj_normal = BinInventory.objects.filter(warehouse=request.POST['warehouse'],
                                                                 sku=Product.objects.filter(product_sku=data[0])[0],
                                                                 bin=bin_inventory.bin,
                                                                 inventory_type=inventory_type_normal[0],
                                                                 batch_id=bin_inventory.batch_id).last()

                    try:
                        if bin_obj_normal:
                            bin_normal_quantity = bin_obj_normal.quantity
                        else:
                            bin_normal_quantity = 0
                    except:
                        bin_normal_quantity = 0

                    # condition to get those object which type is damaged
                    bin_obj_damaged = BinInventory.objects.filter(warehouse=request.POST['warehouse'],
                                                                  sku=Product.objects.filter(product_sku=data[0])[0],
                                                                  bin=bin_inventory.bin,
                                                                  inventory_type=inventory_type_damaged[0],
                                                                  batch_id=bin_inventory.batch_id
                                                                  ).last()

                    try:
                        if bin_obj_damaged:
                            bin_damaged_quantity = bin_obj_damaged.quantity
                        else:
                            bin_damaged_quantity = 0
                    except:
                        bin_damaged_quantity = 0

                    # condition to get those object which type is expired
                    bin_obj_expired = BinInventory.objects.filter(warehouse=request.POST['warehouse'],
                                                                  sku=Product.objects.filter(product_sku=data[0])[0],
                                                                  bin=bin_inventory.bin,
                                                                  inventory_type=inventory_type_expired[0],
                                                                  batch_id=bin_inventory.batch_id
                                                                  ).last()
                    try:
                        if bin_obj_expired:
                            bin_expired_quantity = bin_obj_expired.quantity
                        else:
                            bin_expired_quantity = 0
                    except:
                        bin_expired_quantity = 0

                    # condition to get those object which type is missing
                    bin_obj_missing = BinInventory.objects.filter(warehouse=request.POST['warehouse'],
                                                                  sku=Product.objects.filter(product_sku=data[0])[0],
                                                                  bin=bin_inventory.bin,
                                                                  inventory_type=inventory_type_missing[0],
                                                                  batch_id=bin_inventory.batch_id
                                                                  ).last()
                    try:
                        if bin_obj_missing:
                            bin_missing_quantity = bin_obj_missing.quantity
                        else:
                            bin_missing_quantity = 0
                    except:
                        bin_missing_quantity = 0

                    # get expired date for individual bin and sku
                    expiry_date = set_expiry_date(bin_inventory.batch_id)
                    # append data in a list
                    data_list.append([bin_inventory.warehouse_id,
                                      bin_inventory.sku.product_name + '-' + bin_inventory.sku.product_sku,
                                      product_price,
                                      expiry_date, bin_inventory.bin.bin_id, bin_normal_quantity, bin_damaged_quantity,
                                      bin_expired_quantity,
                                      bin_missing_quantity, 0, 0, 0, 0])
            # sort the list
            data_list.sort()

            # group by and remove duplicate data
            sort_data = list(num for num, _ in itertools.groupby(data_list))
            for row_id, data in enumerate(sort_data):
                # check the length of list
                if len(sort_data) == 1:
                    # if length of list is 1 and sum of Initial and Final Quantity is zero
                    if (int(data[5]) + int(data[6]) + int(data[7]) + int(data[8])) == 0:
                        # return the error message
                        return render(request, 'admin/wms/audit-download.html',
                                      {'form': form, 'error': 'Row' + ' ' + str(row_id + 1) + ': ' +
                                                              'Uploaded SKU does not have quantity,'
                                                              'Please check the quantity in Bin Inventory.'})
                    else:
                        # write the data in csv file
                        writer.writerow([data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7],
                                         data[8], data[9], data[10], data[11], data[12]])
                else:
                    if (int(data[5]) + int(data[6]) + int(data[7]) + int(data[8])) == 0:
                        pass
                    else:
                        # write the data in csv file
                        writer.writerow([data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7],
                                         data[8], data[9], data[10], data[11], data[12]])
            f.seek(0)
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            return response
        else:
            return render(request, 'admin/wms/audit-download.html', {'form': form})
    else:
        form = DownloadAuditAdminForm()
    return render(request, 'admin/wms/audit-download.html', {'form': form})


def audit_upload(request):
    """

    :param request: POST request
    :return: Upload form
    """
    if request.method == 'POST':
        info_logger.info("POST request while upload the .xls file for Audit.")
        form = UploadAuditAdminForm(request.POST, request.FILES)
        if form.is_valid():
            info_logger.info("File format validation has been successfully done.")
            upload_data = form.cleaned_data['file']

            # iteration for csv data
            # with transaction.atomic():
            audit_inventory_obj = AuditInventory.create_audit_entry(request.user, request.FILES['file'])
            for row_id, data in enumerate(upload_data):
                # Check SKU and Expiry data is exist or not
                sku = data[1][-17:]
                expiry_date = data[3]
                # create batch id
                batch_id = create_batch_id(sku, expiry_date)
                bin_exp_obj = BinInventory.objects.filter(warehouse=data[0],
                                                          bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                                          sku=Product.objects.filter(
                                                              product_sku=data[1][-17:]).last(),
                                                          batch_id=batch_id)
                # call function to create audit data in Audit Model
                if bin_exp_obj.exists():
                    # create batch id for SKU and save data in In and Put Away Model
                    bin_inventory_obj = BinInventory.objects.filter(warehouse=data[0],
                                                                    bin=Bin.objects.filter(bin_id=data[4],
                                                                                           warehouse=data[0]).last(),
                                                                    sku=Product.objects.filter(
                                                                        product_sku=data[1][-17:]).last())
                    if not bin_inventory_obj.exists():
                        sku = data[1][-17:]
                        expiry_date = data[3]
                        # create batch id
                        batch_id = create_batch_id(sku, expiry_date)
                        bin_objects_create(data, batch_id)

                        bin_inventory_obj = BinInventory.objects.filter(warehouse=data[0],
                                                                        bin=Bin.objects.filter(bin_id=data[4],
                                                                                               warehouse=data[0]
                                                                                               ).last(),
                                                                        sku=Product.objects.filter(
                                                                            product_sku=data[1][-17:]).last(),
                                                                        batch_id=batch_id)

                else:
                    sku = data[1][-17:]
                    expiry_date = data[3]
                    # create batch id
                    batch_id = create_batch_id(sku, expiry_date)
                    quantity = int(data[9]) + int(data[10]) + int(data[11]) + int(data[12])
                    InCommonFunctions.create_in(Shop.objects.filter(id=data[0])[0], 'Audit Adjustment',
                                                audit_inventory_obj[0].id,
                                                Product.objects.filter(product_sku=data[1][-17:]).last(),
                                                batch_id, int(quantity), int(quantity))
                    # create bin inventory data
                    bin_objects_create(data, batch_id)

                    bin_inventory_obj = BinInventory.objects.filter(warehouse=data[0],
                                                                    bin=Bin.objects.filter(bin_id=data[4],
                                                                                           warehouse=data[0]
                                                                                           ).last(),
                                                                    sku=Product.objects.filter(
                                                                        product_sku=data[1][-17:]).last(),
                                                                    batch_id=batch_id)

                # call function to get inventory types from Bin Inventory
                inventory_type = get_inventory_types_for_bin(data, bin_inventory_obj)
                for key, value in inventory_type.items():
                    # call function to create data in different models like:- Bin Inventory, Warehouse Inventory and
                    # Warehouse Internal Inventory Model
                    AuditInventory.audit_exist_batch_id(data, key, value, audit_inventory_obj, batch_id)
                # pickup_entry_creation_with_cron
            return render(request, 'admin/wms/audit-upload.html', {'form': form,
                                                                   'success': 'Audit CSV uploaded successfully !',
                                                                   })

        else:
            return render(request, 'admin/wms/audit-upload.html', {'form': form})
    else:
        form = UploadAuditAdminForm()
    return render(request, 'admin/wms/audit-upload.html', {'form': form})


def get_inventory_types_for_bin(data, bin_inventory_obj):
    """

    :param data: single row of data from csv
    :param bin_inventory_obj: bin inventory object
    :return: list of inventory types
    """
    try:
        inventory_type = {}
        for bin_inventory in bin_inventory_obj:
            if bin_inventory.inventory_type.inventory_type == 'normal':
                normal = int(data[9])
                inventory_type.update({'normal': normal})
            else:
                if int(data[9]) > 0:
                    normal = int(data[9])
                    inventory_type.update({'normal': normal})

            if bin_inventory.inventory_type.inventory_type == 'damaged':
                damaged = int(data[10])
                inventory_type.update({'damaged': damaged})
            else:
                if int(data[10]) > 0:
                    damaged = int(data[10])
                    inventory_type.update({'damaged': damaged})

            if bin_inventory.inventory_type.inventory_type == 'expired':
                expired = int(data[11])
                inventory_type.update({'expired': expired})

            else:
                if int(data[11]) > 0:
                    expired = int(data[11])
                    inventory_type.update({'expired': expired})

            if bin_inventory.inventory_type.inventory_type == 'missing':
                missing = int(data[12])
                inventory_type.update({'missing': missing})
            else:
                if int(data[12]) > 0:
                    missing = int(data[12])
                    inventory_type.update({'missing': missing})
        return inventory_type
    except Exception as e:
        error_logger.error(e.message)


def bin_objects_create(data, batch_id):
    """

    :param data: single row of data from csv
    :param batch_id: batch id
    :return: None
    """
    if int(data[9]) > 0:
        bin_inventory_obj = BinInventory.objects.filter(warehouse=data[0],
                                                        bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                                        sku=Product.objects.filter(
                                                            product_sku=data[1][-17:]).last(),
                                                        batch_id=batch_id, in_stock=True,
                                                        inventory_type=InventoryType.objects.filter(
                                                            inventory_type='normal').last())
        if bin_inventory_obj.exists():
            bin_inventory_obj.update(quantity=int(data[9]))
        else:
            BinInventory.objects.get_or_create(warehouse=Shop.objects.filter(id=data[0])[0],
                                               bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                               batch_id=batch_id,
                                               sku=Product.objects.filter(
                                                   product_sku=data[1][-17:]).last(),
                                               in_stock=True, quantity=int(data[9]),
                                               inventory_type=InventoryType.objects.filter(
                                                   inventory_type='normal').last())
    if int(data[10]) > 0:
        bin_inventory_obj = BinInventory.objects.filter(warehouse=data[0],
                                                        bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                                        sku=Product.objects.filter(
                                                            product_sku=data[1][-17:]).last(),
                                                        batch_id=batch_id, in_stock=True,
                                                        inventory_type=InventoryType.objects.filter(
                                                            inventory_type='damaged').last())
        if bin_inventory_obj.exists():
            bin_inventory_obj.update(quantity=int(data[10]))
        else:
            BinInventory.objects.get_or_create(
                warehouse=Shop.objects.filter(id=data[0])[0],
                bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                batch_id=batch_id,
                sku=Product.objects.filter(
                    product_sku=data[1][-17:]).last(),
                in_stock=True, quantity=int(data[10]),
                inventory_type=InventoryType.objects.filter(inventory_type='damaged').last())
    if int(data[11]) > 0:
        bin_inventory_obj = BinInventory.objects.filter(warehouse=data[0],
                                                        bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                                        sku=Product.objects.filter(
                                                            product_sku=data[1][-17:]).last(),
                                                        batch_id=batch_id, in_stock=True,
                                                        inventory_type=InventoryType.objects.filter(
                                                            inventory_type='expired').last())
        if bin_inventory_obj.exists():
            bin_inventory_obj.update(quantity=int(data[11]))
        else:
            BinInventory.objects.get_or_create(
                warehouse=Shop.objects.filter(id=data[0])[0],
                bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                batch_id=batch_id,
                sku=Product.objects.filter(
                    product_sku=data[1][-17:]).last(),
                in_stock=True, quantity=int(data[11]),
                inventory_type=InventoryType.objects.filter(inventory_type='expired').last())
    if int(data[12]) > 0:
        bin_inventory_obj = BinInventory.objects.filter(warehouse=data[0],
                                                        bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                                                        sku=Product.objects.filter(
                                                            product_sku=data[1][-17:]).last(),
                                                        batch_id=batch_id, in_stock=True,
                                                        inventory_type=InventoryType.objects.filter(
                                                            inventory_type='missing').last())
        if bin_inventory_obj.exists():
            bin_inventory_obj.update(quantity=int(data[12]))
        else:
            BinInventory.objects.get_or_create(
                warehouse=Shop.objects.filter(id=data[0])[0],
                bin=Bin.objects.filter(bin_id=data[4], warehouse=data[0]).last(),
                batch_id=batch_id,
                sku=Product.objects.filter(
                    product_sku=data[1][-17:]).last(),
                in_stock=True, quantity=int(data[12]),
                inventory_type=InventoryType.objects.filter(inventory_type='missing').last())


def shipment_out_inventory_change(shipment_list, final_status):
    status = OrderedProduct.SHIPMENT_STATUS
    for shipment in shipment_list:
        if shipment.shipment_status == 'READY_TO_SHIP' and final_status == 'OUT_FOR_DELIVERY':
            type_normal = InventoryType.objects.filter(inventory_type="normal").last()
            state_picked = InventoryState.objects.filter(inventory_state="picked").last()
            state_shipped = InventoryState.objects.filter(inventory_state="shipped").last()
            shipment_item_list = OrderedProductMapping.objects.filter(ordered_product=shipment).all()
            with transaction.atomic():
                for shipment_item in shipment_item_list:
                    CommonWarehouseInventoryFunctions.create_warehouse_inventory(shipment.order.seller_shop,
                                                                                 shipment_item.product,
                                                                                 "normal", "picked",
                                                                                 shipment_item.shipped_qty * -1,
                                                                                 True)
                    CommonWarehouseInventoryFunctions.create_warehouse_inventory(shipment.order.seller_shop,
                                                                                 shipment_item.product,
                                                                                 "normal", "shipped",
                                                                                 shipment_item.shipped_qty,
                                                                                 True)

                    InternalWarehouseChange.create_warehouse_inventory_change(shipment.order.seller_shop,
                                                                              shipment_item.product, "shipped_out",
                                                                              shipment.pk, type_normal, state_picked,
                                                                              type_normal, state_shipped,
                                                                              shipment_item.shipped_qty, None)
                    shipment_batch_list = OrderedProductBatch.objects.filter(
                        ordered_product_mapping=shipment_item).all()
                    for shipment_batch in shipment_batch_list:
                        OutCommonFunctions.create_out(shipment.order.seller_shop, 'ship_out',
                                                      shipment.pk, shipment_item.product, shipment_batch.batch_id,
                                                      shipment_batch.quantity)


        else:
            pass


def archive_inventory_cron():
    info_logger.info("WMS : Archiving warehouse inventory data started at {}".format(datetime.now()))
    today = datetime.today()
    archive_entry = InventoryArchiveMaster.objects.create(archive_date=today,
                                                          inventory_type=InventoryArchiveMaster.ARCHIVE_INVENTORY_CHOICES.WAREHOUSE)
    warehouse_inventory_list = WarehouseInventory.objects.all()

    # info_logger.info("WMS : Archiving warehouse inventory : total items {}".format(warehouse_inventory_list.count()))
    for inventory in warehouse_inventory_list:
        historic_entry = WarehouseInventoryHistoric(archive_entry=archive_entry,
                                                    warehouse=inventory.warehouse,
                                                    sku=inventory.sku,
                                                    inventory_type=inventory.inventory_type,
                                                    inventory_state=inventory.inventory_state,
                                                    quantity=inventory.quantity,
                                                    in_stock=inventory.in_stock,
                                                    created_at=inventory.created_at,
                                                    modified_at=inventory.modified_at)
        historic_entry.save()
    info_logger.info("WMS : Archiving bin inventory data started at {}".format(datetime.now()))
    archive_entry = InventoryArchiveMaster.objects.create(archive_date=today,
                                                          inventory_type=InventoryArchiveMaster.ARCHIVE_INVENTORY_CHOICES.BIN)
    bin_inventory_list = BinInventory.objects.all()
    # info_logger.info("WMS : Archiving bin inventory : total items {}".format(bin_inventory_list.count()))
    for inventory in bin_inventory_list:
        historic_entry = BinInventoryHistoric(archive_entry=archive_entry,
                                              warehouse=inventory.warehouse,
                                              sku=inventory.sku,
                                              bin=inventory.bin,
                                              batch_id=inventory.batch_id,
                                              inventory_type=inventory.inventory_type,
                                              quantity=inventory.quantity,
                                              in_stock=inventory.in_stock,
                                              created_at=inventory.created_at,
                                              modified_at=inventory.modified_at)
        historic_entry.save()

    info_logger.info("WMS : Archiving inventory data ended at {}".format(datetime.now()))


def bulk_putaway(self, request, argument_list):
    with transaction.atomic():
        for obj in argument_list:
            try:
                if obj.bin.bin.bin_id is None:
                    message = "You can't Perform this action, Bin Id is None."
                    return message, False
            except:
                message = "You can't Perform this action, Bin Id is None."
                return message, False
            if obj.bin.bin.bin_id == 'V2VZ01SR001-0001':
                message = "You can't assign this BIN ID, This is a Virtual Bin ID."
                return message, False
            else:
                bin_in_obj = BinInventory.objects.filter(warehouse=obj.warehouse,
                                                         sku=Product.objects.filter(
                                                             product_sku=obj.sku_id).last())
                for bin_in in bin_in_obj:
                    if not (bin_in.batch_id == obj.batch_id):
                        if bin_in.bin.bin_id == obj.bin.bin.bin_id:
                            if bin_in.quantity == 0:
                                pass
                            else:
                                message = "You can't perform this action, Non zero qty of more than one Batch ID of a" \
                                          " single SKU can’t be saved in the same Bin ID."
                                return message, False
                bin_id = obj.bin
                if obj.putaway_type == 'Order_Cancelled':
                    ordered_inventory_state = 'ordered',
                    initial_stage = InventoryState.objects.filter(inventory_state='ordered').last(),
                    cancel_ordered(request.user, obj, ordered_inventory_state, initial_stage, bin_id)

                elif obj.putaway_type == 'Pickup_Cancelled':
                    ordered_inventory_state = 'picked',
                    initial_stage = InventoryState.objects.filter(inventory_state='picked').last(),
                    cancel_ordered(request.user, obj, ordered_inventory_state, initial_stage, bin_id)

                elif obj.putaway_type == 'Shipment_Cancelled':
                    ordered_inventory_state = 'picked',
                    initial_stage = InventoryState.objects.filter(inventory_state='picked').last(),
                    cancel_ordered(self.request.user, obj, ordered_inventory_state, initial_stage, bin_id)

                elif obj.putaway_type == 'PAR_SHIPMENT':
                    ordered_inventory_state = 'picked',
                    initial_stage = InventoryState.objects.filter(inventory_state='picked').last(),
                    shipment_obj = OrderedProduct.objects.filter(
                        order__order_no=obj.putaway.putaway_type_id)[
                        0].rt_order_product_order_product_mapping.all()
                    cancel_shipment(request.user, obj, ordered_inventory_state, initial_stage, shipment_obj, bin_id)

                elif obj.putaway_type == 'RETURNED':
                    ordered_inventory_state = 'shipped',
                    initial_stage = InventoryState.objects.filter(inventory_state='shipped').last(),
                    shipment_obj = OrderedProduct.objects.filter(
                        invoice__invoice_no=obj.putaway.putaway_type_id)[
                        0].rt_order_product_order_product_mapping.all()
                    cancel_returned(request.user, obj, ordered_inventory_state, initial_stage, shipment_obj, bin_id)

        message = "Bulk Approval for Put Away has been done successfully."
        return message, True


def shipment_reschedule_inventory_change(shipment_list):
    for shipment in shipment_list:
        type_normal = InventoryType.objects.filter(inventory_type="normal").last()
        state_picked = InventoryState.objects.filter(inventory_state="picked").last()
        state_shipped = InventoryState.objects.filter(inventory_state="shipped").last()
        shipment_item_list = OrderedProductMapping.objects.filter(ordered_product=shipment).all()
        with transaction.atomic():
            try:
                for shipment_item in shipment_item_list:
                    shipment_batch_list = OrderedProductBatch.objects.filter(ordered_product_mapping=shipment_item).all()
                    for shipment_batch in shipment_batch_list:
                        InCommonFunctions.create_only_in(shipment.order.seller_shop, 'reschedule', shipment.pk,
                                                     shipment_item.product, shipment_batch.batch_id,shipment_batch.quantity)
                    CommonWarehouseInventoryFunctions.create_warehouse_inventory(shipment.order.seller_shop,
                                                                                 shipment_item.product,
                                                                                 "normal", "shipped",
                                                                                 shipment_item.shipped_qty * -1,
                                                                                 True)
                    CommonWarehouseInventoryFunctions.create_warehouse_inventory(shipment.order.seller_shop,
                                                                                 shipment_item.product,
                                                                                 "normal", "picked",
                                                                                 shipment_item.shipped_qty,
                                                                                 True)

                    InternalWarehouseChange.create_warehouse_inventory_change(shipment.order.seller_shop,
                                                                              shipment_item.product, "reschedule",
                                                                              shipment.pk, type_normal, state_shipped,
                                                                              type_normal, state_picked,
                                                                              shipment_item.shipped_qty, None)

            except DatabaseError as e:
                print(e)


def populate_expiry_date(request):
    """
    One time activity
    This function populates the expiry_date in IN table.
    Expiry date is calculated based on the batch Id.
    """
    for i in In.objects.all():
        i.expiry_date = get_expiry_date_db(i.batch_id)
        i.save()


class InventoryMovement(object):
    """
    Get all the batch ids expiring on a given date
    Date format to be YYYY-MM-DD
    """
    @classmethod
    def get_inventory_expiring_by_date(cls, date):
        expiring_batch_id_list = In.objects.filter(expiry_date__lt=date).values_list('batch_id', flat=True)
        cron_logger.info('InventoryMovement|get_inventory_expiring_by_date| {} batches expiring on {}'
                         .format(expiring_batch_id_list.count(), date))
        return expiring_batch_id_list

    """
    Get all the Bin inventories to move by batch id list
    batch_ids : list of batch ids
    inventory_type : inventory types to move e.g. normal, damaged etc
    """
    @classmethod
    def get_bin_inventory_to_move(cls, batch_ids, inventory_type):
        bin_inventory = BinInventory.objects.filter(batch_id__in=batch_ids,
                                                    inventory_type=inventory_type,
                                                    quantity__gt=0)
        cron_logger.info('InventoryMovement|get_bin_inventory_to_move| {} bin inventories returned'
                         .format(bin_inventory.count()))
        return bin_inventory

    @classmethod
    def move_bin_inventory(cls, tr_type, tr_id, bin_inventory, inventory_type_to):
        cron_logger.info('InventoryMovement|move_bin_inventory| warehouse {}, bin {}, batch {},'
                          'inventory_type_from {}, inventory_type_to {}, quantity {}'
                          .format(bin_inventory.warehouse, bin_inventory.bin, bin_inventory.batch_id,
                                  bin_inventory.inventory_type, inventory_type_to, bin_inventory.quantity))
        qty = bin_inventory.quantity
        inventory_obj, created = BinInventory.objects.get_or_create(warehouse=bin_inventory.warehouse,
                                                                    bin=bin_inventory.bin,
                                                                    sku=bin_inventory.sku,
                                                                    batch_id=bin_inventory.batch_id,
                                                                    inventory_type=inventory_type_to,
                                                                    defaults={'quantity':bin_inventory.quantity,
                                                                              'in_stock':True})
        bin_inventory.quantity = 0
        bin_inventory.save()
        if not created:
            inventory_obj.quantity = inventory_obj.quantity + qty
            inventory_obj.save()

        BinInternalInventoryChange.objects.create(warehouse_id=bin_inventory.warehouse.id, sku=bin_inventory.sku,
                                                  batch_id=bin_inventory.batch_id,
                                                  initial_bin=bin_inventory.bin,
                                                  final_bin=bin_inventory.bin,
                                                  initial_inventory_type=bin_inventory.inventory_type,
                                                  final_inventory_type=inventory_type_to,
                                                  transaction_type=tr_type,
                                                  transaction_id=tr_id,
                                                  quantity=qty)
        cron_logger.info('InventoryMovement|move_bin_inventory| Inventory movement done.')

    @classmethod
    def move_warehouse_inventory(cls, tr_type, tr_id, warehouse, sku, inventory_state, inventory_type_from,
                                 inventory_type_to, quantity):
        cron_logger.info('InventoryMovement|move_warehouse_inventory| warehouse {}, sku {}, inventory_state{},'
                          'inventory_type_from {}, inventory_type_to {}, quantity {}'
                          .format(warehouse, sku, inventory_state, inventory_type_from, inventory_type_to, quantity))
        warehouse_inventory = WarehouseInventory.objects.filter(warehouse=warehouse,
                                                                sku=sku,
                                                                inventory_state=inventory_state,
                                                                inventory_type=inventory_type_from)
        if warehouse_inventory.count() == 0:
            info_logger.error('InventoryMovement|move_warehouse_inventory| warehouse inventory not found.')
            return False
        if warehouse_inventory.count() > 1:
            info_logger.error('InventoryMovement|move_warehouse_inventory| '
                              'multiple records found in warehouse inventory')
            return False
        warehouse_inventory = warehouse_inventory.last()
        qty_to_move = warehouse_inventory.quantity if quantity > warehouse_inventory.quantity else quantity
        warehouse_inventory_to, created = WarehouseInventory.objects.get_or_create(warehouse=warehouse,
                                                                          sku=sku,
                                                                          inventory_state=inventory_state,
                                                                          inventory_type=inventory_type_to,
                                                                          defaults={'quantity': qty_to_move,
                                                                                    'in_stock':True})
        warehouse_inventory.quantity = warehouse_inventory.quantity-qty_to_move
        warehouse_inventory.save()
        if not created:
            warehouse_inventory_to.quantity = warehouse_inventory_to.quantity + qty_to_move
            warehouse_inventory_to.save()

        WareHouseInternalInventoryChange.create_warehouse_inventory_change(warehouse, sku, tr_type, tr_id,
                                                                           inventory_type_from, inventory_state,
                                                                           inventory_type_to, inventory_state, qty_to_move)

        cron_logger.info('InventoryMovement|move_warehouse_inventory| moved successfully')


def move_expired_inventory_cron():
    today = datetime.today()
    cron_logger.info('move_expired_inventory_cron started at {}'.format(datetime.now()))
    transaction_type = 'expired'
    type_normal = InventoryType.objects.get(inventory_type='normal')
    type_expired = InventoryType.objects.get(inventory_type='expired')
    stage_available = InventoryState.objects.get(inventory_state='available')

    expired_batch_ids = InventoryMovement.get_inventory_expiring_by_date(today)
    bin_inventory_list = InventoryMovement.get_bin_inventory_to_move(expired_batch_ids, type_normal)
    for b in bin_inventory_list:
        try:
            with transaction.atomic():
                quantity_to_move = b.quantity
                product_price = ProductPrice.objects.filter(product=b.sku, approval_status=ProductPrice.APPROVED)
                product_mrp = None
                if product_price.exists():
                    product_mrp = product_price.last().mrp
                ex_inventory = ExpiredInventoryMovement.objects.create(warehouse=b.warehouse, sku=b.sku,
                                                                       batch_id=b.batch_id, bin=b.bin,
                                                                       mrp=product_mrp,
                                                                       inventory_type=b.inventory_type,
                                                                       quantity=quantity_to_move,
                                                                       expiry_date=get_expiry_date_db(b.batch_id))
                InventoryMovement.move_bin_inventory(transaction_type, ex_inventory.id, b, type_expired)
                InventoryMovement.move_warehouse_inventory(transaction_type, ex_inventory.id, b.warehouse, b.sku,
                                                           stage_available, type_normal, type_expired, quantity_to_move)
                commit_updates_to_es(b.warehouse, b.sku)
        except Exception as e:
            cron_logger.error(e)
            cron_logger.error('move_expired_inventory_cron|Exception while moving expired inventory for bin {} batch {}'
                              .format(b.bin, b.batch_id))
    cron_logger.info('move_expired_inventory_cron ended at {}'.format(datetime.now()))

def move_expired_inventory_manual(request):
    move_expired_inventory_cron()
    return HttpResponse("Done")


def rectify_batch_ids(request):
    info_logger.info('WMS: rectify_batch_ids started')
    batch_ids_to_correct = get_25_char_batch_ids()
    info_logger.info('WMS: rectify_batch_ids, total batch ids found - {}'.format(len(batch_ids_to_correct)))
    batch_dict = get_correct_batch_ids(batch_ids_to_correct)
    info_logger.info('WMS: rectify_batch_ids, correct batch_ids count - {}'.format(len(batch_dict)))
    for b_25, b_23 in batch_dict.items():
        with transaction.atomic():
            info_logger.info('WMS: rectify_batch_ids, replacing batch_id - {} with {}'.format(b_25, b_23))
            opb_entries_to_update = OrderedProductBatch.objects.select_for_update().filter(batch_id=b_25)
            opb_entries_to_update.update(batch_id=b_23)

            info_logger.info('WMS: rectify_batch_ids, updated OrderedProductBatch')
            in_entries_to_update = In.objects.select_for_update().filter(batch_id=b_25)
            in_entries_to_update.update(batch_id=b_23)
            info_logger.info('WMS: rectify_batch_ids, updated In')

            pa_entries_to_update = Putaway.objects.select_for_update().filter(batch_id=b_25)
            pa_entries_to_update.update(batch_id=b_23)
            info_logger.info('WMS: rectify_batch_ids, updated Putaway')

            pabi_entries_to_update = PutawayBinInventory.objects.select_for_update().filter(batch_id=b_25)
            pabi_entries_to_update.update(batch_id=b_23)
            info_logger.info('WMS: rectify_batch_ids, updated PutawayBinInventory')

    info_logger.info('WMS: rectify_batch_ids ended')
    return HttpResponse("Done")


def get_25_char_batch_ids():
    return OrderedProductBatch.objects.annotate(length=Length('batch_id')).filter(length=25)\
                                      .values_list('batch_id', flat=True)


def get_correct_batch_ids(batch_ids_to_correct):
    batch_dict = {}
    for b in batch_ids_to_correct:
        correct_batch_id = b[:21] + b[23:25]
        batch_dict[b] = correct_batch_id
    return batch_dict