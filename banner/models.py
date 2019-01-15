from django.db import models
from adminsortable.fields import SortableForeignKey
from adminsortable.models import SortableMixin
from mptt.models import TreeForeignKey
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

# Create your models here.
class Banner(models.Model):

    name= models.CharField(max_length=20, blank=True, null=True)
    image = models.FileField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)
    banner_start_date= models.DateTimeField(blank=True, null=True)
    banner_end_date= models.DateTimeField(blank=True, null=True)
    status = models.BooleanField(('Status'),help_text=('Designates whether the banner is to be displayed or not.'),default=True)
    alt_text= models.CharField(max_length=20, blank=True, null=True)
    text_below_image= models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return '{}'.format(self.image)


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
    page = models.ForeignKey(Page,on_delete=models.CASCADE, null=True)
    bannerslot = models.ForeignKey(BannerSlot,max_length=255, null=True, on_delete=models.CASCADE)
    banner_position_order = models.PositiveIntegerField(default=0,editable=False, db_index=True)

    def __str__(self):
        return  "%s-%s"%(self.page.name, self.bannerslot.name) if self.page else self.bannerslot.name

    class Meta:
        ordering = ['banner_position_order']
        verbose_name = _("Banner Position")
        verbose_name_plural = _("Banner Positions")

class BannerData(SortableMixin):
    slot = SortableForeignKey(BannerPosition,related_name='ban_data',on_delete=models.CASCADE)
    #banner_img= models.ImageField(upload_to='Banner', null=True)
    banner_data = models.ForeignKey(Banner,related_name='banner_position_data',null=True,blank=True, on_delete=models.CASCADE)
    banner_data_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.banner_data.name

    class Meta:
        ordering = ['banner_data_order']
