from dal import autocomplete

from accounts.models import User
from audit.models import AuditDetail, AuditTicketManual
from products.models import Product
from shops.models import Shop, ShopUserMapping
from wms.models import Bin, BinInventory


class WareHouseComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Shop.objects.none()

        qs = Shop.objects.filter(shop_type__shop_type__in=['sp', 'f'])

        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class AssignedUserComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()
        warehouse = self.forwarded.get('warehouse', None)
        user = ShopUserMapping.objects.filter(shop=warehouse).values_list('employee_id', flat=True)
        qs = User.objects.filter(id__in=user)
        if self.q:
            qs = qs.filter(first_name__istartswith=self.q)
        return qs


class AssignedUserFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()

        assigned_user = AuditTicketManual.objects.values_list('assigned_user_id', flat=True)
        qs = User.objects.filter(id__in=assigned_user)

        if self.q:
            qs = qs.filter(first_name__istartswith=self.q)
        return qs


class AuditorFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()

        auditor = AuditDetail.objects.values_list('auditor_id', flat=True)
        qs = User.objects.filter(id__in=auditor)

        if self.q:
            qs = qs.filter(first_name__istartswith=self.q)
        return qs

class SKUComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Product.objects.none()

        warehouse = self.forwarded.get('warehouse', None)
        sku = BinInventory.objects.only('sku_id').filter(warehouse=warehouse)\
                                                 .values_list('sku_id', flat=True)
        qs = Product.objects.filter(product_sku__in=sku, product_type=Product.PRODUCT_TYPE_CHOICE.NORMAL,
                                    repackaging_type__in=['none', 'source', 'destination'])

        if self.q:
            self.q=self.q.strip()
            qs = qs.filter(product_name__istartswith=self.q) | qs.filter(product_sku__istartswith=self.q)
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
