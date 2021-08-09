import logging
from io import StringIO

from admin_auto_filters.filters import AutocompleteFilter
from daterange_filter.filter import DateRangeFilter
from django_filters import BooleanFilter
from nested_admin.nested import NestedTabularInline
from rangefilter.filter import DateTimeRangeFilter
from django_admin_listfilter_dropdown.filters import ChoiceDropdownFilter
from django.contrib import admin, messages
from django.contrib.admin import TabularInline, SimpleListFilter
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponse
from django.conf.urls import url
from django.urls import reverse
from django.utils.html import format_html

from retailer_backend.admin import InputFilter, SelectInputFilter
from retailer_backend.filters import CityFilter, ProductCategoryFilter

from .forms import (ProductCappingForm, ProductForm, ProductPriceAddPerm,
                    ProductPriceChangePerm, ProductPriceNewForm, ProductHSNForm,
                    ProductVendorMappingForm, BulkProductTaxUpdateForm, BulkUploadForGSTChangeForm,
                    RepackagingForm, ParentProductForm, ProductSourceMappingForm, DestinationRepackagingCostMappingForm,
                    ProductSourceMappingFormSet, DestinationRepackagingCostMappingFormSet, ProductImageFormSet,
                    SlabInlineFormSet, PriceSlabForm, ProductPriceSlabForm, ProductPriceSlabCreationForm,
                    ProductPackingMappingForm, ProductPackingMappingFormSet, DiscountedProductForm)

from .models import *
from .resources import (ColorResource, FlavorResource, FragranceResource,
                        PackageSizeResource, ProductPriceResource,
                        ProductResource, SizeResource, TaxResource,
                        WeightResource, ParentProductResource)
from .views import (CityAutocomplete, MultiPhotoUploadView,
                    PincodeAutocomplete, ProductAutocomplete,
                    ProductCategoryAutocomplete, ProductCategoryMapping,
                    ProductPriceAutocomplete, ProductPriceUpload,
                    ProductsUploadSample, RetailerAutocomplete,
                    SellerShopAutocomplete, SpSrProductPrice,
                    VendorAutocomplete, cart_products_mapping,
                    download_all_products, export, gf_product_price,
                    load_brands, load_cities, load_gf, load_sp_sr,
                    product_category_mapping_sample, products_csv_upload_view,
                    products_export_for_vendor, products_filter_view,
                    products_price_filter_view, products_vendor_mapping,
                    ProductShopAutocomplete, SourceRepackageDetail,
                    DestinationProductAutocomplete,
                    parent_product_upload, ParentProductsDownloadSampleCSV,
                    product_csv_upload, ChildProductsDownloadSampleCSV,
                    ParentProductAutocomplete, ParentProductsAutocompleteView,
                    ParentProductMultiPhotoUploadView, cart_product_list_status, upload_master_data_view,
                    UploadMasterDataSampleExcelFile, set_child_with_parent_sample_excel_file,
                    set_inactive_status_sample_excel_file, set_child_data_sample_excel_file,
                    set_parent_data_sample_excel_file,
                    category_sub_category_mapping_sample_excel_file, brand_sub_brand_mapping_sample_excel_file,
                    ParentProductMultiPhotoUploadView, cart_product_list_status,
                    bulk_product_vendor_csv_upload_view, all_product_mapped_to_vendor,
                    get_slab_product_price_sample_csv, slab_product_price_csv_upload, PackingMaterialCheck,
                    packing_material_inventory, packing_material_inventory_download,
                    packing_material_inventory_sample_upload, HSNAutocomplete)

from .filters import BulkTaxUpdatedBySearch, SourceSKUSearch, SourceSKUName, DestinationSKUSearch, DestinationSKUName
from wms.models import Out, WarehouseInventory, BinInventory

info_logger = logging.getLogger('file-info')

class ProductFilter(AutocompleteFilter):
    title = 'Product Name' # display title
    field_name = 'product' # name of the foreign key field
    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(
                Q(product_id=self.value())
            )


class ShopFilter(AutocompleteFilter):
    title = 'Seller Shop' # display title
    field_name = 'seller_shop' # name of the foreign key field
    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(
                Q(seller_shop_id=self.value())
            )

class ProductImageMainAdmin(admin.ModelAdmin):
    readonly_fields = ['image_thumbnail']
    search_fields = ['image', 'image_name']
    list_display = ('product','image', 'image_name')
    list_filter = [ProductFilter,]

    class Media:
        pass

class CategorySearch(InputFilter):
    parameter_name = 'category'
    title = 'Category'

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(
                Q(parent_product__parent_product_pro_category__category__category_name__icontains=self.value())
            )

class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        exclude_fields = ['created_at', 'modified_at']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]
        field_names.extend(['is_ptr_applicable', 'ptr_type','ptr_percent'])
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        if self.model._meta.db_table=='products_product':
            field_names_temp = field_names.copy()
            cost_params = ['raw_material', 'wastage', 'fumigation', 'label_printing', 'packing_labour',
                           'primary_pm_cost', 'secondary_pm_cost', 'final_fg_cost', 'conversion_cost']
            add_fields = ['product_brand', 'product_category', 'image', 'source skus', 'packing_sku',
                          'packing_sku_weight_per_unit_sku'] + cost_params
            for field_name in add_fields:
                field_names_temp.append(field_name)
            writer.writerow(field_names_temp)
        else:
            writer.writerow(field_names)
        for obj in queryset:
            items= [getattr(obj, field) for field in field_names]
            if self.model._meta.db_table == 'products_product':
                items.append(obj.product_brand)
                items.append(self.product_category(obj))
                if obj.use_parent_image and obj.parent_product.parent_product_pro_image.last():
                    items.append(obj.parent_product.parent_product_pro_image.last().image.url)
                elif obj.product_pro_image.last():
                    items.append(obj.product_pro_image.last().image.url)
                else:
                    items.append('-')
                if obj.repackaging_type == 'destination':
                    source_skus = [str(psm.source_sku) for psm in ProductSourceMapping.objects.filter(
                        destination_sku_id=obj.id, status=True)]
                    items.append("\n".join(source_skus))
                    packing_sku = ProductPackingMapping.objects.filter(sku_id=obj.id).last()
                    items.append(str(packing_sku) if packing_sku else '-')
                    items.append(str(packing_sku.packing_sku_weight_per_unit_sku) if packing_sku else '-')
                    cost_obj = DestinationRepackagingCostMapping.objects.filter(destination_id=obj.id).last()
                    for param in cost_params:
                        items.append(str(getattr(cost_obj, param)))
                else:
                    items.append('-')
                    for param in cost_params:
                        items.append('-')
            row = writer.writerow(items)
        return response
    export_as_csv.short_description = "Download CSV of Selected Objects"


class BrandFilter(AutocompleteFilter):
    title = 'Brand'  # display title
    field_name = 'product_brand'  # name of the foreign key field


class ChildParentIDFilter(AutocompleteFilter):
    title = 'Parent Product (ID or Name)'  # display title
    field_name = 'parent_product'  # name of the foreign key field

    def get_autocomplete_url(self, request, model_admin):
        return reverse('admin:parent-product-list-filter-autocomplete')


class ParentBrandFilter(AutocompleteFilter):
    title = 'Brand'  # display title
    field_name = 'parent_brand'  # name of the foreign key field


class CategoryFilter(AutocompleteFilter):
    title = 'Category'  # display title
    field_name = 'category_name'  # name of the foreign key field


class ParentCategorySearch(admin.SimpleListFilter):
    parameter_name = 'category'
    title = 'Category'

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(
                Q(parent_product_pro_category__category__category_name__icontains=self.value())
            )

    template = 'admin/parent_category_select_input_filter.html'

    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        # Grab only the "all" option.
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice


