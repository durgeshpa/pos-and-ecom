from dal import autocomplete

from accounts.models import User
from audit.models import AuditDetail, AuditTicketManual
from products.models import Product
from shops.models import Shop
from wms.models import Bin, BinInventory


class WareHouseComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Shop.objects.none()

        qs = Shop.objects.filter(shop_type__shop_type='sp')

        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class AssignedUserFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()

        qs = User.objects.all()

        if self.q:
            qs = qs.filter(first_name__icontains=self.q)
        return qs

class AuditorComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()

        auditor = AuditDetail.objects.only('auditor').values_list('auditor_id', flat=True)
        qs = User.objects.filter(id__in=auditor)

        if self.q:
            qs = qs.filter(first_name__icontains=self.q)
        return qs

class SKUComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Product.objects.none()

        warehouse = self.forwarded.get('warehouse', None)
        sku = BinInventory.objects.only('sku_id').filter(warehouse=warehouse).values_list('sku_id', flat=True)
        qs = Product.objects.filter(product_sku__in=sku)

        if self.q:
            qs = qs.filter(product_name__istartswith=self.q)
        return qs


class BinComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Bin.objects.none()

        qs = Bin.objects.all()
        warehouse = self.forwarded.get('warehouse', None)
        qs = qs.filter(warehouse=warehouse)
        if self.q:
            qs = qs.filter(bin_id__istartswith=self.q)
        return qs
