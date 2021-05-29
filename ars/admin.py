import csv
import datetime
import logging
import math
from io import StringIO

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone

from ars.filters import WarehouseFilter, ParentProductFilter
from ars.models import ProductDemand
from ars.views import get_current_inventory, get_child_product_with_latest_grn

info_logger = logging.getLogger('file-info')


@admin.register(ProductDemand)
class ProductDemandAdmin(admin.ModelAdmin):

    """
    Class to represent ProductDemand admin
    """
    list_display = ('warehouse', 'parent_id', 'parent_name', 'child_product_sku',
                    'child_product_name', 'average_daily_sales', 'system_inventory', 'current_demand')

    list_filter = [WarehouseFilter,ParentProductFilter,]
    search_fields = ['parent_product__name']
    actions = ['export_as_csv']


    class Media:
        pass

    def get_queryset(self, request):
        """Returns queryset"""
        qs = super(ProductDemandAdmin, self).get_queryset(request)
        # latest_date = ProductDemand.objects.latest('created_at').created_at.date()
        # return qs.filter(created_at__date=latest_date).order_by('-created_at', 'parent_product')
        return qs.order_by('-created_at', 'parent_product_id').distinct('created_at', 'parent_product')

    def parent_id(self, obj):
        """Returns parent product's parent id"""
        return obj.parent_product.parent_id

    def parent_name(self, obj):
        """Returns Parent products's name"""
        return obj.parent_product.name

    def child_product_sku(self, obj):
        """Returns child product's SKU"""
        return obj.active_child_product.product_sku if obj.active_child_product else None

    def child_product_name(self, obj):
        """Returns child product's name"""
        return obj.active_child_product.product_name if obj.active_child_product else None

    def system_inventory(self, obj):
        """
        Returns the current inventory in the system for a parent product for specific warehouse
        """
        return get_current_inventory(obj.warehouse, obj.parent_product)

    def current_demand(self, obj):
        """
        Returns the current demand for a parent product for specific warehouse
        """
        if obj.average_daily_sales <= 0:
            return 0
        current_inventory = get_current_inventory(obj.warehouse, obj.parent_product)
        max_inventory_in_days = obj.parent_product.max_inventory
        demand = (obj.average_daily_sales * max_inventory_in_days) - current_inventory
        return math.ceil(demand) if demand > 0 else 0

    def has_add_permission(self, request):
        """Disabling user to add demand"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disabling user to delete demand"""
        return False

    def has_change_permission(self, request, obj=None):
        """Disabling user to change demand"""
        return False

    def export_as_csv(self, request, queryset):
        """Download the selected records in CSV file"""
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(['warehouse', 'parent_id', 'parent_name', 'child_product_sku', 'child_product_name', 'average_daily_sales', 'current_inventory', 'demand'])
        for obj in queryset:
            try:
                writer.writerow([obj.warehouse, self.parent_id(obj), self.parent_name(obj), self.child_product_sku(obj),
                                 self.child_product_name(obj), obj.average_daily_sales, self.system_inventory(obj),
                                 obj.demand])

            except Exception as exc:
                info_logger.error("Exception|ProductDemandAdmin|export_as_csv. Exception-{}".format(exc))

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=product-demands'+timezone.now().strftime('dd-mm-yy')+'.csv'
        return response
    export_as_csv.short_description = 'Download CSV of selected items'