from django.db import models
from adminsortable.fields import SortableForeignKey
from adminsortable.models import SortableMixin
from django.core.exceptions import ValidationError
from multiselectfield import MultiSelectField
from model_utils import Choices

from addresses.models import City, State
from retailer_backend.validators import (AddressNameValidator, PinCodeValidator)
from django.core.validators import MaxValueValidator
from retailer_backend.validators import CapitalAlphabets
from django.utils.translation import ugettext_lazy as _
from shops.models import Shop
from categories.models import BaseTimeModel, BaseTimestampUserStatusModel, Category
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth import get_user_model

VENDOR_REG_PAYMENT = (
    ("paid", "Paid"),
    ("unpaid", "Un-Paid"),
)

# Create your models here.
CHOICES = (
    ('active', 'Active'),
    ('inactive', 'Inactive'),
)


def validate_image(image):
    file_size = image.size
    if file_size > 300 * 300:
        raise ValidationError("Max size of file is 300 * 300")


# Create your models here.
class Vendor(models.Model):
    ORDERING_DAY_CHOICES = Choices(
        (1, 'Monday', 'Monday'),
        (2, 'Tuesday', 'Tuesday'),
        (3, 'Wednesday', 'Wednesday'),
        (4, 'Thursday', 'Thursday'),
        (5, 'Friday', 'Friday'),
        (6, 'Saturday', 'Saturday'),
        (7, 'Sunday', 'Sunday'),
    )
    company_name = models.CharField(max_length=255, null=True)
    vendor_name = models.CharField(max_length=255, null=True)
    contact_person_name = models.CharField(max_length=255, null=True, blank=True)
    telephone_no = models.CharField(max_length=15, null=True, blank=True)
    mobile = models.CharField(max_length=10, null=True)
    email_id = models.TextField(null=True, blank=True)
    designation = models.CharField(max_length=255, null=True)
    address_line1 = models.CharField(max_length=255, validators=[AddressNameValidator], null=True)
    state = models.ForeignKey(State, related_name='vendor_state_address', on_delete=models.CASCADE, null=True)
    city = models.ForeignKey(City, related_name='vendor_city_address', on_delete=models.CASCADE, null=True)
    pincode = models.CharField(validators=[PinCodeValidator], max_length=6, null=True)
    payment_terms = models.TextField(null=True, blank=True)
    vendor_registion_free = models.CharField(max_length=50, choices=VENDOR_REG_PAYMENT, null=True, blank=True)
    sku_listing_free = models.CharField(max_length=50, choices=VENDOR_REG_PAYMENT, null=True, blank=True)
    return_policy = models.TextField(null=True, blank=True)
    GST_number = models.CharField(max_length=100, null=True)
    MSMED_reg_no = models.CharField(max_length=100, null=True, blank=True)
    MSMED_reg_document = models.FileField(upload_to='vendor/msmed_doc', null=True, blank=True)
    fssai_licence = models.FileField(upload_to='vendor/fssai_licence_doc', null=True, blank=True)
    GST_document = models.FileField(upload_to='vendor/gst_doc', null=True)
    pan_card = models.FileField(upload_to='vendor/pan_card', null=True)
    cancelled_cheque = models.FileField(upload_to='vendor/cancelled_cheque', null=True)
    list_of_sku_in_NPI_formate = models.FileField(upload_to='vendor/slu_list_in_npi', null=True, blank=True)
    vendor_form = models.FileField(upload_to='vendor/vendor_form', null=True, blank=True)
    vendor_products_brand = ArrayField(models.PositiveIntegerField(), null=True, blank=True, editable=False)
    ordering_days = MultiSelectField(max_length=50, choices=ORDERING_DAY_CHOICES, null=True)
    lead_time = models.PositiveSmallIntegerField(verbose_name='Lead Time(In Days)', validators=[MaxValueValidator(999)])

    def __str__(self):
        return self.vendor_name


class Brand(BaseTimestampUserStatusModel):
    brand_name = models.CharField(max_length=20)
    brand_slug = models.SlugField(blank=True, null=True)
    brand_logo = models.FileField(validators=[validate_image], blank=False, null=True)
    brand_parent = models.ForeignKey('self', related_name='brand_child', null=True, blank=True,
                                     on_delete=models.CASCADE, limit_choices_to={'brand_parent': None}, )
    brand_description = models.TextField(null=True, blank=True)
    brand_code = models.CharField(max_length=3, validators=[CapitalAlphabets], help_text="Please enter three "
                                                                                         "character for SKU")
    updated_by = models.ForeignKey(
        get_user_model(), null=True,
        related_name='brand_updated_by',
        on_delete=models.DO_NOTHING
    )

    def __str__(self):
        full_path = [self.brand_name]
        k = self.brand_parent

        while k is not None:
            full_path.append(k.brand_name)
            k = k.brand_parent

        return ' -> '.join(full_path[::-1])

    def save(self, *args, **kwargs):
        if self.brand_parent == self:
            raise ValidationError(_('Brand and Brand Parent cannot be same'))
        else:
            super(Brand, self).save(*args, **kwargs)

    def clean(self, *args, **kwargs):
        if self.brand_parent == self:
            raise ValidationError(_('Brand and Brand Parent cannot be same'))
        else:
            super(Brand, self).clean(*args, **kwargs)


class BrandPosition(SortableMixin):
    shop = models.ForeignKey(Shop, blank=True, on_delete=models.CASCADE, null=True)
    position_name = models.CharField(max_length=255)
    brand_position_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return "%s->%s" % (self.position_name, self.shop) if self.shop else self.position_name

    class Meta:
        ordering = ['brand_position_order']
        verbose_name = _("Brand Position")
        verbose_name_plural = _("Brand Positions")


class BrandData(SortableMixin):
    slot = SortableForeignKey(BrandPosition, related_name='brand_data', null=True, blank=True, on_delete=models.CASCADE)
    brand_data = models.ForeignKey(Brand, related_name='brand_position_data', null=True, blank=True,
                                   on_delete=models.CASCADE)
    brand_data_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.slot.position_name

    class Meta:
        ordering = ['brand_data_order']
