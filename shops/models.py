import logging
from datetime import date
import traceback
from django.db import models
from django.contrib.auth import get_user_model
# from django.conf import settings
from django.utils.safestring import mark_safe
from django.db.models.signals import post_save
from django.dispatch import receiver
from otp.sms import SendSms
import datetime, re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from retailer_backend.validators import *
import datetime
from django.core.validators import MinLengthValidator
from django.contrib.auth.models import Group

# from analytics.post_save_signal import get_retailer_report

Product = 'products.product'
logger = logging.getLogger(__name__)

SHOP_TYPE_CHOICES = (
    ("sp", "Service Partner"),
    ("r", "Retailer"),
    ("sr", "Super Retailer"),
    ("gf", "Gram Factory"),
    ("f", "Franchise")
)

RETAILER_TYPE_CHOICES = (
    ("gm", "General Merchant"),
    ("ps", "Pan Shop"),
    ("foco", "Franchise Company Operated"),
    ("fofo", "Franchise Franchise Operated")
)


class RetailerType(models.Model):
    retailer_type_name = models.CharField(max_length=100, choices=RETAILER_TYPE_CHOICES, default='gm')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.retailer_type_name


class ShopType(models.Model):
    shop_type = models.CharField(max_length=50, choices=SHOP_TYPE_CHOICES, default='r')
    shop_sub_type = models.ForeignKey(RetailerType, related_name='shop_sub_type_shop', null=True, blank=True,
                                      on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)
    shop_min_amount = models.FloatField(default=0)

    def __str__(self):
        return "%s - %s" % (
        self.get_shop_type_display(), self.shop_sub_type.retailer_type_name) if self.shop_sub_type else "%s" % (
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
    shop_name = models.CharField(max_length=255)
    shop_owner = models.ForeignKey(get_user_model(), related_name='shop_owner_shop', on_delete=models.CASCADE)
    shop_type = models.ForeignKey(ShopType, related_name='shop_type_shop', on_delete=models.CASCADE)
    related_users = models.ManyToManyField(get_user_model(), blank=True, related_name='related_shop_user')
    created_by = models.ForeignKey(get_user_model(), related_name='shop_created_by', null=True, blank=True,
                                   on_delete=models.DO_NOTHING)
    shop_code = models.CharField(max_length=1, blank=True, null=True)
    shop_code_bulk = models.CharField(max_length=1, blank=True, null=True)
    shop_code_discounted = models.CharField(max_length=1, blank=True, null=True)
    warehouse_code = models.CharField(max_length=2, blank=True, null=True)
    imei_no = models.CharField(max_length=20, null=True, blank=True)
    favourite_products = models.ManyToManyField(Product, through='shops.FavouriteProduct')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    approval_status = models.IntegerField(choices=APPROVAL_STATUS_CHOICES, default=1)
    status = models.BooleanField(default=False)

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
                return "%s - %s - %s %s - %s - %s" % (self.shop_name,
                                            str(self.shop_owner.phone_number), self.shop_owner.first_name,
                                            self.shop_owner.last_name, str(self.shop_type), str(self.id)
                                            )

            elif self.shop_owner.first_name:
                return "%s - %s - %s - %s - %s" % (self.shop_name, str(self.shop_owner.phone_number), self.shop_owner.first_name,
                                        str(self.shop_type), str(self.id))

            return "%s - %s - %s - %s" % (self.shop_name, str(self.shop_owner.phone_number), str(self.shop_type),
                                        str(self.id))
        except:
            return None

    @property
    def get_shop_shipping_address(self):
        if self.shop_name_address_mapping.exists():
            for address in self.shop_name_address_mapping.filter(address_type='shipping').all():
                return address.address_line1

    get_shop_shipping_address.fget.short_description = 'Shipping Address'

    @property
    def get_shop_pin_code(self):
        if self.shop_name_address_mapping.exists():
            for address in self.shop_name_address_mapping.filter(address_type='shipping').all():
                return address.pincode

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

    SHOP_DOCUMENTS_TYPE_CHOICES = (
        (GSTIN, "GSTIN"),
        (SLN, "Shop License No"),
        (UIDAI, "Aadhaar Card"),
        (ELE_BILL, "Shop Electricity Bill"),
        (PAN, "Pan Card No"),
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
    shop_document_photo = models.FileField(upload_to='shop_photos/shop_name/documents/')

    def shop_document_photo_thumbnail(self):
        return mark_safe('<a href="{}"><img alt="{}" src="{}" height="200px" width="300px"/></a>'.format(
            self.shop_document_photo.url, self.shop_name, self.shop_document_photo.url))

    def __str__(self):
        return "%s - %s" % (self.shop_document_number, self.shop_document_photo.url)

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

                from notification_center.utils import SendNotification
                try:
                    SendNotification(user_id=instance.id, activity_type=activity_type, data=data).send()
                except Exception as e:
                    logging.error(e)
                # message = SendSms(phone=shop.shop_owner,
                #                   body="Dear %s, Your Shop %s has been approved. Click here to start ordering immediately at GramFactory App."\
                #                       " Thanks,"\
                #                       " Team GramFactory " % (username, shop_title))

                # message.send()

        else:
            logging.info("edited: ParentRetailerMapping")

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


class ShopUserMapping(models.Model):
    shop = models.ForeignKey(Shop, related_name='shop_user', on_delete=models.CASCADE)
    manager = models.ForeignKey('self', null=True, blank=True, related_name='employee_list',
                                on_delete=models.DO_NOTHING,
                                limit_choices_to={'manager': None, 'status': True,
                                                  'employee_group__permissions__codename': 'can_sales_manager_add_shop'}, )
    employee = models.ForeignKey(get_user_model(), related_name='shop_employee', on_delete=models.CASCADE)
    employee_group = models.ForeignKey(Group, related_name='shop_user_group', default='1', on_delete=models.SET_DEFAULT)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    # class Meta:
    #     unique_together = ('shop', 'employee', 'status')

    def save(self, *args, **kwargs):
        if self.manager == self:
            raise ValidationError(_('Manager and Employee cannot be same'))
        else:
            ShopUserMapping.objects.filter(shop=self.shop, employee=self.employee, employee_group=self.employee_group,
                                           status=True).update(status=False)
            # ShopUserMapping.objects.filter(shop=self.shop, shop__shop_type__shop_type='r', employee_group=self.employee_group, status=True).update(status=False)
            self.status = True
        if self.status == True and self.employee_group.name == 'Sales Executive':
            ShopUserMapping.objects.filter(shop=self.shop, manager=self.manager, employee_group__name='Sales Executive',
                                           status=True).update(status=False)
            self.status = True
        super().save(*args, **kwargs)

    def __str__(self):
        return "%s" % (self.employee)


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

    )
    day_beat_plan = models.ForeignKey(DayBeatPlanning, related_name='day_beat_plan', null=True, blank=True,
                                      on_delete=models.CASCADE)
    executive_feedback = models.CharField(max_length=25, choices=executive_feedback_choice)
    feedback_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
