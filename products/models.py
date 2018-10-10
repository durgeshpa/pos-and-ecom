from django.db import models
from retailer_backend.validators import NameValidator,ProductNameValidator,EanCodeValidator,ValueValidator,UnitNameValidator
from addresses.models import Country,State,City,Area
from categories.models import Category
from shops.models import ShopType
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

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

    def file_full_path(self, fileurl):
        return ''.join(['http://', get_current_site(request).domain,fileurl])

    def read_csv(self, path):
        with open(path, 'r') as f:
            reader = csv.reader(f,  delimiter=',')
            first_row = next(reader)
            for row in reader:
                product_name = row[0]
                product_slug = row[1]
                product_short_description = row[2]
                product_long_description = row[3]
                product_sku = row[4]
                product_ean_code = row[5]
                product_status = row[6]
                p_cat_id = row[7]
                p_size_id = row[8]
                p_color_id = row[9]
                p_fragrance_id = row[10]
                p_flavor_id = row[11]
                p_weight_id = row[12]
                p_package_size_id = row[13]
                p_tax_id = row[14]
                p_surcharge_name = row[15]
                p_surcharge_start_at = row[16]
                p_surcharge_status = row[17]
                print(product_name,product_slug,product_short_description,\
        product_long_description,product_sku,product_ean_code,\
        product_status,p_cat_id,p_size_id,p_color_id,p_fragrance_id,\
        p_flavor_id,p_weight_id,p_package_size_id,p_tax_id,\
        p_surcharge_name,p_surcharge_start_at,\
        p_surcharge_status)


    def save(self, *args, **kwargs):
        super(ProductCSV, self).save(*args, **kwargs)
        filename = self.file.url
        self.read_csv(filename)
        print("##############################")
