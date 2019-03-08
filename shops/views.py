from django.shortcuts import render
from django.views.generic import TemplateView, CreateView,FormView
from django.shortcuts import get_object_or_404
from shops.models import Shop,ShopAdjustmentFile
from gram_to_brand.models import GRNOrderProductMapping
from sp_to_gram.models import (OrderedProductMapping,Cart ,CartProductMapping, OrderedProduct, ShopStockAdjustment,
                               ShopStockAdjustmentsProductsMapping, Order)
from django.db.models import Sum,Q, F
from dal import autocomplete
from .forms import StockAdjustmentForm
from django.urls import reverse_lazy
import codecs, json, csv
from django.shortcuts import render, redirect
from django.contrib import messages
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from products.models import ProductPrice,Product
from retailer_backend.common_function import getShopMapping


# Create your views here.
class ShopMappedProduct(FormView):
    template_name = "admin/shop/change_list.html"
    form_class = StockAdjustmentForm

    def get_context_data(self, **kwargs):
        shop_obj = get_object_or_404(Shop, pk=self.kwargs.get('pk'))
        data = super(ShopMappedProduct, self).get_context_data(**kwargs)
        if shop_obj.shop_type.shop_type=='gf':
            grn_product = GRNOrderProductMapping.objects.filter(grn_order__order__ordered_cart__gf_shipping_address__shop_name=shop_obj)
            product_sum = grn_product.values('nb','product__product_name', 'product__product_gf_code').annotate(product_qty_sum=Sum('available_qty'))
            data['shop_products'] = product_sum
            data['shop'] = shop_obj

        elif shop_obj.shop_type.shop_type=='sp':

            sp_grn_product = OrderedProductMapping.objects.filter(
                Q(ordered_product__order__ordered_cart__shop=shop_obj)
                | Q(ordered_product__credit_note__shop=shop_obj),
                Q(ordered_product__status=OrderedProduct.ENABLED)|
                Q(ordered_product__status=OrderedProduct.ADJUSTEMENT)
                )
            product_sum = sp_grn_product.values('product','product__product_name', 'product__product_gf_code').annotate(
                product_qty_sum=Sum(F('available_qty')))

            data['shop_products'] = product_sum
            data['shop'] = shop_obj
        else:
            data['shop_products'] = None
        return data

    def form_valid(self, form):
        shop_obj = get_object_or_404(Shop, pk=self.kwargs.get('pk'))
        file = form.cleaned_data.get('file')
        reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
        first_row = next(reader)
        today = datetime.today()
        grn = []
        odr = []

        posative_adjustment_created = False
        negative_adjustment_created = False

        #try:

        shop_adjustment_file = ShopAdjustmentFile.objects.create(shop=shop_obj, stock_adjustment_file=file,
                                                                 created_by=self.request.user)

        for row in reader:

            # import ipdb
            # ipdb.set_trace()

            ordered_product_details = OrderedProductMapping.objects.filter(
                ordered_product__order__shipping_address__shop_name=shop_obj,
                product__id=int(row[1]))

            """
            When quantity greater than available quantity  
            """
            current_avilable_qty = int(row[3])
            available_qty_sum = ordered_product_details.aggregate(available_qty_sum=Sum(F('available_qty')))['available_qty_sum']
            product_obj = Product.objects.get(id=int(row[1]))

            if available_qty_sum is not None and int(current_avilable_qty) > int(available_qty_sum):
                posative = {
                    'product_id':int(row[1]),
                    'po_qty': int(current_avilable_qty)-int(available_qty_sum),
                }
                grn.append(posative)
                if not posative_adjustment_created:
                    shop_stock_adjustment_p = ShopStockAdjustment.objects.create(
                        shop_adjustment_file=shop_adjustment_file,
                        adjustment_type=ShopStockAdjustment.POSITIVE,
                        status=ShopStockAdjustment.ADJUSTED)
                    posative_adjustment_created = True
                ShopStockAdjustmentsProductsMapping.objects.create(shop_stock_adjustment=shop_stock_adjustment_p,
                                                                   product=product_obj, qty=int(current_avilable_qty)-int(available_qty_sum))


            elif available_qty_sum is not None and int(current_avilable_qty) < int(available_qty_sum):

                negative = {
                    'product_id': int(row[1]),
                    'po_qty': int(available_qty_sum)-int(current_avilable_qty),
                }
                odr.append(negative)
                if not negative_adjustment_created:
                    shop_stock_adjustment_n = ShopStockAdjustment.objects.create(
                        shop_adjustment_file=shop_adjustment_file,
                        adjustment_type=ShopStockAdjustment.NEGATIVE,
                        status=ShopStockAdjustment.ADJUSTED)
                    negative_adjustment_created = True
                ShopStockAdjustmentsProductsMapping.objects.create(shop_stock_adjustment=shop_stock_adjustment_n,
                                                                   product=product_obj,qty=int(available_qty_sum)-int(current_avilable_qty))

        """
        Creating a single po for exceeded qty
        """
        if grn:
            """
                Doing GRN
            """
            last_order = Order.objects.filter(ordered_cart__shop=shop_obj).last()

            shipment_planning = OrderedProduct.objects.create(
                status=OrderedProduct.ADJUSTEMENT,
                order=last_order,
                last_modified_by=self.request.user,
            )

            for po_dt in grn:
                product_obj = Product.objects.get(id=int(po_dt['product_id']))
                OrderedProductMapping.objects.create(
                    ordered_product = shipment_planning,
                    product = product_obj,
                    manufacture_date = today,
                    expiry_date = today + relativedelta(months=6),
                    delivered_qty = int(po_dt['po_qty']),
                    available_qty = int(po_dt['po_qty']),
                    last_modified_by = self.request.user,
                )
        if odr:
            """
                Doing Order 
            """
            for po_dt in odr:
                available_deduct_qty = int(po_dt['po_qty'])
                ordered_product_details = OrderedProductMapping.objects.filter(
                    ordered_product__order__shipping_address__shop_name=shop_obj,
                    product__id=int(po_dt['product_id']))

                for available in ordered_product_details.order_by('expiry_date'):
                    if available_deduct_qty <= 0:
                        break

                    deduct_qty = available.sp_available_qty if available_deduct_qty > available.sp_available_qty else available_deduct_qty
                    available.available_qty = int(available.available_qty) - int(deduct_qty)
                    available.save()
                    available_deduct_qty = int(available_deduct_qty) - int(deduct_qty)

        messages.success(self.request, 'Stock uploaded successfully')
        # except:
        #     messages.error(self.request, "Something went wrong!")

        return super(ShopMappedProduct, self).form_valid(form)

    def form_invalid(self, form):
        return super(ShopMappedProduct, self).form_invalid(form)

    def get_success_url(self, **kwargs):
        return reverse_lazy('admin:shop_mapped_product', args=(self.kwargs.get('pk'),))


class ShopParentAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['sp','gf'])
        if self.q:
            qs = qs.filter(Q(shop_owner__phone_number__icontains=self.q) | Q(shop_name__icontains=self.q))
        return qs

class ShopRetailerAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['sp','r'],shop_name_address_mapping__address_type='shipping').distinct('id')
        if self.q:
            qs = qs.filter(Q(shop_owner__phone_number__icontains=self.q) | Q(shop_name__icontains=self.q))
        return qs

from django.http import HttpResponse
import csv

def StockCorrectionUploadSample(request):
    """
        For Stock Correction Sample
    """
    filename = "stock_correction_upload_sample.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['product_name','product_id','product_gf_code','present_available_qty','perish_qty','damage_qty'])
    writer.writerow(['fortune sunflowers oil','123','GF00000121','100','10','2'])
    return response
