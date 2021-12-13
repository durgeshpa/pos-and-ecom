# python imports
import csv
import logging
from io import StringIO
from import_export import resources
from admin_auto_filters.filters import AutocompleteFilter
from rangefilter.filter import DateTimeRangeFilter

# django imports
from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse

# app imports
from .models import (
    PosShopUserMapping, Shop, ShopType, RetailerType, ParentRetailerMapping,
    ShopPhoto, ShopDocument, ShopInvoicePattern, ShopUserMapping,
    ShopRequestBrand, SalesAppVersion, ShopTiming, FavouriteProduct, BeatPlanning, DayBeatPlanning, ExecutiveFeedback, ShopStatusLog)
from addresses.models import Address
from addresses.forms import AddressForm
from .forms import (ParentRetailerMappingForm, PosShopUserMappingForm, ShopParentRetailerMappingForm,
                    ShopForm, RequiredInlineFormSet, BeatPlanningAdminForm,
                    AddressInlineFormSet, ShopUserMappingForm, ShopTimingForm)

from .views import (StockAdjustmentView, bulk_shop_updation, ShopAutocomplete, UserAutocomplete, 
                    ShopUserMappingCsvView, ShopUserMappingCsvSample, ShopTimingAutocomplete
)
from pos.filters import PosShopAutocomplete
from retailer_backend.admin import InputFilter
from services.views import SalesReportFormView, SalesReport
from .utils import create_shops_excel
from retailer_backend.filters import ShopFilter, EmployeeFilter, ManagerFilter, UserFilter
from common.constants import DOWNLOAD_BEAT_PLAN_CSV, FIFTY

logger = logging.getLogger('shop-admin')


class ShopResource(resources.ModelResource):
    class Meta:
        model = Shop
        exclude = ('created_at', 'modified_at')


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        return create_shops_excel(queryset)

    export_as_csv.short_description = "Download CSV of Selected Shops"

    def export_as_csv_fav_product(self, request, queryset):
        meta = self.model._meta
        exclude_fields = ['modified_at']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])
        return response

    export_as_csv_fav_product.short_description = "Download CSV of Selected Objects"


class ShopNameSearch(InputFilter):
    parameter_name = 'shop_name'
    title = 'Shop Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            shop_name = self.value()
            if shop_name is None:
                return
            return queryset.filter(shop_name__icontains=shop_name)


class ShopTypeSearch(InputFilter):
    parameter_name = 'shop_type'
    title = 'Shop Type'

    def queryset(self, request, queryset):
        if self.value() is not None:
            shop_type = self.value()
            if shop_type is None:
                return
            return queryset.filter(shop_type__shop_type=shop_type)


class ShopRelatedUserSearch(InputFilter):
    parameter_name = 'related_users'
    title = 'Related User'

    def queryset(self, request, queryset):
        if self.value() is not None:
            related_user_number = self.value()
            if related_user_number is None:
                return
            return queryset.filter(related_users__phone_number__icontains=related_user_number)


class ShopOwnerSearch(InputFilter):
    parameter_name = 'shop_owner'
    title = 'Shop Owner'

    def queryset(self, request, queryset):
        if self.value() is not None:
            shop_owner_number = self.value()
            if shop_owner_number is None:
                return
            return queryset.filter(shop_owner__phone_number__icontains=shop_owner_number)


class ShopSearchByOwner(InputFilter):
    parameter_name = 'shop_owner'
    title = 'Shop Owner'

    def queryset(self, request, queryset):
        if self.value() is not None:
            shop_owner_number = self.value()
            if shop_owner_number is None:
                return
            return queryset.filter(shop__shop_owner__phone_number__icontains=shop_owner_number)


class BuyerShopFilter(AutocompleteFilter):
    title = 'Shop'  # display title
    field_name = 'buyer_shop'  # name of the foreign key field


class ProductFilter(AutocompleteFilter):
    title = 'Product'  # display title
    field_name = 'product'  # name of the foreign key field


class FavouriteProductAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv_fav_product"]
    list_display = ('buyer_shop', 'product', 'created_at', 'get_product_brand')
    raw_id_fields = ['buyer_shop', 'product']
    list_filter = (BuyerShopFilter, ProductFilter)

    def get_product_brand(self, obj):
        return obj.product.product_brand

    get_product_brand.short_description = 'Brand Name'  # Renames column head

    class Media:
        pass


