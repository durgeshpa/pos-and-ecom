from dal import autocomplete
from wkhtmltopdf.views import PDFTemplateResponse

from django.forms import formset_factory
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum


from rest_framework.views import APIView
from rest_framework import permissions, authentication
from rest_framework.permissions import IsAuthenticated, AllowAny

from retailer_to_sp.models import (
    Cart, CartProductMapping, Order, OrderedProduct, OrderedProductMapping,
    CustomerCare, Payment, Return, ReturnProductMapping, Note
)
from products.models import Product
from retailer_to_sp.forms import (
    OrderedProductForm, OrderedProductMappingShipmentForm,
    OrderedProductMappingDeliveryForm, OrderedProductDispatchForm
)


class ReturnProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Product.objects.all()
        invoice_no_id = self.forwarded.get('invoice_no', None)

        if invoice_no_id:
            ordered_product = OrderedProduct.objects.get(id=invoice_no_id)
            returned_products = ordered_product.\
                rt_order_product_order_product_mapping.all().values('product')
            qs = qs.filter(id__in=[returned_products]).order_by('product_name')
        else:
            qs = None

        if self.q:
            qs = qs.filter(product_name__istartswith=self.q)
        return qs


class DownloadCreditNote(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'credit_note.pdf'
    template_name = 'admin/credit_note/credit_note.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(Return, pk=self.kwargs.get('pk'))
        pk = self.kwargs.get('pk')
        a = Return.objects.get(pk=pk)
        shop = a
        products = a.rt_product_return_product_mapping.all()
        order_id = a.invoice_no.order.order_no
        sum_qty = 0
        sum_amount = 0
        tax_inline = 0
        taxes_list = []
        gst_tax_list = []
        cess_tax_list = []
        surcharge_tax_list = []
        for z in shop.invoice_no.order.seller_shop.\
                shop_name_address_mapping.all():
            shop_name_gram = z.shop_name
            nick_name_gram = z.nick_name
            address_line1_gram = z.address_line1
            city_gram = z.city
            state_gram = z.state
            pincode_gram = z.pincode

        for m in products:
            sum_qty = sum_qty + (
                int(m.returned_product.product_inner_case_size) *
                int(m.total_returned_qty)
            )
            for h in m.get_shop_specific_products_prices_sp_return():
                sum_amount = sum_amount + (
                        int(m.returned_product.product_inner_case_size) *
                        int(m.total_returned_qty) *
                        h.price_to_retailer
                )
                inline_sum_amount = (
                        int(m.returned_product.product_inner_case_size) *
                        int(m.total_returned_qty) *
                        h.price_to_retailer
                )
            for n in m.returned_product.product_pro_tax.all():
                divisor = (1+(n.tax.tax_percentage/100))
                original_amount = (inline_sum_amount/divisor)
                tax_amount = inline_sum_amount - original_amount
                if n.tax.tax_type == 'gst':
                    gst_tax_list.append(tax_amount)
                if n.tax.tax_type == 'cess':
                    cess_tax_list.append(tax_amount)
                if n.tax.tax_type == 'surcharge':
                    surcharge_tax_list.append(tax_amount)

                taxes_list.append(tax_amount)
                igst = sum(gst_tax_list)
                cgst = (sum(gst_tax_list))/2
                sgst = (sum(gst_tax_list))/2
                cess = sum(cess_tax_list)
                surcharge = sum(surcharge_tax_list)

        total_amount = sum_amount
        total_amount_int = int(total_amount)
        print(sum_amount)


        data = {
            "object": order_obj,
            "products": products,
            "shop": shop,
            "total_amount_int": total_amount_int,
            "sum_qty": sum_qty,
            "sum_amount": sum_amount,
            "url": request.get_host(),
            "scheme": request.is_secure() and "https" or "http",
            "igst": igst,
            "cgst": cgst,
            "sgst": sgst,
            "cess": cess,
            "surcharge": surcharge,
            "total_amount": total_amount,
            "order_id": order_id,
            "shop_name_gram": shop_name_gram,
            "nick_name_gram": nick_name_gram,
            "city_gram": city_gram,
            "address_line1_gram": address_line1_gram,
            "pincode_gram": pincode_gram,
            "state_gram": state_gram
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


def ordered_product_mapping_shipment(request):
    order_id = request.GET.get('order_id')
    ordered_product_set = formset_factory(OrderedProductMappingShipmentForm,
                                          extra=1, max_num=1)
    form = OrderedProductForm()
    form_set = ordered_product_set()
    if order_id:
        ordered_product = Cart.objects.filter(pk=order_id)
        ordered_product = Order.objects.get(pk=order_id).ordered_cart
        order_product_mapping = CartProductMapping.objects.filter(
            cart=ordered_product)
        products_list = []
        for item in order_product_mapping.values('cart_product', 'qty'):
            already_shipped_qty = OrderedProductMapping.objects.filter(
                ordered_product__in=Order.objects.get(
                    pk=order_id).rt_order_order_product.all(),
                product_id=item['cart_product']).aggregate(
                Sum('shipped_qty')).get('shipped_qty__sum', 0)
            ordered_qty = item['qty']
            inner_case_size = int(Product.objects.get(pk=item['cart_product']).product_inner_case_size)
            ordered_no_pieces = ordered_qty * inner_case_size
            if ordered_no_pieces != already_shipped_qty:
                products_list.append({
                        'product': item['cart_product'],
                        'ordered_qty': ordered_no_pieces,
                        'already_shipped_qty': already_shipped_qty if already_shipped_qty else 0
                        })
        form_set = ordered_product_set(initial=products_list)
        form = OrderedProductForm(initial={'order': order_id})

    if request.method == 'POST':
        form_set = ordered_product_set(request.POST)
        form = OrderedProductForm(request.POST)
        if form.is_valid() and form_set.is_valid():
            ordered_product_instance = form.save()
            for forms in form_set:
                formset_data = forms.save(commit=False)
                formset_data.ordered_product = ordered_product_instance
                formset_data.save()
            return redirect('/admin/retailer_to_sp/orderedproduct/')

    return render(
        request,
        'admin/retailer_to_sp/OrderedProductMappingShipment.html',
        {'ordered_form': form, 'formset': form_set}
    )


def ordered_product_mapping_delivery(request):
    order_id = request.GET.get('order_id')
    ordered_product_set = formset_factory(OrderedProductMappingDeliveryForm,
                                          extra=1, max_num=1)
    form = OrderedProductForm()
    form_set = ordered_product_set()
    if order_id:
        ordered_product = Cart.objects.filter(pk=order_id)
        ordered_product = Order.objects.get(pk=order_id).ordered_cart
        order_product_mapping = CartProductMapping.objects.filter(
            cart=ordered_product)
        products_list = []
        for item in order_product_mapping.values('cart_product', 'qty'):
            products_list.append({
                    'product': item['cart_product'],
                    'ordered_qty': item['qty'],
                    'already_shipped_qty': OrderedProductMapping.objects.filter(ordered_product__in=Order.objects.get(pk=order_id).rt_order_order_product.all(),product_id=item['cart_product']).aggregate(Sum('shipped_qty')).get('shipped_qty__sum',0)
                    })
        form_set = ordered_product_set(initial=products_list)
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
                return redirect('/admin/retailer_to_sp/orderedproduct/')

    return render(
        request,
        'admin/retailer_to_sp/OrderedProductMappingDelivery.html',
        {'ordered_form': form, 'formset': form_set}
    )


class DownloadPickList(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'pick_list.pdf'
    template_name = 'admin/download/retailer_sp_pick_list.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(Order, pk=self.kwargs.get('pk'))
        cart_products = order_obj.ordered_cart.rt_cart_list.all()
        data = {
            "order_obj": order_obj, "cart_products":cart_products
        }
        cmd_option = {
            "margin-top": 10,
            "zoom": 1,
            "footer-center":
            "[page]/[topage]",
            "no-stop-slow-scripts": True
        }
        response = PDFTemplateResponse(
            request=request, template=self.template_name,
            filename=self.filename, context=data,
            show_content_in_browser=False, cmd_options=cmd_option)
        return response


def dispatch_shipment(request):
    # order_id = request.GET.get('order_id')
    # ordered_product_set = formset_factory(OrderedProductMappingShipmentForm,
    #                                       extra=1, max_num=1)
    # form = OrderedProductDispatchForm()
    # form_set = ordered_product_set()
    # if order_id:
    #     ordered_product = Cart.objects.filter(pk=order_id)
    #     ordered_product = Order.objects.get(pk=order_id).ordered_cart
    #     order_product_mapping = CartProductMapping.objects.filter(
    #         cart=ordered_product)
    #     products_list = []
    #     for item in order_product_mapping.values('cart_product', 'qty'):
    #         already_shipped_qty = OrderedProductMapping.objects.filter(
    #             ordered_product__in=Order.objects.get(
    #                 pk=order_id).rt_order_order_product.all(),
    #             product_id=item['cart_product']).aggregate(
    #             Sum('shipped_qty')).get('shipped_qty__sum', 0)
    #         ordered_qty = item['qty']
    #         inner_case_size = int(Product.objects.get(pk=item['cart_product']).product_inner_case_size)
    #         ordered_no_pieces = ordered_qty * inner_case_size
    #         if ordered_no_pieces != already_shipped_qty:
    #             products_list.append({
    #                     'product': item['cart_product'],
    #                     'ordered_qty': ordered_no_pieces,
    #                     'already_shipped_qty': already_shipped_qty if already_shipped_qty else 0,
    #                     })
    #     form_set = ordered_product_set(initial=products_list)
    #     form = OrderedProductDispatchForm(initial={'order': order_id})
    #
    # if request.method == 'POST':
    #     form_set = ordered_product_set(request.POST)
    #     form = OrderedProductDispatchForm(request.POST)
    #     if form.is_valid() and form_set.is_valid():
    #         ordered_product_instance = form.save()
    #         for forms in form_set:
    #             formset_data = forms.save(commit=False)
    #             formset_data.ordered_product = ordered_product_instance
    #             formset_data.save()
    #         return redirect('/admin/retailer_to_sp/orderedproduct/')
    #import pdb; pdb.set_trace()
    form = OrderedProductDispatchForm()
    invoice_no = request.GET.get('invoice_no')
    print(invoice_no)
    if invoice_no:
        #import ipdb; ipdb.set_trace()
        ordered_product = OrderedProduct.objects.get(pk=invoice_no)
        form = OrderedProductDispatchForm(instance=ordered_product)
        return render(
             request,
             'admin/retailer_to_sp/Dispatch.html',
             {'ordered_form': form}
        )

    if request.method == 'POST':
        print("adfadsfadsfsfsf")
        print(invoice_no)
        #import pdb;pdb.set_trace()
        ordered_product = OrderedProduct.objects.get(pk=170)
        form = OrderedProductDispatchForm(request.POST, instance=ordered_product)
        #import ipdb;ipdb.set_trace()

        form.save()
        return redirect('/admin/retailer_to_sp/orderedproduct/')

    return render(
        request,
        'admin/retailer_to_sp/Dispatch.html',
        {'ordered_form': form}
    )


def order_invoices(request):
    order_id = request.GET.get('order_id')
    if order_id:
        invoices = OrderedProduct.objects.filter(
            order_id=order_id
        )
    else:
        invoices = OrderedProduct.objects.none()
    return render(
        request,
        'admin/retailer_to_sp/invoices_dropdown_list.html',
        {'invoices': invoices}
    )
