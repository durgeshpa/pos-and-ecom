import logging
from datetime import date
import traceback
from typing import Tuple

from django.db import models
from django.contrib.auth import get_user_model
# from django.conf import settings
from django.utils.safestring import mark_safe
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from otp.sms import SendSms
import datetime, re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from retailer_backend.validators import *
import datetime
from django.core.validators import MinLengthValidator
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import JSONField
from categories.models import BaseTimeModel, BaseTimestampUserStatusModel
from .fields import CaseInsensitiveCharField
from django.core.validators import MinValueValidator
from django.contrib.postgres.fields import ArrayField
# from analytics.post_save_signal import get_retailer_report

Product = 'products.product'
logger = logging.getLogger(__name__)

SHOP_TYPE_CHOICES = (
    ("sp", "Service Partner"),
    ("r", "Retailer"),
    ("sr", "Super Retailer"),
    ("gf", "Gram Factory"),
    ("f", "Franchise"),
    ("dc", "Dispatch Center")
)

RETAILER_TYPE_CHOICES = (
    ("gm", "General Merchant"),
    ("ps", "Pan Shop"),
    ("foco", "Franchise Company Operated"),
    ("fofo", "Franchise Franchise Operated")
)

MANAGER, CASHIER, DELIVERY_PERSON, STORE_MANAGER = 'manager', 'cashier', 'delivery_person', 'store_manager'
USER_TYPE_CHOICES = (
    (MANAGER, 'Manager'),
    (STORE_MANAGER, 'Store Manager'),
    (CASHIER, 'Cashier'),
    (DELIVERY_PERSON, 'Delivery Person')
)


class RetailerType(models.Model):
    retailer_type_name = models.CharField(max_length=100, choices=RETAILER_TYPE_CHOICES, default='gm')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.retailer_type_name


class ShopType(BaseTimestampUserStatusModel):
    shop_type = models.CharField(max_length=50, choices=SHOP_TYPE_CHOICES, default='r')
    shop_sub_type = models.ForeignKey(RetailerType, related_name='shop_sub_type_shop', null=True, blank=True,
                                      on_delete=models.CASCADE)
    shop_min_amount = models.FloatField(default=0)
    updated_by = models.ForeignKey(
        get_user_model(), null=True,
        related_name='shop_type_updated_by',
        on_delete=models.DO_NOTHING
    )

    def __str__(self):
        return "%s - %s" % (self.get_shop_type_display(), self.shop_sub_type.retailer_type_name) if self.shop_sub_type else "%s" % (
            self.get_shop_type_display())


