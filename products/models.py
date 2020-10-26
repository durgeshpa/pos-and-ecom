import codecs
import csv
import datetime
import re
import urllib.request

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from addresses.models import Address, Area, City, Country, Pincode, State
from brand.models import Brand, Vendor
from categories.models import Category
from coupon.models import Coupon
from retailer_backend.messages import ERROR_MESSAGES, VALIDATION_ERROR_MESSAGES
from retailer_backend.validators import *
from shops.models import Shop

# from analytics.post_save_signal import get_category_product_report, get_master_report


SIZE_UNIT_CHOICES = (
        ('mm', 'Millimeter'),
        ('cm', 'Centimeter'),
        ('dm', 'Decimeter'),
        ('m', 'Meter'),
    )

WEIGHT_UNIT_CHOICES = (
        #('kg', 'Kilogram'),
        ('gm', 'Gram'),
        # ('mg', 'Milligram'),
        # ('l', 'Litre'),
        # ('ml', 'Milliliter'),
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

    class Meta:
        verbose_name = _("Package Size")
        verbose_name_plural = _("Package Sizes")

class ProductHSN(models.Model):
    #product_hsn_name= models.CharField(max_length=255, null=True, blank=True)
    product_hsn_code = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product_hsn_code

class ParentProduct(models.Model):
    parent_id = models.CharField(max_length=255, validators=[ParentIDValidator])
    name = models.CharField(max_length=255, validators=[ProductNameValidator])
    parent_slug = models.SlugField(max_length=255)
    parent_brand = models.ForeignKey(Brand, related_name='parent_brand_product', blank=False, on_delete=models.CASCADE)
    # category = models.ForeignKey(Category, related_name='category_parent_category', on_delete=models.CASCADE)
    product_hsn = models.ForeignKey(ProductHSN, related_name='parent_hsn', blank=False, on_delete=models.CASCADE)
    GST_CHOICES = (
        (0, '0 %'),
        (5, '5 %'),
        (12, '12 %'),
        (18, '18 %'),
        (28, '28 %'),
    )
    gst = models.PositiveIntegerField(default=0, choices=GST_CHOICES)
    CESS_CHOICES = (
        (0, '0 %'),
        (12, '12 %'),
    )
    cess = models.PositiveIntegerField(default=0, choices=CESS_CHOICES, blank=True)
    surcharge = models.PositiveIntegerField(default=0, blank=True)
    brand_case_size = models.PositiveIntegerField(blank=False)
    inner_case_size = models.PositiveIntegerField(blank=False, default=1)
    PRODUCT_TYPE_CHOICES = (
        ('b2b', 'B2B'),
        ('b2c', 'B2C'),
        ('both', 'Both B2B and B2C'),
    )
    product_type = models.CharField(max_length=5, choices=PRODUCT_TYPE_CHOICES)
    # image = models.ImageField(upload_to='parent_product_image', blank=False)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.parent_slug = slugify(self.name)
        super(ParentProduct, self).save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return "{}-{}".format(self.parent_id, self.name)

class ParentProductSKUGenerator(models.Model):
    cat_sku_code = models.CharField(max_length=3, validators=[CapitalAlphabets], help_text="Please enter three characters for SKU")
    brand_sku_code = models.CharField(max_length=3, validators=[CapitalAlphabets], help_text="Please enter three characters for SKU")
    last_auto_increment = models.CharField(max_length=8)

class ParentProductCategory(models.Model):
    parent_product = models.ForeignKey(ParentProduct, related_name='parent_product_pro_category', on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name='parent_category_pro_category', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Parent Product Category")
        verbose_name_plural = _("Parent Product Categories")


class ParentProductImage(models.Model):
    parent_product = models.ForeignKey(ParentProduct, related_name='parent_product_pro_image', on_delete=models.CASCADE)
    image_name = models.CharField(max_length=255, validators=[ProductNameValidator])
    image_alt_text = models.CharField(max_length=255, null=True, blank=True, validators=[NameValidator])
    image = models.ImageField(upload_to='parent_product_image')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    # status = models.BooleanField(default=True)

    def image_thumbnail(self):
        return mark_safe('<img src="{url}" width="{width}" height={height} />'.format(
            url = self.image.url,
            width='500px',
            height='500px',
            )
    )

    def __str__(self):
        return self.image.name


@receiver(pre_save, sender=ParentProductCategory)
def create_parent_product_id(sender, instance=None, created=False, **kwargs):
    parent_product = ParentProduct.objects.get(pk=instance.parent_product.id)
    cat_sku_code = instance.category.category_sku_part
    brand_sku_code = parent_product.parent_brand.brand_code
    last_sku = ParentProductSKUGenerator.objects.filter(cat_sku_code=cat_sku_code, brand_sku_code=brand_sku_code).last()
    if last_sku:
        last_sku_increment = str(int(last_sku.last_auto_increment) + 1).zfill(len(last_sku.last_auto_increment))
    else:
        last_sku_increment = '0001'
    ParentProductSKUGenerator.objects.create(cat_sku_code=cat_sku_code, brand_sku_code=brand_sku_code, last_auto_increment=last_sku_increment)
    parent_product.parent_id = "P%s%s%s"%(cat_sku_code, brand_sku_code, last_sku_increment)
    parent_product.save()

class Product(models.Model):
    product_name = models.CharField(max_length=255, validators=[ProductNameValidator])
    product_slug = models.SlugField(max_length=255, blank=True)
    # product_short_description = models.CharField(max_length=255, validators=[ProductNameValidator], null=True, blank=True)
    # product_long_description = models.TextField(null=True, blank=True)
    product_sku = models.CharField(max_length=255, blank=False, unique=True)
    # product_gf_code = models.CharField(max_length=255, blank=False, unique=True)
    product_ean_code = models.CharField(max_length=255, blank=True)
    # product_hsn = models.ForeignKey(ProductHSN, related_name='product_hsn', null=True, blank=True, on_delete=models.CASCADE)
    # product_brand = models.ForeignKey(Brand, related_name='prodcut_brand_product', blank=False, on_delete=models.CASCADE)
    # product_inner_case_size = models.CharField(max_length=255, null=True)
    # product_case_size = models.CharField(max_length=255, blank=False)
    product_mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    weight_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    weight_unit = models.CharField(max_length=255, validators=[UnitNameValidator], choices=WEIGHT_UNIT_CHOICES, default='gm')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    STATUS_CHOICES = (
        ('pending_approval', 'Pending Approval'),
        ('active', 'Active'),
        ('deactivated', 'Deactivated'),
    )
    status = models.CharField(max_length=20, default='pending_approval', choices=STATUS_CHOICES, blank=False)
    parent_product = models.ForeignKey(ParentProduct, related_name='product_parent_product', null=True, blank=False, on_delete=models.DO_NOTHING)
    REASON_FOR_NEW_CHILD_CHOICES = (
        ('default', 'Default'),
        ('different_mrp', 'Different MRP'),
        ('different_weight', 'Different Weight'),
        ('different_ean', 'Different EAN'),
        ('offer', 'Offer'),
    )
    reason_for_child_sku = models.CharField(max_length=20, choices=REASON_FOR_NEW_CHILD_CHOICES, default='default')
    use_parent_image = models.BooleanField(default=False)
    # child_product_image = models.ImageField(upload_to='child_product_image', blank=True, null=True)
    REASON_FOR_NEW_CHILD_CHOICES = (
        ('none', 'None'),
        ('source', 'Source'),
        ('destination', 'Destination'),
    )
    repackaging_type = models.CharField(max_length=20, choices=REASON_FOR_NEW_CHILD_CHOICES, default='none')

    def save(self, *args, **kwargs):
        self.product_slug = slugify(self.product_name)
        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return "{}-{}".format(self.product_name, self.product_sku)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Child Product'
        verbose_name_plural = 'Child Products'

    @property
    def product_brand(self):
        return self.parent_product.parent_brand if self.parent_product else ''

    @property
    def product_hsn(self):
        return self.parent_product.product_hsn if self.parent_product else ''

    @property
    def product_gst(self):
        return self.parent_product.gst if self.parent_product else ''

    @property
    def product_cess(self):
        return self.parent_product.cess if self.parent_product else ''

    @property
    def product_surcharge(self):
        return self.parent_product.surcharge if self.parent_product else ''

    @property
    def product_case_size(self):
        return self.parent_product.brand_case_size if self.parent_product else ''

    @property
    def parent_name(self):
        return self.parent_product.name if self.parent_product else ''

    @property
    def product_inner_case_size(self):
        return self.parent_product.inner_case_size if self.parent_product else ''

    @property
    def product_short_description(self):
        return self.product_name

    @property
    def product_long_description(self):
        return ''

    @property
    def product_gf_code(self):
        return ''

    @property
    def product_image(self):
        if self.use_parent_image:
            return self.parent_product.image
        return self.child_product_image

    def get_current_shop_price(self, seller_shop_id, buyer_shop_id):
        '''
        Firstly we will only filter using seller shop. If the queryset exists
        we will further filter to city, pincode and buyer shop level.
        '''
        today = datetime.datetime.today()
        buyer_shop_dt = Address.objects.values('city_id', 'pincode_link')\
            .filter(shop_name_id=buyer_shop_id, address_type='shipping')
        if buyer_shop_dt.exists():
            buyer_shop_dt = buyer_shop_dt.last()
        product_price = self.product_pro_price\
            .filter(Q(seller_shop_id=seller_shop_id),
                    Q(city_id=buyer_shop_dt.get('city_id')) | Q(city_id=None),
                    Q(pincode_id=buyer_shop_dt.get('pincode_link')) | Q(pincode_id=None),
                    Q(buyer_shop_id=buyer_shop_id) | Q(buyer_shop_id=None),
                    approval_status=ProductPrice.APPROVED,
                    start_date__lte=today, end_date__gte=today)\
            .order_by('start_date')
        if product_price.count() > 1:
            product_price = product_price.filter(
                city_id=buyer_shop_dt.get('city_id'))
        if product_price.count() > 1:
            product_price = product_price.filter(
                pincode_id=buyer_shop_dt.get('pincode_link', None))
        if product_price.count() > 1:
            product_price = product_price.filter(
                buyer_shop_id=buyer_shop_id)
        if not product_price:
            product_price = self.product_pro_price.filter(seller_shop_id=seller_shop_id, approval_status=ProductPrice.APPROVED, start_date__lte=today, end_date__gte=today).order_by('start_date')
        if not product_price:
            return None
        return product_price.last()

    def get_current_shop_capping(self, seller_shop_id, buyer_shop_id):
        '''
        Firstly we will only filter using seller shop. If the queryset exists
        we will further filter to city, pincode and buyer shop level.
        '''
        today = datetime.datetime.today()
        buyer_shop_dt = Address.objects.values('city_id', 'pincode_link')\
            .filter(shop_name_id=buyer_shop_id, address_type='shipping')
        if buyer_shop_dt.exists():
            buyer_shop_dt = buyer_shop_dt.last()
        product_capping = self.product_pro_capping\
            .filter(Q(seller_shop_id=seller_shop_id),
                    Q(city_id=buyer_shop_dt.get('city_id')) | Q(city_id=None),
                    Q(pincode_id=buyer_shop_dt.get('pincode_link')) | Q(pincode_id=None),
                    Q(buyer_shop_id=buyer_shop_id) | Q(buyer_shop_id=None),
                    status=True,
                    start_date__lte=today, end_date__gte=today)\
            .order_by('start_date')
        if product_capping.count() > 1:
            product_capping = product_capping.filter(
                city_id=buyer_shop_dt.get('city_id'))
        if product_capping.count() > 1:
            product_capping = product_capping.filter(
                pincode_id=buyer_shop_dt.get('pincode_link', None))
        if product_capping.count() > 1:
            product_capping = product_capping.filter(
                buyer_shop_id=buyer_shop_id)
        if not product_capping:
            product_capping = self.product_pro_capping.filter(seller_shop_id=seller_shop_id, status = True, start_date__lte=today, end_date__gte=today).order_by('start_date')
        if not product_capping:
            return None
        return product_capping.last()


    def getPriceByShopId(self, seller_shop_id, buyer_shop_id):
        return self.get_current_shop_price(seller_shop_id, buyer_shop_id)

    def getMRP(self, seller_shop_id, buyer_shop_id):
        product_price = self.getPriceByShopId(seller_shop_id, buyer_shop_id)
        return product_price.mrp if product_price else False

    def getRetailerPrice(self, seller_shop_id, buyer_shop_id):
        product_price = self.getPriceByShopId(seller_shop_id, buyer_shop_id)
        return product_price.selling_price if product_price else False

    def getCashDiscount(self, seller_shop_id, buyer_shop_id):
        return 0

    def getLoyaltyIncentive(self, seller_shop_id, buyer_shop_id):
        return 0

    def getProductCoupons(self):
        product_coupons = []
        date = datetime.datetime.now()
        for rules in self.purchased_product_coupon.filter(rule__is_active = True, rule__expiry_date__gte = date):
            for rule in rules.rule.coupon_ruleset.filter(is_active=True, expiry_date__gte = date):
                product_coupons.append(rule.coupon_code)
        parent_brand = self.parent_product.parent_brand.brand_parent.id if self.parent_product else None
        # parent_brand = self.product_brand.brand_parent.id if self.product_brand.brand_parent else None
        product_brand_id = self.parent_product.parent_brand.id if self.parent_product else None
        brand_coupons = Coupon.objects.filter(coupon_type = 'brand', is_active = True, expiry_date__gte = date).filter(Q(rule__brand_ruleset__brand = product_brand_id)| Q(rule__brand_ruleset__brand = parent_brand)).order_by('rule__cart_qualifying_min_sku_value')
        for x in brand_coupons:
            product_coupons.append(x.coupon_code)
        return product_coupons


class ProductSKUGenerator(models.Model):
    parent_cat_sku_code = models.CharField(max_length=3,validators=[CapitalAlphabets],help_text="Please enter three characters for SKU")
    cat_sku_code = models.CharField(max_length=3,validators=[CapitalAlphabets],help_text="Please enter three characters for SKU")
    brand_sku_code = models.CharField(max_length=3,validators=[CapitalAlphabets],help_text="Please enter three characters for SKU")
    last_auto_increment = models.CharField(max_length=8)


class ChildProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='child_product_pro_image', blank=True, on_delete=models.CASCADE)
    image_name = models.CharField(max_length=255, blank=True, validators=[ProductNameValidator])
    image_alt_text = models.CharField(max_length=255, null=True, blank=True, validators=[NameValidator])
    image = models.ImageField(upload_to='child_product_image', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    # status = models.BooleanField(default=True)

    def image_thumbnail(self):
        return mark_safe('<img src="{url}" width="{width}" height={height} />'.format(
            url=self.image.url,
            width='500px',
            height='500px',
        ))

    def __str__(self):
        return self.image.name


class ProductSourceMapping(models.Model):
    destination_sku = models.ForeignKey(Product, related_name='destination_product_pro', blank=True, on_delete=models.DO_NOTHING)
    source_sku = models.ForeignKey(Product, related_name='source_product_pro', blank=True, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True, blank=True)

    class Meta:
        verbose_name = _("Product Source Mapping")
        verbose_name_plural = _("Product Source Mappings")


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
    APPROVED = 2
    APPROVAL_PENDING = 1
    DEACTIVATED = 0
    APPROVAL_CHOICES = (
        (APPROVED, 'Approved'),
        (APPROVAL_PENDING, 'Approval Pending'),
        (DEACTIVATED, 'Deactivated'),
    )
    product = models.ForeignKey(Product, related_name='product_pro_price',
                                on_delete=models.CASCADE)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True,
                              blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2,
                                        null=True, blank=False)
    seller_shop = models.ForeignKey(Shop, related_name='shop_product_price',
                                    null=True, blank=True,
                                    on_delete=models.CASCADE)
    buyer_shop = models.ForeignKey(Shop,
                                   related_name='buyer_shop_product_price',
                                   null=True, blank=True,
                                   on_delete=models.CASCADE)
    city = models.ForeignKey(City, related_name='city_pro_price',
                             null=True, blank=True, on_delete=models.CASCADE)
    pincode = models.ForeignKey(Pincode, related_name='pincode_product_price',
                                null=True, blank=True,
                                on_delete=models.CASCADE)
    price_to_retailer = models.FloatField(null=True, blank=False)
    start_date = models.DateTimeField(null=True, blank=False)
    end_date = models.DateTimeField(null=True, blank=False)
    approval_status = models.IntegerField(choices=APPROVAL_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return "%s - %s" % (self.product.product_name, self.selling_price)

    def validate(self, exception_type):
        # if not self.mrp:
        #     raise ValidationError(_('Please enter valid Mrp price.'))
        if not self.selling_price:
            print(self.selling_price)
            raise ValidationError(_('Please enter valid Selling price.'))
            #raise exception_type(ERROR_MESSAGES['INVALID_PRICE_UPLOAD'])
        if self.selling_price and self.mrp and self.selling_price > self.mrp:
            raise exception_type(ERROR_MESSAGES['INVALID_PRICE_UPLOAD'])

    def clean(self):
        super(ProductPrice, self).clean()
        self.validate(ValidationError)

    def update_city_pincode(self):
        if self.buyer_shop and not (self.city or self.pincode):
            address_data = self.buyer_shop.shop_name_address_mapping\
                .values('pincode_link', 'city')\
                .filter(address_type='shipping').last()
            self.city_id = address_data.get('city')
            self.pincode_id = address_data.get('pincode_link')
        if self.pincode and not (self.city and self.buyer_shop):
            self.city_id = self.pincode.city_id

    def save(self, *args, **kwargs):
        self.validate(Exception)
        self.update_city_pincode()
        if self.approval_status == self.APPROVED:
            if self.buyer_shop:
                product_price = ProductPrice.objects.filter(
                    product=self.product,
                    seller_shop=self.seller_shop,
                    buyer_shop=self.buyer_shop,
                    city=self.city,
                    pincode=self.pincode,
                    approval_status=ProductPrice.APPROVED
                )
            elif self.pincode:
                product_price = ProductPrice.objects.filter(
                    product=self.product,
                    seller_shop=self.seller_shop,
                    buyer_shop=None,
                    city=self.city,
                    pincode=self.pincode,
                    approval_status=ProductPrice.APPROVED
                )
            elif self.city:
                product_price = ProductPrice.objects.filter(
                    product=self.product,
                    seller_shop=self.seller_shop,
                    buyer_shop=None,
                    city=self.city,
                    pincode=None,
                    approval_status=ProductPrice.APPROVED
                )
            else:
                product_price = ProductPrice.objects.filter(
                    product=self.product,
                    seller_shop=self.seller_shop,
                    buyer_shop=None,
                    city=None,
                    pincode=None,
                    approval_status=ProductPrice.APPROVED
                )
            product_price.update(approval_status=ProductPrice.DEACTIVATED)
            self.approval_status = ProductPrice.APPROVED
        super().save(*args, **kwargs)

    @property
    def margin(self):
        return (((self.mrp - self.selling_price) / self.mrp) * 100)

    @property
    def sku_code(self):
        return self.product.product_sku

    # @property
    # def mrp(self):
    #     return self.product.product_mrp


class ProductCategory(models.Model):
    product = models.ForeignKey(Product, related_name='product_pro_category',on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name='category_pro_category',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Product Category")
        verbose_name_plural = _("Product Categories")

class ProductCategoryHistory(models.Model):
    product = models.ForeignKey(Product, related_name='product_pro_cat_history',on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name='category_pro_cat_history',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

class ProductImage(models.Model):
    product = models.ForeignKey(Product,related_name='product_pro_image',on_delete=models.CASCADE)
    image_name = models.CharField(max_length=255,validators=[ProductNameValidator])
    image_alt_text = models.CharField(max_length=255,null=True,blank=True,validators=[NameValidator])
    image = models.ImageField(upload_to='product_image')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def image_thumbnail(self):
        return mark_safe('<img src="{url}" width="{width}" height={height} />'.format(
            url = self.image.url,
            width='500px',
            height='500px',
            )
    )

    def __str__(self):
        return self.image.name

class Tax(models.Model):
    TAX_CHOICES = (
            ("cess", "Cess"),
            ("gst", "GST"),
            ("surcharge", "Surcharge"),
        )

    tax_name = models.CharField(max_length=255,validators=[ProductNameValidator])
    tax_type = models.CharField(max_length=255, choices=TAX_CHOICES, null=True)
    tax_percentage = models.FloatField(default=0)
    tax_start_at = models.DateTimeField(null=True,blank=True)
    tax_end_at = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.tax_name

    class Meta:
        verbose_name = _("Tax")
        verbose_name_plural = _("Taxes")

class ProductTaxMapping(models.Model):
    product = models.ForeignKey(Product,related_name='product_pro_tax',on_delete=models.CASCADE)
    tax = models.ForeignKey(Tax,related_name='tax_pro_tax',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return "{}-{}".format(self.product, self.tax.tax_name)

    def get_products_gst_tax(self):
        return self.product.product_pro_tax.filter(tax__tax_type='gst')

    def get_products_gst_cess(self):
        return self.product.product_pro_tax.filter(tax__tax_type='cess')

    def get_products_gst_surcharge(self):
        return self.product.product_pro_tax.filter(tax__tax_type='surcharge')
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

    class Meta:
        verbose_name = _("Product CSV")
        verbose_name_plural = _("Product CSVS")

class ProductPriceCSV(models.Model):
    file = models.FileField(upload_to='products/price/')
    country = models.ForeignKey(Country,null=True,blank=True, on_delete=models.CASCADE)
    states = models.ForeignKey(State, null=True,blank=True, on_delete=models.CASCADE)
    city = models.ForeignKey(City, null=True,blank=True, on_delete=models.CASCADE)
    area = models.ForeignKey(Area,null=True,blank=True,on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.file)

    class Meta:
        verbose_name = _("Product Price CSV")
        verbose_name_plural = _("Product Price CSVS")

class ProductVendorMapping(models.Model):
    vendor = models.ForeignKey(Vendor,related_name='vendor_brand_mapping',on_delete=models.CASCADE)
    product = models.ForeignKey(Product,related_name='product_vendor_mapping',on_delete=models.CASCADE)
    product_price = models.FloatField(verbose_name='Brand To Gram Price')
    product_mrp = models.FloatField(null=True,blank=True)
    case_size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        ProductVendorMapping.objects.filter(product=self.product,vendor=self.vendor,status=True).update(status=False)
        self.status = True
        super().save(*args, **kwargs)

    def __str__(self):
        return '%s' % (self.vendor)

    def sku(self):
        return self.product.product_sku

@receiver(post_save, sender=Vendor)
def create_product_vendor_mapping(sender, instance=None, created=False, **kwargs):
    vendor = instance
    file = instance.vendor_products_csv
    if file:
        reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
        first_row = next(reader)
        product_mapping = []
        for row in reader:
            if row[4]:
                vendor_product = ProductVendorMapping.objects.filter(vendor=vendor, product_id=row[0])
                if vendor_product.exists():
                    vendor_product.update(status=False)
                product_mapping.append(ProductVendorMapping(vendor=vendor, product_id=row[0], product_mrp=row[4], product_price=row[5],case_size=row[6]))

        ProductVendorMapping.objects.bulk_create(product_mapping)
        #ProductVendorMapping.objects.bulk_create([ProductVendorMapping(vendor=vendor, product_id = row[0], product_price=row[3]) for row in reader if row[3]])

@receiver(pre_save, sender=Product)
def create_product_sku(sender, instance=None, created=False, **kwargs):
    # product = Product.objects.get(pk=instance.product_id)
    # if not product.product_sku:
    if not instance.product_sku:
        # cat_sku_code = instance.category.category_sku_part
        parent_product_category = ParentProductCategory.objects.filter(parent_product=instance.parent_product).last().category
        cat_sku_code = parent_product_category.category_sku_part
        parent_cat_sku_code = parent_product_category.category_parent.category_sku_part if parent_product_category.category_parent else cat_sku_code
        brand_sku_code = instance.product_brand.brand_code
        last_sku = ProductSKUGenerator.objects.filter(cat_sku_code=cat_sku_code,parent_cat_sku_code=parent_cat_sku_code, brand_sku_code=brand_sku_code).last()
        if last_sku:
            last_sku_increment = str(int(last_sku.last_auto_increment) + 1).zfill(len(last_sku.last_auto_increment))
        else:
            last_sku_increment = '00000001'
        ProductSKUGenerator.objects.create(cat_sku_code=cat_sku_code, parent_cat_sku_code=parent_cat_sku_code, brand_sku_code=brand_sku_code, last_auto_increment=last_sku_increment)
        instance.product_sku = "%s%s%s%s"%(cat_sku_code, parent_cat_sku_code, brand_sku_code, last_sku_increment)
        # product.save()

class ProductCapping(models.Model):
    product = models.ForeignKey(Product, related_name='product_pro_capping',
                                on_delete=models.CASCADE)
    seller_shop = models.ForeignKey(Shop, related_name='shop_product_capping',
                                    null=True, blank=True,
                                    on_delete=models.CASCADE)
    buyer_shop = models.ForeignKey(Shop,
                                   related_name='buyer_shop_product_capping',
                                   null=True, blank=True,
                                   on_delete=models.CASCADE)
    city = models.ForeignKey(City, related_name='city_pro_capping',
                             null=True, blank=True, on_delete=models.CASCADE)
    pincode = models.ForeignKey(Pincode, related_name='pincode_product_capping',
                                null=True, blank=True,
                                on_delete=models.CASCADE)
    capping_qty = models.PositiveIntegerField(default=0, null=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)


class BulkProductTaxUpdate(models.Model):
    file = models.FileField(upload_to='products/producttaxmapping/')
    updated_by = models.ForeignKey(
        get_user_model(), related_name='bulk_product_tax_update',
        on_delete=models.DO_NOTHING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Bulk Product Tax Update'

    def __str__(self):
        return "Product Tax Mapping updated at %s by %s" % (self.created_at,
                                                            self.updated_by)


class BulkUploadForGSTChange(models.Model):
    file = models.FileField(upload_to='products/producttaxmapping/')
    updated_by = models.ForeignKey(
        get_user_model(), null=True, related_name='bulk_upload_for_gst_change',
        on_delete=models.DO_NOTHING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Bulk Upload For GST Change'

    def __str__(self):
        return f"BulkUpload updated at {self.created_at} by {self.updated_by}"


class Repackaging(models.Model):
    seller_shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    source_sku = models.ForeignKey(Product, related_name='source_sku_repackaging', on_delete=models.CASCADE, null=True)
    destination_sku = models.ForeignKey(Product, related_name='destination_sku_repackaging', on_delete=models.CASCADE, null=True)
    repackage_weight = models.FloatField(default=0, verbose_name='Weight Of Source SKU To Be Repackaged (Kg)', validators=[WeightValidator])
    available_source_weight = models.FloatField(default=0, verbose_name='Available Source SKU Weight (Kg)')
    available_source_quantity = models.PositiveIntegerField(default=0, verbose_name='Available Source SKU Qty(pcs)')
    destination_sku_quantity = models.PositiveIntegerField(default=0, verbose_name='Created Destination SKU Qty (pcs)')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def source_sku_name(self):
        return self.source_sku.product_name

    def destination_sku_name(self):
        return self.destination_sku.product_name

    def source_product_sku(self):
        return self.source_sku.product_sku

    def destination_product_sku(self):
        return self.destination_sku.product_sku

    def save(self, *args, **kwargs):
        if self.pk is None:
            super().save(*args, **kwargs)

    def __str__(self):
        return "REPACKAGING: " + self.source_sku_name() + ' TO ' + self.destination_sku_name()


class RepackagingCost(models.Model):
    repackaging = models.ForeignKey(Repackaging, on_delete=models.CASCADE)
    particular = models.FloatField(default=1, verbose_name='PARTICULAR (KG)', validators=[PriceValidator])
    raw_material = models.FloatField(default=0, validators=[PriceValidator])
    wastage = models.FloatField(default=0, validators=[PriceValidator])
    fumigation = models.FloatField(default=0, validators=[PriceValidator])
    label_printing = models.FloatField(default=0, validators=[PriceValidator])
    packing_labour = models.FloatField(default=0, validators=[PriceValidator])
    primary_pm_cost = models.FloatField(default=0, validators=[PriceValidator])
    secondary_pm_cost = models.FloatField(default=0, validators=[PriceValidator])
    final_fg_cost = models.FloatField(default=0, validators=[PriceValidator])
    conversion_cost = models.FloatField(default=0, validators=[PriceValidator])

    def __str__(self):
        return ""

    def save(self, *args, **kwargs):
        if self.pk is None:
            super().save(*args, **kwargs)
