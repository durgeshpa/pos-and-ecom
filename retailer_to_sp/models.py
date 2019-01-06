from django.db import models

# Create your models here.
from shops.models import Shop
from brand.models import Brand
from django.contrib.auth import get_user_model
from addresses.models import Address
from products.models import Product
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.db.models.signals import post_save
from otp.sms import SendSms
import datetime
from retailer_backend.common_function import order_id_pattern

ORDER_STATUS = (
    ("active","Active"),
    ("pending","Pending"),
    ("deleted","Deleted"),
    ("ordered","Ordered"),
    ("order_shipped","Order Shipped"),
    ("partially_delivered","Partially Delivered"),
    ("delivered","Delivered"),
)
ITEM_STATUS = (
    ("partially_delivered","Partially Delivered"),
    ("delivered","Delivered"),
)

NOTE_TYPE_CHOICES = (
    ("debit_note","Debit Note"),
    ("credit_note","Credit Note"),
)

PAYMENT_MODE_CHOICES = (
    ("cash_on_delivery","Cash On Delivery"),
    ("neft","NEFT"),
)

PAYMENT_STATUS = (
    ("done","Done"),
    ("pending","Pending"),
)

MESSAGE_STATUS = (
    ("pending","Pending"),
    ("resolved","Resolved"),
)
SELECT_ISSUE= (
    ("cancellation"," Cancellation"),
    ("return","Return"),
    ("others","Others")
)

class Cart(models.Model):
    order_id = models.CharField(max_length=255,null=True,blank=True)
    #user = models.ForeignKey(get_user_model(),related_name='rt_user_cart',null=True,blank=True,on_delete=models.CASCADE)
    #shop = models.ForeignKey(Shop,related_name='rt_shop_cart',null=True,blank=True,on_delete=models.CASCADE)
    cart_status = models.CharField(max_length=200,choices=ORDER_STATUS,null=True,blank=True)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='rt_last_modified_user_cart', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_id

@receiver(post_save, sender=Cart)
def create_order_id(sender, instance=None, created=False, **kwargs):
    if created:
        instance.order_id = order_id_pattern(instance.pk)
        instance.save()

