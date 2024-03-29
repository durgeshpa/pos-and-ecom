import logging
import datetime
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
# Create your models here.
from model_utils import Choices

from accounts.middlewares import get_current_user
from shops.models import Shop

logger = logging.getLogger(__name__)

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class BaseTimestampModel(models.Model):
    """
    This abstract class is used as a base model. This provides two fields, created_at and updated_at
    """
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)

    class Meta:
        abstract = True


class BaseTimestampUserModel(models.Model):
    """
        Abstract Model to have helper fields of created_at, created_by, updated_at and updated_by
    """
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)
    created_by = models.ForeignKey(
        get_user_model(), null=True,
        verbose_name="Created by",
        related_name="%(app_label)s_%(class)s_created_by",
        on_delete=models.DO_NOTHING
    )
    updated_by = models.ForeignKey(
        get_user_model(), null=True,
        verbose_name="Updated by",
        related_name="%(app_label)s_%(class)s_updated_by",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        abstract = True


class Scheme(BaseTimestampModel):
    """
    This class is used as representation of Incentive Scheme
    """
    name_regex = RegexValidator(r'^[0-9a-zA-Z ]*$', "Scheme name is not valid")
    name = models.CharField(validators=[name_regex], max_length=50)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
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
    discount_value = models.DecimalField(max_digits=4, decimal_places=2)

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
    user = models.ForeignKey(get_user_model(), related_name='shop_mappings', on_delete=models.CASCADE,
                             verbose_name='Created By')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.id:
            self.user = get_current_user()
        super(SchemeShopMapping, self).save(*args, **kwargs)


class IncentiveDashboardDetails(BaseTimestampModel):
    """
       This class represents of Incentive Dashboard Details
    """
    PRIORITY_CHOICE = Choices((0, 'P1', 'P1'), (1, 'P2', 'P2'))
    sales_manager = models.ForeignKey(get_user_model(), related_name='incentive_details_sales_manager',
                                      on_delete=models.CASCADE, null=True, blank=True)
    sales_executive = models.ForeignKey(get_user_model(), related_name='incentive_details_sales_executive',
                                        on_delete=models.CASCADE, null=True, blank=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    mapped_scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)
    scheme_priority = models.SmallIntegerField(choices=PRIORITY_CHOICE)
    purchase_value = models.FloatField(default=0)
    incentive_earned = models.FloatField(default=0)
    discount_percentage = models.DecimalField(max_digits=4, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return "{}-{}, {}".format(self.shop, self.start_date, self.end_date)


class BulkIncentive(models.Model):
    uploaded_file = models.FileField(
        upload_to='incentive/uploaded_file',
        null=True, blank=False
    )
    uploaded_by = models.ForeignKey(
        get_user_model(), null=True, related_name='incentive_uploaded_by',
        on_delete=models.DO_NOTHING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Incentive(BaseTimestampUserModel):
    """
       This class represents of Incentive
    """

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    capping_applicable = models.BooleanField(default=False)
    capping_value = models.DecimalField(max_digits=8, decimal_places=2)
    date_of_calculation = models.DateField()
    total_ex_tax_delivered_value = models.DecimalField(max_digits=8, decimal_places=2)
    incentive = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return "{}-{}, {}".format(self.shop, self.date_of_calculation, self.incentive)


