from django.db import models

from adminsortable.fields import SortableForeignKey
from adminsortable.models import SortableMixin
from mptt.models import TreeForeignKey


# Create your models here.
class Categories(models.Model):
    """
    We define Category and Sub Category in this model
    """
    category_name = models.CharField(max_length=255)
    category_desc = models.TextField(null=True,blank=True)
    category_parent = models.ForeignKey('self', related_name='cat_parent',null=True,blank=True, on_delete=models.CASCADE)
    #category_parent = TreeForeignKey('self', related_name='cat_parent',null=True,blank=True, on_delete=models.CASCADE)
    category_sku_part = models.CharField(max_length=10,unique=True)
    category_image = models.ImageField(upload_to='category_img',null=True,blank=True)
    is_created = models.DateTimeField(auto_now_add=True)
    is_modified = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.category_name
        #return '%s %s' % ('-' * self, self.category_name)


    # class MPTTMeta:
    #     order_insertion_by = ['category_name']

class CategoryPosation(SortableMixin):
    posation_name = models.CharField(max_length=255)
    category_posation_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.posation_name

    class Meta:
        ordering = ['category_posation_order']

class CategoryData(SortableMixin):
    category = SortableForeignKey(CategoryPosation,related_name='cat_data',null=True,blank=True, on_delete=models.CASCADE)
    category_data = models.ForeignKey(Categories,related_name='category_posation_data',null=True,blank=True, on_delete=models.CASCADE)
    category_data_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.category.posation_name

    class Meta:
        ordering = ['category_data_order']