class CartProductMapping(models.Model):
    cart = models.ForeignKey(Cart,related_name='rt_cart_list',on_delete=models.CASCADE)
    cart_product = models.ForeignKey(Product, related_name='rt_cart_product_mapping', on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=0)
    qty_error_msg = models.CharField(max_length=255,null=True,blank=True,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.cart_product.product_name

class Order(models.Model):
    #user = models.ForeignKey(get_user_model(), related_name='rt_user_order', null=True, blank=True,on_delete=models.CASCADE)
    seller_shop = models.ForeignKey(Shop, related_name='rt_seller_shop_order',null=True,blank=True,on_delete=models.CASCADE)
    buyer_shop = models.ForeignKey(Shop, related_name='rt_buyer_shop_order',null=True,blank=True,on_delete=models.CASCADE)
    ordered_cart = models.ForeignKey(Cart,related_name='rt_order_cart_mapping',on_delete=models.CASCADE)
    order_no = models.CharField(max_length=255, null=True, blank=True)
    billing_address = models.ForeignKey(Address,related_name='rt_billing_address_order',null=True,blank=True,on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(Address,related_name='rt_shipping_address_order',null=True,blank=True,on_delete=models.CASCADE)
    total_mrp = models.FloatField(default=0)
    total_discount_amount = models.FloatField(default=0)
    total_tax_amount = models.FloatField(default=0)
    total_final_amount = models.FloatField(default=0)
    order_status = models.CharField(max_length=50,choices=ORDER_STATUS)
    ordered_by = models.ForeignKey(get_user_model(), related_name='rt_ordered_by_user', null=True, blank=True,on_delete=models.CASCADE)
    received_by = models.ForeignKey(get_user_model(), related_name='rt_received_by_user', null=True, blank=True,on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='rt_order_modified_user', null=True,blank=True, on_delete=models.CASCADE)
    payment_mode = models.CharField(max_length=255, choices=PAYMENT_MODE_CHOICES)
    reference_no = models.CharField(max_length=255, null=True, blank=True)
    payment_amount = models.FloatField(default=0)
    payment_status = models.CharField(max_length=255, choices=PAYMENT_STATUS,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_no or str(self.id)

class OrderedProduct(models.Model):
    order = models.ForeignKey(Order,related_name='rt_order_order_product',on_delete=models.CASCADE,null=True,blank=True)
    invoice_no = models.CharField(max_length=255,null=True,blank=True)
    vehicle_no = models.CharField(max_length=255,null=True,blank=True)
    shipped_by = models.ForeignKey(get_user_model(), related_name='rt_shipped_product_ordered_by_user', null=True, blank=True,on_delete=models.CASCADE)
    received_by = models.ForeignKey(get_user_model(), related_name='rt_ordered_product_received_by_user', null=True, blank=True,on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='rt_last_modified_user_order', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.invoice_no or self.id

# @receiver(pre_save, sender=OrderedProduct)
# def create_order_id(sender, instance=None, created=False, **kwargs):
#     last_ordered_product = OrderedProduct.objects.last()
#     if last_ordered_product:
#         last_invoice_no_increment = str(int(last_ordered_product.invoice_no.rsplit('/', 1)[-1]) + 1).zfill(len(last_ordered_product.invoice_no.rsplit('/', 1)[-1]))
#     else:
#         last_invoice_no_increment = '00001'
#     instance.invoice_no = "ADT/07/%s"%(last_invoice_no_increment)

class OrderedProductMapping(models.Model):
    ordered_product = models.ForeignKey(OrderedProduct,related_name='rt_order_product_order_product_mapping',null=True,blank=True,on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='rt_product_order_product',null=True,blank=True, on_delete=models.CASCADE)
    shipped_qty = models.PositiveIntegerField(default=0)
    delivered_qty = models.PositiveIntegerField(default=0)
    returned_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='rt_last_modified_user_order_product', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class Note(models.Model):
    order = models.ForeignKey(Order, related_name='rt_order_note',null=True,blank=True,on_delete=models.CASCADE)
    ordered_product = models.ForeignKey(OrderedProduct, related_name='rt_order_product_note',null=True, blank=True, on_delete=models.CASCADE)
    note_type = models.CharField(max_length=255,choices=NOTE_TYPE_CHOICES)
    amount = models.FloatField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='rt_last_modified_user_note',null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class CustomerCare(models.Model):
    order_id = models.ForeignKey(Order,on_delete=models.CASCADE, null=True)
    name=models.CharField(max_length=255,null=True,blank=True)
    email_us = models.URLField(default='info@grmafactory.com')
    contact_us =models.CharField(max_length=10, default='7607846774')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    order_status = models.CharField(max_length=20,choices=MESSAGE_STATUS,default='pending', null=True)
    select_issue= models.CharField(verbose_name="Issue", max_length=100,choices=SELECT_ISSUE, null=True)
    complaint_detail = models.CharField(max_length=2000, null=True)

    def save(self, *args,**kwargs):
        super(CustomerCare, self).save()
        self.name = "CustomerCare/Message/%s"%(self.pk)
        super(CustomerCare, self).save()


    def __str__(self):
        return self.name

class Payment(models.Model):
    PAYMENT_DONE_APPROVAL_PENDING = "payment_done_approval_pending"
    CASH_COLLECTED = "cash_collected"
    APPROVED_BY_FINANCE = "approved_by_finance"
    PAYMENT_STATUS = (
        (PAYMENT_DONE_APPROVAL_PENDING, "Payment done approval pending"),
        (CASH_COLLECTED, "Cash Collected"),
        (APPROVED_BY_FINANCE, "Approved by finance"),
    )

    order_id= models.ForeignKey(Order,related_name= 'rt_payment', on_delete=models.CASCADE, null=True)
    name=models.CharField(max_length=255,null=True,blank=True)
    #order_amount= models.ForeignKey(Order, related_name= 'rt_amount', on_delete=models.CASCADE, null=True)
    paid_amount=models.DecimalField(max_digits=20,decimal_places=4,default=('0.0000'))
    payment_choice = models.CharField(max_length=30, choices=PAYMENT_MODE_CHOICES, null=True)
    neft_reference_number= models.CharField(max_length=20, null=True)
    payment_status = models.CharField(max_length=50,null=True,blank=True,choices=PAYMENT_STATUS,default=PAYMENT_DONE_APPROVAL_PENDING)

    def save(self, *args,**kwargs):
        super(Payment, self).save()
        self.name = "Payment/%s"%(self.pk)
        super(Payment, self).save()


    def __str__(self):
        return self.name

@receiver(post_save, sender=Payment)
def order_notification(sender, instance=None, created=False, **kwargs):
    pass
    # otp = '123546'
    # date = datetime.datetime.now().strftime("%a(%d/%b/%y)")
    # time = datetime.datetime.now().strftime("%I:%M %p")
    # message = SendSms(phone=instance.order_id.ordered_by,
    #                   body="%s is your One Time Password for GramFactory Account."\
    #                        " Request time is %s, %s IST." % (otp,date,time))
    #
    # message.send()
