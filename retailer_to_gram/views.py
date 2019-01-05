from django.shortcuts import render, HttpResponse, redirect
from .models import OrderedProduct, OrderedProductMapping, Order, Cart, CartProductMapping
from products.models import Product
from .admin import OrderedProductMappingForm
from .forms import OrderedProductForm
from django.shortcuts import render
from django.forms import inlineformset_factory, modelformset_factory, formset_factory

def ordered_product_mapping(request):
    order_id = request.GET.get('order_id')
    ordered_product_set = formset_factory(OrderedProductMappingForm, extra=1, max_num=1)
    form = OrderedProductForm()
    form_set = ordered_product_set()
    if order_id:
        ordered_product = Cart.objects.filter(pk=order_id)
        ordered_product = Order.objects.get(pk=order_id).ordered_cart
        order_product_mapping = CartProductMapping.objects.filter(cart=ordered_product)
        form_set = ordered_product_set(initial = [{'product':item['cart_product']} for item in order_product_mapping.values('cart_product')])
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
