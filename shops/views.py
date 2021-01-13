import openpyxl
import re
import logging
from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import HttpResponse
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from shops.models import Shop, ShopType, BeatPlanning, DayBeatPlanning
from products.models import Product
from gram_to_brand.models import GRNOrderProductMapping
from sp_to_gram.models import OrderedProduct, OrderedProductMapping, StockAdjustment, StockAdjustmentMapping, \
    OrderedProductReserved
from django.db.models import Sum, Q
from dal import autocomplete

from wms.common_functions import get_stock
from .forms import StockAdjustmentUploadForm, BulkShopUpdation, ShopUserMappingCsvViewForm, BeatUserMappingCsvViewForm

from wms.models import BinInventory, InventoryType, InventoryState, WarehouseInventory
from .forms import StockAdjustmentUploadForm, BulkShopUpdation, ShopUserMappingCsvViewForm
from django.views.generic.edit import FormView
import csv
import codecs
import datetime
from django.db import transaction
from addresses.models import Address, State, City, Pincode
from django.contrib.auth import get_user_model
from shops.models import ShopUserMapping
from rest_framework.views import APIView
from retailer_backend.messages import SUCCESS_MESSAGES, ERROR_MESSAGES
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse
from collections import defaultdict
import itertools
from io import StringIO


# Create your views here.

logger = logging.getLogger('shop')

class ShopMappedProduct(TemplateView):
    template_name = "admin/shop/change_list.html"

    def get_context_data(self, **kwargs):
        shop_obj = get_object_or_404(Shop, pk=self.kwargs.get('pk'))
        context = super().get_context_data(**kwargs)
        context['shop'] = shop_obj
        context['user_has_stock_update_perm'] = self.request.user.has_perm('sp_to_gram.add_stockadjustment')
        if shop_obj.shop_type.shop_type == 'gf':
            grn_product = GRNOrderProductMapping.objects.filter(
                grn_order__order__ordered_cart__gf_shipping_address__shop_name=shop_obj)
            product_sum = grn_product.values('product', 'product__product_name',
                                             'product__product_sku').annotate(product_qty_sum=Sum('available_qty'))
            #   'product__product_gf_code',
            context['shop_products'] = product_sum


        elif shop_obj.shop_type.shop_type in ['sp', 'f']:
            product_list = get_shop_products(shop_obj)
            context['products'] = product_list
        return context


class ShopParentAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            qs = Shop.objects.none()
            return qs
        shop_type = self.forwarded.get('shop_type', None)
        if shop_type:
            dt = {'r': 'sp', 'sp': 'gf', 'f': 'sp'}
            qs = Shop.objects.filter(shop_type__shop_type=dt[ShopType.objects.get(id=shop_type).shop_type])
        else:
            qs = Shop.objects.filter(shop_type__shop_type__in=['gf', 'sp'])
        if self.q:
            qs = qs.filter(Q(shop_owner__phone_number__icontains=self.q) | Q(shop_name__icontains=self.q))
        return qs


class ShopRetailerAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            qs = Shop.objects.none()
            return qs
        qs = Shop.objects.filter(shop_type__shop_type__in=['sp', 'r', 'f'],
                                 shop_name_address_mapping__address_type='shipping').distinct('id')
        if self.q:
            qs = qs.filter(Q(shop_owner__phone_number__icontains=self.q) | Q(shop_name__icontains=self.q))
        return qs

def get_shop_products(shop_obj):
    product_list = {}
    inv_type_qs = InventoryType.objects.all()
    for inv_type in inv_type_qs:
        product_qty_dict = get_stock(shop_obj, inv_type)
        products = Product.objects.filter(id__in=product_qty_dict.keys())

        for p in products:
            if product_list.get(p.product_sku) is None:
                product_temp = {
                    'sku': p.product_sku,
                    'name': p.product_name,
                    'mrp': p.product_mrp,
                    'parent_id': p.parent_product.parent_id if p.parent_product else '',
                    'parent_name': p.parent_product.name if p.parent_product else '',
                    'product_ean_code': p.product_ean_code,
                    'weight': f'{p.weight_value} {p.weight_unit}'
                }
                product_list[p.product_sku] = product_temp
            product_list[p.product_sku][inv_type.inventory_type] = product_qty_dict[p.id]
    return product_list

