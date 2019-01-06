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

SHOP_DOCUMENTS_TYPE_CHOICES = (
    ("gstin", "GSTIN"),
    ("sln", "Shop License Number"),
    ("uidai", "Aadhaar Card"),
    ("bill", "Shop Electricity Bill"),
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
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    def __str__(self):
        return "%s - %s"%(self.shop_name, self.shop_type.get_shop_type_display())

    # def has_changed(instance, status):
    #     import pdb; pdb.set_trace()
    #     if not instance.pk:
    #         return False
    #     old_value = instance.__class__._default_manager.filter(pk=instance.pk).values(status).get()[status]
    #
    #     return not getattr(instance, status) == old_value

# @receiver(post_save, sender=Shop)
# def shop_addition_notification(sender, instance=None, created=False, **kwargs):
#
#         if created:
#             otp = '123546'
#             date = datetime.datetime.now().strftime("%a(%d/%b/%y)")
#             time = datetime.datetime.now().strftime("%I:%M %p")
#             message = SendSms(phone=instance.shop_owner,
#                                               body="%s is your One Time Password for GramFactory Account."\
#                                                    " Request time is %s, %s IST." % (otp,date,time))
#
#             message.send()


@receiver(post_save, sender=Shop)
def shop_verification_notification(sender, instance=None, created=False, **kwargs):

        if not created:
            if instance.status ==True:
                otp = '123546'
                date = datetime.datetime.now().strftime("%a(%d/%b/%y)")
                time = datetime.datetime.now().strftime("%I:%M %p")
                message = SendSms(phone=instance.shop_owner,
                                  body="%s is your One Time Password for GramFactory Account."\
                                       " Request time is %s, %s IST." % (otp,date,time))

                message.send()

class ShopPhoto(models.Model):
    shop_name = models.ForeignKey(Shop, related_name='shop_name_photos', on_delete=models.CASCADE)
    shop_photo = models.FileField(upload_to='shop_photos/shop_name/')

    def shop_photo_thumbnail(self):
        return mark_safe('<img alt="%s" src="%s" />' % (self.shop_name, self.shop_photo.url))

    def __str__(self):
        return "%s - %s"%(self.shop_name, self.shop_photo.url)

class ShopDocument(models.Model):
    shop_name = models.ForeignKey(Shop, related_name='shop_name_documents', on_delete=models.CASCADE)
    shop_document_type = models.CharField(max_length=100, choices=SHOP_DOCUMENTS_TYPE_CHOICES, default='gstin')
    shop_document_number = models.CharField(max_length=100)
    shop_document_photo = models.FileField(upload_to='shop_photos/shop_name/documents/')

    def shop_document_photo_thumbnail(self):
        return mark_safe('<img alt="%s" src="%s" />' % (self.shop_name, self.shop_document_photo.url))

    def __str__(self):
        return "%s - %s"%(self.shop_document_number, self.shop_document_photo.url)

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
