import datetime

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.db.models.signals import post_save
from django.db.models import Sum,F, FloatField
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from retailer_backend.common_function import (
    order_id_pattern, brand_credit_note_pattern, getcredit_note_id,
    retailer_sp_invoice
)
from shops.models import Shop, ShopNameDisplay
from brand.models import Brand
from addresses.models import Address
from products.models import Product,ProductPrice
from otp.sms import SendSms
from accounts.models import UserWithName
# from sp_to_gram.models import (OrderedProduct as SPGRN, OrderedProductMapping as SPGRNProductMapping)

CART_STATUS = (
    ("active", "Active"),
    ("pending", "Pending"),
    ("deleted", "Deleted"),
    ("ordered", "Ordered"),
    ("order_shipped", "Dispatched"),
    ("partially_delivered", "Partially Delivered"),
    ("delivered", "Delivered"),
    ("closed", "Closed"),
    ("payment_done_approval_pending", "Payment Done Approval Pending")
)

ITEM_STATUS = (
    ("partially_delivered", "Partially Delivered"),
    ("delivered", "Delivered"),
)

NOTE_TYPE_CHOICES = (
    ("debit_note", "Debit Note"),
    ("credit_note", "Credit Note"),
)

PAYMENT_MODE_CHOICES = (
    ("cash_on_delivery", "Cash On Delivery"),
    ("neft", "NEFT"),
)

MESSAGE_STATUS = (
    ("pending", "Pending"),
    ("resolved", "Resolved"),
)
SELECT_ISSUE = (
    ("cancellation", "Cancellation"),
    ("return", "Return"),
    ("others", "Others")
)

TRIP_STATUS = (
    ('READY', 'Ready'),
    ('CANCELLED', 'Cancelled'),
    ('STARTED', 'Started'),
    ('COMPLETED', 'Completed')
#   ('READY_FOR_COMMERCIAL', 'Ready for commercial'),
#   ('CLOSED', 'Closed')
)


