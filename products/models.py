from django.db import models
from retailer_backend.validators import *
from addresses.models import Country,State,City,Area
from categories.models import Category
from shops.models import ShopType
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
import urllib.request
import csv
import codecs

class Size(models.Model):
    size_name = models.CharField(max_length=255, validators=[NameValidator])
    size_value = models.CharField(max_length=255, validators=[ValueValidator], null=True, blank=True)
    size_unit = models.CharField(max_length=255, validators=[UnitNameValidator], null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class Color(models.Model):
    color_name = models.CharField(max_length=255, validators=[NameValidator])
    color_code = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)


class Fragrance(models.Model):
    fragrance_name = models.CharField(max_length=255, validators=[NameValidator])
    fragrance_code = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class Flavor(models.Model):
    flavor_name = models.CharField(max_length=255, validators=[NameValidator])
    flavor_code = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class Weight(models.Model):
    weight_name = models.CharField(max_length=255, validators=[NameValidator])
    weight_value = models.CharField(max_length=255, null=True, blank=True)
    weight_unit = models.CharField(max_length=255, validators=[UnitNameValidator], null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class PackageSize(models.Model):
    pack_size_name = models.CharField(max_length=255, validators=[NameValidator])
    pack_size_value = models.CharField(max_length=255, null=True, blank=True)
    pack_size_unit = models.CharField(max_length=255, validators=[UnitNameValidator], null=True, blank=True)
    pack_length = models.CharField(max_length=255, validators=[UnitNameValidator], null=True, blank=True)
    pack_width = models.CharField(max_length=255, validators=[UnitNameValidator], null=True, blank=True)
    pack_height = models.CharField(max_length=255, validators=[UnitNameValidator], null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class Product(models.Model):
    product_name = models.CharField(max_length=255,validators=[ProductNameValidator])
    product_slug = models.SlugField()
    product_short_description = models.CharField(max_length=255,validators=[ProductNameValidator],null=True,blank=True)
    product_long_description = models.TextField(null=True,blank=True)
    product_sku = models.CharField(max_length=255, null=True,blank=True)
    product_ean_code = models.CharField(max_length=255, null=True,blank=True,validators=[EanCodeValidator])
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

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
    shop_type = models.ForeignKey(ShopType,related_name='shop_type_product_price', null=True,blank=True,on_delete=models.CASCADE)
    price = models.FloatField(default=0)
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
    tax_name = models.CharField(max_length=255,validators=[NameValidator])
    tax_percentage = models.FloatField(default=0)
    tax_start_at = models.DateTimeField(null=True,blank=True)
    tax_end_at = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class ProductTaxMapping(models.Model):
    product = models.ForeignKey(Product,related_name='product_pro_tax',on_delete=models.CASCADE)
    tax = models.ForeignKey(Tax,related_name='tax_pro_tax',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class ProductSurcharge(models.Model):
    product = models.ForeignKey(Product, related_name='product_pro_surcharge',on_delete=models.CASCADE)
    surcharge_name = models.CharField(max_length=255, validators=[NameValidator])
    surcharge_percentage = models.FloatField(default=0)
    surcharge_start_at = models.DateTimeField(null=True, blank=True)
    surcharge_end_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class ProductCSV(models.Model):
    file = models.FileField(upload_to='products/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.file)
