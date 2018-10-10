from django.contrib import admin
from .models import (Size,Fragrance,Flavor,Color,PackageSize,ProductOption,
                     Product,ProductHistory,ProductCategory,ProductCategoryHistory,ProductImage,ProductPrice,
                     ProductSurcharge,Tax,Weight,ProductTaxMapping, ProductCSV)
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .forms import ProductCSVForm
#from categories.models import Category

# Register your models here.
admin.site.register(Size)
admin.site.register(Fragrance)
admin.site.register(Flavor)
admin.site.register(Color)
admin.site.register(PackageSize)
admin.site.register(Weight)
admin.site.register(Tax)

class ProductCSVAdmin(admin.ModelAdmin):
    form = ProductCSVForm

class ProductOptionAdmin(admin.TabularInline):
    model = ProductOption

class ProductCategoryAdmin(admin.TabularInline):
    model = ProductCategory

class ProductImageAdmin(admin.TabularInline):
    model = ProductImage

class ProductTaxMappingAdmin(admin.TabularInline):
    model = ProductTaxMapping

class ProductSurchargeAdmin(admin.TabularInline):
    model = ProductSurcharge

class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'product_slug']
    prepopulated_fields = {'product_slug': ('product_name',)}
    inlines = [ProductCategoryAdmin,ProductOptionAdmin,ProductImageAdmin,ProductTaxMappingAdmin,ProductSurchargeAdmin]

#admin.site.register(Category)
#admin.site.register(ProductPrice)


# class OrderItemInline(admin.TabularInline):
#     model = OrderItem
#     raw_id_fields = ['product']
#
#
# class OrderAdmin(admin.ModelAdmin):
#     list_display = ['id', 'first_name', 'last_name', 'email', 'address', 'postal_code', 'city', 'paid', 'created',
#                     'updated']
#     list_filter = ['paid', 'created', 'updated']
#     inlines = [OrderItemInline

admin.site.register(Product,ProductAdmin)
admin.site.register(ProductCSV, ProductCSVAdmin)
