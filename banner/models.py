from django.db import models
from adminsortable.fields import SortableForeignKey
from adminsortable.models import SortableMixin
from mptt.models import TreeForeignKey
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from categories.models import Category
from brand.models import Brand
from products.models import Product
from django.core.exceptions import ValidationError
from shops.models import Shop
from addresses.models import City,Pincode
# Create your models here.

class Banner(models.Model):
    BRAND = "brand"
    SUBBRAND = "subbrand"
    CATEGORY = "category"
    SUBCATEGORY = "subcategory"
    PRODUCT = "product"
    OFFER = "offer"
    BANNER_TYPE = (
        (BRAND, "brand"),
        (SUBBRAND, "subbrand"),
        (CATEGORY, "category"),
        (SUBCATEGORY, "subcategory"),
        (PRODUCT, "product"),
        (OFFER, "offer"),
    )

    name= models.CharField(max_length=20, blank=True, null=True)
    image = models.FileField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)
    banner_start_date= models.DateTimeField(blank=True, null=True)
    banner_end_date= models.DateTimeField(blank=True, null=True)
    banner_type = models.CharField(max_length=255, choices=BANNER_TYPE,null=True, blank=True)
    category = models.ForeignKey(Category,max_length=255, null=True, on_delete=models.CASCADE, blank=True )
    sub_category = models.ForeignKey(Category, related_name='banner_subcategory',max_length=255, null=True, on_delete=models.CASCADE, blank=True )
    brand = models.ForeignKey(Brand,max_length=255, null=True, on_delete=models.CASCADE, blank=True )
    sub_brand = models.ForeignKey(Brand, related_name='banner_subbrand',max_length=255, null=True, on_delete=models.CASCADE, blank=True )
    products = models.ManyToManyField(Product, blank=True )
    status = models.BooleanField(('Status'),help_text=('Designates whether the banner is to be displayed or not.'),default=True)
    alt_text= models.CharField(max_length=20, blank=True, null=True)
    text_below_image= models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return '{}'.format(self.name)


    def clean(self):
        super(Banner, self).clean()
        if (self.banner_type == 'brand' and self.brand is None ):
            raise ValidationError('Please select the Brand')
        if (self.banner_type == 'category' and self.category is None ):
            raise ValidationError('Please select the Category')
        if (self.banner_type == 'subbrand' and self.sub_brand is None ):
            raise ValidationError('Please select the SubBrand')
        if (self.banner_type == 'subcategory' and self.sub_category is None ):
            raise ValidationError('Please select the SubCategory')


class Page(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class BannerSlot(models.Model):
    page= models.ForeignKey(Page,on_delete=models.CASCADE, null =True)
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return  "%s->%s"%(self.page.name, self.name)

    class Meta:
        verbose_name = _("Banner Slot")
        verbose_name_plural = _("Banner Slots")


class BannerPosition(SortableMixin):
    shop = models.ForeignKey(Shop,blank=True, on_delete=models.DO_NOTHING, null=True, verbose_name='Seller Shop')
    page = models.ForeignKey(Page,on_delete=models.CASCADE, null=True)
    bannerslot = models.ForeignKey(BannerSlot,max_length=255, null=True, on_delete=models.DO_NOTHING)
    city = models.ManyToManyField(City, related_name='city_banner', blank=True)
    pincode = models.ManyToManyField(Pincode, related_name='pincode_banner', blank=True)
    buyer_shop = models.ManyToManyField(Shop, related_name='buyer_shop_banner', blank=True)
    banner_position_order = models.PositiveIntegerField(default=0,editable=False, db_index=True)

    def __str__(self):
        return  "%s-%s-%s"%(self.page.name, self.bannerslot.name, self.shop) if self.shop else "%s-%s"%(self.page, self.bannerslot.name)

    class Meta:
        ordering = ['banner_position_order']
        verbose_name = _("Banner Position")
        verbose_name_plural = _("Banner Positions")

    def city_list(self):
        return ", ".join([c.city_name for c in self.city.all()])

    def pincode_list(self):
        return ", ".join([p.pincode for p in self.pincode.all()])

    def buyer_shop_list(self):
        return ", ".join([b.shop_name for b in self.buyer_shop.all()])


class BannerData(SortableMixin):
    slot = SortableForeignKey(BannerPosition,related_name='ban_data',on_delete=models.CASCADE)
    #banner_img= models.ImageField(upload_to='Banner', null=True)
    banner_data = models.ForeignKey(Banner,related_name='banner_position_data',null=True,blank=True, on_delete=models.CASCADE)
    banner_data_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.banner_data.name

    class Meta:
        ordering = ['banner_data_order']


class HomePageMessage(models.Model):
    message = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("HomePage Message")
        verbose_name_plural = _("HomePage Messages")
