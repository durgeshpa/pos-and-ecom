from django.contrib.auth import get_user_model
from django.db import models

# Create your models here.
from model_utils import Choices

from accounts.middlewares import get_current_user
from shops.models import Shop


class BaseTimestampModel(models.Model):
    """
    This abstract class is used as a base model. This provides two fields, created_at and updated_at
    """
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)

    class Meta:
        abstract = True

class Scheme(BaseTimestampModel):
    """
    This class is used as representation of Incentive Scheme
    """
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    user = models.ForeignKey(get_user_model(), related_name='schemes',
                             on_delete=models.CASCADE, verbose_name='Created By')
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.id:
            self.user = get_current_user()
        super(Scheme, self).save(*args, **kwargs)


class SchemeSlab(BaseTimestampModel):
    """
    This class is represents of Incentive Scheme Slabs
    """
    DISCOUNT_TYPE_CHOICE = Choices((0, 'PERCENTAGE', 'Percentage'), (1, 'VALUE', 'Value'))
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)
    min_value = models.IntegerField(verbose_name='Slab Start Value')
    max_value = models.IntegerField(verbose_name='Slab End Value')
    discount_value = models.FloatField()
    discount_type = models.IntegerField(choices=DISCOUNT_TYPE_CHOICE, default=DISCOUNT_TYPE_CHOICE.PERCENTAGE)

    def __str__(self):
        return "{}-{}, {}".format(self.min_value, self.max_value, self.discount_value)


class SchemeShopMapping(BaseTimestampModel):
    """
    This class represents of Shop Scheme Mapping
    """
    PRIORITY_CHOICE = Choices((0, 'P1', 'P1'), (1, 'P2', 'P2'))
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    priority = models.SmallIntegerField(choices=PRIORITY_CHOICE)
    is_active = models.BooleanField(default=True)
    user = models.ForeignKey(get_user_model(), related_name='shop_mappings', on_delete=models.CASCADE, verbose_name='Created By')


    def save(self, *args, **kwargs):
        if not self.id:
            self.user = get_current_user()
        super(SchemeShopMapping, self).save(*args, **kwargs)