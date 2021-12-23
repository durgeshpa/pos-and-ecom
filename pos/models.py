import datetime
import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from model_utils import Choices

from accounts.models import User
from addresses.models import City, State, Pincode
from coupon.models import Coupon, CouponRuleSet, RuleSetProductMapping
from pos.bulk_product_creation import bulk_create_update_validated_products
from pos.common_bulk_validators import bulk_product_validation
from products.models import Product
from products.models import ProductTaxMapping
from retailer_backend.validators import ProductNameValidator, NameValidator, AddressNameValidator, PinCodeValidator
from retailer_to_sp.models import (OrderReturn, OrderedProduct, ReturnItems, Cart, CartProductMapping,
                                   OrderedProductMapping, Order)
from shops.models import Shop
from wms.models import PosInventory, PosInventoryState, PosInventoryChange

PAYMENT_MODE_POS = (
    ('cash', 'Cash Payment'),
    ('online', 'Online Payment'),
    ('credit', 'Credit Payment')
)

logger = logging.getLogger(__name__)

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class MeasurementCategory(models.Model):
    category = models.CharField(choices=(('weight', 'Weight'), ('volume', 'Volume')), max_length=50, unique=True)

    def __str__(self):
        return self.category


class MeasurementUnit(models.Model):
    category = models.ForeignKey(MeasurementCategory, on_delete=models.CASCADE, related_name='measurement_category_unit')
    unit = models.CharField(max_length=50, unique=True)
    conversion = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(0)])
    default = models.BooleanField(default=False)

    def __str__(self):
        return str(self.category) + self.unit