class ProductBrandSearch(admin.SimpleListFilter):
    parameter_name = 'brand'
    title = 'Brand'

    def queryset(self, request, queryset):
        if self.value() is not None:
            # return queryset.filter(
            #     Q(parent_brand_product__brand__brand_name__icontains=self.value())
            # )
            return queryset.filter(
                Q(parent_product__parent_brand__brand_name__icontains=self.value())
            )

    template = 'admin/product_brand_select_input_filter.html'

    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        # Grab only the "all" option.
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice


class ParentIDFilter(InputFilter):
    title = 'Parent ID'
    parameter_name = 'parent_id'

    def queryset(self, request, queryset):
        if self.value() is not None:
            parent_id = self.value()
            if parent_id is None:
                return
            return queryset.filter(
                Q(parent_id__icontains=parent_id)
            )


class VendorFilter(AutocompleteFilter):
    title = 'Vendor Name' # display title
    field_name = 'vendor' # name of the foreign key field

class ExportProductVendor:
    def export_as_csv_product_vendormapping(self, request, queryset):
        meta = self.model._meta
        list_display = ('vendor', 'product', 'product_price', 'product_mrp','case_size','created_at','status')
        field_names = [field.name for field in meta.fields if field.name in list_display]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in list_display])
        return response
    export_as_csv_product_vendormapping.short_description = "Download CSV of selected Productvendormapping"

class ProductVendorMappingAdmin(admin.ModelAdmin, ExportProductVendor):
  
    actions = ["export_as_csv_product_vendormapping",]
    fields = ('vendor', 'product', 'product_price','product_price_pack','product_mrp','case_size', 'is_default')

    list_display = ('vendor', 'product','product_price','product_price_pack', 'mrp','case_size','created_at','status','product_status')
    list_filter = [VendorFilter,ProductFilter,'product__status','status']
    form = ProductVendorMappingForm
    readonly_fields = ['brand_to_gram_price_unit',]
    change_list_template = 'admin/products/bulk_product_vendor_mapping_change_list.html'
    def get_urls(self):
        from django.conf.urls import url
        urls = super(ProductVendorMappingAdmin, self).get_urls()
        urls = [
            url(
                r'^vendor-autocomplete/$',
                self.admin_site.admin_view(VendorAutocomplete.as_view()),
                name="vendor-autocomplete"
            ),
            url(
                r'^product-vendor-csv-upload/$',
                self.admin_site.admin_view(bulk_product_vendor_csv_upload_view),
                name="product-vendor-csv-upload"
            ),
        ] + urls
        return urls

    def product_status(self, obj):
        return obj.product.status == 'active'

    def mrp(self, obj):
        return obj.product.product_mrp

    product_status.boolean = True

    class Media:
        js = (
            '//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',  # jquery
            'admin/js/product_vendor_mapping_form.js'
        )

class SizeAdmin(admin.ModelAdmin,  ExportCsvMixin):
    resource_class = SizeResource
    actions = ["export_as_csv"]
    prepopulated_fields = {'size_name': ('size_value', 'size_unit')}
    search_fields = ['size_name']


class FragranceAdmin(admin.ModelAdmin, ExportCsvMixin):
    resource_class = FragranceResource
    actions = ["export_as_csv"]
    search_fields = ['fragrance_name']


class FlavorAdmin(admin.ModelAdmin, ExportCsvMixin):
    resource_class = FlavorResource
    actions = ["export_as_csv"]
    search_fields = ['flavor_name']


class ColorAdmin(admin.ModelAdmin, ExportCsvMixin):
    resource_class = ColorResource
    actions = ["export_as_csv"]
    search_fields = ['color_name']


class PackageSizeAdmin(admin.ModelAdmin, ExportCsvMixin):
    resource_class = PackageSizeResource
    actions = ["export_as_csv"]
    prepopulated_fields = {
        'pack_size_name': ('pack_size_value', 'pack_size_unit')
    }
    search_fields = ['pack_size_name']


class WeightAdmin(admin.ModelAdmin, ExportCsvMixin):
    resource_class = WeightResource
    actions = ["export_as_csv"]
    prepopulated_fields = {'weight_name': ('weight_value', 'weight_unit')}
    search_fields = ['weight_name']


class TaxAdmin(admin.ModelAdmin, ExportCsvMixin):
    resource_class = TaxResource
    actions = ["export_as_csv"]
    search_fields = ['tax_name']

class ProductSearch(InputFilter):
    parameter_name = 'product_sku'
    title = 'Product (Id or SKU)'

    def queryset(self, request, queryset):
        if self.value() is not None:
            product_sku = self.value()
            if product_sku is None:
                return
            return queryset.filter(
                Q(product_sku__icontains=product_sku)
            )


class ProductEanSearch(InputFilter):
    parameter_name = 'product_ean_search'
    title = 'Product Ean Code'

    def queryset(self, request, queryset):
        if self.value() is not None:
            product_ean = self.value()
            if product_ean is None:
                return
            return queryset.filter(
                Q(product_ean_code__icontains=product_ean)
            )


class ProductSKUSearch(InputFilter):
    parameter_name = 'product_sku'
    title = 'Product SKU'

    def queryset(self, request, queryset):
        if self.value() is not None:
            product_sku = self.value()
            if product_sku is None:
                return
            return queryset.filter(
                Q(product__product_sku__icontains=product_sku)
            )



class ProductOptionAdmin(admin.TabularInline):
    model = ProductOption
    extra = 1
    autocomplete_fields = [
        'size', 'weight', 'color', 'flavor', 'fragrance', 'package_size'
    ]


class AtLeastOneFormSet(BaseInlineFormSet):
    def clean(self):
        super(AtLeastOneFormSet, self).clean()
        non_empty_forms = 0
        for form in self:
            if form.cleaned_data:
                non_empty_forms += 1
        if non_empty_forms - len(self.deleted_forms) < 1:
            raise ValidationError("Please fill at least one form.")


class RequiredInlineFormSet(BaseInlineFormSet):
    def _construct_form(self, i, **kwargs):
        form = super(RequiredInlineFormSet, self)._construct_form(i, **kwargs)
        if i < 1:
            form.empty_permitted = False
        return form


class ProductCategoryAdmin(TabularInline):
    model = ProductCategory
    autocomplete_fields = ['category']
    formset = RequiredInlineFormSet  # or AtLeastOneFormSet


class ProductImageAdmin(admin.TabularInline):
    formset = ProductImageFormSet
    model = ProductImage

class ProductTaxInlineFormSet(BaseInlineFormSet):
   def clean(self):
      super(ProductTaxInlineFormSet, self).clean()
      tax_list_type=[]
      for form in self.forms:
          if form.is_valid() and form.cleaned_data.get('tax'):
              if form.cleaned_data.get('tax').tax_type in tax_list_type:
                  raise ValidationError('{} type tax can be filled only once'.format(form.cleaned_data.get('tax').tax_type))
              tax_list_type.append(form.cleaned_data.get('tax').tax_type)
      if 'gst' not in tax_list_type:
          raise ValidationError('Please fill the GST tax value')

class ProductTaxMappingAdmin(admin.TabularInline):
    model = ProductTaxMapping
    extra = 6
    formset=ProductTaxInlineFormSet
    max_num = 6
    autocomplete_fields = ['tax']

    class Media:
        pass

class ParentProductCategoryAdmin(TabularInline):
    model = ParentProductCategory
    autocomplete_fields = ['category']
    formset = RequiredInlineFormSet  # or AtLeastOneFormSet


def deactivate_selected_products(modeladmin, request, queryset):
    # parent_tax_script_qa4()
    queryset.update(status=False)
    for record in queryset:
        Product.objects.filter(parent_product__parent_id=record.parent_id).update(status='deactivated')

deactivate_selected_products.short_description = "Deactivate Selected Products"

