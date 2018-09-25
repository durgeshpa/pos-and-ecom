from django.db import models
from adminsortable.fields import SortableForeignKey
from adminsortable.models import SortableMixin
from mptt.models import TreeForeignKey

# Create your models here.
YES = 'Y'
NO = 'N'
CHOICES = (
    (YES, 'Yes'),
    (NO, 'No'),
  )
class Banner(models.Model):
    name = models.FileField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)
    status = models.BooleanField(('Status'),help_text=('Designates whether the banner is to be displayed or not.'),default=True)
    Type = models.CharField(('Type'),help_text=('Designates the type of the banner.'), max_length=2,
                                      choices=CHOICES,
                                      default=YES)

    def __str__(self):
        return '{}'.format(self.name)

class BannerPosition(SortableMixin):
    position_name = models.CharField(max_length=255)
    banner_position_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.position_name

    class Meta:
        ordering = ['banner_position_order']

class BannerData(SortableMixin):
    banner = SortableForeignKey(BannerPosition,related_name='ban_data',null=True,blank=True, on_delete=models.CASCADE)
    banner_data = models.ForeignKey(Banner,related_name='banner_posation_data',null=True,blank=True, on_delete=models.CASCADE)
    banner_data_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.banner.position_name

    class Meta:
        ordering = ['banner_data_order']
