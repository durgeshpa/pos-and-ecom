from django.shortcuts import render, HttpResponse, redirect
from .models import OrderedProduct, OrderedProductMapping, Order, Cart, CartProductMapping
from products.models import Product
from .forms import (
    OrderedProductForm, OrderedProductMappingForm,
    OrderedProductMappingCustomForm, OrderedProductMappingCustomFormShipment,
)
from django.shortcuts import render
from django.forms import inlineformset_factory, modelformset_factory, formset_factory
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404, get_list_or_404
from wkhtmltopdf.views import PDFTemplateResponse


def ordered_product_mapping(request):
    order_id = request.GET.get('order_id')
    if request.user.has_perm('sp_to_gram.warehouse_shipment'):
        ordered_product_set = formset_factory(OrderedProductMappingCustomFormShipment, extra=1, max_num=1)
    else:
        ordered_product_set = formset_factory(OrderedProductMappingCustomForm, extra=1, max_num=1)
    form = OrderedProductForm()
    form_set = ordered_product_set()
    if order_id:
        ordered_product = Cart.objects.filter(pk=order_id)
        ordered_product = Order.objects.get(pk=order_id).ordered_cart
        order_product_mapping = CartProductMapping.objects.filter(cart=ordered_product)
        form_set = ordered_product_set(
            initial=[{'product': item['cart_product'], 'ordered_qty': item['qty']} for item in order_product_mapping.values('cart_product', 'qty')])
        form = OrderedProductForm(initial={'order': order_id})

    if request.POST:
        form = OrderedProductForm(request.POST)
        if form.is_valid():
            ordered_product_instance=form.save()
            form_set = ordered_product_set(request.POST)

            if form_set.is_valid():
                for form in form_set:
                    formset_data = form.save(commit=False)
                    formset_data.ordered_product = ordered_product_instance
                    formset_data.save()
                return redirect('/admin/retailer_to_gram/orderedproduct/')

    return render(request, 'admin/retailer_to_gram/orderproductmapping.html',
                              {'ordered_form':form,'formset':form_set})

class DownloadInvoice(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'invoice.pdf'
    template_name = 'admin/invoice/invoice.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(OrderedProduct, pk=self.kwargs.get('pk'))

        #order_obj1= get_object_or_404(OrderedProductMapping)
        pk=self.kwargs.get('pk')
        a = OrderedProduct.objects.get(pk=pk)
        shop=a
        products = a.rtg_order_product_order_product_mapping.all()
        payment_type = a.order.rt_payment.last().payment_choice

        order_id= a.order.order_no

        sum_qty = 0
        sum_amount=0
        tax_inline=0
        taxes_list = []
        gst_tax_list= []
        cess_tax_list= []
        surcharge_tax_list=[]
        for z in shop.order.seller_shop.shop_name_address_mapping.all():
            shop_name_gram= z.shop_name
            nick_name_gram= z.nick_name
            address_line1_gram= z.address_line1
            city_gram= z.city
            state_gram= z.state
            pincode_gram= z.pincode

        for m in products:
            sum_qty = sum_qty + int(m.product.product_inner_case_size) * int(m.shipped_qty)
            for h in m.get_shop_specific_products_prices():
                sum_amount = sum_amount + (int(m.product.product_inner_case_size) * int(m.shipped_qty) * h.price_to_retailer)
                inline_sum_amount = (int(m.product.product_inner_case_size) * int(m.shipped_qty) * h.price_to_retailer)
            for n in m.product.product_pro_tax.all():
                divisor= (1+(n.tax.tax_percentage/100))
                original_amount= (inline_sum_amount/divisor)
                tax_amount = inline_sum_amount - original_amount
                if n.tax.tax_type=='gst':
                    gst_tax_list.append(tax_amount)
                if n.tax.tax_type=='cess':
                    cess_tax_list.append(tax_amount)
                if n.tax.tax_type=='surcharge':
                    surcharge_tax_list.append(tax_amount)
                taxes_list.append(tax_amount)
                igst= sum(gst_tax_list)
                cgst= (sum(gst_tax_list))/2
                sgst= (sum(gst_tax_list))/2
                cess= sum(cess_tax_list)
                surcharge= sum(surcharge_tax_list)
                #tax_inline = tax_inline + (inline_sum_amount - original_amount)
                #tax_inline1 =(tax_inline / 2)
        total_amount = sum_amount
        total_amount_int = int(total_amount)


        data = {"object": order_obj,"order": order_obj.order,"products":products ,"shop":shop, "sum_qty": sum_qty, "sum_amount":sum_amount,"url":request.get_host(), "scheme": request.is_secure() and "https" or "http" , "igst":igst, "cgst":cgst,"sgst":sgst,"cess":cess,"surcharge":surcharge, "total_amount":total_amount,"order_id":order_id,"shop_name_gram":shop_name_gram,"nick_name_gram":nick_name_gram, "city_gram":city_gram, "address_line1_gram":address_line1_gram, "pincode_gram":pincode_gram,"state_gram":state_gram, "payment_type":payment_type,"total_amount_int":total_amount_int}

        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=self.template_name, filename=self.filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        return response