def parent_tax_script_qa4():
    pr = ParentProductTaxMapping.objects.all().values_list('parent_product', flat=True).distinct('parent_product')
    parents = ParentProduct.objects.exclude(id__in=pr)
    for parent in parents:
        if parent.gst is not None and parent.gst == 0:
            ParentProductTaxMapping.objects.create(
                parent_product=parent,
                tax=Tax.objects.get(id=1)
            ).save()
        elif parent.gst and parent.gst == 5:
            ParentProductTaxMapping.objects.create(
                parent_product=parent,
                tax=Tax.objects.get(id=2)
            ).save()
        elif parent.gst and parent.gst == 12:
            ParentProductTaxMapping.objects.create(
                parent_product=parent,
                tax=Tax.objects.get(id=3)
            ).save()
        elif parent.gst and parent.gst == 18:
            ParentProductTaxMapping.objects.create(
                parent_product=parent,
                tax=Tax.objects.get(id=4)
            ).save()
        elif parent.gst and parent.gst == 28:
            ParentProductTaxMapping.objects.create(
                parent_product=parent,
                tax=Tax.objects.get(id=5)
            ).save()
        if parent.cess and parent.cess == 12:
            ParentProductTaxMapping.objects.create(
                parent_product=parent,
                tax=Tax.objects.get(id=6)
            ).save()
        elif parent.cess is not None and parent.cess == 0:
            ParentProductTaxMapping.objects.create(
                parent_product=parent,
                tax=Tax.objects.get(id=7)
            ).save()
        if parent.surcharge is not None and parent.surcharge == 0:
            ParentProductTaxMapping.objects.create(
                parent_product=parent,
                tax=Tax.objects.get(id=8)
            ).save()

def approve_selected_products(modeladmin, request, queryset):
    queryset.update(status=True)
    for record in queryset:
        Product.objects.filter(parent_product__parent_id=record.parent_id).update(status='active')
approve_selected_products.short_description = "Approve Selected Products"


class ParentProductImageAdmin(admin.TabularInline):
    model = ParentProductImage

class ParentProductTaxInlineFormSet(BaseInlineFormSet):
   def clean(self):
      super(ParentProductTaxInlineFormSet, self).clean()
      tax_list_type = []
      for form in self.forms:
          if form.is_valid() and form.cleaned_data.get('tax'):
              if form.cleaned_data.get('tax').tax_type in tax_list_type:
                  raise ValidationError('{} type tax can be filled only once'.format(form.cleaned_data.get('tax').tax_type))
              tax_list_type.append(form.cleaned_data.get('tax').tax_type)
      if 'gst' not in tax_list_type:
          raise ValidationError('Please fill the GST tax value')


class ParentProductTaxMappingAdmin(admin.TabularInline):
    model = ParentProductTaxMapping
    extra = 3
    formset = ParentProductTaxInlineFormSet
    max_num = 6
    autocomplete_fields = ['tax']

    class Media:
        pass


class ParentProductAdmin(admin.ModelAdmin):
    resource_class = ParentProductResource
    form = ParentProductForm

    class Media:
        js = (
            '//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js', # jquery
            'admin/js/child_product_form.js',
            'admin/js/parent_product_form.js',
        )

    change_list_template = 'admin/products/parent_product_change_list.html'
    change_form_template = 'admin/products/parent_product_change_form.html'
    actions = [deactivate_selected_products, approve_selected_products, 'export_as_csv']
    list_display = [
        'parent_id', 'name', 'parent_brand', 'product_category', 'product_hsn',
        'product_gst', 'product_cess', 'product_surcharge', 'product_image', 'status',
        'product_type', 'is_ptr_applicable', 'ptrtype', 'ptrpercent', 'discounted_life_percent'
    ]
    search_fields = [
        'parent_id', 'name'
    ]
    inlines = [
        ParentProductCategoryAdmin, ParentProductImageAdmin, ParentProductTaxMappingAdmin
    ]
    list_filter = [ParentCategorySearch, ParentBrandFilter, ParentIDFilter, 'status']
    list_per_page = 50
    autocomplete_fields = ['product_hsn', 'parent_brand']

    def product_gst(self, obj):
        if ParentProductTaxMapping.objects.filter(parent_product=obj, tax__tax_type='gst').exists():
            return "{} %".format(ParentProductTaxMapping.objects.filter(parent_product=obj, tax__tax_type='gst').last().tax.tax_percentage)
        return ''
    product_gst.short_description = 'Product GST'

    def product_cess(self, obj):
        if ParentProductTaxMapping.objects.filter(parent_product=obj, tax__tax_type='cess').exists():
            return "{} %".format(ParentProductTaxMapping.objects.filter(parent_product=obj, tax__tax_type='cess').last().tax.tax_percentage)
        return ''
    product_cess.short_description = 'Product CESS'

    def product_surcharge(self, obj):
        if ParentProductTaxMapping.objects.filter(parent_product=obj, tax__tax_type='surcharge').exists():
            return "{} %".format(ParentProductTaxMapping.objects.filter(parent_product=obj, tax__tax_type='surcharge').last().tax.tax_percentage)
        return ''
    product_surcharge.short_description = 'Product Surcharge'

    def product_category(self, obj):
        try:
            if obj.parent_product_pro_category.exists():
                cats = [str(c.category) for c in obj.parent_product_pro_category.filter(status=True)]
                return "\n".join(cats)
            return ''
        except:
            return ''
    product_category.short_description = 'Product Category'

    def product_image(self, obj):
        if obj.parent_product_pro_image.exists():
            return format_html('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.format(
                obj.parent_product_pro_image.last().image.url,
                (obj.parent_product_pro_image.last().image_alt_text or obj.parent_product_pro_image.last().image_name),
                obj.parent_product_pro_image.last().image.url
            ))
        return '-'

    def ptrtype(self, obj):
        if obj.is_ptr_applicable :
            return obj.ptr_type_text

    def ptrpercent(self, obj):
        if obj.is_ptr_applicable:
            return obj.ptr_percent

    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [
            'parent_id', 'name', 'parent_brand', 'product_category', 'product_hsn',
            'product_gst', 'product_cess', 'product_surcharge', 'product_image', 'status',
            'product_type', 'is_ptr_applicable', 'ptr_type', 'ptr_percent', 'discounted_life_percent'
        ]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            row = []
            for field in field_names:
                try:
                    val = getattr(obj, field)
                    if field == 'ptr_type':
                        val = getattr(obj, 'ptr_type_text')
                except:
                    if field == 'product_image':
                        if obj.parent_product_pro_image.exists():
                            val = "{}".format(obj.parent_product_pro_image.last().image.url)
                        else:
                            val = '-'
                    else:
                        val = eval("self.{}(obj)".format(field))
                finally:
                    row.append(val)
            writer.writerow(row)
        return response
    export_as_csv.short_description = "Download CSV of Selected Objects"

    def get_urls(self):
        from django.conf.urls import url
        urls = super(ParentProductAdmin, self).get_urls()
        urls = [
            url(
                r'^parent-product-upload-csv/$',
                self.admin_site.admin_view(parent_product_upload),
                name="parent-product-upload"
            ),
            url(
                r'^parent-products-download-sample-csv/$',
                self.admin_site.admin_view(ParentProductsDownloadSampleCSV),
                name="parent-products-download-sample-csv"
            ),
            url(
                r'^parent-product-multiple-photos-upload/$',
                self.admin_site.admin_view(ParentProductMultiPhotoUploadView.as_view()),
                name='parent_product_multiple_photos_upload'
            ),
           url(
               r'^hsn-autocomplete/$',
               self.admin_site.admin_view(HSNAutocomplete.as_view()),
               name="hsn-autocomplete"
           ),
        ] + urls
        return urls


def deactivate_selected_child_products(modeladmin, request, queryset):
    # queryset.update(status='deactivated')
    for item in queryset:
        item.status = 'deactivated'
        item.save()


deactivate_selected_child_products.short_description = "Deactivate Selected Products"