def shop_stock_download(request, shop_id):
    filename = "shop_stock_" + shop_id + ".csv"
    shop = Shop.objects.get(pk=shop_id)
    product_list = get_shop_products(shop)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['SKU Id', 'Product Name', 'MRP', 'Parent ID', 'Parent Name', 'EAN', 'Weight', 'Normal Qty', 'Damaged Qty', 'Expired Qty', 'Missing Qty'])
    for key, value in product_list.items():
        if 'damaged' not in value:
            value['damaged'] = 0
        if 'expired' not in value:
            value['expired'] = 0
        if 'missing' not in value:
            value['missing'] = 0

        writer.writerow(
            [value['sku'], value['name'], value['mrp'], value['parent_id'], value['parent_name'], value['product_ean_code'], value['weight'], value['normal'], value['damaged'], value['expired']
                , value['missing']])
    return response


class StockAdjustmentView(PermissionRequiredMixin, View):
    permission_required = 'sp_to_gram.add_stockadjustment'
    template_name = 'admin/shop/upload_stock_adjustment.html'

    def get(self, request, shop_id):
        shop = Shop.objects.get(pk=shop_id)
        form = StockAdjustmentUploadForm(initial={'shop': shop})
        return render(request, self.template_name, {'form': form, 'shop': shop})

    def post(self, request, shop_id):
        shop = Shop.objects.get(pk=shop_id)
        form = StockAdjustmentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            self.handle_uploaded_file(request.POST.get('shop'), request.FILES['upload_file'])
            form = StockAdjustmentUploadForm()
            return render(request, self.template_name, {'form': form, 'shop': shop})
        return render(request, self.template_name, {'form': form, 'shop': shop})

    def handle_uploaded_file(self, shop_id, f):
        reader = csv.reader(codecs.iterdecode(f, 'utf-8'))
        first_row = next(reader)
        self.shop = Shop.objects.get(pk=shop_id)
        self.stock_adjustment = StockAdjustment.objects.create(shop=self.shop)
        for row in reader:
            gfcode = row[0]
            stock_available, stock_damaged, stock_expired = [int(i) for i in row[3:6]]
            product = Product.objects.get(product_gf_code=gfcode)
            db_available_products = OrderedProductMapping.get_product_availability(self.shop, product)
            db_expired_products = OrderedProductMapping.get_expired_product_qty(self.shop, product)

            product_available = db_available_products.aggregate(Sum('available_qty'))['available_qty__sum']
            product_damaged = db_available_products.aggregate(Sum('damaged_qty'))['damaged_qty__sum']
            product_expired = db_expired_products.aggregate(Sum('available_qty'))['available_qty__sum']
            if not product_available:
                product_available = 0
            if not product_expired:
                product_expired = 0
            if not product_damaged:
                product_damaged = 0
            if stock_expired < product_expired:
                qty = abs(product_expired - stock_expired)
                self.decrement_grn_qty(product, db_expired_products, qty)

            if stock_expired > product_expired:
                qty = abs(product_expired - stock_expired)
                manufacture_date = datetime.datetime.today() - datetime.timedelta(days=180)
                expiry_date = datetime.datetime.today()
                self.increment_grn_qty(product, manufacture_date, expiry_date, qty)

            adjustment_grn = {
                'available_qty': 0,
                'damaged': 0
            }
            if stock_available > product_available:
                # Create GRN and add in stock adjustment
                adjustment_grn['available_qty'] = abs(stock_available - product_available)

            if stock_damaged > product_damaged:
                adjustment_grn['damaged'] = abs(stock_damaged - product_damaged)

            if stock_available < product_available:
                self.decrement_grn_qty(product, db_available_products, abs(stock_available - product_available))

            if stock_damaged < product_damaged:
                self.decrement_grn_qty(product, db_available_products, abs(stock_damaged - product_damaged), True)
            # Creating Fresh GRN
            if adjustment_grn['available_qty'] > 0 or adjustment_grn['damaged'] > 0:
                manufacture_date = datetime.datetime.today()
                expiry_date = datetime.datetime.today() + datetime.timedelta(days=180)
                self.increment_grn_qty(product, manufacture_date, expiry_date, adjustment_grn['available_qty'],
                                       adjustment_grn['damaged'])
        messages.success(self.request, 'Stock Updated .')

    def decrement_grn_qty(self, product, grn_queryset, qty, is_damaged=False):
        adjust_qty = qty
        if is_damaged:
            grn_queryset = grn_queryset.filter(damaged_qty__gt=0).order_by('-expiry_date')
        else:
            grn_queryset = grn_queryset.filter(available_qty__gt=0).order_by('-expiry_date')
        for grn in grn_queryset:
            if is_damaged:
                if grn.damaged_qty >= qty:
                    grn_deduct = qty
                else:
                    grn_deduct = grn.damaged_qty
                grn.damaged_qty -= grn_deduct
            else:
                if grn.available_qty >= qty:
                    grn_deduct = qty
                else:
                    grn_deduct = grn.available_qty
                grn.available_qty -= grn_deduct
            qty -= grn_deduct
            grn.save()
            StockAdjustmentMapping.objects.create(
                stock_adjustment=self.stock_adjustment,
                grn_product=grn,
                adjustment_type=StockAdjustmentMapping.DECREMENT,
                adjustment_qty=grn_deduct
            )
            if qty <= 0:
                return

    def increment_grn_qty(self, product, manufacture_date, expiry_date, qty, damaged=0):
        adjustment_grn = OrderedProductMapping.objects.create(
            product=product,
            shop=self.shop,
            manufacture_date=manufacture_date,
            expiry_date=expiry_date,
            available_qty=qty,
            damaged_qty=damaged
        )
        StockAdjustmentMapping.objects.create(
            stock_adjustment=self.stock_adjustment,
            grn_product=adjustment_grn,
            adjustment_type=StockAdjustmentMapping.INCREMENT,
            adjustment_qty=qty
        )
        return


class ShopTimingAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['r', 'f'])
        if self.q:
            qs = qs.filter(Q(shop_owner__phone_number__icontains=self.q) | Q(shop_name__icontains=self.q))
        return qs


def bulk_shop_updation(request):
    if request.method == 'POST':
        form = BulkShopUpdation(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    wb_obj = openpyxl.load_workbook(form.cleaned_data.get('file'))
                    sheet_obj = wb_obj.active
                    for row in sheet_obj.iter_rows(
                            min_row=2, max_row=None, min_col=None, max_col=None,
                            values_only=True
                    ):
                        # skipping first row(headings)
                        if not re.match('^[1-9][0-9]{5}$', str(int(row[10]))):
                            raise Exception('Pincode must be of 6 digits')
                        if not re.match('^[6-9]\d{9}$', str(int(row[9]))):
                            raise Exception('Mobile no. must be of 10 digits')
                        if row[13] not in ('billing', 'shipping'):
                            raise Exception('Not a valid Address type')
                        address = Address.objects.filter(
                            id=int(row[5]), shop_name_id=int(row[0]))
                        if address.exists():
                            state_id = State.objects.get(
                                state_name=row[11]).id
                            city_id = City.objects.get(
                                city_name=row[12]).id
                            pincode_id = Pincode.objects.get(
                                pincode=int(row[10]),
                                city_id=city_id).id
                            address.update(nick_name=row[6],
                                           address_line1=row[7],
                                           address_contact_name=row[8],
                                           address_contact_number=int(row[9]),
                                           pincode_link_id=pincode_id,
                                           state_id=state_id,
                                           city_id=city_id,
                                           address_type=row[13])
                            shipping_address = Address.objects \
                                .filter(
                                shop_name_id=int(row[0]),
                                address_type='shipping'
                            )
                            if not shipping_address.exists():
                                raise Exception('Atleast one shipping address'
                                                ' is required')
                            Shop.objects.filter(id=int(row[0])).update(
                                shop_name=row[1], status=row[4])
                        else:
                            raise Exception('Shop and Address ID are not'
                                            ' valid')
                return redirect('/admin/shops/shop/')

            except Exception as e:
                messages.error(request, '{} (Shop: {})'.format(e, row[1]))

    else:
        form = BulkShopUpdation

    return render(
        request,
        'admin/shop/bulk-shop-updation.html',
        {'form': form}
    )


class ShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.none
        if self.q:
            qs = Shop.objects.filter(Q(shop_name__icontains=self.q) | Q(shop_owner__phone_number__icontains=self.q))
        return qs


class UserAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = get_user_model().objects.all()
        if self.q:
            qs = qs.filter(phone_number__icontains=self.q)
        return qs


class ShopUserMappingCsvView(FormView):
    form_class = ShopUserMappingCsvViewForm
    template_name = 'admin/shops/shopusermapping/shop_user_mapping.html'
    success_url = '/admin/shops/shopusermapping/'

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        # shop_user_mapping = []
        not_uploaded_list = []
        if form.is_valid():
            file = request.FILES['file']
            reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
            first_row = next(reader)
            for row in reader:
                try:
                    if row[2]:
                        employee = get_user_model().objects.get(phone_number=row[2])
                    if row[1]:
                        manager = ShopUserMapping.objects.filter(employee__phone_number=row[1],
                                                                 employee_group__permissions__codename='can_sales_manager_add_shop',
                                                                 status=True).last()
                        ShopUserMapping.objects.create(shop_id=row[0], manager=manager, employee=employee,
                                                       employee_group_id=row[3])
                    else:
                        ShopUserMapping.objects.create(shop_id=row[0], employee=employee, employee_group_id=row[3])
                except:
                    not_uploaded_list.append(ERROR_MESSAGES['INVALID_MAPPING'] % (row[0], row[2]))
            # ShopUserMapping.objects.bulk_create(shop_user_mapping)
            if not not_uploaded_list:
                messages.success(request, SUCCESS_MESSAGES['CSV_UPLOADED'])
            else:
                messages.success(request, SUCCESS_MESSAGES['CSV_UPLOADED_EXCEPT'] % (not_uploaded_list))
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


from django.views.generic import View


class ShopUserMappingCsvSample(View):
    def get(self, request, *args, **kwargs):
        filename = "shop_user_list.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(['shop', 'manager', 'employee', 'employee_group'])
        writer.writerow(['23', '8989787878', '8989898989', '2'])
        return response


from django.views.generic import View
class BeatUserMappingCsvSample(View):
    """
    This class is used to download the sample beat csv file for individual executive
    """
    def get(self, request, *args, **kwargs):
        """

        :param request: GET request
        :param args: non keyword argument
        :param kwargs: keyword argument
        :return: csv file
        """
        if request.user.is_superuser:
            # get the executive id
            query_set = ShopUserMapping.objects.filter(
                employee=request.GET['shop_user_mapping']).values_list('employee').last()

            # get the shop queryset assigned with executive
            shops = ShopUserMapping.objects.filter(employee=query_set).all()
        else:
            query_set = ShopUserMapping.objects.filter(
                id=request.GET['shop_user_mapping']).values_list('employee').last()

            # get the shop queryset assigned with executive
            shops = ShopUserMapping.objects.filter(employee=query_set[0]).all()

        try:
            # name of the csv file
            filename = shops[0].employee.first_name+'_'+datetime.datetime.today().strftime('%d-%m-%y') + ".csv"
        except Exception as e:
            logger.exception(e)
            user = get_user_model().objects.filter(id=request.GET['shop_user_mapping'])
            filename = user[0].first_name + '_' + datetime.datetime.today().strftime('%d-%m-%y') + ".csv"

        # The response gets a special MIME type, text/csv. This tells browsers that the document is a CSV file,
        # rather than an HTML file. If you leave this off, browsers will probably interpret the output as HTML,
        # which will result in ugly, scary gobbledygook in the browser window.
        # The response gets an additional Content-Disposition header, which contains the name of the CSV file.
        # This filename is arbitrary; call it whatever you want. It’ll be used by browsers in the “Save as…” dialog,
        # etc.
        # We can hook into the CSV-generation API by passing response as the first argument to csv.writer.
        # The csv.writer function expects a file-like object, and HttpResponse objects fit the bill.
        try:
            f = StringIO()
            writer = csv.writer(f)
            # header of csv file
            writer.writerow(['Sales Executive (Number - Name)', 'Shop Name', 'Shop ID ', 'Contact Number', 'Address',
                             'Pin Code', 'Category', 'Date (dd/mm/yyyy)'])
            for shop in shops:
                if shop.shop.approval_status == 2:
                    writer.writerow([shop.employee, shop.shop.shop_name, shop.shop.pk,
                                     shop.shop.shipping_address.address_contact_number,
                                     shop.shop.shipping_address.address_line1, shop.shop.shipping_address.pincode, '', ''])
                else:
                    pass
            f.seek(0)
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            return response
        except Exception as e:
            logger.exception(e)


class BeatUserMappingCsvView(FormView):
    """
    This class is used to upload csv file for sales executive to set the Beat Plan
    """
    form_class = BeatUserMappingCsvViewForm

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
                    # get the list of csv data
                    upload_data = form.cleaned_data['file']
                    # get sale executive id
                    executive_id = get_user_model().objects.filter(
                        phone_number=upload_data[0][0].split('-')[0].split(' ')[0])

                    # set status false for sales executive if executive is exist in the beat planning model
                    executive_beat_plan = BeatPlanning.objects.filter(executive=executive_id[0])
                    if executive_beat_plan:
                        for executive in executive_beat_plan:
                            # set the status False
                            executive.status = False
                            # save the data
                            executive.save()
                    # beat plan created for sales executive
                    beat_plan_object = BeatPlanning.objects.get_or_create(executive=executive_id[0],
                                                                          status=True, manager=request.user)
                    # list of those ids which are either duplicate or already exists in a database
                    not_uploaded_list = []
                    for row, data in enumerate(upload_data):
                        # convert the string date to django model date field
                        try:
                            date = datetime.datetime.strptime(data[7], '%d/%m/%y').strftime("%Y-%m-%d")
                        except:
                            date = datetime.datetime.strptime(data[7], '%d/%m/%Y').strftime("%Y-%m-%d")

                        # day wise beat plan created for sales executive
                        day_beat_plan_object, created = DayBeatPlanning.objects.get_or_create(
                            beat_plan=beat_plan_object[0], shop_id=data[2], beat_plan_date=date, shop_category=data[6],
                            next_plan_date=date)

                        # append the data in a list which is already exist in the database
                        if not created:
                            not_uploaded_list.append(ERROR_MESSAGES["4004"] % (row+1))

                    # return success message while csv data is successfully saved
                    if not not_uploaded_list:
                        result = {'message': SUCCESS_MESSAGES['CSV_UPLOADED']}
                        status = '200'
                    else:
                        result = {'message': SUCCESS_MESSAGES['CSV_UPLOADED_EXCEPT'] % not_uploaded_list}
                        status = '200'
                # return validation error message while uploading csv file
                else:
                    result = {'message': form.errors['file'][0]}
                    status = '400'

                return JsonResponse(result, status=status)
            # exception block
            except Exception as e:
                logger.exception(e)
                result = {'message': ERROR_MESSAGES["4003"]}
                status = '400'
                return JsonResponse(result, status)

        else:
            result = {'message': ERROR_MESSAGES["4005"]}
            status = '400'
        return JsonResponse(result, status)
