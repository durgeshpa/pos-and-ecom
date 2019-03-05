from dal import autocomplete
from wkhtmltopdf.views import PDFTemplateResponse

from django.forms import formset_factory, inlineformset_factory, modelformset_factory, BaseFormSet, ValidationError
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Q


from rest_framework.views import APIView
from rest_framework import permissions, authentication
from rest_framework.permissions import IsAuthenticated, AllowAny

from retailer_to_sp.models import (
    Cart, CartProductMapping, Order, OrderedProduct, OrderedProductMapping,
    CustomerCare, Payment, Return, ReturnProductMapping, Note, Trip, Dispatch
)
from products.models import Product
from retailer_to_sp.forms import (
    OrderedProductForm, OrderedProductMappingShipmentForm,
    OrderedProductMappingDeliveryForm, OrderedProductDispatchForm,
    TripForm, DispatchForm, DispatchDisabledForm
)

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity


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


class RequiredFormSet(BaseFormSet):

    def clean(self):
        to_ship_sum = []
        for form in self.forms:
            to_ship_pieces = form.cleaned_data.get('shipped_qty')
            if to_ship_pieces:
                to_ship_sum.append(to_ship_pieces)
        if sum(to_ship_sum) == 0:
            raise ValidationError("Please add shipment quantity for at least one product")


def ordered_product_mapping_shipment(request):
    order_id = request.GET.get('order_id')
    ordered_product_set = formset_factory(OrderedProductMappingShipmentForm,
                                          extra=1, max_num=1, formset=RequiredFormSet
                                          )
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
                Sum('delivered_qty')).get('delivered_qty__sum', 0)
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
        if form.is_valid():
            status = form.cleaned_data.get('shipment_status')
            if status == 'CANCELLED':
                ordered_product_set = formset_factory(OrderedProductMappingShipmentForm,
                                                      extra=1, max_num=1
                                                      )
                form_set = ordered_product_set(request.POST)

            if form_set.is_valid():
                ordered_product_instance = form.save()
                for forms in form_set:
                    if forms.is_valid():
                        formset_data = forms.save(commit=False)
                        formset_data.ordered_product = ordered_product_instance
                        formset_data.save()
                return redirect('/admin/retailer_to_sp/shipment/')

    return render(
        request,
        'admin/retailer_to_sp/OrderedProductMappingShipment.html',
        {'ordered_form': form, 'formset': form_set}
    )


def trip_planning(request):
    TripDispatchFormset = modelformset_factory(
        Dispatch,
        fields=[
            'selected', 'items', 'invoice_amount', 'invoice_city', 'invoice_date', 'order', 'shipment_address'
        ],
        form=DispatchForm, extra=0
    )
    trip_id = request.GET.get('trip_id')

    if request.method == 'POST':
        formset = TripDispatchFormset(request.POST)
        form = TripForm(request.user, request.POST)
        if form.is_valid() and formset.is_valid():
            trip = form.save()
            for formset_form in formset:
                if formset_form.is_valid():
                    selected_form = formset_form.cleaned_data.get('selected')
                    if selected_form:
                        dispatch = formset_form.save(commit=False)
                        dispatch.trip = trip
                        dispatch.shipment_status = 'READY_TO_DISPATCH'
                        dispatch.save()
                    else:
                        dispatch = formset_form.save(commit=False)
                        if dispatch.trip:
                            dispatch.trip = None
                            dispatch.shipment_status = 'READY_TO_SHIP'
                            dispatch.save()
            return redirect('/admin/retailer_to_sp/trip/')

    else:
        formset = TripDispatchFormset(queryset=Dispatch.objects.none())
        form = TripForm(request.user)

    return render(
        request,
        'admin/retailer_to_sp/TripPlanning.html',
        {'form':form, 'formset': formset}
    )