class ShopPhotosAdmin(admin.TabularInline):
    model = ShopPhoto
    fields = ('shop_photo', 'shop_photo_thumbnail',)
    readonly_fields = ('shop_photo_thumbnail',)
    formset = RequiredInlineFormSet
    extra = 2


class ShopDocumentsAdmin(admin.TabularInline):
    model = ShopDocument
    fields = ('shop_document_type', 'shop_document_number', 'shop_document_photo', 'shop_document_photo_thumbnail',)
    readonly_fields = ('shop_document_photo_thumbnail',)
    formset = RequiredInlineFormSet
    extra = 2


class ShopInvoicePatternAdmin(admin.TabularInline):
    model = ShopInvoicePattern
    extra = 1
    fields = ('pattern', 'status')


class AddressAdmin(admin.TabularInline):
    model = Address
    formset = AddressInlineFormSet
    form = AddressForm
    fields = ('nick_name', 'address_contact_name', 'address_contact_number',
              'address_type', 'address_line1', 'state', 'city', 'pincode_link')
    extra = 2


class ShopParentRetailerMapping(admin.TabularInline):
    model = ParentRetailerMapping
    form = ShopParentRetailerMappingForm
    fields = ('parent',)
    fk_name = 'retailer'
    extra = 1
    max_num = 1


class ServicePartnerFilter(InputFilter):
    title = 'Service Partner'
    parameter_name = 'service partner'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(retiler_mapping__parent__shop_name__icontains=value)
        return queryset


class ShopCityFilter(InputFilter):
    title = 'City'
    parameter_name = 'city'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(shop_name_address_mapping__city__city_name__icontains=value,
                                   shop_name_address_mapping__address_type='shipping')
        return queryset