class Shop(models.Model):
    APPROVAL_AWAITING = 1
    APPROVED = 2
    DISAPPROVED = 0
    APPROVAL_STATUS_CHOICES = (
        (APPROVAL_AWAITING, 'Awaiting Approval'),
        (APPROVED, 'Approved'),
        (DISAPPROVED, 'Disapproved'),
    )
    # LOCATION_STARTED = 'LOCATION_STARTED'
    # SHOP_ONBOARDED = 'SHOP_ONBOARDED'
    BUSINESS_CLOSED = 'BUSINESS_CLOSED'
    BLOCKED_BY_GRAMFACTORY = 'BLOCKED_BY_GRAMFACTORY'
    NOT_SERVING_SHOP_LOCATION = 'NOT_SERVING_SHOP_LOCATION'
    PERMANENTLY_CLOSED = 'PERMANENTLY_CLOSED'
    MISBEHAVIOUR_OR_DISPUTE = 'MISBEHAVIOUR_OR_DISPUTE'
    MULTIPLE_SHOP_IDS = 'MULTIPLE_SHOP_IDS'
    FREQUENT_CANCELLATION_HOLD_AND_RETURN_OF_ORDERS = 'FREQUENT_CANCELLATION_HOLD_AND_RETURN_OF_ORDERS'
    MOBILE_NUMBER_LOST_CLOSED_CHANGED = 'MOBILE_NUMBER_LOST_CLOSED_CHANGED'
    REGION_NOT_SERVICED = 'REGION_NOT_SERVICED'

    DISAPPROVED_STATUS_REASON_CHOICES = (
        (BUSINESS_CLOSED, 'Business Closed'),
        (BLOCKED_BY_GRAMFACTORY, 'Blocked By Gramfactory'),
        (NOT_SERVING_SHOP_LOCATION, 'Not Serving Shop Location'),
        (PERMANENTLY_CLOSED, 'Permanently Closed'),
        (REGION_NOT_SERVICED, 'Region Not Serviced'),
        (MISBEHAVIOUR_OR_DISPUTE, 'Misbehaviour Or Dispute'),
        (MULTIPLE_SHOP_IDS, 'Multiple Shop Ids'),
        (FREQUENT_CANCELLATION_HOLD_AND_RETURN_OF_ORDERS, 'Frequent Cancellation, Return And Holds Of Orders'),
        (MOBILE_NUMBER_LOST_CLOSED_CHANGED, 'Mobile Number Changed'),
    )
    Choices = (('active', 'Active'),
                ('deactive', 'Deactive'))
    shop_name = models.CharField(max_length=255)
    shop_owner = models.ForeignKey(get_user_model(), related_name='shop_owner_shop', on_delete=models.CASCADE)
    shop_type = models.ForeignKey(ShopType, related_name='shop_type_shop', on_delete=models.CASCADE)
    related_users = models.ManyToManyField(get_user_model(), blank=True, related_name='related_shop_user')
    created_by = models.ForeignKey(get_user_model(), related_name='shop_created_by', null=True, blank=True,
                                   on_delete=models.DO_NOTHING)
    enable_loyalty_points = models.BooleanField( default=False)
    shop_code = models.CharField(max_length=1, blank=True, null=True)
    shop_code_bulk = models.CharField(max_length=1, blank=True, null=True)
    shop_code_discounted = models.CharField(max_length=1, blank=True, null=True)
    warehouse_code = models.CharField(max_length=3, blank=True, null=True)
    imei_no = models.CharField(max_length=20, null=True, blank=True)
    favourite_products = models.ManyToManyField(Product, through='shops.FavouriteProduct')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approval_status = models.IntegerField(choices=APPROVAL_STATUS_CHOICES, default=1)
    disapproval_status_reason = models.CharField(choices=DISAPPROVED_STATUS_REASON_CHOICES, max_length=50,
                                              null=True, blank=True)
    status = models.BooleanField(default=False)
    updated_by = models.ForeignKey(
        get_user_model(), null=True, related_name='shop_uploaded_by',
        on_delete=models.DO_NOTHING
    )
    pos_enabled = models.BooleanField(default=False, verbose_name='Enabled For POS')
    latitude = models.DecimalField(max_digits=30, decimal_places=15, null=True, verbose_name='Latitude For Ecommerce')
    longitude = models.DecimalField(max_digits=30, decimal_places=15, null=True, verbose_name='Longitude For Ecommerce')
    online_inventory_enabled = models.BooleanField(default=True, verbose_name='Online Inventory Enabled')
    cutoff_time = models.TimeField(null=True, blank=True)
    dynamic_beat = models.BooleanField(default=False)
    superstore_enable = models.BooleanField(default=False)
    #status_reward_configuration = models.CharField(max_length=20, choices=Choices, default='deactive')

    # last_order_at = models.DateTimeField(auto_now_add=True)
    # last_login_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # return "%s-%s"%(self.shop_name, self.shop_owner)
        if self.shop_owner.first_name and self.shop_owner.last_name:
            return "%s - %s - %s %s - %s - %s" % (self.shop_name,
                                        str(self.shop_owner.phone_number), self.shop_owner.first_name,
                                        self.shop_owner.last_name, str(self.shop_type), str(self.id)
                                        )

        elif self.shop_owner.first_name:
            return "%s - %s - %s - %s - %s" % (self.shop_name, str(self.shop_owner.phone_number), self.shop_owner.first_name,
                                     str(self.shop_type), str(self.id))

        return "%s - %s - %s - %s" % (self.shop_name, str(self.shop_owner.phone_number), str(self.shop_type),
                                      str(self.id))

    def __init__(self, *args, **kwargs):
        super(Shop, self).__init__(*args, **kwargs)
        self.__original_status = self.status

    @property
    def parent_shop(self):
        # return self.get_shop_parent
        try:
            if self.retiler_mapping.exists():
                parent = ParentRetailerMapping.objects.get(retailer=self.id, status=True).parent
                return parent.shop_name
        except:
            return None
    
    @property
    def shipping_address(self):
        try:
            if self.shop_name_address_mapping.exists():
                return self.shop_name_address_mapping.filter(address_type='shipping').last().address_line1
        except:
            return None
    
    @property
    def shipping_address_obj(self):
        try:
            if self.shop_name_address_mapping.exists():
                return self.shop_name_address_mapping.filter(address_type='shipping').last()
        except:
            return None

    @property
    def city_name(self):
        try:
            if self.shop_name_address_mapping.exists():
                return self.shop_name_address_mapping.filter(address_type='shipping').last().city.city_name
        except:
            return None

    @property
    def pin_code(self):
        try:
            if self.shop_name_address_mapping.exists():
                return self.shop_name_address_mapping.filter(address_type='shipping').last().pincode
        except:
            return None

    @property
    def owner(self):
        try:
            if self.shop_owner.first_name and self.shop_owner.last_name:
                return "%s %s - %s" % (self.shop_owner.first_name, self.shop_owner.last_name, str(self.shop_owner.id))

            elif self.shop_owner.first_name:
                return "%s - %s" % (self.shop_owner.first_name, str(self.shop_owner.id))

            return "%s - %s" % (str(self.shop_owner.phone_number), str(self.shop_owner.id))
        except:
            return None

    @property
    def get_shop_shipping_address(self):
        if self.shop_name_address_mapping.exists():
            return self.shop_name_address_mapping.filter(address_type='shipping').last().address_line1

    get_shop_shipping_address.fget.short_description = 'Shipping Address'

    @property
    def get_shop_pin_code(self):
        if self.shop_name_address_mapping.exists():
            pincode = self.shop_name_address_mapping.filter(address_type='shipping').last().pincode
            if pincode:
                return pincode
            else:
                return self.shop_name_address_mapping.filter(address_type='shipping').last().pincode_link.pincode

    get_shop_pin_code.fget.short_description = 'PinCode'

    @property
    def get_shop_city(self):
        if self.shop_name_address_mapping.exists():
            return self.shop_name_address_mapping.filter(address_type='shipping').last().city

    get_shop_city.fget.short_description = 'Shop City'

    @property
    def get_shop_parent(self):
        if self.retiler_mapping.exists():
            return self.retiler_mapping.last().parent

    get_shop_parent.fget.short_description = 'Parent Shop'

    @property
    def shop_approved(self):
        return True if self.status == True and self.retiler_mapping.filter(
            status=True).exists() and self.approval_status == self.APPROVED else False

    @property
    def get_shop_parent_name(self):
        if self.retiler_mapping.exists():
            return self.retiler_mapping.last().parent.shop_name

    get_shop_parent_name.fget.short_description = 'Parent Shop Name'

    def get_orders(self):
        return self.rt_buyer_shop_order.all()

    # def clean(self):
    #     if self.approval_status == Shop.DISAPPROVED and self.disapproval_status_reason is None:
    #         raise ValidationError('Disapproval status reason is required.')

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        if self.status != self.__original_status and self.status is True and ParentRetailerMapping.objects.filter(
                retailer=self, status=True).exists():
            username = self.shop_owner.first_name if self.shop_owner.first_name else self.shop_owner.phone_number
            shop_title = str(self.shop_name)

            activity_type = "SHOP_VERIFIED"  # SHOP_VERIFIED
            user_id = self.shop_owner.id
            data = {}
            data['username'] = username
            data['phone_number'] = self.shop_owner.phone_number
            data['shop_title'] = shop_title

            # from notification_center.utils import SendNotification
            # SendNotification(user_id=user_id, activity_type=activity_type, data=data).send()

            # message = SendSms(phone=data['phone_number'],
            #                   body="Dear %s, Your Shop %s has been approved. Click here to start ordering immediately at GramFactory App." \
            #                        " Thanks," \
            #                        " Team GramFactory " % (username, shop_title))
            # message.send()

        super(Shop, self).save(force_insert, force_update, *args, **kwargs)

    # def available_product(self, product):
    #     ProductMapping = {
    #         "sp":
    #     }
    #     products = OrderedProductMapping.objects.filter(
    #                     ordered_product__order__shipping_address__shop_name=self,
    #                     product=product).order_by('-expiry_date')

    class Meta:
        permissions = (
            ("can_see_all_shops", "Can See All Shops"),
            ("can_do_reconciliation", "Can Do Reconciliation"),
            ("can_sales_person_add_shop", "Can Sales Person Add Shop"),
            ("can_sales_manager_add_shop", "Can Sales Manager Add Shop"),
            ("is_delivery_boy", "Is Delivery Boy"),
            ("hide_related_users", "Hide Related User"),
        )


