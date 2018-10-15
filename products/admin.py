from django.contrib import admin
from .models import *
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django.contrib import messages
from django import forms
import csv
import codecs
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from retailer_backend.validators import *
from categories.models import Category

# Register your models here.
admin.site.register(Size)
admin.site.register(Fragrance)
admin.site.register(Flavor)
admin.site.register(Color)
admin.site.register(PackageSize)
admin.site.register(Weight)
admin.site.register(Tax)

class ProductCSVForm(forms.ModelForm):

    class Meta:
        model = ProductCSV
        fields = ('file', )

class ProductCSVAdmin(admin.ModelAdmin):
    form = ProductCSVForm
    list_display = ['file']


    def save_model(self, request, obj, form, change):
        file = form.cleaned_data['file']
        errors = self.read_csv(file,request)
        if not errors:
            messages.set_level(request, messages.SUCCESS)
            messages.success(request,"Products uploaded successfully!")
            super(ProductCSVAdmin, self).save_model(request, obj, form, change)

    def read_csv(self, path,request):
        reader = csv.reader(codecs.iterdecode(path, 'utf-8'))
        first_row = next(reader)
        errors = []
        error_rows = {}
        for id,row in enumerate(reader):
            error_rows[id] = []

            try:
                ProductNameValidator(row[0])
            except:
                error_rows[id].append(row[0])

            try:
                SlugValidator(row[1])
            except:
                error_rows[id].append(row[1])

            try:
                ProductNameValidator(row[2])
            except:
                error_rows[id].append(row[3])

            try:
                ProductNameValidator(row[3])
            except:
                error_rows[id].append(row[3])

            try:
                SKUValidator(row[4])
            except:
                error_rows[id].append(row[4])

            try:
                EanCodeValidator(row[5])
            except:
                error_rows[id].append(row[5])

            try:
                StatusValidator(row[6])
            except:
                error_rows[id].append(row[6])

            try:
                IDValidator(row[7])
            except:
                error_rows[id].append(row[7])

            try:
                StatusValidator(row[8])
            except:
                error_rows[id].append(row[8])

            try:
                IDValidator(row[9])
            except:
                error_rows[id].append(row[9])

            try:
                IDValidator(row[10])
            except:
                error_rows[id].append(row[10])

            try:
                IDValidator(row[11])
            except:
                error_rows[id].append(row[11])

            try:
                IDValidator(row[12])
            except:
                error_rows[id].append(row[12])

            try:
                IDValidator(row[13])
            except:
                error_rows[id].append(row[13])

            try:
                IDValidator(row[14])
            except:
                error_rows[id].append(row[14])

            try:
                IDValidator(row[15])
            except:
                error_rows[id].append(row[15])

            try:
                StatusValidator(row[16])
            except:
                error_rows[id].append(row[16])

            try:
                NameValidator(row[17])
            except:
                error_rows[id].append(row[17])

            try:
                PercentageValidator(row[18])
            except:
                error_rows[id].append(row[18])

            try:
                DateTimeValidator(row[19])
            except:
                error_rows[id].append(row[19])

            try:
                DateTimeValidator(row[20])
            except:
                error_rows[id].append(row[20])

            try:
                StatusValidator(row[21])
            except:
                error_rows[id].append(row[21])
        for k,v in error_rows.items():
            if v:
                errors.append(v)
                messages.set_level(request, messages.ERROR)
                messages.error(request,"You have errors at row[%s] in values %s"%(str(k+2), [str(i) for i in v]))
        if not errors:
            reader = csv.reader(codecs.iterdecode(path, 'utf-8'))
            first_row = next(reader)
            for row in reader:
                self.create_product(product_name = row[0],\
                product_slug = row[1],\
                product_short_description = row[2],\
                product_long_description = row[3],\
                product_sku = row[4],\
                product_ean_code = row[5],\
                product_status = row[6],\
                p_cat_id = row[7],\
                p_cat_status = row[8],\
                p_size_id = row[9],\
                p_color_id = row[10],\
                p_fragrance_id = row[11],\
                p_flavor_id = row[12],\
                p_weight_id = row[13],\
                p_package_size_id = row[14],\
                p_tax_id = row[15],\
                p_tax_status = row[16],\
                p_surcharge_name = row[17],\
                p_surcharge_percentage = row[18],\
                p_surcharge_start_at = row[19],\
                p_surcharge_end_at = row[20],\
                p_surcharge_status = row[21])
        return errors

    def create_product(self, **kwargs):
        product = Product.objects.create(product_name=kwargs.get('product_name'),\
                  product_slug=kwargs.get('product_slug'),\
                  product_short_description=kwargs.get('product_short_description'),\
                  product_long_description = kwargs.get('product_long_description'),\
                  product_sku = kwargs.get('product_sku'),\
                  product_ean_code = kwargs.get('product_ean_code'),\
                  status=kwargs.get('product_status'))

        category = Category.objects.get(pk=kwargs.get('p_cat_id'))
        product_category = ProductCategory.objects.create(product=product,\
                  category=category, status=kwargs.get('p_cat_status'))

        size = Size.objects.get(pk=kwargs.get('p_size_id'))
        color = Color.objects.get(pk=kwargs.get('p_color_id'))
        fragrance = Fragrance.objects.get(pk=kwargs.get('p_fragrance_id'))
        flavor = Flavor.objects.get(pk=kwargs.get('p_flavor_id'))
        weight = Weight.objects.get(pk=kwargs.get('p_weight_id'))
        packagesize = PackageSize.objects.get(pk=kwargs.get('p_package_size_id'))
        productoptions = ProductOption.objects.create(product=product,size=size,\
                color=color,fragrance=fragrance,flavor=flavor,weight=weight,\
                package_size=packagesize)

        tax = Tax.objects.get(pk=kwargs.get('p_tax_id'))
        producttax = ProductTaxMapping(product=product,tax=tax,status=kwargs.get('p_tax_status'))

        surcharge = ProductSurcharge.objects.create(product=product, surcharge_name=kwargs.get('p_surcharge_name'),\
                  surcharge_percentage= kwargs.get('p_surcharge_percentage'),\
                  surcharge_start_at=kwargs.get('p_surcharge_start_at'), \
                  surcharge_end_at=kwargs.get('p_surcharge_end_at'), \
                  status = kwargs.get('p_surcharge_percentage'))

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

admin.site.register(Product,ProductAdmin)
admin.site.register(ProductCSV, ProductCSVAdmin)
