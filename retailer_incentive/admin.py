import csv
import datetime

from django.contrib import admin, messages
from io import StringIO

# Register your models here.
from django.db.models import Q
from django.http import HttpResponse
from nested_admin.nested import NestedTabularInline

from retailer_incentive.forms import SchemeCreationForm, SchemeSlabCreationForm, SchemeShopMappingCreationForm, \
    SlabInlineFormSet
from retailer_incentive.models import Scheme, SchemeSlab, SchemeShopMapping, IncentiveDashboardDetails
from retailer_incentive.utils import get_active_mappings
from retailer_incentive.views import get_scheme_shop_mapping_sample_csv, scheme_shop_mapping_csv_upload


class SchemeSlabAdmin(NestedTabularInline):
    model = SchemeSlab
    form = SchemeSlabCreationForm
    formset = SlabInlineFormSet
    list_display = ('min_value', 'max_value','discount_value', 'discount_type')
    min_num = 2

    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 0
        return 5

    def has_add_permission(self, request, obj):
        if obj:
            return False
        return True

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    """
    This class is used to get the Scheme data on admin
    """
    model = Scheme
    form = SchemeCreationForm
    list_display = ('name', 'start_date','end_date', 'is_active')
    inlines = [SchemeSlabAdmin, ]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


@admin.register(SchemeShopMapping)
class SchemeShopMappingAdmin(admin.ModelAdmin):
    """
    This class is used to get the Scheme Shop Mapping data on admin
    """
    model = SchemeShopMapping
    form = SchemeShopMappingCreationForm
    list_display = ('scheme_id', 'scheme_name', 'shop_name', 'priority', 'is_active', 'user',  'start_date', 'end_date',)
    actions = ['download_active_scheme_mappings', 'deactivate_selected_mappings', 'activate_selected_mappings']

    def scheme_id(self, obj):
        return obj.scheme_id

    def scheme_name(self, obj):
        return obj.scheme.name

    def shop_name(self, obj):
        return obj.shop

    def activate_selected_mappings(self, request, queryset):
        """
        Action method to activate selected scheme mappings
        Validations:
            Scheme should be active
            Scheme should not be expired
            total active scheme of the shop should not be more than two
        """
        to_be_deleted = []
        error_messages = []
        count = 0
        unique_mapping = set()
        for item in queryset:
            if not item.scheme.is_active:
                error_messages.append("Scheme Id - {} is not active"
                                      .format(item.scheme_id))
                to_be_deleted.append(item.id)
                continue
            if item.scheme.end_date < datetime.datetime.today().date():
                error_messages.append("Scheme Id - {} has already expired. scheme end date {}"
                                      .format(item.scheme_id, item.scheme.end_date))
                to_be_deleted.append(item.id)
                continue
            active_mappings = get_active_mappings(item.shop)
            if active_mappings.count() >= 2:
                error_messages.append("Shop Id - {} already has 2 active mappings".format(item.shop_id))
                to_be_deleted.append(item.id)
                continue
            existing_active_mapping = active_mappings.last()
            if existing_active_mapping and existing_active_mapping.priority == item.priority:
                error_messages.append("Shop Id - {} already has an active {} mappings"
                                      .format(item.shop_id, SchemeShopMapping.PRIORITY_CHOICE[item.priority]))
                to_be_deleted.append(item.id)
                continue
            if (item.shop_id, item.scheme_id, item.priority) in unique_mapping:
                to_be_deleted.append(item.id)
                continue
            unique_mapping.add((item.shop_id, item.scheme_id, item.priority))
            if not item.is_active:
                count = count + 1
        error_messages = set(error_messages)
        for message in error_messages:
            messages.error(request, message)
        queryset.filter(~Q(id__in=to_be_deleted)).update(is_active=True)
        messages.success(request, "{} mappings activated.".format(count))

    def deactivate_selected_mappings(self, request, queryset):
        """
        Action method to deactivate selected scheme mappings
        """
        count = queryset.filter(is_active=True).count()
        queryset.update(is_active=False)
        messages.success(request, "{} mappings de-activated.".format(count))


    def download_active_scheme_mappings(self, request, queryset):
        """
        Action method to download CSV file of all the active scheme mappings
        """
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(['Scheme ID', 'Scheme Name', 'Shop ID', 'Shop Name', 'Priority', 'Is Active',
                         'Created By', 'Created At'])

        queryset = queryset.filter(is_active=True, scheme__end_date__gte=datetime.datetime.today().date())
        error_messages = []
        for obj in queryset:
            try:
                writer.writerow([obj.scheme_id, obj.scheme.name, obj.shop_id,
                                 obj.shop, SchemeShopMapping.PRIORITY_CHOICE[obj.priority],
                                 obj.is_active, obj.user, obj.created_at])

            except Exception as e:
                error_messages.append(e)

        if len(error_messages) == 0:
            f.seek(0)
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=scheme-shop-mapping.csv'
            return response
        error_messages = set(error_messages)
        for message in error_messages:
            messages.error(request, message)

    def get_urls(self):
        """
        returns the added action urls for Scheme Shop Mapping
        """
        from django.conf.urls import url
        urls = super(SchemeShopMappingAdmin, self).get_urls()
        urls = [
                   url(
                       r'^scheme-shop-mapping-csv-sample/$',
                       self.admin_site.admin_view(get_scheme_shop_mapping_sample_csv),
                       name="scheme-shop-mapping-csv-sample"
                   ),
                   url(
                       r'^scheme-shop-mapping-csv-upload/$',
                       self.admin_site.admin_view(scheme_shop_mapping_csv_upload),
                       name="scheme-shop-mapping-csv-upload"
                   ),

               ] + urls
        return urls

    change_list_template = 'admin/retailer_incentive/scheme-shop-mapping-change-list.html'

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


@admin.register(IncentiveDashboardDetails)
class IncentiveDashboardDetails(admin.ModelAdmin):
    """
    This class is used to get the Previous Scheme Details
    """
    model = IncentiveDashboardDetails
    list_display = ('sales_manager', 'sales_executive','shop', 'mapped_scheme', 'scheme_priority', 'purchase_value',
                    'incentive_earned', 'start_date', 'end_date')

    class Media:
        pass


@admin.register(SchemeSlab)
class IncentiveDashboardDetails(admin.ModelAdmin):
    """
    This class is used to get the SchemeSlab
    """
    model = SchemeSlab
    list_display = ('scheme', 'min_value', 'max_value', 'discount_value', 'discount_type',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass
