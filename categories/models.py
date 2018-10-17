from django.db import models

from adminsortable.fields import SortableForeignKey
from adminsortable.models import SortableMixin
from mptt.models import TreeForeignKey

# Create your models here.
class Category(models.Model):
    """
    We define Category and Sub Category in this model
    """
    category_name = models.CharField(max_length=255,unique=True)
    category_slug = models.SlugField(unique=True)
    category_desc = models.TextField(null=True,blank=True)
    category_parent = models.ForeignKey('self', related_name='cat_parent', null=True, blank=True,on_delete=models.CASCADE)
    category_sku_part = models.CharField(max_length=2,unique=True,help_text="Please enter two character for SKU")
    category_image = models.FileField(upload_to='category_img_file',null=True,blank=True)
    is_created = models.DateTimeField(auto_now_add=True)
    is_modified = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        full_path = [self.category_name]
        k = self.category_parent

        while k is not None:
            full_path.append(k.category_name)
            k = k.category_parent

        return ' -> '.join(full_path[::-1])

    # def save(self, *args,**kwargs):
    #     super(Category, self).save()
    #     if self.pk and int(self.pk) >= 1 and int(self.pk) < 10:
    #         self.category_sku_part = "0%s"%(self.pk)
    #     else:
    #         self.category_sku_part = "%s"%(self.pk)
    #     super(Category, self).save()

    class Meta:
        unique_together = ('category_slug', 'category_parent',)

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
    category_pos = SortableForeignKey(CategoryPosation,related_name='cat_data',null=True,blank=True, on_delete=models.CASCADE)
    category_data = models.ForeignKey(Category,related_name='category_posation_data',null=True,blank=True, on_delete=models.CASCADE)
    category_data_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)


    def __str__(self):
        return self.category_pos.posation_name

    class Meta:
        ordering = ['category_data_order']


# class SubCategory(models.Model):
#     """
#     We define Category and Sub Category in this model
#     """
#     sub_category_name = models.CharField(max_length=255)
#     sub_category_desc = models.TextField(null=True,blank=True)
#     sub_category_parent = models.ForeignKey('self', related_name='cat_parent',null=True,blank=True, on_delete=models.CASCADE)
#     sub_category_sku_part = models.CharField(max_length=10,unique=True,help_text="Please enter 2 charechters into it")
#     sub_category_image = models.ImageField(upload_to='category_img',null=True,blank=True)
#     is_created = models.DateTimeField(auto_now_add=True)
#     is_modified = models.DateTimeField(auto_now=True)
#     status = models.BooleanField(default=True)
#
#     def __str__(self):
#         return self.sub_category_name