def trip_planning_change(request, pk):
    trip_dispatch_formset = modelformset_factory(
        Dispatch,
        fields=[
            'selected', 'items', 'invoice_amount', 'invoice_city', 'invoice_date', 'order', 'shipment_address'
        ],
        form=DispatchForm, extra=0
    )
    trip_instance = Trip.objects.get(pk=pk)
    trip_status = trip_instance.trip_status
    if request.method == 'POST':
        formset = trip_dispatch_formset(request.POST)
        form = TripForm(request.user, request.POST, instance=trip_instance)
        if trip_status == 'READY' or trip_status == 'CANCELLED':
            if form.is_valid() and formset.is_valid():
                trip = form.save()
                current_trip_status = trip.trip_status
                for formset_form in formset:
                    if formset_form.is_valid():
                        selected_form = formset_form.cleaned_data.get('selected')
                        if selected_form and not current_trip_status == 'CANCELLED':
                            dispatch = formset_form.save(commit=False)
                            dispatch.trip = trip
                            if current_trip_status == 'STARTED':
                                dispatch.shipment_status = 'OUT_FOR_DELIVERY'
                            dispatch.save()
                        else:
                            dispatch = formset_form.save(commit=False)
                            if dispatch.trip:
                                dispatch.trip = None
                                dispatch.shipment_status = 'READY_TO_SHIP'
                                dispatch.save()
                return redirect('/admin/retailer_to_sp/trip/')

        else:
            if form.is_valid():
                form.save()
                return redirect('/admin/retailer_to_sp/trip/')

    else:
        if trip_status == 'READY':
            formset = trip_dispatch_formset(
                queryset=Dispatch.objects.filter(
                    Q(trip=pk) | Q(shipment_status='READY_TO_SHIP')
                )
            )
        else:
            trip_dispatch_formset = modelformset_factory(
                Dispatch,
                fields=[
                    'selected', 'items', 'invoice_amount', 'invoice_city', 'invoice_date', 'order', 'shipment_address'
                ],
                form=DispatchDisabledForm, extra=0
            )
            formset = trip_dispatch_formset(
                queryset=Dispatch.objects.filter(trip=pk)
            )
        form = TripForm(request.user, instance=trip_instance)
    return render(
        request,
        'admin/retailer_to_sp/TripPlanningChange.html',
        {'form':form, 'formset': formset}
    )


