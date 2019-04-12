from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import HttpResponse
from django.views import View
from django.shortcuts import get_object_or_404
from django.contrib import messages
from shops.models import Shop, ShopType
from products.models import Product
from gram_to_brand.models import GRNOrderProductMapping
from sp_to_gram.models import OrderedProduct, OrderedProductMapping, StockAdjustment, StockAdjustmentMapping,OrderedProductReserved
from django.db.models import Sum,Q
from dal import autocomplete
from .forms import StockAdjustmentUploadForm
import csv
import codecs
import datetime

# Create your views here.
class ShopMappedProduct(TemplateView):
    template_name = "admin/shop/change_list.html"

    def get_context_data(self, **kwargs):
        shop_obj = get_object_or_404(Shop, pk=self.kwargs.get('pk'))
        context = super().get_context_data(**kwargs)
        context['shop'] = shop_obj
        if shop_obj.shop_type.shop_type=='gf':
            grn_product = GRNOrderProductMapping.objects.filter(grn_order__order__ordered_cart__gf_shipping_address__shop_name=shop_obj)
            product_sum = grn_product.values('product','product__product_name', 'product__product_gf_code').annotate(product_qty_sum=Sum('available_qty'))
            context['shop_products'] = product_sum

        elif shop_obj.shop_type.shop_type=='sp':
            sp_grn_product = OrderedProductMapping.get_shop_stock(shop_obj)

            product_sum = sp_grn_product.values('product','product__product_name', 'product__product_gf_code').annotate(product_qty_sum=Sum('available_qty')).annotate(damaged_qty_sum=Sum('damaged_qty'))
            context['shop_products'] = product_sum
        else:
            context['shop_products'] = None
        return context

class ShopParentAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = None
        shop_type = self.forwarded.get('shop_type', None)
        if shop_type:
            dt = {'r':'sp','sp':'gf'}
            qs = Shop.objects.filter(shop_type__shop_type=dt[ShopType.objects.get(id=shop_type).shop_type])
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

    products_available = db_available_products.values('product','product__product_name', 'product__product_gf_code').annotate(product_qty_sum=Sum('available_qty')).annotate(damaged_qty_sum=Sum('damaged_qty'))
    products_expired = db_expired_products.values('product','product__product_name', 'product__product_gf_code').annotate(product_qty_sum=Sum('available_qty'))
    expired_products = {}
    for product in products_expired:
        expired_products[product['product__product_gf_code']] = product['product_qty_sum']
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['product_gf_code','Available','Damaged','Expired'])
    for product in products_available:
        expired_product = expired_products.get(product['product__product_gf_code'],0)
        writer.writerow([product['product__product_gf_code'],product['product_qty_sum'],product['damaged_qty_sum'],expired_product])
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