def approve_selected_child_products(modeladmin, request, queryset):
    fail_skus = []
    success_skus = []
    price_fail = ''
    message = "All selected Child SKUs were successfully approved"
    for record in queryset:
        parent_sku = ParentProduct.objects.filter(parent_id=record.parent_product.parent_id).last()
        if not ProductPrice.objects.filter(approval_status=ProductPrice.APPROVED, product_id=record.id).exists():
            price_fail += ' ' + str(record.product_sku) + ','
            continue

        if parent_sku.status:
            record.status = 'active'
            record.save()
            success_skus.append(record.product_sku)
        else:
            parent_sku.status = True
            parent_sku.save()
            record.status = 'active'
            record.save()
            fail_skus.append(record.product_sku)

    if fail_skus:
        message = "All selected Child SKUs were successfully approved along with their Parent SKU activation where required"

    modeladmin.message_user(request, message, level=messages.SUCCESS)

    if price_fail != '':
        price_fail = price_fail.strip(',')
        modeladmin.message_user(request, "Products" + price_fail + " were not be approved due to non existent active Product Price",
                                level=messages.ERROR)
approve_selected_child_products.short_description = "Approve Selected Products"


class ProductSourceMappingAdmin(admin.TabularInline):
    model = ProductSourceMapping
    fk_name = "destination_sku"
    form = ProductSourceMappingForm
    formset = ProductSourceMappingFormSet

    def get_urls(self):
        from django.conf.urls import url
        urls = super(ProductSourceMappingAdmin, self).get_urls()
        urls = [
            url(
                r'^source-product-autocomplete/$',
                self.admin_site.admin_view(SourceProductAutocomplete.as_view()),
                name='source-product-autocomplete',
            ),
        ] + urls
        return urls


class ChildProductImageAdmin(admin.TabularInline):
    model = ChildProductImage


class DestinationRepackagingCostMappingAdmin(admin.TabularInline):
    model = DestinationRepackagingCostMapping
    form = DestinationRepackagingCostMappingForm
    formset = DestinationRepackagingCostMappingFormSet
    extra = 1
    max_num = 1

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


class ProductPackingMappingAdmin(admin.TabularInline):
    model = ProductPackingMapping
    fk_name = "sku"
    form = ProductPackingMappingForm
    formset = ProductPackingMappingFormSet
    max_num = 1

    def has_delete_permission(self, request, obj=None):
        return False