class ShopStatusAdmin(admin.TabularInline):
    model = ShopStatusLog
    fields = ('reason', 'user', 'created_at')
    readonly_fields = ('reason', 'user', 'created_at')
    extra = 0

    def created_at(self, obj):
        return obj.changed_at

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ShopAdmin(admin.ModelAdmin, ExportCsvMixin):
    change_list_template = 'admin/shops/shop/change_list.html'
    change_form_template = 'admin/shops/shop/change_form.html'
    resource_class = ShopResource
    form = ShopForm
    fields = ['shop_name', 'shop_owner', 'shop_type', 'status', 'pos_enabled', 'online_inventory_enabled',
              'approval_status']
    actions = ["export_as_csv", "disable_shop"]
    inlines = [
        ShopPhotosAdmin, ShopDocumentsAdmin,
        AddressAdmin, ShopInvoicePatternAdmin, ShopParentRetailerMapping, ShopStatusAdmin
    ]
    list_display = (
        'shop_name', 'get_shop_shipping_address', 'get_shop_pin_code', 'get_shop_parent',
        'shop_owner', 'shop_type', 'created_at', 'status', 'get_shop_city', 'approval_status',
        'shop_mapped_product', 'imei_no', 'warehouse_code'
    )
    filter_horizontal = ('related_users',)
    list_filter = (ShopCityFilter, ServicePartnerFilter, ShopNameSearch, ShopTypeSearch, ShopRelatedUserSearch,
                   ShopOwnerSearch, 'approval_status', 'status', ('created_at', DateTimeRangeFilter))
    search_fields = ('shop_name', )
    list_per_page = 50

    class Media:
        css = {"all": ("admin/css/hide_admin_inline_object_name.css",)}

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.shop_type.shop_type == 'f':
            return self.readonly_fields + ('shop_code', 'warehouse_code')
        return self.readonly_fields

    def get_urls(self):
        from django.conf.urls import url
        urls = super(ShopAdmin, self).get_urls()
        urls = [
                   url(
                       r'^adjust-stock/(?P<shop_id>\w+)/$',
                       self.admin_site.admin_view(StockAdjustmentView.as_view()),
                       name="StockAdjustment"
                   ),
                   # url(
                   #     r'^adjust-stock-sample/(?P<shop_id>\w+)/$',
                   #     self.admin_site.admin_view(stock_adjust_sample),
                   #     name="ShopStocks"
                   # ),
                   url(
                       r'^shop-sales-report/$',
                       self.admin_site.admin_view(SalesReport.as_view()),
                       name="shop-sales-report"
                   ),
                   url(
                       r'^shop-sales-form/$',
                       self.admin_site.admin_view(SalesReportFormView.as_view()),
                       name="shop-sales-form"
                   ),
                   url(
                       r'^shop-timing-autocomplete/$',
                       self.admin_site.admin_view(ShopTimingAutocomplete.as_view()),
                       name="shop-timing-autocomplete"
                   ),
                   url(
                       r'^bulk-shop-updation/$',
                       self.admin_site.admin_view(bulk_shop_updation),
                       name="bulk-shop-updation"
                   ),
                   url(
                       r'^shop-autocomplete/$',
                       self.admin_site.admin_view(ShopAutocomplete.as_view()),
                       name="shop-autocomplete"
                   ),
                   url(
                       r'^user-autocomplete/$',
                       self.admin_site.admin_view(UserAutocomplete.as_view()),
                       name="user-autocomplete"
                   ),
                    url(
                        r'^adjust-stock/(?P<shop_id>\w+)/$',
                        self.admin_site.admin_view(StockAdjustmentView.as_view()),
                        name="StockAdjustment"
                    ),
                    # url(
                    #     r'^shop-sales-report/$',
                    #     self.admin_site.admin_view(SalesReport.as_view()),
                    #     name="shop-sales-report"
                    # ),
                    # url(
                    #     r'^shop-sales-form/$',
                    #     self.admin_site.admin_view(SalesReportFormView.as_view()),
                    #     name="shop-sales-form"
                    # ),
                    url(
                        r'^shop-timing-autocomplete/$',
                        self.admin_site.admin_view(ShopTimingAutocomplete.as_view()),
                        name="shop-timing-autocomplete"
                    ),
                    url(
                        r'^bulk-shop-updation/$',
                        self.admin_site.admin_view(bulk_shop_updation),
                        name="bulk-shop-updation"
                    ),
                    url(
                        r'^shop-autocomplete/$',
                        self.admin_site.admin_view(ShopAutocomplete.as_view()),
                        name="shop-autocomplete"
                    ),
                    url(
                        r'^user-autocomplete/$',
                        self.admin_site.admin_view(UserAutocomplete.as_view()),
                        name="user-autocomplete"
                    ),

               ] + urls
        return urls

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.fields + ['shop_location','latitude', 'longitude', 'related_users', 'shop_code', 'shop_code_bulk', 'shop_code_discounted',
                                  'warehouse_code', 'created_by', 'dynamic_beat']
        elif request.user.has_perm('shops.hide_related_users'):
            return self.fields
        return self.fields + ['shop_location','latitude', 'longitude', 'related_users', 'shop_code', 'shop_code_bulk', 'shop_code_discounted', 'warehouse_code',
                              'created_by', 'dynamic_beat']

    def disable_shop(modeladmin, request, queryset):
        queryset.update(approval_status=0)
        for shop in queryset:
            ShopStatusLog.objects.create(reason='Disapproved', user=request.user, shop=shop)

    def shop_mapped_product(self, obj):
        if obj.shop_type.shop_type in ['gf', 'sp', 'f']:
            return format_html(
                "<a href = '/admin/shops/shop-mapped/%s/product/' class ='addlink' > Product List</a>" % (obj.id))

    shop_mapped_product.short_description = 'Product List with Qty'
    disable_shop.short_description = "Disapprove shops"

    def get_shop_city(self, obj):
        if obj.shop_name_address_mapping.exists():
            return obj.shop_name_address_mapping.last().city

    get_shop_city.short_description = 'Shop City'

    def get_shop_parent(self, obj):
        if obj.retiler_mapping.exists():
            return obj.retiler_mapping.last().parent

    def save_model(self, request, obj, form, change):
        if 'approval_status' in form.changed_data:
            approval_status = form.cleaned_data['approval_status']
            if approval_status == 0:
                reason = 'Disapproved'
            elif approval_status == 1:
                reason = 'Awaiting Approval'
            else:
                reason = 'Approved'
            ShopStatusLog.objects.create(reason = reason, user = request.user, shop = obj)
        return super(ShopAdmin, self).save_model(request, obj, form, change)

    get_shop_parent.short_description = 'Parent Shop'


class ParentFilter(AutocompleteFilter):
    title = 'Parent'  # display title
    field_name = 'parent'  # name of the foreign key field


class RetailerFilter(AutocompleteFilter):
    title = 'Retailer'  # display title
    field_name = 'retailer'  # name of the foreign key field


class ParentRetailerMappingAdmin(admin.ModelAdmin):
    form = ParentRetailerMappingForm
    list_filter = (ParentFilter, RetailerFilter, 'status')

    class Media:
        pass


class ShopTimingAdmin(admin.ModelAdmin):
    list_display = ('shop', 'open_timing', 'closing_timing', 'break_start_times', 'break_end_times', 'off_day')
    list_filter = (ShopFilter,)
    form = ShopTimingForm

    def break_start_times(self, obj):
        if str(obj.break_start_time) == '00:00:00':
            return "-"
        return obj.break_start_time

    break_start_times.short_description = 'break start time'

    def break_end_times(self, obj):
        if str(obj.break_end_time) == '00:00:00':
            return "-"
        return obj.break_end_time

    break_end_times.short_description = 'break end time'

    class Media:
        pass


class ShopFilter(AutocompleteFilter):
    title = 'Shop'  # display title
    field_name = 'shop'  # name of the foreign key field


class BrandNameFilter(InputFilter):
    title = 'Brand Name'  # display title
    parameter_name = 'brand_name'  # name of the foreign key field

    def queryset(self, request, queryset):
        if self.value() is not None:
            brand_name = self.value()
            return queryset.filter(brand_name__icontains=brand_name)


class ProductSKUFilter(InputFilter):
    title = 'Product SKU'  # display title
    parameter_name = 'product_sku'  # name of the foreign key field

    def queryset(self, request, queryset):
        if self.value() is not None:
            product_sku = self.value()
            return queryset.filter(product_sku__icontains=product_sku)


class ExportCsvMixin:
    def export_as_csv_shop_request_brand(self, request, queryset):
        meta = self.model._meta
        list_display = ('shop', 'brand_name', 'product_sku', 'request_count', 'created_at')
        field_names = [field.name for field in meta.fields if field.name in list_display]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in list_display])
        return response

    export_as_csv_shop_request_brand.short_description = "Download CSV of Shop Request Brand"


class ShopRequestBrandAdmin(ExportCsvMixin, admin.ModelAdmin):
    actions = ['export_as_csv_shop_request_brand']
    list_display = ('shop', 'brand_name', 'product_sku', 'request_count','created_at',)
    list_filter = (ShopFilter, ShopSearchByOwner, ProductSKUFilter, BrandNameFilter, ('created_at', DateTimeRangeFilter))
    raw_id_fields = ('shop',)

    class Media:
        pass


class ShopUserMappingAdmin(admin.ModelAdmin):
    form = ShopUserMappingForm
    list_display = ('shop', 'get_manager', 'employee', 'employee_group', 'created_at', 'status')
    list_filter = [ShopFilter, ManagerFilter, EmployeeFilter, 'employee_group', 'status', ('created_at', DateTimeRangeFilter), ]
    search_fields = ('shop__shop_name', 'employee_group__permissions__codename', 'employee__phone_number')

    def get_manager(self, obj):
        if obj.manager:
            return str(obj.manager) + " - " + str(obj.manager.employee_group)
        return obj.manager
    get_manager.short_description = 'Manager'
    get_manager.admin_order_field = 'manager__employee_group'

    def get_urls(self):
        from django.conf.urls import url
        urls = super(ShopUserMappingAdmin, self).get_urls()
        urls = [
            url(
               r'^upload/csv/$',
               self.admin_site.admin_view(ShopUserMappingCsvView.as_view()),
               name="shop-user-upload-csv"
            ),
           url(
               r'^upload/csv/sample$',
               self.admin_site.admin_view(ShopUserMappingCsvSample.as_view()),
               name="shop-user-upload-csv-sample"),

               ] + urls
        return urls

    class Media:
        pass

    def has_change_permission(self, request, obj=None):
        pass

class PosShopUserMappingAdmin(admin.ModelAdmin):
    form = PosShopUserMappingForm
    list_display = ('shop', 'user', 'user_type', 'is_delivery_person', 'created_at', 'modified_at', 'status')
    list_filter = [ShopFilter, UserFilter, 'status', ('created_at', DateTimeRangeFilter), ]
    search_fields = ('shop__shop_name', 'user__phone_number')

    class Media:
        pass

    # def has_change_permission(self, request, obj=None):
    #     pass

    def get_urls(self):
        from django.conf.urls import url
        urls = super(PosShopUserMappingAdmin, self).get_urls()
        urls = [
                   url(
                       r'^user-autocomplete/$',
                       self.admin_site.admin_view(UserAutocomplete.as_view()),
                       name="user-autocomplete"
                   ),
                    url(
                        r'^pos-shop-autocomplete/$',
                        self.admin_site.admin_view(PosShopAutocomplete.as_view()),
                        name="pos-shop-autocomplete"
                    ),

               ] + urls
        return urls

    