def load_dispatches(request):
    """Return list of dispatches for specific seller shop

    :param request: seller_shop_id
    :return: list of dispatch
    """
    seller_shop = request.GET.get('seller_shop_id')
    area = request.GET.get('area')
    trip_id = request.GET.get('trip_id')

    vector = SearchVector('order__shipping_address__address_line1')
    query = SearchQuery(area)
    similarity = TrigramSimilarity('order__shipping_address__address_line1', area)

    if seller_shop and area and trip_id:
        dispatches = Dispatch.objects.annotate(
                        rank=SearchRank(vector, query) + similarity
                        ).filter(Q(shipment_status='READY_TO_SHIP') |
                                 Q(trip=trip_id), order__seller_shop=seller_shop).order_by('-rank')

    elif seller_shop and trip_id:
        dispatches = Dispatch.objects.filter(Q(shipment_status='READY_TO_SHIP') |
                                             Q(trip=trip_id), order__seller_shop=seller_shop)
    elif seller_shop and area:
        dispatches = Dispatch.objects.annotate(
                        rank=SearchRank(vector, query) + similarity
                        ).filter(shipment_status='READY_TO_SHIP', order__seller_shop=seller_shop).order_by('-rank')

    elif seller_shop:
        dispatches = Dispatch.objects.filter(shipment_status='READY_TO_SHIP',
                                             order__seller_shop=seller_shop)
    elif area and trip_id:
        dispatches = Dispatch.objects.annotate(
                        rank=SearchRank(vector, query) + similarity
                        ).filter(Q(shipment_status='READY_TO_SHIP') |
                                 Q(trip=trip_id)).order_by('-rank')

    elif area:
        dispatches = Dispatch.objects.annotate(
                        rank=SearchRank(vector, query) + similarity
                        ).order_by('-rank')

    else:
        dispatches = Dispatch.objects.none()
    TripDispatchFormset = modelformset_factory(
        Dispatch,
        fields=[
            'selected', 'items', 'invoice_amount', 'invoice_city', 'invoice_date', 'order', 'shipment_address'
        ],
        form=DispatchForm, extra=0
    )
    formset = TripDispatchFormset(queryset=dispatches)
    return render(
        request, 'admin/retailer_to_sp/DispatchesList.html',
        {'formset': formset}
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
        cart_product_list = []

        for cart_pro in cart_products:
            product_list = {
                "product_name":cart_pro.cart_product.product_name,
                "product_mrp":cart_pro.cart_product.product_pro_price.filter(shop=order_obj.seller_shop).last().mrp,
                "ordered_qty":cart_pro.qty,
                "no_of_pieces":int(cart_pro.cart_product.product_inner_case_size)*int(cart_pro.qty),
            }
            cart_product_list.append(product_list)




        data = {
            "order_obj": order_obj, "cart_products":cart_product_list
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


def update_delivered_qty(instance, inline_form):

    instance.delivered_qty = instance.shipped_qty - (
        inline_form.cleaned_data.get('returned_qty', 0)+
        inline_form.cleaned_data.get('damaged_qty', 0)
    )
    instance.save()


def update_shipment_status(form, formsets):
    form_instance = getattr(form, 'instance', None)
    shipped_qty_list = []
    returned_qty_list = []
    damaged_qty_list = []

    for inline_forms in formsets:
        for inline_form in inline_forms:
            instance = getattr(inline_form, 'instance', None)
            update_delivered_qty(instance, inline_form)
            shipped_qty_list.append(instance.shipped_qty if instance else 0)
            returned_qty_list.append(inline_form.cleaned_data.get('returned_qty', 0))
            damaged_qty_list.append(inline_form.cleaned_data.get('damaged_qty', 0))

    shipped_qty = sum(shipped_qty_list)
    returned_qty = sum(returned_qty_list)
    damaged_qty = sum(damaged_qty_list)

    if shipped_qty == (returned_qty + damaged_qty):
        form_instance.shipment_status = 'FULLY_RETURNED_AND_COMPLETED'

    elif (returned_qty + damaged_qty) == 0:
        form_instance.shipment_status = 'FULLY_DELIVERED_AND_COMPLETED'

    elif shipped_qty > (returned_qty + damaged_qty):
        form_instance.shipment_status = 'PARTIALLY_DELIVERED_AND_COMPLETED'

    form_instance.save()


def update_order_status(form):
    form_instance = getattr(form, 'instance', None)
    total_delivered_qty = []
    total_shipped_qty = []
    total_returned_qty = []
    total_damaged_qty = []
    current_order_shipment = form_instance.order.rt_order_order_product.all()
    for shipment in current_order_shipment:
        shipment_product = shipment.rt_order_product_order_product_mapping.all()
        ordered_qty = sum([int(i.ordered_qty) for i in shipment_product])
        delivered_qty = shipment_product.aggregate(Sum('delivered_qty')).get('delivered_qty__sum', 0)
        shipped_qty = shipment_product.aggregate(Sum('shipped_qty')).get('shipped_qty__sum', 0)
        returned_qty = shipment_product.aggregate(Sum('returned_qty')).get('returned_qty__sum', 0)
        damaged_qty = shipment_product.aggregate(Sum('damaged_qty')).get('damaged_qty__sum', 0)

        total_delivered_qty.append(delivered_qty)
        total_shipped_qty.append(shipped_qty)
        total_returned_qty.append(returned_qty)
        total_damaged_qty.append(damaged_qty)

    order = form_instance.order
    if ordered_qty == (sum(total_delivered_qty) + sum(total_returned_qty) + sum(total_damaged_qty)):
        order.order_status = 'SHIPPED'

    elif (sum(total_returned_qty) == sum(total_shipped_qty) or
          (sum(total_damaged_qty) + sum(total_returned_qty)) == sum(total_shipped_qty)):
        order.order_status = 'DENIED'

    elif (sum(total_delivered_qty) == 0 and sum(total_shipped_qty) > 0 and
            sum(total_returned_qty) == 0 and sum(total_damaged_qty) == 0):
        order.order_status = 'DISPATCH_PENDING'

    elif (ordered_qty - sum(total_delivered_qty)) > 0 and sum(total_delivered_qty) > 0:
        order.order_status = 'PARTIALLY_SHIPPED'
    order.save()