class ProductAdmin(admin.ModelAdmin, ExportCsvMixin):
    resource_class = ProductResource
    form = ProductForm

    class Media:
        js = (
            '//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js', # jquery
            'admin/js/child_product_form.js'
        )

    exclude = ('product_sku',)

    change_list_template = 'admin/products/product_change_list.html'
    change_form_template = 'admin/products/product_change_form.html'

    def get_urls(self):
        from django.conf.urls import url
        urls = super(ProductAdmin, self).get_urls()
        urls = [
            url(
                r'^productsfilter/$',
                self.admin_site.admin_view(products_filter_view),
                name="productsfilter"
            ),
            url(
                r'^productscsvupload/$',
                self.admin_site.admin_view(products_csv_upload_view),
                name="productscsvupload"
            ),
            url(
                r'^productspricefilter/$',
                self.admin_site.admin_view(products_price_filter_view),
                name="productspricefilter"
            ),
            url(
                r'^productsuploadsample/$',
                self.admin_site.admin_view(ProductsUploadSample),
                name="productsuploadsample"
            ),
            url(
                r'^sp-sr-productprice/$',
                self.admin_site.admin_view(SpSrProductPrice.as_view()),
                name="sp_sr_productprice"
            ),
            url(
                r'^gf-productprice/$',
                self.admin_site.admin_view(gf_product_price),
                name="gf_productprice"
            ),
            url(
                r'^ajax/load-cities/$',
                self.admin_site.admin_view(load_cities),
                name='ajax_load_cities'
            ),
            url(
                r'^ajax/load-sp-sr/$',
                self.admin_site.admin_view(load_sp_sr),
                name='ajax_load_sp_sr'
            ),
            url(
                r'^products-export/$',
                self.admin_site.admin_view(export),
                name='products-export'
            ),
            url(
                r'^ajax/load-brands/$',
                self.admin_site.admin_view(load_brands),
                name='ajax_load_brands'
            ),
            url(
                r'^ajax/load-gf/$',
                self.admin_site.admin_view(load_gf),
                name='ajax_load_gf'
            ),
            url(
                r'^products-export-for-vendor/+(?P<id>\d+)?',
                self.admin_site.admin_view(products_export_for_vendor),
                name='products_export_for_vendor'
            ),
             url(
                r'^all-product-mapped-to-vendor/+(?P<id>\d+)?',
                self.admin_site.admin_view(all_product_mapped_to_vendor),
                name='all_product_mapped_to_vendor'
            ),
            url(
                r'^multiple-photos-upload/$',
                self.admin_site.admin_view(MultiPhotoUploadView.as_view()),
                name='multiple_photos_upload'
            ),
            url(
                r'^products-vendor-mapping/(?P<pk>\d+)/$',
                self.admin_site.admin_view(products_vendor_mapping),
                name='products_vendor_mapping'
            ),
            url(
                r'^cart-products-mapping/(?P<pk>\d+)/$',
                self.admin_site.admin_view(cart_products_mapping),
                name='cart_products_mapping'
            ),
            url(
                r'^cart-products-list/(?P<order_status_info>(.*))/$',
                self.admin_site.admin_view(cart_product_list_status),
                name='cart_products_list_status'
            ),
            url(
                r'^product-price-autocomplete/$',
                self.admin_site.admin_view(ProductPriceAutocomplete.as_view()),
                name="product-price-autocomplete"
            ),
            url(
                r'^product-category-autocomplete/$',
                self.admin_site.admin_view(ProductCategoryAutocomplete.as_view()),
                name="product-category-autocomplete"
            ),
            url(
                r'^download-all-products/$',
                self.admin_site.admin_view(download_all_products),
                name="download-all-products"
            ),
            url(
                r'^product-category-mapping/$',
                self.admin_site.admin_view(ProductCategoryMapping.as_view()),
                name="product-category-mapping"
            ),
            url(
                r'^product-category-mapping-sample/$',
                self.admin_site.admin_view(product_category_mapping_sample),
                name="product-category-mapping-sample"
            ),
            url(
                r'^city-autocomplete/$',
                self.admin_site.admin_view(CityAutocomplete.as_view()),
                name="city_autocomplete"
            ),
            url(
                r'^retailer-autocomplete/$',
                self.admin_site.admin_view(RetailerAutocomplete.as_view()),
                name="retailer_autocomplete"
            ),
            url(
                r'^seller-shop-autocomplete/$',
                self.admin_site.admin_view(SellerShopAutocomplete.as_view()),
                name="seller_shop_autocomplete"
            ),
            url(
                r'^product-autocomplete/$',
                self.admin_site.admin_view(ProductAutocomplete.as_view()),
                name="product_autocomplete"
            ),
            url(
                r'^pincode-autocomplete/$',
                self.admin_site.admin_view(PincodeAutocomplete.as_view()),
                name="pincode_autocomplete"
            ),
            url(
                r'^product-shop-autocomplete/$',
                self.admin_site.admin_view(ProductShopAutocomplete.as_view()),
                name="product-shop-autocomplete"
            ),
            url(
                r'^destination-product-autocomplete/$',
                self.admin_site.admin_view(DestinationProductAutocomplete.as_view()),
                name="destination-product-autocomplete"
            ),
            url(
                r'^source-repackage-detail/$',
                self.admin_site.admin_view(SourceRepackageDetail.as_view()),
                name="source-repackage-detail"
            ),
            url(
                r'^product-csv-upload/$',
                self.admin_site.admin_view(product_csv_upload),
                name="product-csv-upload"
            ),
            url(
                r'^upload-master-data/$',
                self.admin_site.admin_view(upload_master_data_view),
                name="upload-master-data"
            ),
            url(
               r'^category-sub-category-mapping/$',
               self.admin_site.admin_view(category_sub_category_mapping_sample_excel_file),
               name="category-sub-category-mapping"
            ),
            url(
                r'^brand-sub-brand-mapping/$',
                self.admin_site.admin_view(brand_sub_brand_mapping_sample_excel_file),
                name="brand-sub-brand-mapping"
            ),
            url(
                r'^chld-products-download-sample-csv/$',
                self.admin_site.admin_view(ChildProductsDownloadSampleCSV),
                name="child-products-download-sample-csv"
            ),
            url(
                r'^upload-master-data-sample-excel-file/$',
                self.admin_site.admin_view(UploadMasterDataSampleExcelFile),
                name="upload-master-data-sample-excel-file"
            ),
            url(
               r'^parent-data-sample-excel-file/$',
               self.admin_site.admin_view(set_parent_data_sample_excel_file),
               name="parent-data-sample-excel-file"
            ),
            url(
               r'^child-data-sample-excel-file/$',
               self.admin_site.admin_view(set_child_data_sample_excel_file),
               name="child-data-sample-excel-file"
            ),
            url(
               r'^parent-child-mapping-sample-excel-file/$',
               self.admin_site.admin_view(set_child_with_parent_sample_excel_file),
               name="parent-child-mapping-sample-excel-file"
            ),
            url(
               r'^set-inactive-status-sample-file/$',
               self.admin_site.admin_view(set_inactive_status_sample_excel_file),
               name="set-inactive-status-sample-file"
            ),
            url(
                r'^parent-product-autocomplete/$',
                self.admin_site.admin_view(ParentProductAutocomplete.as_view()),
                name='parent-product-autocomplete',
            ),
            url(
                r'^parent-product-list-filter-autocomplete/$',
                self.admin_site.admin_view(ParentProductsAutocompleteView.as_view(model_admin=self)),
                name='parent-product-list-filter-autocomplete',
            ),
            url(
                r'^packing-material-check/$',
                self.admin_site.admin_view(PackingMaterialCheck.as_view()),
                name="packing-material-check"
            ),
            # url('custom_search/', self.admin_site.admin_view(CustomSearchView.as_view(model_admin=self)),
            #      name='custom_search'),
        ] + urls
        return urls

    actions = [deactivate_selected_child_products, approve_selected_child_products, 'export_as_csv']
    # list_display = [
    #     'product_sku', 'product_name', 'product_short_description',
    #     'product_brand', 'product_gf_code', 'product_images'
    # ]
    # list_display = [
    #     'product_sku', 'product_name',
    #     'product_brand', 'product_images'
    # ]
    list_display = [
        'product_sku', 'product_name', 'parent_product', 'parent_name',
        'product_brand', 'product_category', 'product_ean_code', 'product_hsn', 'product_gst',
        'product_mrp',  'is_ptr_applicable', 'ptr_type', 'ptr_percent',  'products_image', 'status',
        'moving_average_buying_price'
    ]

    search_fields = ['product_name', 'id']
    list_filter = [CategorySearch, ProductBrandSearch, ProductSearch, ChildParentIDFilter, 'status', ProductEanSearch]
    list_per_page = 50

    inlines = [ProductImageAdmin, ProductSourceMappingAdmin, ProductPackingMappingAdmin, DestinationRepackagingCostMappingAdmin]

    autocomplete_fields = ['parent_product']

    def product_images(self,obj):
        if obj.product_pro_image.exists():
            return mark_safe('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.
                             format(obj.product_pro_image.last().image.url, obj.product_pro_image.last().image_alt_text,
                                    obj.product_pro_image.last().image.url))

    product_images.short_description = 'Product Image'

    def products_image(self, obj):
        if obj.use_parent_image and obj.parent_product.parent_product_pro_image.exists():
            return format_html('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.format(
                obj.parent_product.parent_product_pro_image.last().image.url,
                (obj.parent_product.parent_product_pro_image.last().image_alt_text or obj.parent_product.parent_product_pro_image.last().image_name),
                obj.parent_product.parent_product_pro_image.last().image.url
            ))
        elif not obj.use_parent_image and obj.product_pro_image.exists():
            return format_html('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.format(
                obj.product_pro_image.last().image.url,
                (obj.product_pro_image.last().image_alt_text or obj.product_pro_image.last().image_name),
                obj.product_pro_image.last().image.url
            ))
        elif not obj.use_parent_image and obj.child_product_pro_image.exists():
            return format_html('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.format(
                obj.child_product_pro_image.last().image.url,
                (obj.child_product_pro_image.last().image_alt_text or obj.child_product_pro_image.last().image_name),
                obj.child_product_pro_image.last().image.url
            ))
        return '-'

    def product_gst(self, obj):
        if obj.product_gst is not None:
            return "{} %".format(obj.product_gst)
        return ''
    product_gst.short_description = 'Product GST'

    def is_ptr_applicable(self, obj):
        return obj.parent_product.is_ptr_applicable

    def ptr_type(self, obj):
        return obj.parent_product.ptr_type_text

    def ptr_percent(self, obj):
        return obj.parent_product.ptr_percent

    def product_category(self, obj):
        try:
            if obj.parent_product.parent_product_pro_category.exists():
                cats = [str(c.category) for c in obj.parent_product.parent_product_pro_category.filter(status=True)]
                return "\n".join(cats)
            return ''
        except:
            return ''
    product_category.short_description = 'Product Category'

    def get_changeform_initial_data(self, request):
        if request.GET.get('product'):
            product_details = Product.objects.filter(pk=int(request.GET.get('product'))).last()
            return {
                'parent_product': product_details.parent_product
            }
        return super().get_changeform_initial_data(request)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.repackaging_type != 'none':
            if obj.repackaging_type == 'packing_material':
                return self.readonly_fields + ('repackaging_type', 'weight_value', 'weight_unit', 'status')
            return self.readonly_fields + ('repackaging_type',)
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        self.inlines = [ProductImageAdmin, ProductSourceMappingAdmin, ProductPackingMappingAdmin,
                        DestinationRepackagingCostMappingAdmin]
        if obj and obj.repackaging_type != 'destination':
            self.inlines.remove(ProductSourceMappingAdmin)
            self.inlines.remove(DestinationRepackagingCostMappingAdmin)
            self.inlines.remove(ProductPackingMappingAdmin)
        return super(ProductAdmin, self).get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if 'repackaging_type' in form.changed_data and form.cleaned_data['repackaging_type'] == 'packing_material':
            self.update_weight_inventory(obj)
        if 'repackaging_type' in form.cleaned_data and form.cleaned_data['repackaging_type'] == 'packing_material':
            obj.status = 'pending_approval'
        super(ProductAdmin, self).save_model(request, obj, form, change)

    @staticmethod
    def update_weight_inventory(obj):
        warehouse_inv = WarehouseInventory.objects.filter(sku=obj)
        for inv in warehouse_inv:
            inv.weight = inv.quantity * obj.weight_value
            inv.save()
        bin_inv = BinInventory.objects.filter(sku=obj)
        for inv in bin_inv:
            inv.weight = inv.quantity * obj.weight_value
            inv.save()


class MRPSearch(InputFilter):
    parameter_name = 'mrp'
    title = 'MRP'

    def queryset(self, request, queryset):
        if self.value() is not None:
            mrp = self.value()
            if mrp is None:
                return
            return queryset.filter(
                Q(mrp__icontains=mrp)
            )

class ExportProductPrice:
    def export_as_csv_productprice(self, request, queryset):
        meta = self.model._meta
        # list_display = [
        #     'product' ,'sku_code', 'mrp', 'price_to_service_partner','price_to_retailer', 'price_to_super_retailer',
        #     'shop', 'cash_discount','loyalty_incentive','margin','start_date', 'end_date', 'status'
        # ]
        list_display = [
            'product', 'sku_code', 'mrp', 'selling_price', 'seller_shop', 'buyer_shop', 'city',
            'pincode', 'start_date', 'end_date', 'approval_status', 'status'
        ]
        # field_names = [field.name for field in meta.fields if field.name in list_display]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            row = [getattr(obj, field) for field in list_display]
            row[2] = Product.objects.get(id=obj.product.id).product_mrp
            if row[-2] == 2:
                row[-2] = 'Active'
            elif row[-2] == 1:
                row[-2] = 'Approval Pending'
            else:
                row[-2] = 'Deactivated'
            writer.writerow(row)
        return response
    export_as_csv_productprice.short_description = "Download CSV of Selected ProductPrice"