class SalesAppVersionAdmin(admin.ModelAdmin):
    list_display = ('app_version', 'update_recommended', 'force_update_required', 'created_at', 'modified_at')


class BeatPlanningAdmin(admin.ModelAdmin):
    """
    This class is used to view the Beat Planning Admin Form
    """
    form = BeatPlanningAdminForm
    list_display = ('manager', 'executive', 'created_at', 'status')
    list_display_links = None
    actions = ['download_bulk_beat_plan_csv']
    list_per_page = FIFTY
    search_fields = ('executive__phone_number', 'manager__phone_number')

    def render_change_form(self, request, context, *args, **kwargs):
        """

        :param request: request
        :param context: context processor
        :param args: non keyword argument
        :param kwargs: keyword argument
        :return: Beat Planning Admin form
        """
        self.change_form_template = 'admin/shops/shop_beat_plan/change_form.html'
        return super(BeatPlanningAdmin, self).render_change_form(request, context, *args, **kwargs)

    def get_form(self, request, *args, **kwargs):
        """

        :param request: request
        :param args: non keyword argument
        :param kwargs: keyword argument
        :return: form
        """
        form = super(BeatPlanningAdmin, self).get_form(request, *args, **kwargs)
        form.current_user = request.user
        return form

    def download_bulk_beat_plan_csv(self, request, queryset):
        """

        :param request: get request
        :param queryset: Beat plan queryset
        :return: csv file
        """
        f = StringIO()
        writer = csv.writer(f)
        # set the header name
        writer.writerow(["Sales Executive (Number - Name)", "Sales Manager (Number - Name)", "Shop ID ",
                         "Contact Number", "Address", "Pin Code", "Priority", "Date (dd/mm/yyyy)", "Status"])

        for query in queryset:
            # get day beat plan queryset
            day_beat_plan_query_set = DayBeatPlanning.objects.filter(beat_plan=query)
            # get object from queryset
            for plan_obj in day_beat_plan_query_set:
                # write data into csv file
                address = plan_obj.shop.shop_name_address_mapping.last()
                writer.writerow([plan_obj.beat_plan.executive, plan_obj.beat_plan.manager,
                                 plan_obj.shop_id, address.address_contact_number,
                                 address.address_line1,
                                 address.pincode,
                                 plan_obj.shop_category,
                                 plan_obj.beat_plan_date.strftime("%d/%m/%y"),
                                 'Active' if plan_obj.beat_plan.status is True else 'Inactive'])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=executive_beat_plan.csv'
        return response

    # download bulk invoice short description
    download_bulk_beat_plan_csv.short_description = DOWNLOAD_BEAT_PLAN_CSV

    # Media file
    class Media:
        js = ('admin/js/beat_plan_list.js', )

    # def has_delete_permission(self, request, obj=None):
    #     return False

    def get_queryset(self, request):
        """

        :param request: get request
        :return: queryset
        """
        qs = super(BeatPlanningAdmin, self).get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(manager=request.user)
        return qs


class ShopTypeAdmin(admin.ModelAdmin):
    fields = ('shop_type', 'shop_sub_type', 'shop_min_amount', 'status')


class ExecutiveFeedbackAdmin(admin.ModelAdmin):
    fields = ('day_beat_plan', 'executive_feedback', 'feedback_date', 'latitude',
              'longitude', 'is_valid', 'distance_in_km')
    list_display = ('id', 'day_beat_plan_id', 'executive_feedback', 'feedback_date')
    readonly_fields = ('day_beat_plan', 'executive_feedback', 'feedback_date', 'latitude',
              'longitude', 'is_valid', 'distance_in_km')

    def day_beat_plan_id(self, obj):
        return obj.day_beat_plan.id


admin.site.register(ParentRetailerMapping, ParentRetailerMappingAdmin)
admin.site.register(ShopType, ShopTypeAdmin)
admin.site.register(RetailerType)
admin.site.register(Shop, ShopAdmin)
admin.site.register(FavouriteProduct, FavouriteProductAdmin)
admin.site.register(ShopRequestBrand, ShopRequestBrandAdmin)
admin.site.register(ShopUserMapping, ShopUserMappingAdmin)
admin.site.register(SalesAppVersion, SalesAppVersionAdmin)
admin.site.register(ShopTiming, ShopTimingAdmin)
admin.site.register(BeatPlanning, BeatPlanningAdmin)
admin.site.register(PosShopUserMapping, PosShopUserMappingAdmin)
admin.site.register(ExecutiveFeedback, ExecutiveFeedbackAdmin)
