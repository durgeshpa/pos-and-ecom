import csv
import io
import xlsxwriter

from django.contrib import admin
from .models import (
    Shop, ShopType, RetailerType, ParentRetailerMapping,
    ShopPhoto, ShopDocument, ShopInvoicePattern
)
from addresses.models import Address, State, City
from .forms import (ParentRetailerMappingForm, ShopParentRetailerMappingForm,
                    ShopForm, AddressForm, RequiredInlineFormSet,
                    AddressInlineFormSet)
from .views import StockAdjustmentView, stock_adjust_sample
from retailer_backend.admin import InputFilter
from django.db.models import Q
from django.utils.html import format_html
from import_export import resources
from django.http import HttpResponse
from admin_auto_filters.filters import AutocompleteFilter
from services.views import SalesReportFormView, SalesReport
from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter


class ShopResource(resources.ModelResource):
    class Meta:
        model = Shop
        exclude = ('created_at','modified_at')


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):

        cities_list = City.objects.values_list('city_name', flat=True)
        states_list = State.objects.values_list('state_name', flat=True)

        output = io.BytesIO()
        data = Address.objects.values_list(
            'shop_name_id', 'shop_name__shop_name',
            'shop_name__shop_type__shop_type',
            'shop_name__shop_owner__phone_number',
            'shop_name__status', 'id', 'nick_name', 'address_line1',
            'address_contact_name', 'address_contact_number', 'pincode',
            'state__state_name', 'city__city_name', 'address_type'
        ).filter(shop_name__in=queryset)

        data_rows = data.count()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        header_format = workbook.add_format({
            'border': 1,
            'bg_color': '#C6EFCE',
            'bold': True,
            'text_wrap': True,
            'valign': 'vcenter',
            'indent': 1,
        })

        # to set the width of column
        worksheet.set_column('A:A', 10)
        worksheet.set_column('B:B', 130)
        worksheet.set_column('C:C', 10)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 10)
        worksheet.set_column('F:F', 10)
        worksheet.set_column('G:G', 50)
        worksheet.set_column('H:H', 100)
        worksheet.set_column('I:I', 20)
        worksheet.set_column('J:J', 15)
        worksheet.set_column('K:K', 10)
        worksheet.set_column('L:L', 20)
        worksheet.set_column('M:M', 20)
        worksheet.set_column('N:N', 10)

        # to set the hieght of row 
        worksheet.set_row(0, 36)

        # column headings
        worksheet.write('A1', 'Shop ID', header_format)
        worksheet.write('B1', 'Shop Name', header_format)
        worksheet.write('C1', 'Shop Type', header_format)
        worksheet.write('D1', 'Shop Owner', header_format)
        worksheet.write('E1', 'Shop Activated', header_format)
        worksheet.write('F1', 'Address ID', header_format)
        worksheet.write('G1', 'Address Name', header_format)
        worksheet.write('H1', 'Address', header_format)
        worksheet.write('I1', "Contact Person", header_format)
        worksheet.write('J1', 'Contact Number', header_format)
        worksheet.write('K1', 'Pincode', header_format)
        worksheet.write('L1', 'State', header_format)
        worksheet.write('M1', 'City', header_format)
        worksheet.write('N1', 'Address Type', header_format)

        for row_num, columns in enumerate(data):
            for col_num, cell_data in enumerate(columns):
                worksheet.write(row_num+1, col_num, cell_data)

        worksheet.data_validation(
            'L2:L{}'.format(data_rows), 
            {'validate': 'list',
             'source': list(states_list)})

        worksheet.data_validation(
            'M2:M{}'.format(data_rows), 
            {'validate': 'list',
             'source': list(cities_list)})

        workbook.close()

        # Rewind the buffer.
        output.seek(0)

        # Set up the Http response.
        filename = 'Shops_sheet.xlsx'
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=%s' % filename

        return response

    export_as_csv.short_description = "Download CSV of Selected Shops"

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
            return queryset.filter(shop_type__shop_type__icontains=shop_type)

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

class ShopPhotosAdmin(admin.TabularInline):
    model = ShopPhoto
    fields = ( 'shop_photo','shop_photo_thumbnail', )
    readonly_fields = ('shop_photo_thumbnail',)
    formset = RequiredInlineFormSet
    extra = 2

class ShopDocumentsAdmin(admin.TabularInline):
    model = ShopDocument
    fields = ( 'shop_document_type','shop_document_number','shop_document_photo','shop_document_photo_thumbnail', )
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
    fields = ('nick_name','address_contact_name','address_contact_number','address_type','address_line1','state','city','pincode',)
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
        if value :
            return queryset.filter(retiler_mapping__parent__shop_name__icontains=value )
        return queryset

