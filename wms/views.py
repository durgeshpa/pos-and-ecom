# python imports
import csv
from io import StringIO
import codecs
import itertools
import openpyxl
import re
import logging

# django imports
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
from sp_to_gram.tasks import update_shop_product_es
from django.db.models.signals import post_save
from django.db.models import Sum
from django.dispatch import receiver
from django.db import transaction
from datetime import datetime
from .common_functions import CommonPickBinInvFunction, common_for_release, CommonPickupFunctions
from .models import Bin, InventoryType, WarehouseInternalInventoryChange, WarehouseInventory, OrderReserveRelease
from .models import Bin, WarehouseInventory, PickupBinInventory
from shops.models import Shop
from retailer_to_sp.models import Cart, Order, generate_picklist_id, PickerDashboard
from products.models import Product, ProductPrice
from gram_to_brand.models import GRNOrderProductMapping

# third party imports
from wkhtmltopdf.views import PDFTemplateResponse
from .forms import BulkBinUpdation, BinForm, StockMovementCsvViewForm, DownloadAuditAdminForm, UploadAuditAdminForm
from .models import Pickup, BinInventory, InventoryState
from .common_functions import InternalInventoryChange, CommonBinInventoryFunctions, PutawayCommonFunctions, \
    InCommonFunctions, WareHouseCommonFunction, InternalWarehouseChange, StockMovementCSV,\
    InternalStockCorrectionChange, get_product_stock, updating_tables_on_putaway, AuditInventory

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
        put_away_new = put_quantity if pu.last().quantity >= put_quantity else put_quantity -(put_quantity - pu.last().quantity)
        updated_putaway=pu.last().putaway_quantity
        if updated_putaway==pu.last().quantity:
            return put_quantity
        pu.update(putaway_quantity=updated_putaway+put_away_new, putaway_user=user)
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
                                              {'error': 'Row' + ' ' + str(row_id+1) + ' ' + 'Duplicate Bin ID,'
                                                                                      ' Please verify at your end.',
                                               'form': form})
                            else:
                                bin_obj, created = Bin.objects.get_or_create(warehouse=warehouse.last(),
                                                                             bin_id=data[3],
                                                                             bin_type=data[2],
                                                                             is_active='t')
                                if not created:
                                    return render(request, 'admin/wms/bulk-bin-updation.html', {
                                        'error': 'Row' + ' ' + str(row_id+1) + ' ' + 'Same Data is already exist in the system.'
                                                                             'Please re-verify at your end.',
                                        'form': form})
                        else:
                            return render(request, 'admin/wms/bulk-bin-updation.html', {
                                'error': 'Row' + ' ' + str(row_id+1) + ' ' + 'WareHouse ID is not exist in the system,'
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
    return render(request, 'admin/wms/putaway.html', {'form':form})


class CreatePickList(APIView):
    permission_classes = (AllowAny,)
    filename = 'picklist.pdf'
    template_name = 'admin/wms/picklist.html'

    def get(self, request, *args, **kwargs):
        order = get_object_or_404(Order, pk=self.kwargs.get('pk'))
        picku_bin_inv = PickupBinInventory.objects.filter(pickup__pickup_type_id=order.order_no)
        data_list=[]
        new_list=[]
        for i in picku_bin_inv:
            product = i.pickup.sku.product_name
            sku = i.pickup.sku.product_sku
            mrp = i.pickup.sku.rt_cart_product_mapping.all().order_by('created_at')[0].cart_product_price.mrp
            qty = i.quantity
            batch_id = i.batch_id
            bin_id = i.bin.bin.bin_id
            prod_list = {"product": product, "sku": sku, "mrp": mrp, "qty": qty, "batch_id": batch_id,"bin": bin_id}
            data_list.append(prod_list)
        data = {"data_list": data_list}

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
                writer.writerow(['1393', 'ORCPCRTOY00000002', 'ORCPCRTOY000000020820', 'B2BZ01SR01-001', 'B2BZ01SR01-002',
                                 'normal', 'damaged', '100'])
            elif request.GET['inventory_movement_type'] == '3':
                filename = 'stock_correction' + ".csv"
                f = StringIO()
                writer = csv.writer(f)
                # header of csv file
                writer.writerow(['Warehouse ID', 'SKU', 'Batch ID', 'Bin ID', 'In/Out', 'Quantity'])
                writer.writerow(['1393', 'ORCPCRTOY00000002', 'ORCPCRTOY000000020820', 'B2BZ01SR01-001', 'In', '100'])

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
                            stock_correction_data(upload_data, stock_movement_obj)
                        else:
                            warehouse_inventory_change_data(upload_data, stock_movement_obj)
                        result = {'message': 'CSV uploaded successfully.'}
                        status = '200'
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
        available_qty = int(int(products_available)/int(product.product_inner_case_size))
    except Exception as e:
        return False
    if not available_qty:
        status = False
    update_shop_product_es.delay(shop.id, product.id, available=available_qty, status=status)


@receiver(post_save, sender=WarehouseInventory)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: commit_updates_to_es(instance.warehouse, instance.sku))


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
                                                                                            Bin.objects.get(bin_id=data[3]),
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
                                                                                          Bin.objects.get(bin_id=data[4]),
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
            for data in upload_data:
                # get the type of stock
                stock_correction_type = 'stock_adjustment'
                try:
                    # create stock correction id
                    stock_correction_id = 'stock_' + data[4] + data[0] + data[3][11:] + data[2][16:]
                except Exception as e:
                    error_logger.error(e)
                    # default correction id
                    stock_correction_id = 'stock_' + '00001'

                # Create data in IN Model
                putaway_quantity = 0
                InCommonFunctions.create_in(Shop.objects.get(id=data[0]), stock_correction_type,
                                           stock_correction_id, Product.objects.get(product_sku=data[1]), data[2],
                                           data[5], putaway_quantity)

                # Create date in BinInventory, Put Away BinInventory and WarehouseInventory
                inventory_type = 'normal'
                inventory_state = 'available'
                in_stock = 't'
                put_away_obj = PutawayCommonFunctions.get_filtered_putaways(batch_id=data[2],
                                                                            warehouse=Shop.objects.get(id=data[0]))
                updating_tables_on_putaway(Shop.objects.get(id=data[0]), data[3], put_away_obj, data[2], inventory_type,
                                           inventory_state, in_stock, data[5])

                # Create data in Stock Correction change Model
                InternalStockCorrectionChange.create_stock_inventory_change(Shop.objects.get(id=data[0]),
                                                                            Product.objects.get(product_sku=data[1]),
                                                                            data[2], Bin.objects.get(bin_id=data[3]),
                                                                            data[4], data[5], stock_movement_obj[0])
            return
    except Exception as e:
        error_logger.error(e)


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
                    transaction_id = 'war_' + data[0] + data[1][14:] + data[2][0:5] + data[3][0:4] + data[4][0:4] + data[5]
                except Exception as e:
                    error_logger.error(e)
                    transaction_id = 'war_tran_' + '00001'
                InternalWarehouseChange.create_warehouse_inventory_change(Shop.objects.get(id=data[0]).id,
                                                                          Product.objects.get(product_sku=data[1]),
                                                                          transaction_type,
                                                                          transaction_id,
                                                                          InventoryState.objects.get(inventory_state=data[2]),
                                                                          InventoryState.objects.get(inventory_state=data[3]),
                                                                          InventoryType.objects.get(inventory_type=data[4]),
                                                                          int(data[5]), stock_movement_obj[0])
            return
    except Exception as e:
        error_logger.error(e)


def release_blocking_with_cron():
    cart = Cart.objects.filter(cart_status='active')
    for i in cart:
        item_details = WarehouseInternalInventoryChange.objects.filter(transaction_id=i.order_id, transaction_type='reserved',
                                                                       status=True)
        sku_id = [p.sku.id for p in item_details]
        for k in item_details:
            elapsed_time = datetime.now() - k.created_at
            res_time = divmod(elapsed_time.total_seconds(), 60)[0]
            if int(res_time) == 8:
                transaction_id = k.transaction_id
                shop_id = k.warehouse.id
                transaction_type = 'released'
                order_status = 'available'
                common_for_release(sku_id, shop_id, transaction_type, transaction_id, order_status)


def pickup_entry_creation_with_cron():
    cart = Cart.objects.filter(rt_order_cart_mapping__order_status='ordered')
    data_list=[]
    if cart.exists():
        cart = [cart.last()]
        order_obj = [i.rt_order_cart_mapping for i in cart]
        for i in order_obj:
            try:
                pincode = "00"  # instance.shipping_address.pincode
            except:
                pincode = "00"
            PickerDashboard.objects.create(
                order=i,
                picking_status="picking_pending",
                picklist_id=generate_picklist_id(pincode),
            )
            Order.objects.filter(order_no=i.order_no).update(order_status='PICKUP_CREATED')
            shop = Shop.objects.filter(id=i.seller_shop.id).last()
            order_no = i.order_no
            for j in i.ordered_cart.rt_cart_list.all():
                CommonPickupFunctions.create_pickup_entry(shop, 'Order', order_no, j.cart_product, j.no_of_pieces, 'pickup_creation')
            pu = Pickup.objects.filter(pickup_type_id=order_no)
            for obj in pu:
                bin_inv_dict = {}
                pickup_obj = obj
                qty = obj.quantity
                bin_lists = obj.sku.rt_product_sku.filter(quantity__gt=0).order_by('-batch_id', 'quantity')
                for k in bin_lists:
                    bin_inv_dict[str(datetime.strptime('30-' + k.batch_id[17:19] + '-' + '20' + k.batch_id[19:21], "%d-%m-%Y"))]=k
                bin_inv_dict = list(bin_inv_dict.items())
                bin_inv_dict.sort()
                bin_inv_dict = dict(bin_inv_dict)
                product = obj.sku.product_name
                sku = obj.sku.product_sku
                mrp = obj.sku.rt_cart_product_mapping.all().last().cart_product_price.mrp if obj.sku.rt_cart_product_mapping.all().last().cart_product_price else None
                for i, j in bin_inv_dict.items():
                    if qty == 0:
                        break
                    already_picked=0
                    batch_id = j.batch_id if j else None
                    qty_in_bin = j.quantity if j else 0
                    ids = j.id if j else None
                    shops = j.warehouse
                    bin_id = j.bin.bin_id if j else None
                    if qty - already_picked <= qty_in_bin:
                        already_picked += qty
                        remaining_qty = qty_in_bin - already_picked
                        qty = 0
                        prod_list = {"product": product, "sku": sku, "mrp": mrp, "qty": already_picked, "batch_id": batch_id, "bin": bin_id}
                        print(bin_id)
                        data_list.append(prod_list)
                        CommonPickBinInvFunction.create_pick_bin_inventory(shops, pickup_obj, batch_id, j, quantity=already_picked, pickup_quantity=0)
                    else:
                        already_picked = qty_in_bin
                        remaining_qty = qty - already_picked
                        qty = remaining_qty
                        prod_list = {"product": product, "sku": sku, "mrp": mrp, "qty": already_picked, "batch_id": batch_id,"bin": bin_id}
                        data_list.append(prod_list)
                        CommonPickBinInvFunction.create_pick_bin_inventory(shops, pickup_obj, batch_id,j,quantity=already_picked, pickup_quantity=0)


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
        info_logger.info("POST request while upload the .xls file for Audit file download.")
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
                # get the expire date for particular product
                expiry_date = GRNOrderProductMapping.objects.filter(product=product[0])[0].expiry_date
                # get the product price for particular product
                product_price = ProductPrice.objects.filter(product=product[0])[0].mrp
                # filter query for Bin Inventory model to get all Bin id which consists same warehouse and sku
                bin_inventory_obj = BinInventory.objects.filter(warehouse=request.POST['warehouse'],
                                                                sku=Product.objects.filter(product_sku=data[0])[0])
                # for loop for every bin inventory object
                for bin_inventory in bin_inventory_obj:
                    # condition to get those object which type is normal
                    bin_obj_normal = BinInventory.objects.filter(warehouse=request.POST['warehouse'],
                                                sku=Product.objects.filter(product_sku=data[0])[0],
                                                bin=bin_inventory.bin, inventory_type=inventory_type_normal[0]).last()

                    if bin_obj_normal:
                        bin_normal_quantity = bin_obj_normal.quantity
                    else:
                        bin_normal_quantity = 0

                    # condition to get those object which type is damaged
                    bin_obj_damaged = BinInventory.objects.filter(warehouse=request.POST['warehouse'],
                                                          sku=Product.objects.filter(product_sku=data[0])[0],
                                                          bin=bin_inventory.bin,
                                                          inventory_type=inventory_type_damaged[0]).last()

                    if bin_obj_damaged:
                        bin_damaged_quantity = bin_obj_damaged.quantity
                    else:
                        bin_damaged_quantity = 0

                    # condition to get those object which type is expired
                    bin_obj_expired = BinInventory.objects.filter(warehouse=request.POST['warehouse'],
                                                                  sku=Product.objects.filter(product_sku=data[0])[0],
                                                                  bin=bin_inventory.bin,
                                                                  inventory_type=inventory_type_expired[0]).last()
                    if bin_obj_expired:
                        bin_expired_quantity = bin_obj_expired.quantity
                    else:
                        bin_expired_quantity = 0

                    # condition to get those object which type is missing
                    bin_obj_missing = BinInventory.objects.filter(warehouse=request.POST['warehouse'],
                                                          sku=Product.objects.filter(product_sku=data[0])[0],
                                                          bin=bin_inventory.bin,
                                                          inventory_type=inventory_type_missing[0]).last()
                    if bin_obj_missing:
                        bin_missing_quantity = bin_obj_missing.quantity
                    else:
                        bin_missing_quantity = 0

                    # append data in a list
                    data_list.append([bin_inventory.warehouse_id, bin_inventory.sku.product_name + '-' + bin_inventory.sku.product_sku, product_price,
                                     expiry_date, bin_inventory.bin.bin_id, bin_normal_quantity, bin_damaged_quantity, bin_expired_quantity,
                                     bin_missing_quantity, 0, 0, 0, 0])
            # sort the list
            data_list.sort()

            # group by and remove duplicate data
            sort_data = list(num for num, _ in itertools.groupby(data_list))
            for data in sort_data:
                # write the data in csv file
                writer.writerow([data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8],data[9],data[10],
                                 data[11], data[12]])
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
        info_logger.info("POST request while upload the .xls file for Bin generation.")
        form = UploadAuditAdminForm(request.POST, request.FILES)
        if form.is_valid():
            info_logger.info("File format validation has been successfully done.")
            upload_data = form.cleaned_data['file']

            # call function to create audit data in Audit Model
            audit_inventory_obj = AuditInventory.create_audit_entry(request.user, request.FILES['file'])
            # iteration for csv data
            for data in upload_data:
                # convert expiry date according to database field type
                expiry_date = datetime.strptime(data[3], '%d/%m/%y').strftime('%Y-%m-%d')

                # Check SKU and Expiry data is exist or not
                grn_order_obj = GRNOrderProductMapping.objects.filter(
                    product__product_sku=data[1].split('-')[1],
                    expiry_date=expiry_date)
                if not grn_order_obj.exists():
                    shop_object = Shop.objects.filter(id=data[0])
                    sku = Product.objects.filter(product_sku=data[1].split('-')[1]).last()
                    quantity = int(data[9]) + int(data[10]) + int(data[11]) + int(data[12])
                    batch_id = '{}{}'.format(data[1].split('-')[1], datetime.strptime(data[3], '%d/%m/%y').strftime('%d%m%y'))
                    InCommonFunctions.create_in(shop_object[0], 'Audit Adjustment', audit_inventory_obj[0].id, sku,
                                                batch_id, int(quantity), int(quantity))
                # condition to check for Final Inventory types quantity
                bin_inventory_obj = BinInventory.objects.filter(warehouse=data[0],
                                            bin=Bin.objects.filter(bin_id=data[4]).last(),
                                            sku=Product.objects.filter(
                                                product_sku=data[1].split('-')[1]).last())
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
                for key, value in inventory_type.items():
                    # call function to create data in different models like:- Bin Inventory, Warehouse Inventory and
                    # Warehouse Internal Inventory Model
                    AuditInventory.audit_exist_batch_id(data, key, value, audit_inventory_obj)
            return render(request, 'admin/wms/audit-upload.html', {'form': form})

        else:
            return render(request, 'admin/wms/audit-upload.html', {'form': form})
    else:
        form = UploadAuditAdminForm()
    return render(request, 'admin/wms/audit-upload.html', {'form': form})
