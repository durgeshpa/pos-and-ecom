from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.shortcuts import get_object_or_404
from shops.models import Shop
from gram_to_brand.models import GRNOrderProductMapping
from sp_to_gram.models import OrderedProductMapping
from django.db.models import Sum

# Create your views here.
class ShopMappedProduct(TemplateView):
    template_name = "admin/shop/change_list.html"

    def get_context_data(self, **kwargs):
        shop_obj = get_object_or_404(Shop, pk=self.kwargs.get('pk'))
        context = super().get_context_data(**kwargs)
        if shop_obj.shop_type.shop_type=='gf':
            grn_product = GRNOrderProductMapping.objects.filter(grn_order__order__ordered_cart__gf_shipping_address__shop_name=shop_obj)
            product_sum = grn_product.values('product','product__product_name').annotate(product_qty_sum=Sum('available_qty'))
            context['shop_products'] = product_sum

        elif shop_obj.shop_type.shop_type=='sp':
            sp_grn_product = OrderedProductMapping.objects.filter(ordered_product__order__ordered_cart__shop=shop_obj)
            product_sum = sp_grn_product.values('product','product__product_name').annotate(product_qty_sum=Sum('available_qty'))
            context['shop_products'] = product_sum
        else:
            context['shop_products'] = None
        return context