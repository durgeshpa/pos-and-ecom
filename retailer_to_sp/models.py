import datetime

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.db.models.signals import post_save
from django.db.models import Sum,F, FloatField
from django.utils.translation import ugettext_lazy as _

from retailer_backend.common_function import (
    order_id_pattern, brand_credit_note_pattern, getcredit_note_id,
    retailer_sp_invoice
)
from shops.models import Shop
from brand.models import Brand
from addresses.models import Address
from products.models import Product,ProductPrice
from otp.sms import SendSms
# from sp_to_gram.models import (OrderedProduct as SPGRN, OrderedProductMapping as SPGRNProductMapping)

ORDER_STATUS = (
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

PAYMENT_STATUS = (
    ("done", "Done"),
    ("pending", "Pending"),
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
        max_length=200, choices=ORDER_STATUS,
        null=True, blank=True
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

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
    DISPATCHED = 'dispatched'
    PARTIAL_DELIVERED = 'p_delivered'
    DELIVERED = 'delivered'
    CLOSED = 'closed'
    PDAP = 'payment_done_approval_pending'
    ORDER_PLACED_DISPATCH_PENDING = 'opdp'

    ORDER_STATUS = (
        (ACTIVE, "Active"),
        (PENDING, "Pending"),
        (DELETED, "Deleted"),
        (ORDERED, "Ordered"),
        (DISPATCHED, "Dispatched"),
        (PARTIAL_DELIVERED, "Partially Delivered"),
        (DELIVERED, "Delivered"),
        (CLOSED, "Closed"),
        (PDAP, "Payment Done Approval Pending"),
        (ORDER_PLACED_DISPATCH_PENDING, "Order Placed Dispatch Pending")

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
    total_final_amount = models.FloatField(default=0)
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
    payment_mode = models.CharField(
        max_length=255, choices=PAYMENT_MODE_CHOICES
    )
    reference_no = models.CharField(max_length=255, null=True, blank=True)
    payment_amount = models.FloatField(default=0)
    payment_status = models.CharField(
        max_length=255, choices=PAYMENT_STATUS,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_no or str(self.id)

    class Meta:
        ordering = ['-created_at']

class OrderedProduct(models.Model): 
    order = models.ForeignKey(
        Order, related_name='rt_order_order_product',
        on_delete=models.CASCADE, null=True, blank=True
    )
    invoice_no = models.CharField(max_length=255, null=True, blank=True)
    vehicle_no = models.CharField(max_length=255, null=True, blank=True)
    driver_name = models.CharField(max_length=60, null=True, blank=True)
    shipped_by = models.ForeignKey(
        get_user_model(), related_name='rt_shipped_product_ordered_by_user',
        null=True, blank=True, on_delete=models.CASCADE
    )
    received_by = models.ForeignKey(
        get_user_model(), related_name='rt_ordered_product_received_by_user',
        null=True, blank=True, on_delete=models.CASCADE
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_order',
        null=True, blank=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shipment Planning'

    def __str__(self):
        return self.invoice_no or str(self.id)

    def save(self, *args, **kwargs):
        if self._state.adding:
            invoice_prefix = self.order.ordered_cart.seller_shop.invoce_pattern.filter(
                status='ACT').last().pattern
            # last_invoice = OrderedProduct.objects.filter(
            #     order__in=self.order.ordered_cart.seller_shop.rt_seller_shop_order.all()
            # ).order_by('invoice_no').last()

            last_invoice = self.order.rt_order_order_product.filter(order__ordered_cart__in=self.order.ordered_cart.seller_shop.rt_seller_shop_cart.all()).order_by('invoice_no').last()
            if last_invoice:
                invoice_id = getcredit_note_id(last_invoice.invoice_no, invoice_prefix)
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
    shipped_qty = models.PositiveIntegerField(default=0)
    delivered_qty = models.PositiveIntegerField(default=0)
    returned_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_order_product',
        null=True, blank=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super(OrderedProductMapping,self).clean()
        delivered_qty = int(self.delivered_qty)
        returned_qty = int(self.returned_qty)
        damaged_qty = int(self.damaged_qty)
        already_shipped_qty = int(self.shipped_qty)
        if (delivered_qty or returned_qty) and sum([delivered_qty, returned_qty,
                damaged_qty]) != already_shipped_qty:
            raise ValidationError(
                _('Sum of Delivered, Returned and Damaged Quantity should be '
                  'equals to Already Shipped Quantity '),
            )

    @property
    def ordered_qty(self):
        if self.ordered_product:
            qty = self.ordered_product.order.ordered_cart.rt_cart_list.filter(
                cart_product=self.product).values('qty')
            print(qty)
            qty = qty.first().get('qty')
            return str(qty)
        return str("-")

    def get_shop_specific_products_prices_sp(self):
        return self.product.product_pro_price.filter(
            shop__shop_type__shop_type='sp', status=True
        ).last()

    def get_products_gst_tax(self):
        return self.product.product_pro_tax.filter(tax__tax_type='gst')

    def get_products_gst_cess(self):
        return self.product.product_pro_tax.filter(tax__tax_type='cess')


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
    payment_choice = models.CharField(max_length=30,choices=PAYMENT_MODE_CHOICES, null=True)
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



# @receiver(post_save, sender=ReturnProductMapping)
# def create_credit_note(sender, instance=None, created=False, **kwargs):
#     if created:
#         if instance.total_returned_qty > 0:
#             credit_note = Note.objects.filter(return_no=instance.return_id)
#             if credit_note.exists():
#                 credit_note = credit_note.last()
#                 credit_note.credit_note_id = brand_credit_note_pattern(
#                     instance.return_id.pk)
#                 credit_note.amount = credit_note.amount + (
#                         int(
#                             instance.total_returned_qty
#                         ) *
#                         int(
#                             instance.returned_product.product_inner_case_size
#                         ) *
#                         float(
#                             instance.returned_product.product_pro_price.filter(
#                                 shop__shop_type__shop_type='sp', status=True
#                             ).last().price_to_retailer)
#                 )
#                 credit_note.save()
#             else:
#                 credit_note = Note.objects.create(
#                     credit_note_id=brand_credit_note_pattern(instance.return_id.pk),
#                     order=instance.return_id.invoice_no.order,
#                     return_no=instance.return_id,
#                     amount=int(instance.total_returned_qty) *
#                     int(instance.returned_product.product_inner_case_size) *
#                     float(instance.returned_product.product_pro_price.filter(
#                         shop__shop_type__shop_type='sp', status=True
#                         ).last().price_to_retailer),
#                     status=True)

