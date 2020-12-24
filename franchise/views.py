from django.shortcuts import redirect
from django.db.models import Q

from shops.models import Shop
from django.views import View
from django.contrib import messages
# Create your views here.


class ProductList(View):
    """
        Product List to display on admin site under B2C Franchise Management
        To link to products mapped with the particular Franchise shop mapped with the logged in user
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.is_superuser:
            franchise_shop = Shop.objects.filter(shop_type__shop_type__in=['f'])
            franchise_shop = franchise_shop.filter(Q(related_users=user) | Q(shop_owner=user)).last()
            if franchise_shop:
                return redirect('/admin/shops/shop-mapped/'+str(franchise_shop.id)+'/product/')
            messages.add_message(request, messages.ERROR, 'No Franchise Shop Mapping Exists To Show Product List For')
        return redirect('/admin/')