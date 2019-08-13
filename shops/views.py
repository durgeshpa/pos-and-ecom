import openpyxl
import re

from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import HttpResponse
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from shops.models import Shop, ShopType
from products.models import Product
from gram_to_brand.models import GRNOrderProductMapping
from sp_to_gram.models import OrderedProduct, OrderedProductMapping, StockAdjustment, StockAdjustmentMapping,OrderedProductReserved
from django.db.models import Sum,Q
from dal import autocomplete
from .forms import StockAdjustmentUploadForm, BulkShopUpdation, ShopUserMappingCsvViewForm
from django.views.generic.edit import FormView
import csv
import codecs
import datetime
from django.db import transaction
from addresses.models import Address, State, City
from django.contrib.auth import get_user_model
from shops.models import ShopUserMapping
from rest_framework.views import APIView

# Create your views here.
class ShopMappedProduct(TemplateView):
    template_name = "admin/shop/change_list.html"

    def get_context_data(self, **kwargs):
        shop_obj = get_object_or_404(Shop, pk=self.kwargs.get('pk'))
        context = super().get_context_data(**kwargs)
        context['shop'] = shop_obj
        if shop_obj.shop_type.shop_type=='gf':
            grn_product = GRNOrderProductMapping.objects.filter(grn_order__order__ordered_cart__gf_shipping_address__shop_name=shop_obj)
            product_sum = grn_product.values('product','product__product_name', 'product__product_gf_code', 'product__product_sku').annotate(product_qty_sum=Sum('available_qty'))
            context['shop_products'] = product_sum

        elif shop_obj.shop_type.shop_type=='sp':
            sp_grn_product = OrderedProductMapping.get_shop_stock(shop_obj)

            product_sum = sp_grn_product.values('product','product__product_name', 'product__product_gf_code', 'product__product_sku').annotate(product_qty_sum=Sum('available_qty')).annotate(damaged_qty_sum=Sum('damaged_qty'))
            context['shop_products'] = product_sum
        else:
            context['shop_products'] = None
        return context

class ShopParentAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        shop_type = self.forwarded.get('shop_type', None)
        if shop_type:
            dt = {'r':'sp','sp':'gf'}
            qs = Shop.objects.filter(shop_type__shop_type=dt[ShopType.objects.get(id=shop_type).shop_type])
        else:
            qs = Shop.objects.filter(shop_type__shop_type__in=['gf','sp'])
        if self.q:
            qs = qs.filter(Q(shop_owner__phone_number__icontains=self.q) | Q(shop_name__icontains=self.q))
        return qs

class ShopRetailerAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['sp','r'],shop_name_address_mapping__address_type='shipping').distinct('id')
        if self.q:
            qs = qs.filter(Q(shop_owner__phone_number__icontains=self.q) | Q(shop_name__icontains=self.q))
        return qs

def stock_adjust_sample(request, shop_id):
    filename = "stock_correction_upload_sample.csv"
    shop = Shop.objects.get(pk=shop_id)
    sp_grn_product = OrderedProductMapping.get_shop_stock(shop)
    db_available_products = sp_grn_product.filter(expiry_date__gt = datetime.datetime.today())
    db_expired_products = OrderedProductMapping.get_shop_stock_expired(shop)

    products_available = db_available_products.values('product','product__product_name', 'product__product_gf_code', 'product__product_sku').annotate(product_qty_sum=Sum('available_qty')).annotate(damaged_qty_sum=Sum('damaged_qty'))
    products_expired = db_expired_products.values('product','product__product_name', 'product__product_gf_code', 'product__product_sku').annotate(product_qty_sum=Sum('available_qty'))
    expired_products = {}
    for product in products_expired:
        expired_products[product['product__product_gf_code']] = product['product_qty_sum']
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['product_gf_code','product_name','product_sku','Available','Damaged','Expired'])
    for product in products_available:
        expired_product = expired_products.get(product['product__product_gf_code'],0)
        writer.writerow([product['product__product_gf_code'],product['product__product_name'],product['product__product_sku'],product['product_qty_sum'],product['damaged_qty_sum'],expired_product])
    return response

class StockAdjustmentView(View):
    template_name = 'admin/shop/upload_stock_adjustment.html'
    def get(self, request, shop_id):
        shop = Shop.objects.get(pk=shop_id)
        form = StockAdjustmentUploadForm(initial={'shop':shop})
        return render(request, self.template_name, {'form': form, 'shop':shop})

    def post(self,request, shop_id):
        shop = Shop.objects.get(pk=shop_id)
        form = StockAdjustmentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            self.handle_uploaded_file(request.POST.get('shop'), request.FILES['upload_file'])
            form = StockAdjustmentUploadForm()
            return render(request, self.template_name, {'form': form, 'shop':shop})
        return render(request, self.template_name, {'form': form, 'shop':shop})

    def handle_uploaded_file(self, shop_id, f):
        reader = csv.reader(codecs.iterdecode(f, 'utf-8'))
        first_row = next(reader)
        self.shop = Shop.objects.get(pk=shop_id)
        self.stock_adjustment = StockAdjustment.objects.create(shop=self.shop)
        for row in reader:
            gfcode = row[0]
            stock_available, stock_damaged, stock_expired = [int(i) for i in row[1:4]]
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
                'available_qty' : 0,
                'damaged' : 0
            }
            if stock_available > product_available:
                #Create GRN and add in stock adjustment
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
                self.increment_grn_qty(product, manufacture_date, expiry_date, adjustment_grn['available_qty'], adjustment_grn['damaged'])
        messages.success(self.request, 'Stock Updated .')

    def decrement_grn_qty(self, product, grn_queryset, qty, is_damaged=False):
        adjust_qty = qty
        if is_damaged:
            grn_queryset = grn_queryset.filter(damaged_qty__gt = 0).order_by('-expiry_date')
        else:
            grn_queryset = grn_queryset.filter(available_qty__gt = 0).order_by('-expiry_date')
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
                stock_adjustment = self.stock_adjustment,
                grn_product = grn,
                adjustment_type = StockAdjustmentMapping.DECREMENT,
                adjustment_qty = grn_deduct
            )
            if qty <= 0:
                return

    def increment_grn_qty(self, product, manufacture_date, expiry_date, qty, damaged=0):
        adjustment_grn = OrderedProductMapping.objects.create(
                product = product,
                shop=self.shop,
                manufacture_date = manufacture_date,
                expiry_date = expiry_date,
                available_qty = qty,
                damaged_qty = damaged
            )
        StockAdjustmentMapping.objects.create(
                stock_adjustment = self.stock_adjustment,
                grn_product = adjustment_grn,
                adjustment_type = StockAdjustmentMapping.INCREMENT,
                adjustment_qty = qty
            )
        return


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
                            address.update(nick_name=row[6],
                                           address_line1=row[7],
                                           address_contact_name=row[8],
                                           address_contact_number=int(row[9]),
                                           pincode=str(int(row[10])),
                                           state_id=state_id,
                                           city_id=city_id,
                                           address_type=row[13])
                            shipping_address = Address.objects\
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
            qs = Shop.objects.filter(shop_name__icontains=self.q)
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
        #shop_user_mapping = []
        file = request.FILES['file']
        reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
        first_row = next(reader)
        for row in reader:
            if row[1]:
                manager = get_user_model().objects.get(phone_number=row[1])
            if row[2]:
                employee = get_user_model().objects.get(phone_number=row[2])
            ShopUserMapping.objects.create(shop_id=row[0],manager=manager, employee=employee, employee_group_id=row[3])
        #ShopUserMapping.objects.bulk_create(shop_user_mapping)
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