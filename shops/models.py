from django.db import models
from django.contrib.auth import get_user_model
#from django.conf import settings
from django.utils.safestring import mark_safe
from django.db.models.signals import post_save
from django.dispatch import receiver
from otp.sms import SendSms
import datetime


SHOP_TYPE_CHOICES = (
    ("sp","Service Partner"),
    ("r","Retailer"),
    ("sr","Super Retailer"),
    ("gf","Gram Factory"),
)

RETAILER_TYPE_CHOICES = (
    ("gm", "General Merchant"),
    ("ps", "Pan Shop"),
)

class RetailerType(models.Model):
    retailer_type_name = models.CharField(max_length=100, choices=RETAILER_TYPE_CHOICES, default='gm')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.retailer_type_name

class ShopType(models.Model):
    shop_type = models.CharField(max_length=50, choices=SHOP_TYPE_CHOICES, default='r')
    shop_sub_type = models.ForeignKey(RetailerType, related_name='shop_sub_type_shop', null=True, blank=True,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return "%s - %s"%(self.get_shop_type_display(),self.shop_sub_type.retailer_type_name) if self.shop_sub_type else "%s"%(self.get_shop_type_display())

class Shop(models.Model):
    shop_name = models.CharField(max_length=255)
    shop_owner = models.ForeignKey(get_user_model(), related_name='shop_owner_shop',on_delete=models.CASCADE)
    shop_type = models.ForeignKey(ShopType,related_name='shop_type_shop',on_delete=models.CASCADE)
    related_users = models.ManyToManyField(get_user_model(),blank=True, related_name='related_shop_user')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    def __str__(self):
        return "%s - %s - %s"%(self.shop_name,self.shop_owner, self.shop_type.get_shop_type_display())

    def __init__(self, *args, **kwargs):
        super(Shop, self).__init__(*args, **kwargs)
        self.__original_status = self.status

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        if self.status != self.__original_status and self.status is True and ParentRetailerMapping.objects.filter(retailer=self, status=True).exists():
            username = self.shop_owner.first_name if self.shop_owner.first_name else self.shop_owner.phone_number
            shop_title = str(self.shop_name)
            message = SendSms(phone=self.shop_owner,
                              body="Dear %s, Your Shop %s has been approved. Click here to start ordering immediately at GramFactory App." \
                                   " Thanks," \
                                   " Team GramFactory " % (username, shop_title))
            message.send()
        super(Shop, self).save(force_insert, force_update, *args, **kwargs)

    # def available_product(self, product):
    #     ProductMapping = {
    #         "sp":
    #     }
    #     products = OrderedProductMapping.objects.filter(
    #                     ordered_product__order__shipping_address__shop_name=self,
    #                     product=product).order_by('-expiry_date')

    class Meta:
        permissions = (
            ("can_see_all_shops", "Can See All Shops"),
        )

class ShopPhoto(models.Model):
    shop_name = models.ForeignKey(Shop, related_name='shop_name_photos', on_delete=models.CASCADE)
    shop_photo = models.FileField(upload_to='shop_photos/shop_name/')

    def shop_photo_thumbnail(self):
        return mark_safe('<a href="{}"><img alt="{}" src="{}" height="200px" width="300px"/></a>'.format(self.shop_photo.url,self.shop_name, self.shop_photo.url))

    def __str__(self):
        return "{}".format(self.shop_name)

class ShopDocument(models.Model):
    GSTIN = 'gstin'
    SLN = 'sln'
    UIDAI = 'uidai'
    ELE_BILL = 'bill'
    PAN = 'pan'
    FSSAI = 'fssai'

    SHOP_DOCUMENTS_TYPE_CHOICES = (
        (GSTIN, "GSTIN"),
        (SLN, "Shop License No"),
        (UIDAI, "Aadhaar Card"),
        (ELE_BILL, "Shop Electricity Bill"),
        (PAN, "Pan Card No"),
        (FSSAI, "Fssai License No"),
    )
    shop_name = models.ForeignKey(Shop, related_name='shop_name_documents', on_delete=models.CASCADE)
    shop_document_type = models.CharField(max_length=100, choices=SHOP_DOCUMENTS_TYPE_CHOICES, default='gstin')
    shop_document_number = models.CharField(max_length=100)
    shop_document_photo = models.FileField(upload_to='shop_photos/shop_name/documents/')

    def shop_document_photo_thumbnail(self):
        return mark_safe('<a href="{}"><img alt="{}" src="{}" height="200px" width="300px"/></a>'.format(self.shop_document_photo.url,self.shop_name,self.shop_document_photo.url))

    def __str__(self):
        return "%s - %s"%(self.shop_document_number, self.shop_document_photo.url)


class ShopInvoicePattern(models.Model):
    ACTIVE = 'ACT'
    DISABLED = 'DIS'
    SHOP_INVOICE_CHOICES = (
        (ACTIVE, 'Active'),
        (DISABLED, 'Disabled'),
        )
    shop = models.ForeignKey(Shop, related_name='invoice_pattern', on_delete=models.CASCADE)
    pattern = models.CharField(max_length=15, null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=3, choices=SHOP_INVOICE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        last_invoice_pattern = ShopInvoicePattern.objects.filter(
            shop=self.shop, status=self.ACTIVE).update(status=self.DISABLED)
        self.status = self.ACTIVE
        super().save(*args, **kwargs)


class ParentRetailerMapping(models.Model):
    parent = models.ForeignKey(Shop,related_name='parrent_mapping',on_delete=models.CASCADE)
    retailer = models.ForeignKey(Shop,related_name='retiler_mapping',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta:
        unique_together = ('parent', 'retailer',)

    def __str__(self):
        return "%s(%s) --mapped to-- %s(%s)(%s)"%(self.retailer.shop_name,self.retailer.shop_type,self.parent.shop_name,self.parent.shop_type,"Active" if self.status else "Inactive")

@receiver(post_save, sender=ParentRetailerMapping)
def shop_verification_notification1(sender, instance=None, created=False, **kwargs):
        if created:
            shop = instance.retailer
            if shop.status == True:
                username = shop.shop_owner.first_name if shop.shop_owner.first_name else shop.shop_owner.phone_number
                shop_title = str(shop.shop_name)
                message = SendSms(phone=shop.shop_owner,
                                  body="Dear %s, Your Shop %s has been approved. Click here to start ordering immediately at GramFactory App."\
                                      " Thanks,"\
                                      " Team GramFactory " % (username, shop_title))

                message.send()

class ShopAdjustmentFile(models.Model):
    shop = models.ForeignKey(Shop, related_name='stock_adjustment_shop', on_delete=models.CASCADE)
    stock_adjustment_file = models.FileField(upload_to='stock_adjustment')
    created_by = models.ForeignKey(get_user_model(),null=True,blank=True, related_name='stock_adjust_by',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