class ProductPriceAdmin(admin.ModelAdmin, ExportProductPrice):
    resource_class = ProductPriceResource
    form = ProductPriceNewForm
    actions = ['export_as_csv_productprice']
    list_select_related = ('product', 'seller_shop', 'buyer_shop', 'city', 'pincode')
    list_display = [
        'product', 'product_sku', 'product_mrp', 'selling_price',
        'seller_shop', 'buyer_shop', 'city', 'pincode',
        'start_date', 'end_date', 'approval_status', 'status'
    ]

    autocomplete_fields = ['product']
    search_fields = [
        'product__product_name',
        'product__parent_product__parent_brand__brand_name', 'seller_shop__shop_name',
        'buyer_shop__shop_name'
    ]
    list_filter = [
        ProductSKUSearch, ProductFilter, ShopFilter, MRPSearch, CityFilter, ProductCategoryFilter,
        ('start_date', DateRangeFilter), ('end_date', DateRangeFilter),
        'approval_status']
    fields = ('product', 'mrp', 'selling_price', 'seller_shop',
              'buyer_shop', 'city', 'pincode',
              'start_date', 'approval_status')

    change_form_template = 'admin/products/product_price_change_form.html'

    class Media:
        js = (
            '//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            'admin/js/child_product_form.js'
        )

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            if obj and obj.approval_status == ProductPrice.APPROVED:
                return self.readonly_fields + (
                    'product', 'mrp', 'selling_price', 'seller_shop',
                    'buyer_shop', 'city', 'pincode',
                    'start_date', 'approval_status')
        return self.readonly_fields

    def product_sku(self, obj):
        return obj.product.product_sku

    product_sku.short_description = 'Product SKU'

    def product_mrp(self, obj):
        # if obj.mrp:
        #     return obj.mrp
        if obj.product.product_mrp:
            return obj.product.product_mrp
        return ''

    def product_gf_code(self, obj):
        return obj.product.product_gf_code

    product_gf_code.short_description = 'Gf Code'

    def approve_product_price(self, request, queryset):
        queryset = queryset.filter(approval_status=ProductPrice.APPROVAL_PENDING).order_by('created_at')
        for product in queryset:
            product.approval_status = ProductPrice.APPROVED
            product.save()

    def disapprove_product_price(self, request, queryset):
        for product in queryset:
            product.approval_status = ProductPrice.DEACTIVATED
            product.save()

    approve_product_price.short_description = "Approve Selected Products Prices"
    approve_product_price.allowed_permissions = ('change',)
    disapprove_product_price.short_description = "Disapprove Selected Products Prices"
    disapprove_product_price.allowed_permissions = ('change',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # if request.user.is_superuser:
        #     return True
        return False

    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = ProductPriceNewForm
        # if request.user.is_superuser:
        #     kwargs['form'] = ProductPriceNewForm
        # elif request.user.has_perm('products.add_productprice'):
        #     kwargs['form'] = ProductPriceAddPerm
        # elif request.user.has_perm('products.change_productprice'):
        #     kwargs['form'] = ProductPriceChangePerm
        return super().get_form(request, obj, **kwargs)

    def get_queryset(self, request):
        qs = super(ProductPriceAdmin, self).get_queryset(request)
        qs = qs.filter(price_slabs__isnull=True)
        if request.user.is_superuser or request.user.has_perm('products.change_productprice'):
            return qs
        return qs.filter(
            Q(seller_shop__related_users=request.user) |
            Q(seller_shop__shop_owner=request.user)
        ).distinct()


class ProductHSNAdmin(admin.ModelAdmin, ExportCsvMixin):
    form = ProductHSNForm
    fields = ['product_hsn_code']
    list_display = ['product_hsn_code']
    actions = ['export_as_csv']
    search_fields = ['product_hsn_code']

class ProductCappingAdmin(admin.ModelAdmin):
    form = ProductCappingForm
    list_display = ('product', 'seller_shop', 'capping_qty', 'status')
    list_filter = [
        ProductSKUSearch, ProductFilter, ShopFilter,
        'status']
    readonly_fields = ('buyer_shop', 'city', 'pincode')
    class Media:
        pass


class ProductTaxAdmin(admin.ModelAdmin, ExportCsvMixin):
    template = 'admin/products/producttaxmapping/change_list.html'
    list_display = ('product', 'tax')
    list_select_related = ('product', 'tax')
    search_fields = ['product__product_name']


class BulkProductTaxUpdateAdmin(admin.ModelAdmin):
    form = BulkProductTaxUpdateForm
    list_display = ('created_at', 'updated_by', 'file')
    list_select_related = ('updated_by',)
    list_filter = (('created_at', DateTimeRangeFilter), BulkTaxUpdatedBySearch)
    fields = ('download_sample_file', 'file', 'updated_by')
    readonly_fields = ('updated_by', 'download_sample_file')

    def get_urls(self):
        urls = super().get_urls()
        urls = [
            url(
                r'^sample-file/$',
                self.admin_site.admin_view(self.form.sample_file),
                name="bulk-tax-update-sample-file"
            )
        ] + urls
        return urls

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:
            readonly_fields = readonly_fields + ('file',)
        return readonly_fields

    def download_sample_file(self, obj):
        return format_html(
            "<a href= '%s' >bulk_product_tax_update_sample.csv</a>" %
            (reverse('admin:bulk-tax-update-sample-file'))
        )
    download_sample_file.short_description = 'Download Sample File'

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return True

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class BulkUploadForGSTChangeAdmin(admin.ModelAdmin):
    form = BulkUploadForGSTChangeForm
    list_display = ('created_at', 'updated_by', 'file',)
    fields = ('download_sample_file', 'file', 'updated_by')
    readonly_fields = ('updated_by', 'download_sample_file', )

    def get_urls(self):
        urls = super().get_urls()
        urls = [
            url(
                r'^sample-file1/$',
                self.admin_site.admin_view(self.form.sample_file1),
                name="bulk-upload-for-gst-change-sample-file"
            )
        ] + urls
        return urls

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:
            readonly_fields = readonly_fields + ('file',)
        return readonly_fields

    def download_sample_file(self, obj):
        return format_html(
            "<a href= '%s' >bulk_upload_for_gst_change_sample.csv</a>" %
            (reverse('admin:bulk-upload-for-gst-change-sample-file'))
        )
    download_sample_file.short_description = 'Download Sample File'


class BulkUploadForProductAttributesAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'updated_by', 'file',)
    fields = ('file', 'updated_by')
    readonly_fields = ('updated_by', 'file',)

    change_list_template = 'admin/products/product_attributes_change_list.html'

    def has_add_permission(self, request):
        return False


