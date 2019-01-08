from django.db import models
from retailer_backend.validators import *
from addresses.models import Country,State,City,Area
from categories.models import Category
from shops.models import Shop
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
import urllib.request
import csv
import codecs
from brand.models import Brand,Vendor
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

SIZE_UNIT_CHOICES = (
        ('mm', 'Millimeter'),
        ('cm', 'Centimeter'),
        ('dm', 'Decimeter'),
        ('m', 'Meter'),
    )

WEIGHT_UNIT_CHOICES = (
        ('kg', 'Kilogram'),
        ('gm', 'Gram'),
        ('mg', 'Milligram'),
    )

class Size(models.Model):
    size_value = models.CharField(max_length=255, validators=[ValueValidator], null=True, blank=True)
    size_unit = models.CharField(max_length=255, validators=[UnitNameValidator], choices=SIZE_UNIT_CHOICES, default = 'mm')
    size_name = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.size_name

class Color(models.Model):
    color_name = models.CharField(max_length=255, validators=[ProductNameValidator])
    color_code = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.color_name

class Fragrance(models.Model):
    fragrance_name = models.CharField(max_length=255, validators=[ProductNameValidator])
    fragrance_code = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.fragrance_name

class Flavor(models.Model):
    flavor_name = models.CharField(max_length=255, validators=[ProductNameValidator])
    flavor_code = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.flavor_name

class Weight(models.Model):
    weight_value = models.CharField(max_length=255, null=True, blank=True)
    weight_unit = models.CharField(max_length=255, validators=[UnitNameValidator],choices=WEIGHT_UNIT_CHOICES, default = 'kg')
    weight_name = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.weight_name

