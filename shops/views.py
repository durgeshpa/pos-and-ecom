from django.shortcuts import render
from django.views.generic import TemplateView, CreateView,FormView
from django.shortcuts import get_object_or_404
from shops.models import Shop,ShopStockAdjustment
from gram_to_brand.models import GRNOrderProductMapping
from sp_to_gram.models import OrderedProductMapping,Cart ,CartProductMapping, OrderedProduct
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
        #context = super().get_context_data(**kwargs)
        data = super(ShopMappedProduct, self).get_context_data(**kwargs)
        if shop_obj.shop_type.shop_type=='gf':
            grn_product = GRNOrderProductMapping.objects.filter(grn_order__order__ordered_cart__gf_shipping_address__shop_name=shop_obj)
            product_sum = grn_product.values('product','product__product_name', 'product__product_gf_code').annotate(product_qty_sum=Sum('available_qty'))
            data['shop_products'] = product_sum
            data['shop'] = shop_obj

        elif shop_obj.shop_type.shop_type=='sp':

            sp_grn_product = OrderedProductMapping.objects.filter(
                Q(ordered_product__order__ordered_cart__shop=shop_obj)
                | Q(ordered_product__credit_note__shop=shop_obj),
                Q(ordered_product__status=OrderedProduct.ENABLED)
                )
            product_sum = sp_grn_product.values('product','product__product_name', 'product__product_gf_code').annotate(product_qty_sum=Sum(F('available_qty') - (F('damaged_qty') + F('lossed_qty'))))
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
        po = []
        #try:
        for row in reader:

            #import ipdb
            #ipdb.set_trace()

            ordered_product_details = OrderedProductMapping.objects.filter(
                ordered_product__order__shipping_address__shop_name=shop_obj,
                product__id=int(row[1]))

            # Expired Product
            expired_dt = ordered_product_details.filter(expiry_date__lte=today)
            expired_deduct_qty = int(row[4])

            """
            When quantity greater than current expired quantity
            """
            if int(expired_deduct_qty) > expired_dt.count():
                expired_deduct_qty= expired_deduct_qty-expired_dt.count()
                for expired in expired_dt.order_by('expiry_date'):
                    if expired_deduct_qty <=0:
                        break

                    deduct_qty = expired.sp_available_qty if expired_deduct_qty > expired.sp_available_qty else expired_deduct_qty
                    expired.perished_qty = int(expired.perished_qty) + int(deduct_qty)
                    expired.save()
                    expired_deduct_qty = int(expired_deduct_qty) - int(deduct_qty)

            else:
                expired_deduct_qty = expired_deduct_qty - expired_dt.count()
                for expired in expired_dt.order_by('-expiry_date'):
                    if expired_deduct_qty > expired.sp_available_qty:
                        deduct_qty = expired.sp_available_qty
                        expired.expiry_date = expired.expiry_date + relativedelta(months=3)
                        expired.save()
                    else:
                        break
                    expired_deduct_qty = int(expired_deduct_qty) - int(deduct_qty)

            """
            When qantity greater than demege quantity 
            """
            damage_deduct_qty = int(row[5])
            damaged_qty_sum = ordered_product_details.aggregate(damaged_qty_sum=Sum(F('damaged_qty')))['damaged_qty_sum']

            if damaged_qty_sum is not None and int(damage_deduct_qty) > int(damaged_qty_sum):
                damaged_qty_sum = int(damaged_qty_sum) - int(damage_deduct_qty)
                for damaged in ordered_product_details.order_by('expiry_date'):
                    if damage_deduct_qty <= 0:
                        break

                    deduct_qty = damaged.sp_available_qty if damage_deduct_qty > damaged.sp_available_qty else damage_deduct_qty
                    damaged.damaged_qty = int(damaged.damaged_qty) + int(deduct_qty)
                    damaged.save()
                    damage_deduct_qty = int(damage_deduct_qty) - int(deduct_qty)

            else:
                for damaged in ordered_product_details.order_by('expiry_date'):
                    damaged_qty_sum = int(damaged_qty_sum) - int(damage_deduct_qty)
                    if damage_deduct_qty <= 0:
                        break

                    deduct_qty = damaged.damaged_qty if damaged.damaged_qty >0 else 0
                    damaged.damaged_qty = int(damaged.damaged_qty) - int(deduct_qty)
                    damaged.save()
                    damage_deduct_qty = int(damage_deduct_qty) - int(deduct_qty)

            """
            When quantity greater than available quantity  
            """
            current_avilable_qty = int(row[3])
            available_qty_sum = ordered_product_details.aggregate(available_qty_sum=Sum(F('available_qty') - (F('damaged_qty') + F('lossed_qty') + F('perished_qty'))))['available_qty_sum']

            if available_qty_sum is not None and int(current_avilable_qty) > int(available_qty_sum):
                temp = {
                    'product_id':int(row[1]),
                    'po_qty': int(current_avilable_qty)-int(available_qty_sum),
                }
                po.append(temp)

            else:
                current_avilable_qty = int(current_avilable_qty) - int(available_qty_sum)
                for avilable_qty in ordered_product_details.order_by('expiry_date'):
                    if current_avilable_qty <= 0:
                        break

                    deduct_qty = avilable_qty.sp_available_qty if current_avilable_qty > avilable_qty.sp_available_qty else current_avilable_qty
                    avilable_qty.lossed_qty = int(avilable_qty.lossed_qty) + int(deduct_qty)
                    avilable_qty.save()
                    current_avilable_qty = int(current_avilable_qty) - int(deduct_qty)

        """
        Creating a single po for exceeded qty
        """
        if po:
            shop_parent = getShopMapping(int(self.kwargs.get('pk')))

            sp_cart = Cart.objects.create(
                shop=shop_obj,
                po_status='ordered_to_gram',
                po_raised_by=self.request.user,
                last_modified_by=self.request.user,
                po_validity_date=today + relativedelta(months=1),
                is_stock_adjustment=True
            )

            for po_dt in po:
                product_obj = Product.objects.get(id=int(po_dt['product_id']))
                CartProductMapping.objects.create(
                    cart= sp_cart,
                    cart_product = product_obj,
                    qty = int(po_dt['po_qty']),
                    case_size=1,
                    number_of_cases = 1,
                    price =ProductPrice.objects.get(product=product_obj,shop=shop_parent.parent,status=True).price_to_service_partner
                )

            """
                Doing GRN
            """
            shipment_planning = OrderedProduct.objects.create(
                order=sp_cart.sp_order_cart_mapping.last(),
                last_modified_by=self.request.user,
            )

            for po_dt in po:
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
        ShopStockAdjustment.objects.create(shop=shop_obj,stock_adjustment_file=file,created_by=self.request.user)
        messages.success(self.request, 'Stock uploaded successfully')
        # except:
        #     messages.error(self.request, "Something went wrong!")

        return super(ShopMappedProduct, self).form_valid(form)

    def form_invalid(self, form):
        #print('Form invalid!')
        #print(form.errors)
        #data = json.dumps(form.errors)
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
