from admin_auto_filters.filters import AutocompleteFilter
from daterange_filter.filter import DateRangeFilter
from django_filters import BooleanFilter
from rangefilter.filter import DateTimeRangeFilter

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
                    ProductPriceChangePerm, ProductPriceNewForm,
                    ProductVendorMappingForm, BulkProductTaxUpdateForm, BulkUploadForGSTChangeForm,
                    ParentProductForm)
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
                    parent_product_upload, ParentProductsDownloadSampleCSV,
                    product_csv_upload, ChildProductsDownloadSampleCSV,
                    ParentProductAutocomplete, ParentProductsAutocompleteView)
from .filters import BulkTaxUpdatedBySearch


class ProductFilter(AutocompleteFilter):
    title = 'Product Name' # display title
    field_name = 'product' # name of the foreign key field

class ShopFilter(AutocompleteFilter):
    title = 'Seller Shop' # display title
    field_name = 'seller_shop' # name of the foreign key field

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
                Q(product_pro_category__category__category_name__icontains=self.value())
            )

class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        exclude_fields = ['created_at', 'modified_at']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        if self.model._meta.db_table=='products_product':
            field_names_temp = field_names.copy()
            field_names_temp.append('image')
            writer.writerow(field_names_temp)
        else:
            writer.writerow(field_names)
        for obj in queryset:
            items= [getattr(obj, field) for field in field_names]
            if self.model._meta.db_table == 'products_product':
                if obj.product_pro_image.last():
                    items.append(obj.product_pro_image.last().image.url)
                else:
                    items.append('-')
            row = writer.writerow(items)
        return response
    export_as_csv.short_description = "Download CSV of Selected Objects"


class BrandFilter(AutocompleteFilter):
    title = 'Brand'  # display title
    field_name = 'product_brand'  # name of the foreign key field


class ChildParentIDFilter(AutocompleteFilter):
    title = 'Parent ID'  # display title
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
    actions = ["export_as_csv_product_vendormapping", ]
    fields = ('vendor', 'product', 'product_price','product_mrp','case_size')
    list_display = ('vendor', 'product','product_price','product_mrp','case_size','created_at','status','product_status')
    list_filter = [VendorFilter,ProductFilter,'product__status']
    form = ProductVendorMappingForm

    def get_urls(self):
        from django.conf.urls import url
        urls = super(ProductVendorMappingAdmin, self).get_urls()
        urls = [
            url(
                r'^vendor-autocomplete/$',
                self.admin_site.admin_view(VendorAutocomplete.as_view()),
                name="vendor-autocomplete"
            ),
        ] + urls
        return urls

    def product_status(self, obj):
        return  obj.product.status
    product_status.boolean = True

    class Media:
        pass

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
    parent_tax_script_qa4()
    # queryset.update(status=False)
    # for record in queryset:
    #     Product.objects.filter(parent_product__parent_id=record.parent_id).update(status='deactivated')

deactivate_selected_products.short_description = "Deactivate Selected Products"

def parent_tax_script_qa4():
    parents = ParentProduct.objects.all()
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
            'admin/js/child_product_form.js'
        )

    change_list_template = 'admin/products/parent_product_change_list.html'
    change_form_template = 'admin/products/parent_product_change_form.html'
    actions = [deactivate_selected_products, approve_selected_products]
    list_display = [
        'parent_id', 'name', 'parent_brand', 'product_hsn', 'product_gst', 'product_image', 'status'
    ]
    search_fields = [
        'parent_id', 'name'
    ]
    inlines = [
        ParentProductCategoryAdmin, ParentProductImageAdmin, ParentProductTaxMappingAdmin
    ]
    list_filter = [ParentCategorySearch, ParentBrandFilter, ParentIDFilter, 'status']
    autocomplete_fields = ['product_hsn', 'parent_brand']

    def product_image(self, obj):
        if obj.parent_product_pro_image.exists():
            return format_html('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.format(
                obj.parent_product_pro_image.last().image.url,
                (obj.parent_product_pro_image.last().image_alt_text or obj.parent_product_pro_image.last().image_name),
                obj.parent_product_pro_image.last().image.url
            ))
        return '-'

    def product_gst(self, obj):
        if obj.gst:
            return "{} %".format(obj.gst)
        return ''

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
            )
        ] + urls
        return urls


def deactivate_selected_child_products(modeladmin, request, queryset):
    queryset.update(status='deactivated')
deactivate_selected_child_products.short_description = "Deactivate Selected Products"


def approve_selected_child_products(modeladmin, request, queryset):
    fail_skus = []
    success_skus = []
    for record in queryset:
        parent_sku = ParentProduct.objects.filter(parent_id=record.parent_product.parent_id).last()
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
        modeladmin.message_user(
            request,
            "All selected Child SKUs were successfully approved along with their Parent SKU activation where required",
            level=messages.SUCCESS
        )
    else:
        modeladmin.message_user(request, "All selected Child SKUs were successfully approved", level=messages.SUCCESS)
approve_selected_child_products.short_description = "Approve Selected Products"