class ExportRepackaging:
    def export_as_csv_products_repackaging(self, request, queryset):
        meta = self.model._meta
        list_display = ['Repackaging ID', 'Repackaging Status', 'Source SKU Name', 'Source SKU ID',
                        'Destination SKU Name', 'Destination SKU ID', 'Destination SKU Batch ID',
                        'Source SKU Qty to be Repackaged', 'Destination SKU Qty Created',
                        'Raw Material Cost', 'Wastage Cost', 'Fumigation Cost', 'Label Printing Cost',
                        'Packing Labour Cost', 'Primary PM Cost', 'Secondary PM Cost', 'Final FG Cost',
                        'Conversion Cost', 'Created At']
        field_names = ['destination_batch_id', 'source_repackage_quantity', 'destination_sku_quantity']
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            items = [obj.repackaging_no, obj.status, obj.source_sku_name(), obj.source_product_sku(),
                     obj.destination_sku_name(), obj.destination_product_sku()]
            items1 = [getattr(obj, field) for field in field_names]
            items = items + items1
            rep = obj.destination_sku.destination_product_repackaging.all()
            add = ['raw_material', 'wastage', 'fumigation', 'label_printing', 'packing_labour', 'primary_pm_cost',
                   'secondary_pm_cost', 'final_fg_cost', 'conversion_cost']
            for key in add:
                if rep:
                    join_all = ", ".join([str(getattr(k, key)) for k in rep])
                else:
                    join_all = ""
                items.append(join_all)
            items = items + [getattr(obj, 'created_at').strftime("%b. %d, %Y, %-I:%M %p")]
            writer.writerow(items)
        return response
    export_as_csv_products_repackaging.short_description = "Download CSV of Selected Repackaging"


class RepackagingAdmin(admin.ModelAdmin, ExportRepackaging):
    form = RepackagingForm
    fields = ('seller_shop', 'source_sku', 'destination_sku', 'source_repackage_quantity')
    list_display = ('repackaging_no', 'status', 'source_sku_name', 'source_product_sku', 'source_picking_status',
                    'destination_sku_name', 'destination_product_sku', 'destination_batch_id',
                    'destination_sku_quantity', 'download_batch_id_barcode', 'created_at', 'modified_at')
    actions = ["export_as_csv_products_repackaging"]

    change_list_template = 'admin/products/repackaging_change_list.html'

    def get_urls(self):
        from django.conf.urls import url
        urls = super(RepackagingAdmin, self).get_urls()
        urls = [
                   url(
                       r'^packing-material-inventory/$',
                       self.admin_site.admin_view(packing_material_inventory),
                       name="packing-material-inventory"
                   ),
                   url(
                       r'^packing-material-inventory-download/$',
                       self.admin_site.admin_view(packing_material_inventory_download),
                       name="packing-material-inventory-download"
                   ),
                   url(
                       r'^packing-material-inventory-sample-upload/$',
                       self.admin_site.admin_view(packing_material_inventory_sample_upload),
                       name="packing-material-inventory-sample-upload"
                   )
               ] + urls
        return urls

    def get_fields(self, request, obj=None):
        if obj:
            if obj.status == 'completed':
                return self.fields + ('destination_sku_quantity', 'expiry_date', 'status', 'remarks')
            return self.fields + ('source_picking_status', 'available_packing_material_weight',
                                  'destination_sku_quantity', 'available_packing_material_weight_initial',
                                  'packing_sku_weight_per_unit_sku', 'expiry_date', 'status', 'remarks')
        else:
            return self.fields + ('available_source_weight', 'available_source_quantity', 'status')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            add_f = []
            if request.method == "GET":
                if obj.status == 'completed':
                    add_f = ['destination_sku_quantity', 'status', 'expiry_date', 'remarks']
            return ['seller_shop', 'source_sku', "destination_sku", "source_repackage_quantity",
                    "available_source_weight", "available_source_quantity", "source_picking_status"] + add_f
        else:
            return ['status', 'destination_sku_quantity', 'remarks', 'expiry_date', 'source_picking_status']
    list_filter = [SourceSKUSearch, SourceSKUName, DestinationSKUSearch, DestinationSKUName,
                   ('status', ChoiceDropdownFilter), ('created_at', DateTimeRangeFilter)]
    list_per_page = 10

    def download_batch_id_barcode(self, obj):
        html_ret = '';
        if obj.source_sku:
            outs = Out.objects.filter(out_type='repackaging', out_type_id=obj.id, sku=obj.source_sku)
            if outs.exists():
                for out_obj in outs:
                    if out_obj.batch_id:
                        grn_order_pro = obj.source_sku.product_grn_order_product.filter(batch_id=out_obj.batch_id).last()
                        if grn_order_pro is not None:
                            if grn_order_pro.barcode_id is None:
                                product_id = str(grn_order_pro.product_id).zfill(5)
                                expiry_date = datetime.datetime.strptime(str(grn_order_pro.expiry_date), '%Y-%m-%d').strftime(
                                    '%d%m%y')
                                barcode_id = str("2" + product_id + str(expiry_date))
                            else:
                                barcode_id = grn_order_pro.barcode_id
                            html_ret += "<a href= '{0}' >{1}</a><br>".format(reverse('batch_barcodes', args=[grn_order_pro.pk]), barcode_id)
                        else:
                            html_ret += '{0}<br>'.format(out_obj.batch_id);
                    else:
                        html_ret += '--<br>'
        html_ret = '-' if html_ret == '' else html_ret;
        return format_html(html_ret)

    def has_change_permission(self, request, obj=None):
        if obj and obj.status and obj.status == 'completed' and request.method == "GET":
            return False
        return True

    class Media:
        js = ("admin/js/repackaging.js",)

class PriceSlabAdmin(TabularInline):
    """
    This class is used to create Price Slabs from admin panel
    """
    model = PriceSlab
    form = PriceSlabForm
    formset = SlabInlineFormSet
    min_num = 0
    extra = 2
    max_num = 2
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return self.readonly_fields
        return self.readonly_fields + ('start_value', 'end_value','selling_price', 'offer_price',
                                       'offer_price_start_date', 'offer_price_end_date')
    class Media:
        pass