def warehouse_code_generator():
    """
        This Function will create auto Incrementel Warehouse_code
    """

    latest_record = Shop.objects.filter(shop_type__shop_type='f', approval_status=2).last()
    return int(latest_record.warehouse_code) + 1


@receiver(pre_save, sender=Shop)
def create_auto_warehouse_code_for_franchise(sender, instance=None, created=False, **kwargs):
    """
        Creating warehouse_code for a Franchise shop.
        warehouse_code created when the shop is approved
    """
    if instance.shop_type.shop_type == 'f' and instance.approval_status == 2 and not instance.warehouse_code:
        warehouse_code = warehouse_code_generator()
        instance.warehouse_code = str(warehouse_code)
        instance.shop_code = 'F'


@receiver(post_save, sender=Shop)
def create_default_bin_franchise(sender, instance=None, created=False, **kwargs):
    """
        Creating single virtual bin for a Franchise shop to be used for it's bin inventory management.
        Bin created when the shop is approved
    """
    if instance.shop_type.shop_type == 'f' and instance.approval_status == 2:
        from wms.models import Bin
        from franchise.models import get_default_virtual_bin_id
        virtual_bin_id = get_default_virtual_bin_id()
        if not Bin.objects.filter(warehouse=instance, bin_id=virtual_bin_id).exists():
            Bin.objects.create(warehouse=instance, bin_id=virtual_bin_id, bin_type='SR', is_active=1)


