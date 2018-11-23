from django.db import models
from adminsortable.fields import SortableForeignKey
from adminsortable.models import SortableMixin
from mptt.models import TreeForeignKey
from django.core.exceptions import ValidationError
# Create your models here.
CHOICES = (
    (1, 'Active'),
    (2, 'Inactive'),
  )

def validate_image(image):
    file_size = image.file.size
    if file_size > 300 * 300:
        raise ValidationError("Max size of file is 300 * 300" )

    #limit_mb = 8
    #if file_size > limit_mb * 1024 * 1024:
    #    raise ValidationError("Max size of file is %s MB" % limit_mb)

class Brand(models.Model):
    brand_name = models.CharField(max_length=20)
    #brand_slug = models.SlugField(unique=True)
    brand_logo = models.FileField(validators=[validate_image], blank=False,null=True)
    brand_parent = models.ForeignKey('self', related_name='brnd_parent', null=True, blank=True,on_delete=models.CASCADE)
    brand_description = models.TextField(null=True, blank=True)
    brand_code = models.CharField(max_length=3,help_text="Please enter three character for SKU")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active_status = models.PositiveSmallIntegerField(('Active Status'),choices=CHOICES,default='1')

    def __str__(self):
        full_path = [self.brand_name]
        k = self.brand_parent

        while k is not None:
            full_path.append(k.brand_name)
            k = k.brand_parent

        return ' -> '.join(full_path[::-1])

    # class Meta:
    #     unique_together = ('brand_name', 'brand_slug',)

class BrandPosition(SortableMixin):
    #page = models.ForeignKey(Page,on_delete=models.CASCADE, null=True)
    position_name = models.CharField(max_length=255)
    brand_position_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.position_name

    class Meta:
        ordering = ['brand_position_order']

class BrandData(SortableMixin):
    slot = SortableForeignKey(BrandPosition,related_name='brand_data',null=True,blank=True, on_delete=models.CASCADE)
    brand_data = models.ForeignKey(Brand,related_name='brand_position_data',null=True,blank=True, on_delete=models.CASCADE)
    brand_data_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.slot.position_name

    class Meta:
        ordering = ['brand_data_order']