class Cart(models.Model):
    order_id = models.CharField(max_length=255, null=True, blank=True)
    seller_shop = models.ForeignKey(
        Shop, related_name='rt_seller_shop_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    buyer_shop = models.ForeignKey(
        Shop, related_name='rt_buyer_shop_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    cart_status = models.CharField(
        max_length=200, choices=CART_STATUS,
        null=True, blank=True
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Order Items Detail'

    def __str__(self):
        return self.order_id

    @property
    def subtotal(self):
        return self.rt_cart_list.aggregate(subtotal_sum=Sum(F('cart_product_price__price_to_retailer') * F('no_of_pieces'),output_field=FloatField()))['subtotal_sum']

    @property
    def qty_sum(self):
        return self.rt_cart_list.aggregate(qty_sum=Sum('qty'))['qty_sum']


@receiver(post_save, sender=Cart)
def create_order_id(sender, instance=None, created=False, **kwargs):
    if created:
        instance.order_id = order_id_pattern(instance.pk)
        instance.save()


class CartProductMapping(models.Model):
    cart = models.ForeignKey(Cart, related_name='rt_cart_list',
                             on_delete=models.CASCADE)
    cart_product = models.ForeignKey(
        Product, related_name='rt_cart_product_mapping',
        on_delete=models.CASCADE
    )
    cart_product_price = models.ForeignKey(
        ProductPrice, related_name='rt_cart_product_price_mapping',
        on_delete=models.CASCADE, null=True, blank=True
    )
    qty = models.PositiveIntegerField(default=0)
    #tax = models.PositiveIntegerField(default=0)
    no_of_pieces = models.PositiveIntegerField(default=0)
    qty_error_msg = models.CharField(
        max_length=255, null=True,
        blank=True, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.cart_product.product_name


class Order(models.Model):
    ACTIVE = 'active'
    PENDING = 'pending'
    DELETED = 'deleted'
    ORDERED = 'ordered'
    PAYMENT_DONE_APPROVAL_PENDING = 'payment_done_approval_pending'
    OPDP = 'opdp'
    DISPATCHED = 'dispatched'
    PARTIAL_DELIVERED = 'p_delivered'
    DELIVERED = 'delivered'
    CLOSED = 'closed'
    PDAP = 'payment_done_approval_pending'
    ORDER_PLACED_DISPATCH_PENDING = 'opdp'

    ORDER_STATUS = (
        (ORDERED, 'Order Placed'),
        ('DISPATCH_PENDING', 'Dispatch Pending'),
        (ACTIVE, "Active"),
        (PENDING, "Pending"),
        (DELETED, "Deleted"),
        (ORDERED, "Ordered"),
        (DISPATCHED, "Dispatched"),
        (PARTIAL_DELIVERED, "Partially Delivered"),
        (DELIVERED, "Delivered"),
        (CLOSED, "Closed"),
        (PDAP, "Payment Done Approval Pending"),
        (ORDER_PLACED_DISPATCH_PENDING, "Order Placed Dispatch Pending"),
        ('DISPATCH_PENDING', 'Dispatch Placed'),
        ('PARTIALLY_SHIPPED', 'Partially Shipped'),
        ('SHIPPED', 'Shipped'),
        ('CANCELLED', 'Cancelled'),
        ('DENIED', 'Denied'),
        (PAYMENT_DONE_APPROVAL_PENDING, "Payment Done Approval Pending"),
        (OPDP, "Order Placed Dispatch Pending"),

    )
    #Todo Remove
    seller_shop = models.ForeignKey(
        Shop, related_name='rt_seller_shop_order',
        null=True, blank=True, on_delete=models.CASCADE
    )
    #Todo Remove
    buyer_shop = models.ForeignKey(
        Shop, related_name='rt_buyer_shop_order',
        null=True, blank=True, on_delete=models.CASCADE
    )
    ordered_cart = models.OneToOneField(
        Cart, related_name='rt_order_cart_mapping',
        on_delete=models.CASCADE
    )
    order_no = models.CharField(max_length=255, null=True, blank=True)
    billing_address = models.ForeignKey(
        Address, related_name='rt_billing_address_order',
        null=True, blank=True, on_delete=models.CASCADE
    )
    shipping_address = models.ForeignKey(
        Address, related_name='rt_shipping_address_order',
        null=True, blank=True, on_delete=models.CASCADE
    )
    total_mrp = models.FloatField(default=0)
    total_discount_amount = models.FloatField(default=0)
    total_tax_amount = models.FloatField(default=0)
    total_final_amount = models.FloatField(
        default=0, verbose_name='Ordered Amount')
    order_status = models.CharField(max_length=50,choices=ORDER_STATUS)
    ordered_by = models.ForeignKey(
        get_user_model(), related_name='rt_ordered_by_user',
        null=True, blank=True, on_delete=models.CASCADE
    )
    received_by = models.ForeignKey(
        get_user_model(), related_name='rt_received_by_user',
        null=True, blank=True, on_delete=models.CASCADE
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_order_modified_user',
        null=True, blank=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_no or str(self.id)

    class Meta:
        ordering = ['-created_at']

    def payments(self):
        payment_mode = []
        payment_amount = []
        payments = self.rt_payment.all()
        if payments:
            for payment in payments:
                payment_mode.append(payment.get_payment_choice_display())
                payment_amount.append(float(payment.paid_amount))
        return payment_mode, payment_amount

    @property
    def payment_mode(self):
        payment_mode, _ = self.payments()
        return payment_mode

    @property
    def paid_amount(self):
        _, payment_amount = self.payments()
        return payment_amount

    @property
    def total_paid_amount(self):
        _, payment_amount = self.payments()
        return sum(payment_amount)


class Trip(models.Model):
    seller_shop = models.ForeignKey(
        Shop, related_name='trip_seller_shop',
        on_delete=models.CASCADE
    )
    dispatch_no = models.CharField(max_length=50, unique=True)
    delivery_boy = models.ForeignKey(
        UserWithName, related_name='order_delivered_by_user',
        on_delete=models.CASCADE, verbose_name='Delivery Boy'
    )
    vehicle_no = models.CharField(max_length=50)
    trip_status = models.CharField(max_length=100, choices=TRIP_STATUS)
    e_way_bill_no = models.CharField(max_length=50, blank=True, null=True)
    starts_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} -> {}".format(
            self.dispatch_no,
            self.delivery_boy.first_name if self.delivery_boy.first_name else self.delivery_boy.phone_number
        )

    def save(self, *args, **kwargs):
        if self._state.adding:
            date = datetime.date.today().strftime('%d%m%y')
            shop = self.seller_shop_id
            shop_id_date = "%s/%s" % (shop, date)
            last_dispatch_no = Trip.objects.filter(
                dispatch_no__contains=shop_id_date)
            if last_dispatch_no:
                dispatch_attempt = int(
                    last_dispatch_no.last().dispatch_no.split('/')[-1])
                dispatch_attempt += 1
            else:
                dispatch_attempt = 1
            final_dispatch_no = "%s/%s/%s" % ('DIS', shop_id_date, dispatch_attempt)
            self.dispatch_no = final_dispatch_no
        if self.trip_status == 'STARTED':
            self.starts_at = datetime.datetime.now()
        elif self.trip_status == 'COMPLETED':
            self.completed_at = datetime.datetime.now()
        super().save(*args, **kwargs)

    def dispathces(self):
        return mark_safe("<a href='/admin/retailer_to_sp/cart/trip-planning/%s/change/'>%s<a/>" % (self.pk,
                                                                                                   self.dispatch_no)
                         )

    @property
    def current_trip_status(self):
        trip_status = self.trip_status
        if trip_status:
            return str(self.get_trip_status_display())
        return str("-------")


class OrderedProduct(models.Model):
    SHIPMENT_STATUS = (
        ('SHIPMENT_CREATED', 'QC Pending'),
        ('READY_TO_SHIP', 'QC Passed'),
        ('READY_TO_DISPATCH', 'Ready to Dispatch'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('FULLY_RETURNED_AND_COMPLETED', 'Fully Returned and Completed'),
        ('PARTIALLY_DELIVERED_AND_COMPLETED', 'Partially Delivered and Completed'),
        ('FULLY_DELIVERED_AND_COMPLETED', 'Fully Delivered and Completed'),
        ('FULLY_RETURNED_AND_CLOSED', 'Fully Returned and Closed'),
        ('PARTIALLY_DELIVERED_AND_CLOSED', 'Partially Delivered and Closed'),
        ('FULLY_DELIVERED_AND_CLOSED', 'Fully Delivered and Closed'),
        ('CANCELLED', 'Cancelled')
    )
    order = models.ForeignKey(
        Order, related_name='rt_order_order_product',
        on_delete=models.CASCADE, null=True, blank=True
    )
    shipment_status = models.CharField(
        max_length=50, choices=SHIPMENT_STATUS,
        null=True, blank=True, verbose_name='Current Shipment Status',
        default='READY_TO_SHIP'
    )
    invoice_no = models.CharField(max_length=255, null=True, blank=True)
    trip = models.ForeignKey(
        Trip, related_name="rt_invoice_trip",
        null=True, blank=True, on_delete=models.CASCADE,
    )
    received_by = models.ForeignKey(
        get_user_model(), related_name='rt_ordered_product_received_by_user',
        null=True, blank=True, on_delete=models.CASCADE
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_order',
        null=True, blank=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Invoice Date")
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Update Delivery/ Returns/ Damage'

    def __str__(self):
        return self.invoice_no or str(self.id)

    @property
    def shipment_address(self):
        if self.order:
            address = Address.objects.select_related(
                'shop_name').get(pk=self.order.shipping_address_id)
            address_line = address.address_line1
            contact = address.address_contact_number
            shop_name = address.shop_name.shop_name
            return str("%s, %s(%s)") % (shop_name, address_line, contact)
        return str("-")

    def payments(self):
        payment_mode = []
        payment_amount = []
        order = self.order
        if order:
            payments = order.rt_payment.all()
            if payments:
                for payment in payments:
                    payment_mode.append(payment.get_payment_choice_display())
                    payment_amount.append(float(payment.paid_amount))
            return payment_mode, payment_amount

    @property
    def payment_mode(self):
        payment_mode, _ = self.payments()
        return payment_mode

    @property
    def invoice_city(self):
        city = self.order.shipping_address.city
        return str(city)

    @property
    def invoice_amount(self):
        if self.order:
            total_amount = []
            seller_shop = self.order.seller_shop
            ordered_products = self.rt_order_product_order_product_mapping.all()
            for product in ordered_products:
                if product.product:
                    # product_price = ProductPrice.objects.filter(
                    #     shop=seller_shop, product=product.product, status=True
                    # ).last().price_to_retailer
                    product_price = float(round(product.product.rt_cart_product_mapping.last().cart_product_price.price_to_retailer, 2))
                    shipped_qty = float(product.shipped_qty)
                    amount = shipped_qty * product_price
                    total_amount.append(amount)
            return str(round(sum(total_amount),2))
        return str("-")

    def save(self, *args, **kwargs):
        if self._state.adding:
            invoice_prefix = self.order.seller_shop.invoice_pattern.filter(
                status='ACT').last().pattern
            last_invoice = OrderedProduct.objects.filter(
                order__in=self.order.seller_shop.rt_seller_shop_order.all()
            ).order_by('invoice_no').last()
            if last_invoice:
                invoice_id = getcredit_note_id(last_invoice.invoice_no,
                                               invoice_prefix)
                invoice_id += 1
            else:
                invoice_id = 1
            self.invoice_no = retailer_sp_invoice(invoice_prefix, invoice_id)
        super().save(*args, **kwargs)


class OrderedProductMapping(models.Model):
    ordered_product = models.ForeignKey(
        OrderedProduct, related_name='rt_order_product_order_product_mapping',
        null=True, blank=True, on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product, related_name='rt_product_order_product',
        null=True, blank=True, on_delete=models.CASCADE
    )
    shipped_qty = models.PositiveIntegerField(default=0, verbose_name="Shipped Pieces")
    delivered_qty = models.PositiveIntegerField(default=0, verbose_name="Delivered Pieces")
    returned_qty = models.PositiveIntegerField(default=0, verbose_name="Returned Pieces")
    damaged_qty = models.PositiveIntegerField(default=0, verbose_name="Damaged Pieces")
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_order_product',
        null=True, blank=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super(OrderedProductMapping, self).clean()
        returned_qty = int(self.returned_qty)
        damaged_qty = int(self.damaged_qty)
        if returned_qty > 0 or damaged_qty > 0:
            already_shipped_qty = int(self.shipped_qty)
            if sum([returned_qty, damaged_qty]) > already_shipped_qty:
                raise ValidationError(
                    _('Sum of returned and damaged pieces should be '
                      'less than no. of pieces to ship'),
                )

    @property
    def ordered_qty(self):
        if self.ordered_product:
            qty = self.ordered_product.order.ordered_cart.rt_cart_list.filter(
                cart_product=self.product).values('qty')
            qty = qty.first().get('qty')
            inner_case_size = self.product.product_inner_case_size
            no_of_pieces = int(inner_case_size) * int(qty if qty else 0)
            return str(no_of_pieces)
        return str("-")
    ordered_qty.fget.short_description = "Ordered Pieces"

    @property
    def already_shipped_qty(self):
        already_shipped_qty = OrderedProductMapping.objects.filter(
            ordered_product__in=self.ordered_product.order.rt_order_order_product.all(),
            product=self.product).aggregate(
            Sum('delivered_qty')).get('delivered_qty__sum', 0)
        return already_shipped_qty if already_shipped_qty else 0
    already_shipped_qty.fget.short_description = "Delivered Qty"

    @property
    def to_be_shipped_qty(self):
        all_ordered_product = self.ordered_product.order.rt_order_order_product.all()
        all_ordered_product_exclude_current = all_ordered_product.exclude(id=self.ordered_product_id)
        to_be_shipped_qty = OrderedProductMapping.objects.filter(
            ordered_product__in=all_ordered_product_exclude_current,
            product=self.product).aggregate(
            Sum('shipped_qty')).get('shipped_qty__sum', 0)
        to_be_shipped_qty = to_be_shipped_qty if to_be_shipped_qty else 0
        to_be_shipped_qty = to_be_shipped_qty - self.already_shipped_qty
        return to_be_shipped_qty
    to_be_shipped_qty.fget.short_description = "Already Shipped Qty"

    @property
    def gf_code(self):
        if self.product:
            gf_code = self.product.product_gf_code
            return str(gf_code)
        return str("-")

    def get_shop_specific_products_prices_sp(self):
        return self.product.product_pro_price.filter(
            shop__shop_type__shop_type='sp', status=True
        ).last()

    def get_products_gst_tax(self):
        return self.product.product_pro_tax.filter(tax__tax_type='gst')

    def get_products_gst_cess(self):
        return self.product.product_pro_tax.filter(tax__tax_type='cess')


class Dispatch(OrderedProduct):
    class Meta:
        proxy = True


class DispatchProductMapping(OrderedProductMapping):
    class Meta:
        proxy = True
        verbose_name = _("To be Ship product")
        verbose_name_plural = _("To be Ship products")


class Shipment(OrderedProduct):
    class Meta:
        proxy = True
        verbose_name = _("Plan Shipment")
        verbose_name_plural = _("Plan Shipment")


class ShipmentProductMapping(OrderedProductMapping):

    class Meta:
        proxy = True
        verbose_name = _("To be Ship product")
        verbose_name_plural = _("To be Ship products")

    def clean(self):
        ordered_qty = int(self.ordered_qty)
        shipped_qty = int(self.shipped_qty)
        to_be_shipped_qty = int(self.to_be_shipped_qty)
        already_shipped_qty = int(self.already_shipped_qty)
        max_qty_allowed = ordered_qty - (to_be_shipped_qty + already_shipped_qty)
        if max_qty_allowed < shipped_qty:
            raise ValidationError(
                _('Max. allowed Qty: %s') % max_qty_allowed,
                )


ShipmentProductMapping._meta.get_field('shipped_qty').verbose_name = 'No. of Pieces to Ship'


class CustomerCare(models.Model):
    order_id = models.ForeignKey(
        Order, on_delete=models.CASCADE, null=True
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    email_us = models.URLField(default='info@grmafactory.com')
    contact_us = models.CharField(max_length=10, default='7607846774')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    order_status = models.CharField(
        max_length=20, choices=MESSAGE_STATUS,
        default='pending', null=True
    )
    select_issue = models.CharField(
        verbose_name="Issue", max_length=100,
        choices=SELECT_ISSUE, null=True
    )
    complaint_detail = models.CharField(max_length=2000, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(CustomerCare, self).save()
        self.name = "CustomerCare/Message/%s" % self.pk
        super(CustomerCare, self).save()


class Payment(models.Model):
    PAYMENT_DONE_APPROVAL_PENDING = "payment_done_approval_pending"
    CASH_COLLECTED = "cash_collected"
    APPROVED_BY_FINANCE = "approved_by_finance"
    PAYMENT_STATUS = (
        (PAYMENT_DONE_APPROVAL_PENDING, "Payment done approval pending"),
        (CASH_COLLECTED, "Cash Collected"),
        (APPROVED_BY_FINANCE, "Approved by finance"),
    )

    order_id = models.ForeignKey(
        Order, related_name='rt_payment',
        on_delete=models.CASCADE, null=True
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')
    payment_choice = models.CharField(verbose_name="Payment Mode",max_length=30,choices=PAYMENT_MODE_CHOICES, null=True)
    neft_reference_number = models.CharField(max_length=20, null=True,blank=True)
    imei_no = models.CharField(max_length=100, null=True, blank=True)
    payment_status = models.CharField(max_length=50, null=True, blank=True,choices=PAYMENT_STATUS, default=PAYMENT_DONE_APPROVAL_PENDING)

    def __str__(self):
        return self.name

    def save(self, *args,**kwargs):
        super(Payment, self).save()
        self.name = "Payment/%s" % self.pk
        super(Payment, self).save()


@receiver(post_save, sender=Payment)
def order_notification(sender, instance=None, created=False, **kwargs):

    if created:
        if instance.order_id.ordered_by.first_name:
            username = instance.order_id.ordered_by.first_name
        else:
            username = instance.order_id.ordered_by.phone_number
        order_no = str(instance.order_id)
        total_amount = str(instance.order_id.total_final_amount)
        shop_name = str(instance.order_id.ordered_cart.buyer_shop.shop_name)
        items_count = instance.order_id.ordered_cart.rt_cart_list.count()
        message = SendSms(phone=instance.order_id.ordered_by,
                          body="Hi %s, We have received your order no. %s with %s items and totalling to %s Rupees for your shop %s. We will update you further on shipment of the items."\
                              " Thanks," \
                              " Team GramFactory" % (username, order_no,items_count, total_amount, shop_name))
        message.send()


class Return(models.Model):
    invoice_no = models.ForeignKey(
        OrderedProduct, on_delete=models.CASCADE,
        null=True, verbose_name='Shipment Id'
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    shipped_by = models.ForeignKey(
        get_user_model(),
        related_name='return_shipped_product_ordered_by_user',
        null=True, blank=True, on_delete=models.CASCADE
    )
    received_by = models.ForeignKey(
        get_user_model(),
        related_name='return_ordered_product_received_by_user',
        null=True, blank=True, on_delete=models.CASCADE
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='return_last_modified_user_order',
        null=True, blank=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        super(Return, self).save()
        self.name = "Return/%s" % self.pk
        super(Return, self).save()


class ReturnProductMapping(models.Model):
    return_id = models.ForeignKey(
        Return, related_name='rt_product_return_product_mapping',
        null=True, blank=True, on_delete=models.CASCADE
    )
    returned_product = models.ForeignKey(
        Product, related_name='rt_product_return_product',
        null=True, blank=True, on_delete=models.CASCADE
    )
    total_returned_qty = models.PositiveIntegerField(default=0)
    reusable_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(
        get_user_model(),
        related_name='return_last_modified_user_return_product',
        null=True, blank=True, on_delete=models.CASCADE
    )
    manufacture_date = models.DateField()
    expiry_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str('')

    def clean(self):
        super(ReturnProductMapping, self).clean()
        total_returned_qty = self.reusable_qty + self.damaged_qty
        if total_returned_qty != self.total_returned_qty:
            raise ValidationError(
                """Sum of Reusable quantity and damaged
                quantity must be equal to total returned quantity"""
            )

    def get_shop_specific_products_prices_sp_return(self):
        return self.returned_product.product_pro_price.filter(
            shop__shop_type__shop_type='sp', status=True
        )

    def get_products_gst_tax_return(self):
        return self.returned_product.product_pro_tax.filter(
            tax__tax_type='gst'
        )

    def get_products_gst_cess_return(self):
        return self.returned_product.product_pro_tax.filter(
            tax__tax_type='cess'
        )


class Note(models.Model):
    shop = models.ForeignKey(Shop, related_name='credit_notes', null=True, blank=True, on_delete=models.CASCADE)
    credit_note_id = models.CharField(max_length=255, null=True, blank=True)
    shipment = models.ForeignKey(OrderedProduct, null=True, blank=True, on_delete=models.CASCADE, related_name='credit_note')
    note_type = models.CharField(
        max_length=255, choices=NOTE_TYPE_CHOICES, default='credit_note'
    )
    amount = models.FloatField(default=0)
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_note',
        null=True, blank=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Credit Note"
        verbose_name_plural = "Credit Notes"

    def __str__(self):
        return str(self.credit_note_id)

    @property
    def invoice_no(self):
        if self.shipment:
            return self.shipment.invoice_no


# @receiver(post_save, sender=OrderedProduct)
# def change_order_status(sender, instance=None, created=False, **kwargs):
#     import pdb;pdb.set_trace()
#
#     if created:
#         ordered_products = instance.order.rt_order_order_product.all()
#         all_shipment_status = [ordered_product.shipment_status
#                                for ordered_product in ordered_products]
#         all_shipment_status = list(set(all_shipment_status))
#
#
# @receiver(post_save, sender=OrderedProductMapping)
# def change_order_status(sender, instance=None, created=False, **kwargs):
#     import pdb;pdb.set_trace()
#     ordered_product_mapping = instance.ordered_product.\
#         rt_order_product_order_product_mapping.all()
#     import pdb;pdb.set_trace()
#     shipment_status =  instance.ordered_product.shipment_status



