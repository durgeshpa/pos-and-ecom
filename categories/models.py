from django.db import models
from django.core.exceptions import ValidationError

from adminsortable.fields import SortableForeignKey
from adminsortable.models import SortableMixin

from retailer_backend.validators import CapitalAlphabets
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
# Create your models here.


class BaseTimeModel(models.Model):
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


class BaseTimestampUserStatusModel(models.Model):
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)
    created_by = models.ForeignKey(
        get_user_model(), null=True,
        verbose_name="Created by",
        on_delete=models.DO_NOTHING
    )
    status = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Category(BaseTimestampUserStatusModel):
    """
    We define Category and Sub Category in this model
    """
    CATEGORY_TYPE_CHOICES = (
        ('grocery', 'Grocery'),
        ('superstore', 'SuperStore')
    )
    category_name = models.CharField(max_length=255, unique=True)
    category_slug = models.SlugField(unique=True)
    category_desc = models.TextField(null=True, blank=True)
    category_parent = models.ForeignKey('self', related_name='cat_parent', blank=True, null=True,
                                        on_delete=models.CASCADE)
    category_sku_part = models.CharField(max_length=3, unique=True, validators=[CapitalAlphabets],
                                         help_text="Please enter three characters for SKU")
    category_image = models.FileField(upload_to='category_img_file', null=True, blank=True)
    category_type = models.CharField(max_length=10, default='grocery', choices=CATEGORY_TYPE_CHOICES)
    updated_by = models.ForeignKey(
        get_user_model(), null=True,
        related_name='category_updated_by',
        on_delete=models.DO_NOTHING
    )

    def __str__(self):
        full_path = [self.category_name]
        k = self.category_parent

        while k is not None:
            full_path.append(k.category_name)
            k = k.category_parent

        return ' -> '.join(full_path[::-1])

    def save(self, *args, **kwargs):
        if self.category_parent == self:
            raise ValidationError(_('Category and Category Parent cannot be same'))
        else:
            super(Category, self).save(*args, **kwargs)

    def clean(self, *args, **kwargs):
        if self.category_parent == self:
            raise ValidationError(_('Category and Category Parent cannot be same'))
        elif self.category_parent and self.category_parent.category_type != self.category_type:
            raise ValidationError({'category_parent':_('Category and Category Parent should be of same type.')})
        else:
            super(Category, self).clean(*args, **kwargs)

    class Meta:
        unique_together = ('category_slug', 'category_parent',)
        verbose_name_plural = _("Categories")

    # class MPTTMeta:
    #     order_insertion_by = ['category_name']


class CategoryDisplayOrder(BaseTimestampUserStatusModel):
    
    category = models.OneToOneField(Category, 
                                    related_name='category_view_order', 
                                    on_delete=models.CASCADE,
                                    limit_choices_to={'category_type': 'superstore'})
    order_no = models.PositiveIntegerField(default=0)
    
    
    def __str__(self) -> str:
        return f"{self.category} | {self.order_no}"
    
    class Meta:
        verbose_name = _('Category Display Order')
        verbose_name_plural = _('Category Display Orders')


class CategoryPosation(SortableMixin):
    posation_name = models.CharField(max_length=255)
    category_posation_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.posation_name

    class Meta:
        ordering = ['category_posation_order']
        verbose_name = _("Category Position")
        verbose_name_plural = _("Category Positions")


class CategoryData(SortableMixin):
    category_pos = SortableForeignKey(CategoryPosation, related_name='cat_data', null=True, blank=True, on_delete=models.CASCADE)
    category_data = models.ForeignKey(Category, related_name='category_posation_data', null=True,blank=True, on_delete=models.CASCADE)
    category_data_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.category_pos.posation_name

    class Meta:
        ordering = ['category_data_order']


class B2cCategory(BaseTimestampUserStatusModel):
    category_name = models.CharField(max_length=255, unique=True)
    category_slug = models.SlugField(unique=True)
    category_desc = models.TextField(null=True, blank=True)
    category_parent = models.ForeignKey('self', related_name='b2c_cat_parent', blank=True, null=True,
                                        on_delete=models.CASCADE)
    category_sku_part = models.CharField(max_length=3, unique=True, validators=[CapitalAlphabets],
                                         help_text="Please enter three characters for SKU")
    category_image = models.FileField(upload_to='b2c_category_img_file', null=True, blank=True)
    updated_by = models.ForeignKey(
        get_user_model(), null=True,
        related_name='b2c_category_updated_by',
        on_delete=models.DO_NOTHING
    )

    def __str__(self):
        full_path = [self.category_name]
        k = self.category_parent

        while k is not None:
            full_path.append(k.category_name)
            k = k.category_parent

        return ' -> '.join(full_path[::-1])

    def save(self, *args, **kwargs):
        if self.category_parent == self:
            raise ValidationError(_('Category and Category Parent cannot be same'))
        else:
            super(B2cCategory, self).save(*args, **kwargs)

    def clean(self, *args, **kwargs):
        if self.category_parent == self:
            raise ValidationError(_('Category and Category Parent cannot be same'))
        else:
            super(B2cCategory, self).clean(*args, **kwargs)

    class Meta:
        unique_together = ('category_slug', 'category_parent',)
        verbose_name_plural = _("B2C Categories")


class B2cCategoryData(SortableMixin):
    category_pos = SortableForeignKey(CategoryPosation, related_name='b2c_cat_data', null=True, blank=True, on_delete=models.CASCADE)
    category_data = models.ForeignKey(B2cCategory, related_name='b2c_category_posation_data', null=True,blank=True, on_delete=models.CASCADE)
    category_data_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.category_pos.posation_name

    class Meta:
        ordering = ['category_data_order']