class ShopAdmin(admin.ModelAdmin, ExportCsvMixin):
    resource_class = ShopResource
    form = ShopForm
    actions = ["export_as_csv"]
    inlines = [
        ShopPhotosAdmin, ShopDocumentsAdmin,
        AddressAdmin, ShopInvoicePatternAdmin,ShopParentRetailerMapping
    ]
    list_display = ('shop_name', 'get_shop_shipping_address', 'get_shop_pin_code', 'get_shop_parent','shop_owner','shop_type','created_at','status', 'get_shop_city','shop_mapped_product','imei_no')
    filter_horizontal = ('related_users',)
    list_filter = (ServicePartnerFilter,ShopNameSearch,ShopTypeSearch,ShopRelatedUserSearch,ShopOwnerSearch,'status',('created_at', DateTimeRangeFilter))
    search_fields = ('shop_name', )

    class Media:
        css = {"all": ("admin/css/hide_admin_inline_object_name.css",)}

    def get_urls(self):
        from django.conf.urls import url
        urls = super(ShopAdmin, self).get_urls()
        urls = [
            url(
                r'^adjust-stock/(?P<shop_id>\w+)/$',
                self.admin_site.admin_view(StockAdjustmentView.as_view()),
                name="StockAdjustment"
            ),
            url(
                r'^adjust-stock-sample/(?P<shop_id>\w+)/$',
                self.admin_site.admin_view(stock_adjust_sample),
                name="ShopStocks"
            ),
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
        ] + urls
        return urls


    def get_queryset(self, request):
        qs = super(ShopAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.has_perm('shops.can_see_all_shops'):
            return qs
        return qs.filter(
            Q(related_users=request.user) |
            Q(shop_owner=request.user)
        )

    def shop_mapped_product(self, obj):
        if obj.shop_type.shop_type in ['gf','sp']:
            return format_html("<a href = '/admin/shops/shop-mapped/%s/product/' class ='addlink' > Product List</a>"% (obj.id))

    shop_mapped_product.short_description = 'Product List with Qty'


    # def get_shop_pending_amount(self, obj):
    #     pending_amount_gf = 0
    #     pending_amount_sp = 0
    #     pending_amount_total=0
    #     if obj.shop_type.shop_type == 'r':
    #         #if obj.retiler_mapping.filter(status=True).last().parent.shop_type.shop_type=='gf':
    #         orders_to_gf = obj.rtg_buyer_shop_order.all()
    #         for order in orders_to_gf:
    #             if order.rt_payment.last().payment_status == 'payment_done_approval_pending' or order.rt_payment.last().payment_status == 'cash_collected':
    #                 pending_amount_gf = pending_amount_gf + order.total_final_amount
    #         #return pending_amount
    #         #elif obj.retiler_mapping.filter(status=True).last().parent.shop_type.shop_type=='sp':
    #         orders_to_sp = obj.rt_buyer_shop_order.all()
    #         for order in orders_to_sp:
    #             if order.rt_payment.last().payment_status == 'payment_done_approval_pending' or order.rt_payment.last().payment_status == 'cash_collected':
    #                 pending_amount_sp = pending_amount_sp + order.total_final_amount
    #         #return pending_amount
    #         pending_amount_total = pending_amount_gf + pending_amount_sp
    #         return pending_amount_total
    #     elif obj.shop_type.shop_type == 'sp':
    #         carts_to_gf = obj.sp_shop_cart.all()
    #         total_pending_amount = 0
    #         for cart in carts_to_gf:
    #             for order in cart.sp_order_cart_mapping.all():
    #                 total_pending_amount = total_pending_amount + order.total_final_amount
    #         return total_pending_amount
    # get_shop_pending_amount.short_description = 'Shop Pending Amount'

class ParentFilter(AutocompleteFilter):
    title = 'Parent' # display title
    field_name = 'parent' # name of the foreign key field

class RetailerFilter(AutocompleteFilter):
    title = 'Retailer' # display title
    field_name = 'retailer' # name of the foreign key field

class ParentRetailerMappingAdmin(admin.ModelAdmin):
    form = ParentRetailerMappingForm
    list_filter = (ParentFilter,RetailerFilter,'status')

    class Media:
        pass

admin.site.register(ParentRetailerMapping,ParentRetailerMappingAdmin)
admin.site.register(ShopType)
admin.site.register(RetailerType)
admin.site.register(Shop,ShopAdmin)
