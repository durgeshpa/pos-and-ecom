from dal import autocomplete
from products.models import Product
from brand.models import Brand
from categories.models import Category

class BrandAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Brand.objects.all()
        category_id = self.forwarded.get('category', None)
        if category_id:
            qs = qs.filter(categories=category_id).order_by('brand_name')
        else:
            qs = qs

        if self.q:
            qs = qs.filter(brand_name__istartswith=self.q)
        return qs

class CategoryAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Category.objects.all()

        if self.q:
            qs = qs.filter(category_name__istartswith=self.q)
        return qs

class ProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Product.objects.all()
        brand_id = self.forwarded.get('brand', None)
        if brand_id:
            qs = qs.filter(product_brand = brand_id).order_by('product_name')
        else:
            qs = qs

        if self.q:
            qs = qs.filter(product_name__istartswith=self.q)
        return qs

from shops.models import Shop
from django.db.models import Q
class BannerShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['sp',])
        if self.q:
            qs = qs.filter(Q(shop_owner__phone_number__icontains=self.q) | Q(shop_name__icontains=self.q))
        return qs
