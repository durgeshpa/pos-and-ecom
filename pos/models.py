from django.utils.safestring import mark_safe
from django.db import models
from django.utils.translation import gettext_lazy as _

from addresses.models import City, State, Pincode
from shops.models import Shop
from products.models import Product
from retailer_backend.validators import ProductNameValidator, NameValidator, AddressNameValidator, PinCodeValidator
from accounts.models import User

PAYMENT_MODE_POS = (
    ('cash', 'Cash Payment'),
    ('online', 'Online Payment'),
    ('credit', 'Credit Payment')
)


class RetailerProduct(models.Model):
    PRODUCT_ORIGINS = (
        (1, 'CREATED'),
        (2, 'LINKED'),
        # (3, 'LINKED_EDITED'),
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('deactivated', 'Deactivated'),
    )
    shop = models.ForeignKey(Shop, related_name='retailer_product', on_delete=models.CASCADE)
    sku = models.CharField(max_length=255, blank=False, unique=True)
    name = models.CharField(max_length=255, validators=[ProductNameValidator])
    product_ean_code = models.CharField(max_length=255, blank=False)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    linked_product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    description = models.CharField(max_length=255, validators=[ProductNameValidator], null=True, blank=True)
    sku_type = models.IntegerField(choices=PRODUCT_ORIGINS, default=1)
    status = models.CharField(max_length=20, default='active', choices=STATUS_CHOICES, blank=False,
                              verbose_name='Product Status')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id) + ' - ' + str(self.sku) + " - " + str(self.name)

    @property
    def product_short_description(self):
        return self.name

    @property
    def product_name(self):
        return self.name

    @property
    def product_sku(self):
        return self.sku

    @property
    def product_mrp(self):
        return self.mrp

    @property
    def product_price(self):
        return self.selling_price

    def save(self, *args, **kwargs):
        super(RetailerProduct, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Product'


class RetailerProductImage(models.Model):
    product = models.ForeignKey(RetailerProduct, related_name='retailer_product_image', on_delete=models.CASCADE)
    image_name = models.CharField(max_length=255, validators=[ProductNameValidator], null=True, blank=True)
    image_alt_text = models.CharField(max_length=255, null=True, blank=True, validators=[NameValidator])
    image = models.ImageField(upload_to='uploads/retailer_product_image/')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def image_thumbnail(self):
        return mark_safe(
            '<a href="{}"><img alt="{}" src="{}" height="200px" width="300px"/></a>'.format(self.image.url,
                                                                                            self.image_name,
                                                                                            self.image.url))

    def __str__(self):
        return self.product.sku + " - " + self.product.name

    class Meta:
        verbose_name = 'Product Image'


class ShopCustomerMap(models.Model):
    user = models.ForeignKey(User, related_name='registered_user', null=True, blank=True, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, related_name='registered_shop', null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shop Customer Mapping'


class Payment(models.Model):
    order = models.ForeignKey('retailer_to_sp.Order', related_name='rt_payment_retailer_order',
                              on_delete=models.DO_NOTHING)
    payment_mode = models.CharField(max_length=50, choices=PAYMENT_MODE_POS, default="cash")
    paid_by = models.ForeignKey(User, related_name='rt_payment_retailer_buyer', null=True, blank=True,
                                on_delete=models.DO_NOTHING)
    processed_by = models.ForeignKey(User, related_name='rt_payment_retailer', null=True, blank=True,
                                     on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Vendor(models.Model):
    company_name = models.CharField(max_length=255)
    vendor_name = models.CharField(max_length=255)
    contact_person_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=10)
    alternate_phone_number = models.CharField(max_length=10, null=True)
    email = models.EmailField(_('email address'))
    address = models.CharField(max_length=255, validators=[AddressNameValidator])
    pincode = models.CharField(validators=[PinCodeValidator], max_length=6)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, null=True)
    gst_number = models.CharField(max_length=100)
    retailer_shop = models.ForeignKey(Shop, related_name='retailer_shop_vendor', on_delete=models.CASCADE)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.vendor_name

    def save(self, *args, **kwargs):
        pin_code_obj = Pincode.objects.filter(pincode=self.pincode).last()
        self.city = pin_code_obj.city
        self.state = pin_code_obj.city.state
        super().save(*args, **kwargs)


class PosCart(models.Model):
    OPEN = "open"
    PARTIAL_DELIVERED = "partially_delivered"
    PARTIAL_DELIVERED_CLOSE = "partially_delivered_closed"
    DELIVERED = "delivered"
    CANCELED = "cancelled"
    PARTIAL_RETURN = 'partially_returned'
    CLOSE = "closed"
    ORDER_STATUS = (
        (OPEN, "Open"),
        (PARTIAL_DELIVERED, "Partially Delivered"),
        (PARTIAL_DELIVERED_CLOSE, "Partially Delivered and Closed"),
        (PARTIAL_RETURN, "Partially Returned"),
        (DELIVERED, "Completely delivered and Closed"),
        (CANCELED, "Canceled"),
        (CLOSE, "Closed")
    )

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    retailer_shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    po_no = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=200, choices=ORDER_STATUS, null=True, blank=True, default='open')
    products = models.ManyToManyField(RetailerProduct, through='pos.PosCartProductMapping')
    raised_by = models.ForeignKey(User, related_name='po_raise_user', null=True, blank=True, on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(User, related_name='po_last_modified_user', null=True, blank=True,
                                         on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Purchase Order"

    def vendor_name(self):
        return self.vendor.vendor_name

    def __str__(self):
        return str(self.po_no)


class PosCartProductMapping(models.Model):
    cart = models.ForeignKey(PosCart, related_name='po_products', on_delete=models.CASCADE)
    product = models.ForeignKey(RetailerProduct, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    is_grn_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product')

    def total_price(self):
        return round(self.price * self.qty, 2)

    def product_name(self):
        return self.product.name

    def __str__(self):
        return self.product.name


class PosOrder(models.Model):
    ordered_cart = models.OneToOneField(PosCart, related_name='pos_po_order', on_delete=models.CASCADE)
    order_no = models.CharField(verbose_name='PO Number', max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.order_no)


# class PosGRNOrder(models.Model):
#     order = models.ForeignKey(PosOrder, verbose_name='PO Number', on_delete=models.CASCADE)
#     invoice_no = models.CharField(max_length=255)
#     invoice_date = models.DateField(null=True)
#     invoice_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')
#     tcs_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')
#     grn_id = models.CharField(max_length=255, null=True, blank=True)
#     last_modified_by = models.ForeignKey(User, related_name='grn_order_last_modified', null=True,
#                                          blank=True, on_delete=models.CASCADE)
#     grn_date = models.DateField(auto_now_add=True)
#     products = models.ManyToManyField(RetailerProduct, through='PosGRNOrderProductMapping')
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateTimeField(auto_now=True)
#
#
# class PosGRNOrderProductMapping(models.Model):
#     grn_order = models.ForeignKey(PosGRNOrder, on_delete=models.CASCADE)
#     product = models.ForeignKey(RetailerProduct, on_delete=models.CASCADE)
#     received_qty = models.PositiveIntegerField(default=0)
#     last_modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateTimeField(auto_now=True)
#
#
# class Document(models.Model):
#     grn_order = models.ForeignKey(PosGRNOrder, null=True, blank=True, on_delete=models.CASCADE)
#     document_number = models.CharField(max_length=255, null=True, blank=True)
#     document_image = models.FileField(null=True, blank=True, upload_to='pos_grn_invoice')