class RetailerProduct(models.Model):
    PRODUCT_ORIGINS = (
        (1, 'CREATED'),
        (2, 'LINKED'),
        # (3, 'LINKED_EDITED'),
        (4, 'DISCOUNTED')
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('deactivated', 'Deactivated'),
    )
    shop = models.ForeignKey(Shop, related_name='retailer_product', on_delete=models.CASCADE)
    sku = models.CharField(max_length=255, blank=False, unique=True)
    name = models.CharField(max_length=255, validators=[ProductNameValidator])
    product_ean_code = models.CharField(max_length=255, blank=False, null=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    offer_start_date = models.DateField(null=True, blank=True)
    offer_end_date = models.DateField(null=True, blank=True)
    linked_product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    description = models.CharField(max_length=255, validators=[ProductNameValidator], null=True, blank=True)
    sku_type = models.IntegerField(choices=PRODUCT_ORIGINS, default=1)
    product_ref = models.OneToOneField('self', related_name='discounted_product', null=True, blank=True,
                                       on_delete=models.CASCADE, verbose_name='Reference Product')
    status = models.CharField(max_length=20, default='active', choices=STATUS_CHOICES, blank=False,
                              verbose_name='Product Status')
    product_pack_type = models.CharField(choices=(('packet', 'Packet'), ('loose', 'Loose')), max_length=50,
                                         default='packet')
    measurement_category = models.ForeignKey(MeasurementCategory, on_delete=models.DO_NOTHING, null=True)
    purchase_pack_size = models.PositiveIntegerField(default=1)
    initial_purchase_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    online_enabled = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    online_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

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

    @property
    def product_tax(self):
        return ProductTaxMapping.objects.filter(product=self.id).first().tax if ProductTaxMapping.objects.filter(product=self.id).first() else 0

    def save(self, *args, **kwargs):
        # Discounted
        if self.sku_type != 4 and hasattr(self, 'discounted_product'):
            discounted = self.discounted_product
            discounted.name = self.name
            discounted.description = self.description
            discounted.product_ean_code = self.product_ean_code
            discounted.mrp = self.mrp
            discounted.save()
        if self.online_enabled and not self.online_price:
            self.online_price = self.selling_price
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
        verbose_name = 'Store - Customer Mapping'


class PaymentType(models.Model):
    type = models.CharField(max_length=20, unique=True)
    enabled = models.BooleanField(default=True)
    app = models.CharField(choices=(('pos', 'POS'), ('ecom', 'ECOM'), ('both', 'Both')), default='pos', max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Mode'
        verbose_name_plural = _("Payment Modes")

    def __str__(self) -> str:
        return self.type


class Payment(models.Model):
    order = models.ForeignKey('retailer_to_sp.Order', related_name='rt_payment_retailer_order',
                              on_delete=models.DO_NOTHING)
    payment_type = models.ForeignKey(PaymentType, default=None, null=True, related_name='payment_type_payment', on_delete=models.DO_NOTHING)
    transaction_id = models.CharField(max_length=70, default=None, null=True, blank=True, help_text="Transaction ID for Non Cash Payments.")
    paid_by = models.ForeignKey(User, related_name='rt_payment_retailer_buyer', null=True, blank=True,
                                on_delete=models.DO_NOTHING)
    processed_by = models.ForeignKey(User, related_name='rt_payment_retailer', null=True, blank=True,
                                     on_delete=models.DO_NOTHING)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Buyer - Payment'


class DiscountedRetailerProduct(RetailerProduct):
    class Meta:
        proxy = True
        verbose_name = 'Discounted Product'
        verbose_name_plural = 'Discounted Products'


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
    retailer_shop = models.ForeignKey(Shop, related_name='retailer_shop_vendor', on_delete=models.CASCADE,
                                      null=True, blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.vendor_name

    def save(self, *args, **kwargs):
        pin_code_obj = Pincode.objects.filter(pincode=self.pincode).last()
        if pin_code_obj:
            self.city = pin_code_obj.city
            self.state = pin_code_obj.city.state
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Store - Vendor'


class PosCart(models.Model):
    OPEN = "open"
    PARTIAL_DELIVERED = "partially_delivered"
    DELIVERED = "fully_delivered"
    CANCELLED = "cancelled"
    ORDER_STATUS = (
        (OPEN, "Open"),
        (PARTIAL_DELIVERED, "Partially Delivered"),
        (DELIVERED, "Completely Delivered"),
        (CANCELLED, "Cancelled")
    )

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    retailer_shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    po_no = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=200, choices=ORDER_STATUS, null=True, blank=True, default='open')
    products = models.ManyToManyField(RetailerProduct, through='pos.PosCartProductMapping')
    raised_by = models.ForeignKey(User, related_name='po_raise_user', null=True, blank=True, on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(User, related_name='po_last_modified_user', null=True, blank=True,
                                         on_delete=models.CASCADE)
    gf_order_no = models.CharField(null=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store - PO"

    def vendor_name(self):
        return self.vendor.vendor_name

    def __str__(self):
        return str(self.po_no)


class PosCartProductMapping(models.Model):
    cart = models.ForeignKey(PosCart, related_name='po_products', on_delete=models.CASCADE)
    product = models.ForeignKey(RetailerProduct, on_delete=models.CASCADE)
    qty = models.DecimalField(max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(0)], null=True)
    pack_size = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    is_grn_done = models.BooleanField(default=False)
    is_bulk = models.BooleanField(default=False)
    qty_conversion_unit = models.ForeignKey(MeasurementUnit, related_name='rt_unit_pos_cart_mapping',
                                            null=True, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product')

    @property
    def ordered_packs(self):
        if self.product.product_pack_type == 'packet' and not self.is_bulk:
            return int(self.pack_size)
        return None

    @property
    def qty_given(self):
        qty = self.qty
        if self.product.product_pack_type == 'loose' and qty:
            default_unit = MeasurementUnit.objects.get(category=self.product.measurement_category, default=True)
            if self.qty_conversion_unit:
                return round(Decimal(qty) * default_unit.conversion / self.qty_conversion_unit.conversion, 3)
            else:
                return round(Decimal(qty) * default_unit.conversion / default_unit.conversion, 3)

        elif self.product.product_pack_type == 'packet' and qty:
            return int(qty)
            # return int(Decimal(qty) / Decimal(self.pack_size))
        return int(qty)

    @property
    def given_qty_unit(self):
        if self.product.product_pack_type == 'loose':
            if self.qty_conversion_unit:
                return self.qty_conversion_unit.unit
            else:
                default_unit = MeasurementUnit.objects.get(category=self.product.measurement_category, default=True)
                return default_unit.unit

        return None

    def total_pieces(self):
        if self.is_bulk:
            return int(self.qty)
        return round(self.qty * self.pack_size, 2)

    def total_price(self):
        if self.is_bulk:
            return round(self.price * self.qty, 2)
        return round(self.price * self.qty * self.pack_size, 2)

    def product_name(self):
        return self.product.name

    def product_pack_type(self):
        return self.product.product_pack_type

    def __str__(self):
        return self.product.name


class PosOrder(models.Model):
    ordered_cart = models.OneToOneField(PosCart, related_name='pos_po_order', on_delete=models.CASCADE)
    order_no = models.CharField(verbose_name='PO Number', max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.order_no)


class PosGRNOrder(models.Model):
    grn_id = models.CharField(max_length=255, null=True, blank=True)
    invoice_no = models.CharField(max_length=100, null=True)
    invoice_date = models.DateField(null=True)
    invoice_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')
    order = models.ForeignKey(PosOrder, verbose_name='PO Number', on_delete=models.CASCADE)
    added_by = models.ForeignKey(User, related_name='grn_order_added', null=True, blank=True, on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(User, related_name='grn_order_last_modified', null=True, blank=True,
                                         on_delete=models.CASCADE)
    products = models.ManyToManyField(RetailerProduct, through='pos.PosGRNOrderProductMapping')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @property
    def po_no(self):
        return self.order.ordered_cart.po_no

    @property
    def vendor_name(self):
        return self.order.ordered_cart.vendor_name

    @property
    def po_status(self):
        return self.order.ordered_cart.status

    class Meta:
        verbose_name = "Store - GRN"


class PosGRNOrderProductMapping(models.Model):
    grn_order = models.ForeignKey(PosGRNOrder, related_name='po_grn_products', on_delete=models.CASCADE)
    product = models.ForeignKey(RetailerProduct, related_name='pos_product_grn_order_product', on_delete=models.CASCADE)
    received_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    pack_size = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @property
    def received_packs(self):
        if self.product.product_pack_type == 'packet':
            return int(self.pack_size)
        return None

    @property
    def qty_given(self):
        qty = self.received_qty
        if self.product.product_pack_type == 'loose' and qty:
            po_product = PosCartProductMapping.objects.filter(
                cart=self.grn_order.order.ordered_cart, product=self.product).last()
            default_unit = MeasurementUnit.objects.get(category=self.product.measurement_category, default=True)
            if po_product.qty_conversion_unit:
                return round(Decimal(qty) * default_unit.conversion / po_product.qty_conversion_unit.conversion, 3)
            else:
                return round(Decimal(qty) * default_unit.conversion / default_unit.conversion, 3)
        elif self.product.product_pack_type == 'packet' and qty:
            return int(qty)
        return qty

    @property
    def given_qty_unit(self):
        if self.product.product_pack_type == 'loose':
            if PosCartProductMapping.objects.filter(cart=self.grn_order.order.ordered_cart,
                                                    product=self.product).last().qty_conversion_unit:
                return PosCartProductMapping.objects.filter(cart=self.grn_order.order.ordered_cart,
                                                            product=self.product).last().qty_conversion_unit.unit
            else:
                return MeasurementUnit.objects.get(category=self.product.measurement_category, default=True).unit
        return None


class Document(models.Model):
    grn_order = models.OneToOneField(PosGRNOrder, null=True, blank=True, on_delete=models.CASCADE,
                                     related_name='pos_grn_invoice')
    document_number = models.CharField(max_length=255, null=True, blank=True)
    document = models.FileField(null=True, blank=True, upload_to='pos_grn_invoice')


class ProductChange(models.Model):
    EVENT_TYPE_CHOICES = (
        ('product', 'Product'),
        ('cart', 'Cart'),
    )
    product = models.ForeignKey(RetailerProduct, related_name='retailer_product', on_delete=models.CASCADE)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    event_id = models.CharField(max_length=255)
    changed_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)


class ProductChangeFields(models.Model):
    COLUMN_CHOICES = (
        ('selling_price', 'Selling Price'),
        ('mrp', 'MRP'),
        ('offer_price', 'offer_price'),
        ('offer_start_date', 'Offer Start Date'),
        ('offer_end_date', 'Offer End Date'),
    )
    product_change = models.ForeignKey(ProductChange, related_name='price_change_cols', on_delete=models.DO_NOTHING)
    column_name = models.CharField(max_length=255, choices=COLUMN_CHOICES)
    old_value = models.CharField(max_length=255, null=True)
    new_value = models.CharField(max_length=255, null=True)


class RetailerCouponRuleSet(CouponRuleSet):
    class Meta:
        proxy = True
        verbose_name = 'Coupon Ruleset'


class RetailerRuleSetProductMapping(RuleSetProductMapping):
    class Meta:
        proxy = True
        verbose_name = 'Coupon Ruleset Product Mapping'


class RetailerCoupon(Coupon):
    class Meta:
        proxy = True
        verbose_name = 'Coupon'


class RetailerCart(Cart):
    class Meta:
        proxy = True
        verbose_name = 'Buyer - Cart'


class RetailerCartProductMapping(CartProductMapping):
    class Meta:
        proxy = True
        verbose_name = 'Cart Product Mapping'


class RetailerOrderedProduct(OrderedProduct):
    class Meta:
        proxy = True
        verbose_name = 'Buyer - Order'


class RetailerOrderedProductMapping(OrderedProductMapping):
    class Meta:
        proxy = True
        verbose_name = 'Ordered Product Mapping'


class RetailerOrderReturn(OrderReturn):
    class Meta:
        proxy = True
        verbose_name = 'Buyer - Return'

    @property
    def order_no(self):
        return self.order.order_no


class RetailerReturnItems(ReturnItems):
    class Meta:
        proxy = True
        verbose_name = 'Return Item'

    def __str__(self):
        return ''


class InventoryStatePos(PosInventoryState):
    class Meta:
        proxy = True
        verbose_name = 'Inventory State'


class InventoryPos(PosInventory):
    class Meta:
        proxy = True
        verbose_name = 'Inventory'


class InventoryChangePos(PosInventoryChange):
    class Meta:
        proxy = True
        verbose_name = 'Inventory Change'


class PosReturnGRNOrder(models.Model):
    RETURNED, CANCELLED = 'RETURNED', 'CANCELLED'
    RETURN_STATUS = Choices((RETURNED, 'Returned'), (CANCELLED, 'Cancelled'))
    pr_number = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=10, choices=RETURN_STATUS, default=RETURN_STATUS.RETURNED)
    grn_ordered_id = models.ForeignKey(PosGRNOrder, related_name='grn_order_return', null=True, blank=True,
                                       on_delete=models.DO_NOTHING)
    vendor_id = models.ForeignKey(Vendor, related_name='vendor_return', null=True, blank=True,
                                  on_delete=models.DO_NOTHING)
    last_modified_by = models.ForeignKey(User, related_name='grn_return_last_modified_user', null=True, blank=True,
                                         on_delete=models.CASCADE)
    debit_note_number = models.CharField(max_length=255, null=True, blank=True)
    debit_note = models.FileField(upload_to='pos/purchase_return/documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store - GRN - Return"

    @property
    def po_no(self):
        try:
            return self.grn_ordered_id.order.ordered_cart.po_no
        except Exception:
            return None


class PosReturnItems(models.Model):
    grn_return_id = models.ForeignKey(PosReturnGRNOrder, related_name='grn_order_return', on_delete=models.CASCADE)
    product = models.ForeignKey(RetailerProduct, related_name='grn_product_return', on_delete=models.CASCADE)
    selling_price = models.FloatField(null=True, blank=True)
    return_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    pack_size = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store - GRN - Return items"
        unique_together = ('grn_return_id', 'product')

    @property
    def qty_given(self):
        qty = self.return_qty
        if self.product.product_pack_type == 'loose' and qty and self.grn_return_id.grn_ordered_id:
            po_product = PosCartProductMapping.objects.filter(
                cart=self.grn_return_id.grn_ordered_id.order.ordered_cart, product=self.product).last()
            default_unit = MeasurementUnit.objects.get(category=self.product.measurement_category, default=True)
            if po_product.qty_conversion_unit:
                return round(Decimal(qty) * default_unit.conversion / po_product.qty_conversion_unit.conversion, 3)
            return round(Decimal(qty) * default_unit.conversion / default_unit.conversion, 3)

        elif self.product.product_pack_type == 'loose' and qty and not self.grn_return_id.grn_ordered_id:
            default_unit = MeasurementUnit.objects.get(category=self.product.measurement_category, default=True)
            return round(Decimal(qty) * default_unit.conversion / default_unit.conversion, 3)

        elif self.product.product_pack_type == 'packet' and qty:
            return int(qty)
        return qty

    @property
    def given_qty_unit(self):
        if self.product.product_pack_type == 'loose' and self.grn_return_id.grn_ordered_id:
            if PosCartProductMapping.objects.filter(cart=self.grn_return_id.grn_ordered_id.order.ordered_cart,
                                                    product=self.product).last().qty_conversion_unit:
                return PosCartProductMapping.objects.filter(cart=self.grn_return_id.grn_ordered_id.order.ordered_cart,
                                                            product=self.product).last().qty_conversion_unit.unit
            else:
                return MeasurementUnit.objects.get(category=self.product.measurement_category, default=True).unit
        elif self.product.product_pack_type == 'loose' and not self.grn_return_id.grn_ordered_id:
            return MeasurementUnit.objects.get(category=self.product.measurement_category, default=True).unit
        return None

    @property
    def grn_received_qty(self):
        return self.grn_return_id.grn_ordered_id.po_grn_products.filter(product=self.product).first().received_qty

    def save(self, *args, **kwargs):
        if not self.id and self.grn_return_id.grn_ordered_id:
            po_product = PosCartProductMapping.objects.filter(
                cart=self.grn_return_id.grn_ordered_id.order.ordered_cart, product=self.product).last()
            self.selling_price = po_product.price if po_product else 0
        # elif not self.id:
        #     self.selling_price = self.return_price
        super(PosReturnItems, self).save(*args, **kwargs)


class RetailerOrderedReport(Order):
    class Meta:
        proxy = True
        verbose_name = 'Order - Report'


class PosTrip(models.Model):
    ORDER_TRIP_TYPE = (
        ('ECOM', 'Ecom'),
    )
    shipment = models.ForeignKey(OrderedProduct,
                                 related_name='pos_trips',
                                 on_delete=models.CASCADE)
    trip_type = models.CharField(choices=ORDER_TRIP_TYPE,
                                 max_length=10)
    trip_start_at = models.DateTimeField(null=True,
                                         blank=True)
    trip_end_at = models.DateTimeField(null=True,
                                       blank=True)

    def __str__(self):
        return str(self.id) + ' | ' + self.trip_type


class BulkRetailerProduct(models.Model):
    products_csv = models.FileField(
        upload_to='pos/products_csv',
        null=True, blank=False
    )
    seller_shop = models.ForeignKey(
        Shop, related_name='pos_bulk_seller_shop',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    uploaded_by = models.ForeignKey(
        get_user_model(), null=True, related_name='product_uploaded_by',
        on_delete=models.DO_NOTHING
    )
    bulk_no = models.CharField(unique=True, max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def uploaded_product_list_status(self, error_dict):
        product_upload_status_info = []
        info_logger.info(f"[pos:models.py:BulkRetailerProduct]-uploaded_product_list_status function called")
        error_dict[str('bulk_no')] = str(self.bulk_no)
        product_upload_status_info.extend([error_dict])

        status = "Bulk Product Creation"
        url = f"""<h2 style="color:blue;"><a href="%s" target="_blank">
        Download {status} List Status</a></h2>""" % \
              (
                  reverse(
                      'admin:products_list_status',
                      args=(product_upload_status_info)
                  )
              )
        return url

    def clean(self, *args, **kwargs):
        if self.products_csv:
            self.save()
            error_dict, validated_rows = bulk_product_validation(self.products_csv, self.seller_shop.pk)
            bulk_create_update_validated_products(self.uploaded_by, self.seller_shop.pk, validated_rows)
            if len(error_dict) > 0:
                error_logger.info(f"Product can't create/update for some rows: {error_dict}")
                raise ValidationError(mark_safe(f"Product can't create/update for some rows, Please click the "
                                                f"below Link for seeing the status"
                                                f"{self.uploaded_product_list_status(error_dict)}"))
        else:
            super(BulkRetailerProduct, self).clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.pk is None:
            current_date = datetime.datetime.now().strftime("%d%m%Y")
            starts_with = "BP" + str(current_date) + str(self.seller_shop.pk).zfill(6)
            last_number = 0
            instance_with_current_pattern = BulkRetailerProduct.objects.filter(bulk_no__icontains=starts_with)
            if instance_with_current_pattern.exists():
                last_instance_no = BulkRetailerProduct.objects.filter(bulk_no__icontains=starts_with).latest('bulk_no')
                last_number = int(getattr(last_instance_no, 'bulk_no')[-3:])
            last_number += 1
            self.bulk_no = starts_with + str(last_number).zfill(3)
            self.uploaded_by = self.uploaded_by
            super().save(*args, **kwargs)


