from django.contrib import admin
from django.http import HttpResponse
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.contrib.admin import TabularInline

from admin_auto_filters.filters import AutocompleteFilter
from daterange_filter.filter import DateRangeFilter
from retailer_backend.admin import InputFilter
from .models import *
from .views import (
    sp_sr_productprice, load_cities, load_sp_sr, export,
    load_brands, products_filter_view, products_price_filter_view,
    ProductsUploadSample, products_csv_upload_view, gf_product_price,
    load_gf, products_export_for_vendor, products_vendor_mapping,
    MultiPhotoUploadView , ProductPriceAutocomplete, ShopPriceAutocomplete
    )
from .resources import (
    SizeResource, ColorResource, FragranceResource,
    FlavorResource, WeightResource, PackageSizeResource,
    ProductResource, ProductPriceResource, TaxResource
    )

from .forms import ProductPriceForm

class ProductFilter(AutocompleteFilter):
    title = 'Product Name' # display title
    field_name = 'product' # name of the foreign key field

class ShopFilter(AutocompleteFilter):
    title = 'Shop' # display title
    field_name = 'shop' # name of the foreign key field

class ProductImageMainAdmin(admin.ModelAdmin):
    readonly_fields = ['image_thumbnail']
    search_fields = ['image', 'image_name']
    list_display = ('product','image', 'image_name')
    list_filter = [ProductFilter,]

    class Media:
        pass


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        exclude_fields = ['created_at', 'modified_at']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])
        return response
    export_as_csv.short_description = "Download CSV of Selected Objects"


class BrandFilter(AutocompleteFilter):
    title = 'Brand'  # display title
    field_name = 'product_brand'  # name of the foreign key field


class CategoryFilter(AutocompleteFilter):
    title = 'Category'  # display title
    field_name = 'category_name'  # name of the foreign key field

class VendorFilter(AutocompleteFilter):
    title = 'Vendor Name' # display title
    field_name = 'vendor' # name of the foreign key field

class ProductVendorMappingAdmin(admin.ModelAdmin):
    fields = ('vendor', 'product', 'product_price','product_mrp','case_size')
    list_display = ('vendor', 'product', 'product_price','product_mrp','case_size','created_at','status')
    list_filter = [VendorFilter,ProductFilter,]

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


class CategorySearch(InputFilter):
    parameter_name = 'qty'
    title = 'Category'

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(
                Q(product_pro_category__category__category_name__icontains=self.value())
            )

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


class ProductAdmin(admin.ModelAdmin, ExportCsvMixin):
    resource_class = ProductResource

    class Media:
            pass
    exclude = ('product_sku',)

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
                self.admin_site.admin_view(sp_sr_productprice),
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
        ] + urls
        return urls

    actions = ['export_as_csv']
    list_display = [
        'product_sku', 'product_name', 'product_short_description',
        'product_brand', 'product_gf_code','product_images'
    ]
    search_fields = ['product_name', 'id', 'product_gf_code']
    list_filter = [BrandFilter, CategorySearch, ProductSearch]
    prepopulated_fields = {'product_slug': ('product_name',)}
    inlines = [
        ProductCategoryAdmin, ProductOptionAdmin,
        ProductImageAdmin, ProductTaxMappingAdmin
    ]

    def product_images(self,obj):
        if obj.product_pro_image.first():
            return mark_safe('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.
                             format(obj.product_pro_image.first().image.url,obj.product_pro_image.first().image_alt_text,
                                    obj.product_pro_image.first().image.url))

    product_images.short_description = 'Product Image'

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
class ProductPriceAdmin(admin.ModelAdmin, ExportCsvMixin):
    resource_class = ProductPriceResource
    form = ProductPriceForm
    actions = ["export_as_csv"]
    list_display = [
        'product', 'product_gf_code', 'mrp', 'price_to_service_partner',
        'price_to_retailer', 'price_to_super_retailer','shop',
        'start_date', 'end_date', 'status'
    ]
    autocomplete_fields=['product',]
    search_fields = [
        'product__product_name', 'product__product_gf_code',
        'product__product_brand__brand_name', 'shop__shop_name'
    ]
    list_filter= [ProductFilter,ShopFilter,MRPSearch,('start_date', DateRangeFilter),('end_date', DateRangeFilter)]
    fields=('product','city','area','mrp','shop','price_to_retailer','price_to_super_retailer','price_to_service_partner','start_date','end_date','status')
    class Media:
        pass
    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('mrp','price_to_retailer','price_to_super_retailer','price_to_service_partner' )
        return self.readonly_fields

    def product_gf_code(self, obj):
        return obj.product.product_gf_code

    product_gf_code.short_description = 'Gf Code'

    def get_queryset(self, request):
        qs = super(ProductPriceAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(shop__related_users=request.user) |
            Q(shop__shop_owner=request.user),
            status=True
        ).distinct()


class ProductHSNAdmin(admin.ModelAdmin, ExportCsvMixin):
    fields = ['product_hsn_code']
    list_display = ['product_hsn_code']
    actions = ['export_as_csv']


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