class PackageSize(models.Model):
    pack_size_value = models.CharField(max_length=255, null=True, blank=True)
    pack_size_unit = models.CharField(max_length=255, validators=[UnitNameValidator], choices=SIZE_UNIT_CHOICES, default = 'mm')
    pack_size_name = models.SlugField(unique=True)
    pack_length = models.CharField(max_length=255, validators=[UnitNameValidator], null=True, blank=True)
    pack_width = models.CharField(max_length=255, validators=[UnitNameValidator], null=True, blank=True)
    pack_height = models.CharField(max_length=255, validators=[UnitNameValidator], null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.pack_size_name

class Product(models.Model):
    product_name = models.CharField(max_length=255,validators=[ProductNameValidator])
    product_slug = models.SlugField(max_length=255)
    product_short_description = models.CharField(max_length=255,validators=[ProductNameValidator],null=True,blank=True)
    product_long_description = models.TextField(null=True,blank=True)
    product_sku = models.CharField(max_length=255, blank=False, unique=True)
    product_gf_code = models.CharField(max_length=255, blank=False, unique=True)
    product_ean_code = models.CharField(max_length=255, blank=True)
    product_brand = models.ForeignKey(Brand,related_name='prodcut_brand_product',blank=False,on_delete=models.CASCADE)
    #hsn_code = models.PositiveIntegerField(null=True,blank=True,validators=[EanCodeValidator])
    product_inner_case_size = models.CharField(max_length=255,blank=False, default=1)
    product_case_size = models.CharField(max_length=255,blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.product_slug = slugify(self.product_name)
        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return self.product_name

    @classmethod
    def _product_list(cls):
        id = threadlocals.get_current_product()
        if id is not None:
            return [id]
        else:
            return Product.objects.all().values('pk').query
    def get_my_id(self):
        return self.id

class ProductSKUGenerator(models.Model):
    parent_cat_sku_code = models.CharField(max_length=3,validators=[CapitalAlphabets],help_text="Please enter three characters for SKU")
    cat_sku_code = models.CharField(max_length=3,validators=[CapitalAlphabets],help_text="Please enter three characters for SKU")
    brand_sku_code = models.CharField(max_length=3,validators=[CapitalAlphabets],help_text="Please enter three characters for SKU")
    last_auto_increment = models.CharField(max_length=8)

class ProductOption(models.Model):
    product = models.ForeignKey(Product, related_name='product_opt_product', on_delete=models.CASCADE)
    size = models.ForeignKey(Size,related_name='size_pro_option',null=True,blank=True,on_delete=models.CASCADE)
    color = models.ForeignKey(Color,related_name='color_pro_option',null=True,blank=True,on_delete=models.CASCADE)
    fragrance = models.ForeignKey(Fragrance,related_name='fragrance_pro_option',null=True,blank=True,on_delete=models.CASCADE)
    flavor = models.ForeignKey(Flavor,related_name='flavor_pro_option',null=True,blank=True,on_delete=models.CASCADE)
    weight = models.ForeignKey(Weight,related_name='weight_pro_option',null=True,blank=True,on_delete=models.CASCADE)
    package_size = models.ForeignKey(PackageSize,related_name='package_size_pro_option',null=True,blank=True,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class ProductHistory(models.Model):
    product_name = models.CharField(max_length=255,validators=[ProductNameValidator])
    product_short_description = models.CharField(max_length=255,validators=[ProductNameValidator],null=True,blank=True)
    product_long_description = models.TextField(null=True,blank=True)
    product_sku = models.CharField(max_length=255,null=True,blank=True)
    product_ean_code = models.CharField(max_length=255, null=True,blank=True,validators=[EanCodeValidator])
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class ProductPrice(models.Model):
    product = models.ForeignKey(Product,related_name='product_pro_price',on_delete=models.CASCADE)
    #country = models.ForeignKey(Country,related_name='country_pro_price',null=True,blank=True,on_delete=models.CASCADE)
    #state = models.ForeignKey(Country,related_name='state_pro_price',null=True,blank=True,on_delete=models.CASCADE)
    city = models.ForeignKey(City,related_name='city_pro_price',null=True,blank=True,on_delete=models.CASCADE)
    area = models.ForeignKey(Area,related_name='area_pro_price',null=True,blank=True,on_delete=models.CASCADE)
    #pincode_from = models.PositiveIntegerField(default=0,null=True,blank=True)
    #pincode_to = models.PositiveIntegerField(default=0,null=True,blank=True)
    mrp = models.FloatField(default=0,null=True,blank=True)
    # price_to_service_partner = models.FloatField(default=0,null=True,blank=True)
    # price_to_retailer = models.FloatField(default=0,null=True,blank=True)
    # price_to_super_retailer = models.FloatField(default=0,null=True,blank=True)
    shop = models.ForeignKey(Shop,related_name='shop_product_price', null=True,blank=True,on_delete=models.CASCADE)
    #price = models.FloatField(default=0)
    price_to_service_partner = models.FloatField(default=0,null=True,blank=True)
    price_to_retailer = models.FloatField(default=0,null=True,blank=True)
    price_to_super_retailer = models.FloatField(default=0,null=True,blank=True)
    start_date = models.DateTimeField(null=True,blank=True)
    end_date = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class ProductCategory(models.Model):
    product = models.ForeignKey(Product, related_name='product_pro_category',on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name='category_pro_category',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class ProductCategoryHistory(models.Model):
    product = models.ForeignKey(Product, related_name='product_pro_cat_history',on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name='category_pro_cat_history',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class ProductImage(models.Model):
    product = models.ForeignKey(Product,related_name='product_pro_image',on_delete=models.CASCADE)
    image_name = models.CharField(max_length=255,validators=[NameValidator])
    image_alt_text = models.CharField(max_length=255,null=True,blank=True,validators=[NameValidator])
    image = models.ImageField(upload_to='product_image')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class Tax(models.Model):
    TAX_CHOICES = (
            ("cess", "Cess"),
            ("gst", "GST"),
            ("surcharge", "Surcharge"),
        )

    tax_name = models.CharField(max_length=255,validators=[ProductNameValidator])
    tax_type=  models.CharField(max_length=255, choices=TAX_CHOICES, null=True)
    tax_percentage = models.FloatField(default=0)
    tax_start_at = models.DateTimeField(null=True,blank=True)
    tax_end_at = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.tax_name

class ProductTaxMapping(models.Model):
    product = models.ForeignKey(Product,related_name='product_pro_tax',on_delete=models.CASCADE)
    tax = models.ForeignKey(Tax,related_name='tax_pro_tax',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

# class ProductSurcharge(models.Model):
#     product = models.ForeignKey(Product, related_name='product_pro_surcharge',on_delete=models.CASCADE)
#     surcharge_name = models.CharField(max_length=255, validators=[NameValidator])
#     surcharge_percentage = models.FloatField(default=0)
#     surcharge_start_at = models.DateTimeField(null=True, blank=True)
#     surcharge_end_at = models.DateTimeField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateTimeField(auto_now=True)
#     status = models.BooleanField(default=True)

class ProductCSV(models.Model):
    file = models.FileField(upload_to='products/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.file)

    def sample_file(self):
        return mark_safe("<a href='%s'>Download</a>" % ("/admin/products/product/productsuploadsample/"))

    sample_file.allow_tags = True

class ProductPriceCSV(models.Model):
    file = models.FileField(upload_to='products/price/')
    country = models.ForeignKey(Country,null=True,blank=True, on_delete=models.CASCADE)
    states = models.ForeignKey(State, null=True,blank=True, on_delete=models.CASCADE)
    city = models.ForeignKey(City, null=True,blank=True, on_delete=models.CASCADE)
    area = models.ForeignKey(Area,null=True,blank=True,on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.file)

class ProductVendorMapping(models.Model):
    vendor = models.ForeignKey(Vendor,related_name='vendor_brand_mapping',on_delete=models.CASCADE)
    product = models.ForeignKey(Product,related_name='product_vendor_mapping',on_delete=models.CASCADE)
    product_price = models.FloatField(verbose_name='Brand To Gram Price')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return '%s' % (self.vendor)

@receiver(post_save, sender=Vendor)
def create_product_vendor_mapping(sender, instance=None, created=False, **kwargs):
    vendor = instance
    file = instance.vendor_products_csv
    if file:
        reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
        first_row = next(reader)
        ProductVendorMapping.objects.bulk_create([ProductVendorMapping(vendor=vendor, product_id = row[0], product_price=row[2]) for row in reader if row[2]])

@receiver(pre_save, sender=ProductCategory)
def create_product_sku(sender, instance=None, created=False, **kwargs):
    cat_sku_code = instance.category.category_sku_part
    parent_cat_sku_code = instance.category.category_parent.category_sku_part if instance.category.category_parent else cat_sku_code
    brand_sku_code = instance.product.product_brand.brand_code
    last_sku = ProductSKUGenerator.objects.filter(cat_sku_code=cat_sku_code,parent_cat_sku_code=parent_cat_sku_code,brand_sku_code=brand_sku_code).last()
    if last_sku:
        last_sku_increment = str(int(last_sku.last_auto_increment) + 1).zfill(len(last_sku.last_auto_increment))
    else:
        last_sku_increment = '00000001'
    ProductSKUGenerator.objects.create(cat_sku_code=cat_sku_code,parent_cat_sku_code=parent_cat_sku_code,brand_sku_code=brand_sku_code,last_auto_increment=last_sku_increment)
    product = Product.objects.get(pk=instance.product_id)
    product.product_sku="%s%s%s%s"%(cat_sku_code,parent_cat_sku_code,brand_sku_code,last_sku_increment)
    product.save()
