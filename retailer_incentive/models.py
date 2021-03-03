from django.db import models

# Create your models here.
from model_utils import Choices

from shops.models import Shop


class BaseTimestampModel(models.Model):
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)

    class Meta:
        abstract = True

class Scheme(BaseTimestampModel):
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField()

    def __str__(self):
        return self.name


class SchemeSlab(BaseTimestampModel):
    DISCOUNT_TYPE_CHOICE = Choices((0, 'PERCENTAGE', 'Percentage'), (1, 'VALUE', 'Value'))
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)
    min_value = models.IntegerField(verbose_name='Slab Start Value')
    max_value = models.IntegerField(verbose_name='Slab End Value')
    discount_value = models.FloatField()
    discount_type = models.IntegerField(choices=DISCOUNT_TYPE_CHOICE, default=DISCOUNT_TYPE_CHOICE.PERCENTAGE)

    def __str__(self):
        return "{}-{}, {}".format(self.min_value, self.max_value, self.discount_value)


class SchemeShopMapping(BaseTimestampModel):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)