@receiver(post_save, sender=Shop)
def assign_franchise_group_to_user(sender, instance=None, created=False, **kwargs):
    if instance.shop_type.shop_type == 'f' and instance.approval_status == 2:
        from django.contrib.auth.models import Group
        instance.shop_owner.is_staff = True
        instance.shop_owner.save()
        my_group = Group.objects.get(name='Franchise')
        my_group.user_set.add(instance.shop_owner)


@receiver(post_save, sender=Shop)
def create_shop_status_log(sender, instance=None, created=False, **kwargs):
    if not created:
        user = instance.updated_by
    else:
        user = instance.created_by
    if instance and instance.approval_status in [0, 1, 2]:
        approval_status = instance.approval_status
        if approval_status == 0:
            reason = 'Disapproved'
        elif approval_status == 1:
            reason = 'Awaiting Approval'
        else:
            reason = 'Approved'
        last_status = ShopStatusLog.objects.filter(shop=instance).last()
        if not last_status or last_status.reason != reason or \
                last_status.status_change_reason != instance.get_disapproval_status_reason_display():
            ShopStatusLog.objects.create(reason=reason, status_change_reason=
            instance.get_disapproval_status_reason_display(), user=user, shop=instance)


class FavouriteProduct(models.Model):
    # user = models.ForeignKey(get_user_model(), related_name='user_favourite',on_delete=models.CASCADE)
    buyer_shop = models.ForeignKey(Shop, related_name='shop_favourite', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='product_favourite', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product.product_sku


class ShopNameDisplay(Shop):
    class Meta:
        proxy = True

    def __str__(self):
        return "%s - %s" % (self.shop_name.split()[0], self.shop_name.split()[-1])


class ShopPhoto(models.Model):
    shop_name = models.ForeignKey(Shop, related_name='shop_name_photos', on_delete=models.CASCADE)
    shop_photo = models.FileField(upload_to='shop_photos/shop_name/')

    def shop_photo_thumbnail(self):
        return mark_safe(
            '<a href="{}"><img alt="{}" src="{}" height="200px" width="300px"/></a>'.format(self.shop_photo.url,
                                                                                            self.shop_name,
                                                                                            self.shop_photo.url))

    def __str__(self):
        return "{}".format(self.shop_name)


class ShopDocument(models.Model):
    GSTIN = 'gstin'
    SLN = 'sln'
    UIDAI = 'uidai'
    ELE_BILL = 'bill'
    PAN = 'pan'
    FSSAI = 'fssai'
    DL = 'dl'
    EC = 'ec'
    WSVD = 'wsvd'
    DRUG_L = 'drugl'
    UDYOG_AADHAR = 'ua'
    PASSPORT = 'passport'

    SHOP_DOCUMENTS_TYPE_CHOICES = (
        (GSTIN, "GSTIN"),
        (SLN, "Shop License No"),
        (UIDAI, "Aadhaar Card"),
        (ELE_BILL, "Shop Electricity Bill"),
        (PAN, "Pan Card No"),
        (PASSPORT, "Passport"),
        (FSSAI, "Fssai License No"),
        (DL, "Driving Licence"),
        (EC, "Election Card"),
        (WSVD, "Weighing Scale Verification Document"),
        (DRUG_L, 'Drug License'),
        (UDYOG_AADHAR, 'Udyog Aadhar')
    )
    shop_name = models.ForeignKey(Shop, related_name='shop_name_documents', on_delete=models.CASCADE)
    shop_document_type = models.CharField(max_length=100, choices=SHOP_DOCUMENTS_TYPE_CHOICES, default='gstin')
    shop_document_number = models.CharField(max_length=100)
    shop_document_photo = models.FileField(upload_to='shop_photos/shop_name/documents/', null=True, blank=True)

    def shop_document_photo_thumbnail(self):
        if self.shop_document_photo:
            return mark_safe('<a href="{}"><img alt="{}" src="{}" height="200px" width="300px"/></a>'.format(
                self.shop_document_photo.url, self.shop_name, self.shop_document_photo.url))

    def __str__(self):
        if self.shop_document_photo:
            return "%s - %s" % (self.shop_document_number, self.shop_document_photo.url)
        return "%s" % (self.shop_document_number)

    def clean(self):
        super(ShopDocument, self).clean()
        if self.shop_document_type == 'gstin' and len(
                self.shop_document_number) > 15 or self.shop_document_type == 'gstin' and len(
                self.shop_document_number) < 15:
            raise ValidationError(_("GSTIN Number must be equal to 15 digits only"))
        if self.shop_document_type == 'gstin' and not re.match("^[a-zA-Z0-9]*$", self.shop_document_number):
            raise ValidationError(_("GSTIN values must be alphanumeric only"))


class ShopInvoicePattern(models.Model):
    ACTIVE = 'ACT'
    DISABLED = 'DIS'
    SHOP_INVOICE_CHOICES = (
        (ACTIVE, 'Active'),
        (DISABLED, 'Disabled'),
    )
    shop = models.ForeignKey(Shop, related_name='invoice_pattern', on_delete=models.CASCADE)
    pattern = models.CharField(max_length=15, null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=3, choices=SHOP_INVOICE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        last_invoice_pattern = ShopInvoicePattern.objects.filter(
            shop=self.shop, status=self.ACTIVE).update(status=self.DISABLED)
        self.status = self.ACTIVE
        super().save(*args, **kwargs)


class ParentRetailerMapping(models.Model):
    parent = models.ForeignKey(Shop, related_name='parrent_mapping', on_delete=models.CASCADE)
    retailer = models.ForeignKey(Shop, related_name='retiler_mapping', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta:
        unique_together = ('parent', 'retailer',)

    def __str__(self):
        return "%s(%s) --mapped to-- %s(%s)(%s)" % (
        self.retailer.shop_name, self.retailer.shop_type, self.parent.shop_name, self.parent.shop_type,
        "Active" if self.status else "Inactive")


@receiver(post_save, sender=ParentRetailerMapping)
def shop_verification_notification1(sender, instance=None, created=False, **kwargs):
    try:
        logging.info("in post_save: ParentRetailerMapping")
        shop = instance.retailer
        username = shop.shop_owner.first_name if shop.shop_owner.first_name else shop.shop_owner.phone_number
        shop_title = str(shop.shop_name)

        user_id = shop.shop_owner.id
        data = {}
        data['username'] = username
        data['phone_number'] = instance.retailer.shop_owner.phone_number
        data['shop_id'] = shop.id

        if created:
            logging.info("created: ParentRetailerMapping")

            if shop.status == True:
                username = shop.shop_owner.first_name if shop.shop_owner.first_name else shop.shop_owner.phone_number
                shop_title = str(shop.shop_name)

                activity_type = "SHOP_VERIFIED"

                # from notification_center.utils import SendNotification
                # try:
                #     SendNotification(user_id=instance.id, activity_type=activity_type, data=data).send()
                # except Exception as e:
                #     logging.error(e)
                # message = SendSms(phone=shop.shop_owner,
                #                   body="Dear %s, Your Shop %s has been approved. Click here to start ordering immediately at GramFactory App."\
                #                       " Thanks,"\
                #                       " Team GramFactory " % (username, shop_title))

                # message.send()

        else:
            # logging.info("edited: ParentRetailerMapping")

            activity_type = "SHOP_CREATED"

            # from notification_center.utils import SendNotification
            # SendNotification(user_id=instance.id, activity_type=activity_type, data=data).send()
    except Exception as e:
        logging.error("error in post_save: shop verification")
        logging.error(str(e))


class ShopAdjustmentFile(models.Model):
    shop = models.ForeignKey(Shop, related_name='stock_adjustment_shop', on_delete=models.CASCADE)
    stock_adjustment_file = models.FileField(upload_to='stock_adjustment')
    created_by = models.ForeignKey(get_user_model(), null=True, blank=True, related_name='stock_adjust_by',
                                   on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class ShopRequestBrand(models.Model):
    shop = models.ForeignKey(Shop, related_name='shop_request_brand',
                             on_delete=models.CASCADE)
    brand_name = models.CharField(max_length=100, blank=True, null=True)
    product_sku = models.CharField(max_length=100, blank=True, null=True)
    request_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # if self.brand_name:
        #     return "%s - %s"%(self.shop.shop_name,self.brand_name)
        # else:
        return "%s - %s" % (self.shop.shop_name, self.id)

    def __init__(self, *args, **kwargs):
        super(ShopRequestBrand, self).__init__(*args, **kwargs)


class ShopUserMapping(BaseTimestampUserStatusModel):
    shop = models.ForeignKey(Shop, related_name='shop_user', on_delete=models.CASCADE)
    manager = models.ForeignKey('self', null=True, blank=True, related_name='employee_list',
                                on_delete=models.DO_NOTHING,
                                limit_choices_to={'manager': None, 'status': True,
                                                  'employee_group__permissions__codename': 'can_sales_manager_add_shop'}, )
    employee = models.ForeignKey(get_user_model(), related_name='shop_employee', on_delete=models.CASCADE)
    employee_group = models.ForeignKey(Group, related_name='shop_user_group', default='1', on_delete=models.SET_DEFAULT)
    updated_by = models.ForeignKey(
        get_user_model(), null=True,
        related_name='shop_user_mapping_updated_by',
        on_delete=models.DO_NOTHING
    )

    # class Meta:
    #     unique_together = ('shop', 'employee', 'status')

    def save(self, *args, **kwargs):
        if self.manager == self:
            raise ValidationError(_('Manager and Employee cannot be same'))
        else:
            ShopUserMapping.objects.filter(shop=self.shop, employee=self.employee, employee_group=self.employee_group,
                                           status=True).update(status=False)
            self.status = True
        if self.status == True and self.employee_group.name == 'Sales Executive':
            ShopUserMapping.objects.filter(shop=self.shop, manager=self.manager, employee_group__name='Sales Executive',
                                           status=True).update(status=False)
            self.status = True
        super().save(*args, **kwargs)

    def __str__(self):
        return "%s" % self.employee


class PosShopUserMapping(models.Model):
    shop = models.ForeignKey(Shop, related_name='pos_shop', on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), related_name='pos_shop_user', on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default="cashier")
    is_delivery_person = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    created_by = models.ForeignKey(get_user_model(), related_name='pos_shop_created_by', null=True, blank=True,
                                   on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'POS Shop User Mapping'
        verbose_name_plural = 'POS Shop User Mappings'
        unique_together = ['shop', 'user']

    def save(self, *args, **kwargs):
        if self.user_type == 'delivery_person':
            self.is_delivery_person = True
        super().save(*args, **kwargs)

    def __str__(self):
        return "%s" % self.user


class SalesAppVersion(models.Model):
    app_version = models.CharField(max_length=200)
    update_recommended = models.BooleanField(default=False)
    force_update_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.app_version


from django.contrib.postgres.fields import ArrayField


class ShopTiming(models.Model):
    SUN = 'SUN'
    MON = 'MON'
    TUE = 'TUE'
    WED = 'WED'
    THU = 'THU'
    FRI = 'FRI'
    SAT = 'SAT'

    off_day_choices = (
        (SUN, 'SUN'),
        (MON, 'MON'),
        (TUE, 'TUE'),
        (WED, 'WED'),
        (THU, 'THU'),
        (FRI, 'FRI'),
        (SAT, 'FRI'),
    )
    shop = models.OneToOneField(Shop, related_name='shop_timing', null=True, blank=True, on_delete=models.DO_NOTHING)
    open_timing = models.TimeField()
    closing_timing = models.TimeField()
    break_start_time = models.TimeField(null=True, blank=True)
    break_end_time = models.TimeField(null=True, blank=True)
    off_day = ArrayField(models.CharField(max_length=25, choices=off_day_choices, null=True, blank=True), null=True,
                         blank=True)

class ShopMigrationMapp(models.Model):
    gf_addistro_shop = models.IntegerField(default=0)
    sp_gfdn_shop = models.IntegerField(default=0)
    new_sp_addistro_shop = models.IntegerField(default=0)


# post_save.connect(get_retailer_report, sender=ParentRetailerMapping)

class BeatPlanning(models.Model):
    """
    This model is used for Beat Planning
    """

    manager = models.ForeignKey(get_user_model(), related_name='shop_manager', on_delete=models.CASCADE)
    executive = models.ForeignKey(get_user_model(), related_name='shop_executive', on_delete=models.CASCADE,
                                  verbose_name="Sales Executive",)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)


class DayBeatPlanning(models.Model):
    """
    This model is used for to store day wise beat plan for sales executive
    """
    shop_category_choice = (
        ("P1", "P1"),
        ("P2", "P2"),
        ("P3", "P3"),
        ("P4", "P4")
    )
    beat_plan = models.ForeignKey(BeatPlanning, related_name='beat_plan', null=True, blank=True,
                                  on_delete=models.CASCADE)
    shop_category = models.CharField(max_length=25, choices=shop_category_choice, default="P1")
    beat_plan_date = models.DateField(default=date.today)
    next_plan_date = models.DateField(default=date.today)
    temp_status = models.BooleanField(default=False)
    shop = models.ForeignKey(Shop, related_name='shop_id', null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)


class ExecutiveFeedback(models.Model):
    """
    This model is used for to store day wise beat plan for sales executive
    """
    executive_feedback_choice = (
        (1, "Place Order"),
        (2, "No Order For Today"),
        (3, "Price Not Matching"),
        (4, "Stock Not Available"),
        (5, "Could Not Visit"),
        (6, "Shop Closed"),
        (7, "Owner NA"),
        (8, "BDA on Leave"),
        (9, "Already ordered today")

    )
    day_beat_plan = models.ForeignKey(DayBeatPlanning,
                                      related_name='day_beat_plan',
                                      null=True, blank=True,
                                      on_delete=models.CASCADE,
                                      unique=True)
    executive_feedback = models.CharField(max_length=25, choices=executive_feedback_choice)
    feedback_date = models.DateField(null=True, blank=True)
    feedback_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    latitude = models.DecimalField(max_digits=30, decimal_places=15, null=True)
    longitude = models.DecimalField(max_digits=30, decimal_places=15, null=True)
    is_valid = models.BooleanField(default=False)
    distance_in_km = models.DecimalField(max_digits=30, decimal_places=15, null=True)
    last_shop_distance = models.DecimalField(max_digits=30, decimal_places=15, null=True)


class ShopStatusLog(models.Model):
    """
    Maintain Log of Shop enabled and disabled
    """
    reason = models.CharField(max_length=125, blank=True, null=True)
    status_change_reason = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(get_user_model(), related_name='shop_status_changed_by', on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, related_name='shop_detail', on_delete=models.CASCADE)
    changed_at = models.DateTimeField(auto_now_add=True)


class FOFOConfigCategory(models.Model):
    """
    Master model for FOFO configuration category
    """
    name = CaseInsensitiveCharField(max_length=125, unique=True)

    def __str__(self):
        return self.name

    # def save(self, *args, **kwargs):
    #     self.name = self.name.upper()
    #     super(FOFOConfigCategory, self).save(*args, **kwargs)


class FOFOConfigSubCategory(models.Model):
    """
    Master model for FOFO configuration sub-category
    """
    FIELD_TYPE_CHOICES = (
        ("str", "String"),
        ("int", "Integer"),
        ("float", "Float"),
        ("bool", "Boolean"),
    )
    category = models.ForeignKey(FOFOConfigCategory, related_name='fofo_category_details', on_delete=models.CASCADE,null=True, blank=True)
    name = CaseInsensitiveCharField(max_length=125)
    type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default='int')

    class Meta:
        unique_together = ('category', 'name',)

    def __str__(self):
        if self.category:
            return str(self.category) + " - " + str(self.name)

        return str(" ".join(str(self.name).split('_')))

class FOFOConfigurations(models.Model):
    """
        Master model for FOFO configuration
    """
    shop = models.ForeignKey(Shop, related_name='fofo_shop', on_delete=models.CASCADE)
    key = models.ForeignKey(FOFOConfigSubCategory, related_name='fofo_category', on_delete=models.CASCADE)
    value = JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('shop', 'key',)

    def clean(self):
        if self.value and self.value.__class__.__name__ == 'JSONString':
            self.value = str(self.value)
        if self.value == "true":
            self.value = True
        if self.value == "false":
            self.value = False
        if self.value and self.value.__class__.__name__ != self.key.type:
            raise ValidationError('value {} can only be {} type'.format(self.value, self.key.get_type_display()))

    def save(self, *args, **kwargs):
        try:
            if self.value == "TRUE" or self.value == "True" or self.value == "true":
                self.value = "True"
            if self.value == "FALSE" or self.value == "False" or self.value == "false":
                self.value = "False"
            if self.value:
                self.value = eval(self.key.type)(self.value)
        except Exception as e:
            raise ValidationError('value {} can only be {} type'.format(self.value, self.key.get_type_display()))
        super(FOFOConfigurations, self).save(*args, **kwargs)

    def __str__(self):
        return str(" ".join(str(self.key).split('_')))

    class Meta:
        permissions = (
            ("has_fofo_config_operations", "Has update FOFO config operations"),
        )


class FOFOConfig(models.Model):
    # SUN = 'SUN'
    # MON = 'MON'
    # TUE = 'TUE'
    # WED = 'WED'
    # THU = 'THU'
    # FRI = 'FRI'
    # SAT = 'SAT'

    # working_day_choices = (
    #     (SUN, 'SUN'),
    #     (MON, 'MON'),
    #     (TUE, 'TUE'),
    #     (WED, 'WED'),
    #     (THU, 'THU'),
    #     (FRI, 'FRI'),
    #     (SAT, 'FRI'),
    # )
    shop = models.OneToOneField(Shop, related_name='fofo_shop_config', null=True, blank=True, unique=True, on_delete=models.CASCADE,)
    shop_opening_timing = models.TimeField(null=True, blank=True)
    shop_closing_timing = models.TimeField(null=True, blank=True)

    working_off_start_date = models.DateField(null=True, blank=True)
    working_off_end_date = models.DateField(null=True, blank=True)
    
    delivery_redius = models.DecimalField(max_digits=8, decimal_places=1, blank=True, null=True, help_text="Insert value in meters")
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=199,validators=[MinValueValidator(199)], blank=True, null=True)
    delivery_time = models.IntegerField(blank=True, null=True, help_text="Insert value in minutes")

    class Meta:
        permissions = (
            ("has_fofo_config_operations_shop", "Has update FOFO  shop config operations"),
        )


class ShopFcmTopic(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='fcm_topics', unique=True)
    topic_name = models.CharField(max_length=200)
    registration_ids = ArrayField(models.CharField(max_length=500))
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    def __str__(self) -> str:
        return f"{self.shop} >> {self.topic_name} >> {len(self.registration_ids)}"
    
    class Meta:
        verbose_name = 'Shop Fcm Topic'
        verbose_name_plural = 'Shop Fcm Topics'