class ProductSlabPriceAdmin(admin.ModelAdmin, ExportProductPrice):

    """
    This class is used to create Slabbed Product Price from admin panel
    """
    inlines = [PriceSlabAdmin]
    form = ProductPriceSlabForm
    list_display = ['product', 'product_mrp', 'is_ptr_applicable', 'ptr_type', 'ptr_percent',
                    'seller_shop', 'buyer_shop', 'city', 'pincode', 'approval_status', 'slab1_details', 'slab2_details'
                    ]
    autocomplete_fields = ['product']
    list_filter = [ProductSKUSearch, ProductFilter, ShopFilter, MRPSearch, ProductCategoryFilter, 'approval_status']
    fieldsets = (
        ('Basic', {
            'fields': ('product', 'mrp', 'seller_shop', 'buyer_shop', 'city', 'pincode', 'approval_status',),
            'classes': ('required',)
        }),
    )
    change_form_template = 'admin/products/product_price_change_form.html'

    class Media:
        js = (
            '//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            'admin/js/child_product_form.js',
            'admin/js/price-slab-form.js'
        )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(ProductSlabPriceAdmin, self).get_fieldsets(request, obj)
        if obj is None:
            fieldsets = (
                            ('Basic', {
                                'fields': ('product', 'mrp', 'seller_shop', 'buyer_shop', 'city', 'pincode', 'approval_status',),
                                'classes': ('required',)})
                            ,
                            ('Slab Price Applicable', {
                                'fields': ('slab_price_applicable',),
                                'classes': ('slab_applicable',)}),
                            ('Price Details', {
                                'fields': ('selling_price', 'offer_price', 'offer_price_start_date', 'offer_price_end_date'),
                                'classes': ('single_slab',)
                            })
            )
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return self.readonly_fields
        if not request.user.is_superuser:
            return self.readonly_fields + (
                'product', 'mrp', 'seller_shop', 'buyer_shop', 'city', 'pincode', 'approval_status')
        return self.readonly_fields + ( 'product', 'mrp', 'seller_shop', 'buyer_shop', 'city', 'pincode')


    def slab1_details(self, obj):
        first_slab = obj.price_slabs.filter(start_value=0).last()
        return first_slab

    def slab2_details(self, obj):
        last_slab = obj.price_slabs.filter(~Q(start_value=0), end_value=0).last()
        return last_slab

    def product_mrp(self, obj):
        if obj.product.product_mrp:
            return obj.product.product_mrp
        return ''

    def is_ptr_applicable(self, obj):
        return obj.product.is_ptr_applicable

    def ptr_type(self, obj):
        return obj.product.ptr_type

    def ptr_percent(self, obj):
        return obj.product.ptr_percent

    def approve_product_price(self, request, queryset):
        queryset = queryset.filter(approval_status=ProductPrice.APPROVAL_PENDING).order_by('created_at')
        for product in queryset:
            product.approval_status = ProductPrice.APPROVED
            product.save()

    def disapprove_product_price(self, request, queryset):
        failed_counter = 0
        success_counter = 0
        for product in queryset:
            if product.buyer_shop or product.pincode or product.city:
                product.approval_status = ProductPrice.DEACTIVATED
                product.save()
                success_counter+=1
            else:
                failed_counter+=1
        if success_counter>0:
            self.message_user(request, '{} prices were deactivated.'.format(success_counter), level=messages.SUCCESS)
        if failed_counter>0:
            self.message_user(request, '{} warehouse level prices were not deactivated.'.format(failed_counter), level=messages.ERROR)


    approve_product_price.short_description = "Approve Selected Products Prices"
    approve_product_price.allowed_permissions = ('change',)
    disapprove_product_price.short_description = "Disapprove Selected Products Prices"
    disapprove_product_price.allowed_permissions = ('change',)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_form(self, request, obj=None, **kwargs):
        if not obj:
            kwargs['form'] = ProductPriceSlabCreationForm
        else:
            kwargs['form'] = ProductPriceSlabForm
        return super().get_form(request, obj, **kwargs)


    def get_queryset(self, request):
        qs = super(ProductSlabPriceAdmin, self).get_queryset(request)
        qs = qs.filter(id__in=qs.filter(price_slabs__isnull=False).values_list('pk', flat=True))
        if request.user.is_superuser or request.user.has_perm('products.change_productprice'):
            return qs
        return qs.filter(
            Q(seller_shop__related_users=request.user) |
            Q(seller_shop__shop_owner=request.user)
        ).distinct()

    def get_urls(self):
        """
        returns the added action urls for Slab Product Pricing
        """
        from django.conf.urls import url
        urls = super(ProductSlabPriceAdmin, self).get_urls()
        urls = [
                   url(
                       r'^slab_product_price_sample_csv/$',
                       self.admin_site.admin_view(get_slab_product_price_sample_csv),
                       name="slab_product_price_sample_csv"
                   ),
                   url(
                       r'^slab_product_price_csv_upload/$',
                       self.admin_site.admin_view(slab_product_price_csv_upload),
                       name="slab_product_price_csv_upload"
                   ),

               ] + urls
        return urls

    def export_as_csv(self, request, queryset):
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(["SKU", "Product Name", "Shop Id", "Shop Name", "MRP", "is_ptr_applicable", "ptr_type", "ptr_percent",
                         "Slab 1 Qty", "Selling Price 1", "Offer Price 1", "Offer Price 1 Start Date", "Offer Price 1 End Date",
                     "Slab 2 Qty", "Selling Price 2", "Offer Price 2", "Offer Price 2 Start Date", "Offer Price 2 End Date"])
        for query in queryset:
            obj = SlabProductPrice.objects.get(id=query.id)
            try:
                row = [obj.product.product_sku, obj.product.product_name, obj.seller_shop.id, obj.seller_shop.shop_name,
                       obj.mrp, obj.product.is_ptr_applicable, obj.product.ptr_type, obj.product.ptr_percent]
                first_slab=True
                for slab in obj.price_slabs.all().order_by('start_value'):
                    if first_slab:
                        row.append(slab.end_value)
                    else:
                        row.append(slab.start_value)
                    row.append(slab.selling_price)
                    row.append(slab.offer_price)
                    row.append(slab.offer_price_start_date)
                    row.append(slab.offer_price_end_date)
                    first_slab = False
                writer.writerow(row)

            except Exception as exc:
                info_logger.error(exc)

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=slab_product_prices.csv'
        return response

    actions = [export_as_csv, disapprove_product_price]
    change_list_template = 'admin/products/products-slab-price-change-list.html'


class DiscountedProductsAdmin(admin.ModelAdmin, ExportCsvMixin):
    form = DiscountedProductForm
    list_display = [
        'product_sku', 'product_name', 'parent_product', 'parent_name',
        'product_brand', 'product_ean_code', 'product_hsn', 'product_gst',
        'product_mrp',   'products_image',  'status'
    ]
    readonly_fields = ('product_sku', 'product_name', 'parent_product', 'reason_for_child_sku', 'product_name',
                       'product_ean_code', 'product_mrp', 'status')

    list_filter = [ProductSearch, ChildParentIDFilter]

    search_fields = ['product_name', 'id']

    actions = ['export_as_csv']
    def get_queryset(self, request):
        qs = super().get_queryset(request).filter(product_type=1)
        return qs
    
    def product_images(self,obj):
        if obj.product_pro_image.exists():
            return mark_safe('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.
                             format(obj.product_pro_image.last().image.url, obj.product_pro_image.last().image_alt_text,
                                    obj.product_pro_image.last().image.url))

    product_images.short_description = 'Product Image'

    def products_image(self, obj):
        if obj.use_parent_image and obj.parent_product.parent_product_pro_image.exists():
            return format_html('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.format(
                obj.parent_product.parent_product_pro_image.last().image.url,
                (obj.parent_product.parent_product_pro_image.last().image_alt_text or obj.parent_product.parent_product_pro_image.last().image_name),
                obj.parent_product.parent_product_pro_image.last().image.url
            ))
        elif not obj.use_parent_image and obj.product_pro_image.exists():
            return format_html('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.format(
                obj.product_pro_image.last().image.url,
                (obj.product_pro_image.last().image_alt_text or obj.product_pro_image.last().image_name),
                obj.product_pro_image.last().image.url
            ))
        elif not obj.use_parent_image and obj.child_product_pro_image.exists():
            return format_html('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.format(
                obj.child_product_pro_image.last().image.url,
                (obj.child_product_pro_image.last().image_alt_text or obj.child_product_pro_image.last().image_name),
                obj.child_product_pro_image.last().image.url
            ))
        return '-'

    def product_gst(self, obj):
        if obj.product_gst is not None:
            return "{} %".format(obj.product_gst)
        return ''
    product_gst.short_description = 'Product GST'

    def product_category(self, obj):
        try:
            if obj.parent_product.parent_product_pro_category.exists():
                cats = [str(c.category) for c in obj.parent_product.parent_product_pro_category.filter(status=True)]
                return "\n".join(cats)
            return ''
        except:
            return ''
    product_category.short_description = 'Product Category'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(DiscountedProduct, DiscountedProductsAdmin)
admin.site.register(ProductImage, ProductImageMainAdmin)
admin.site.register(ProductVendorMapping, ProductVendorMappingAdmin)
admin.site.register(Size, SizeAdmin)
admin.site.register(Fragrance, FragranceAdmin)
admin.site.register(Flavor, FlavorAdmin)
admin.site.register(Color, ColorAdmin)
admin.site.register(PackageSize, PackageSizeAdmin)
admin.site.register(Weight, WeightAdmin)
admin.site.register(Tax, TaxAdmin)
admin.site.register(Product, ProductAdmin)
# admin.site.register(ProductPrice, ProductPriceAdmin)
admin.site.register(ProductHSN, ProductHSNAdmin)
admin.site.register(ProductCapping, ProductCappingAdmin)
admin.site.register(ProductTaxMapping, ProductTaxAdmin)
admin.site.register(BulkProductTaxUpdate, BulkProductTaxUpdateAdmin)
admin.site.register(BulkUploadForGSTChange, BulkUploadForGSTChangeAdmin)
admin.site.register(BulkUploadForProductAttributes, BulkUploadForProductAttributesAdmin)
admin.site.register(Repackaging, RepackagingAdmin)
admin.site.register(ParentProduct, ParentProductAdmin)
admin.site.register(SlabProductPrice, ProductSlabPriceAdmin)