class ChildProductImageAdmin(admin.TabularInline):
    model = ChildProductImage


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
                r'^products-export-for-vendor/$',
                self.admin_site.admin_view(products_export_for_vendor),
                name='products_export_for_vendor'
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
                r'^product-price-upload/$',
                self.admin_site.admin_view(ProductPriceUpload.as_view()),
                name="product_price_upload"
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
                r'^product-csv-upload/$',
                self.admin_site.admin_view(product_csv_upload),
                name="product-csv-upload"
            ),
            url(
                r'^chld-products-download-sample-csv/$',
                self.admin_site.admin_view(ChildProductsDownloadSampleCSV),
                name="child-products-download-sample-csv"
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
        'product_brand', 'product_ean_code', 'product_mrp',
        'product_hsn', 'product_gst', 'products_image', 'status'
    ]

    # search_fields = ['product_name', 'id', 'product_gf_code']
    search_fields = ['product_name', 'id']
    # list_filter = [BrandFilter, CategorySearch, ProductSearch, 'status']
    list_filter = [CategorySearch, ProductBrandSearch, ProductSearch, ChildParentIDFilter, 'status']
    # prepopulated_fields = {'product_slug': ('product_name',)}
    # inlines = [
    #     ProductCategoryAdmin, ProductOptionAdmin,
    #     ProductImageAdmin, ProductTaxMappingAdmin
    # ]
    inlines = [ChildProductImageAdmin]
    # autocomplete_fields = ['product_hsn', 'product_brand']
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
        elif not obj.use_parent_image and obj.child_product_pro_image.exists():
            return format_html('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.format(
                obj.child_product_pro_image.last().image.url,
                (obj.child_product_pro_image.last().image_alt_text or obj.child_product_pro_image.last().image_name),
                obj.child_product_pro_image.last().image.url
            ))
        return '-'

    def product_gst(self, obj):
        if obj.product_gst:
            return "{} %".format(obj.product_gst)
        return ''
    product_gst.short_description = 'Product GST'

    def get_changeform_initial_data(self, request):
        if request.GET.get('product'):
            product_details = Product.objects.filter(pk=int(request.GET.get('product'))).last()
            return {
                'parent_product': product_details.parent_product
            }
        return super().get_changeform_initial_data(request)


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
        list_display = [
            'product' ,'sku_code', 'mrp', 'price_to_service_partner','price_to_retailer', 'price_to_super_retailer',
            'shop', 'cash_discount','loyalty_incentive','margin','start_date', 'end_date', 'status'
        ]
        field_names = [field.name for field in meta.fields if field.name in list_display]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in list_display])
        return response
    export_as_csv_productprice.short_description = "Download CSV of Selected ProductPrice"


class ProductPriceAdmin(admin.ModelAdmin, ExportProductPrice):
    resource_class = ProductPriceResource
    form = ProductPriceNewForm
    actions = ['export_as_csv_productprice', 'approve_product_price', 'disapprove_product_price']
    list_select_related = ('product', 'seller_shop', 'buyer_shop', 'city',
                           'pincode')
    list_display = [
        'product', 'product_sku', 'product_mrp', 'selling_price',
        'seller_shop', 'buyer_shop', 'city', 'pincode',
        'start_date', 'end_date', 'approval_status', 'status'
    ]

    autocomplete_fields = ['product']
    search_fields = [
        'product__product_name', 'product__product_gf_code',
        'product__product_brand__brand_name', 'seller_shop__shop_name',
        'buyer_shop__shop_name'
    ]
    list_filter = [
        ProductSKUSearch, ProductFilter, ShopFilter, MRPSearch, CityFilter, ProductCategoryFilter,
        ('start_date', DateRangeFilter), ('end_date', DateRangeFilter),
        'approval_status']
    fields = ('product', 'mrp', 'selling_price', 'seller_shop',
              'buyer_shop', 'city', 'pincode',
              'start_date', 'end_date', 'approval_status')

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
                    'start_date', 'end_date', 'approval_status')
        return self.readonly_fields

    def product_sku(self, obj):
        return obj.product.product_sku

    product_sku.short_description = 'Product SKU'

    def product_mrp(self, obj):
        if obj.product.product_mrp:
            return obj.product.product_mrp
        elif obj.mrp:
            return obj.mrp
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

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def get_form(self, request, obj=None, **kwargs):
        if request.user.is_superuser:
            kwargs['form'] = ProductPriceNewForm
        elif request.user.has_perm('products.add_productprice'):
            kwargs['form'] = ProductPriceAddPerm
        elif request.user.has_perm('products.change_productprice'):
            kwargs['form'] = ProductPriceChangePerm
        return super().get_form(request, obj, **kwargs)

    def get_queryset(self, request):
        qs = super(ProductPriceAdmin, self).get_queryset(request)
        if request.user.is_superuser or request.user.has_perm('products.change_productprice'):
            return qs
        return qs.filter(
            Q(seller_shop__related_users=request.user) |
            Q(seller_shop__shop_owner=request.user),
            approval_status=ProductPrice.APPROVAL_PENDING
        ).distinct()


class ProductHSNAdmin(admin.ModelAdmin, ExportCsvMixin):
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
admin.site.register(ProductPrice, ProductPriceAdmin)
admin.site.register(ProductHSN, ProductHSNAdmin)
admin.site.register(ProductCapping, ProductCappingAdmin)
admin.site.register(ProductTaxMapping, ProductTaxAdmin)
admin.site.register(BulkProductTaxUpdate, BulkProductTaxUpdateAdmin)
admin.site.register(ParentProduct, ParentProductAdmin)
admin.site.register(BulkUploadForGSTChange, BulkUploadForGSTChangeAdmin)