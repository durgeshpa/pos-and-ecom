from django.db import models

# Create your models here.
from shops.models import Shop
from brand.models import Brand
from django.contrib.auth import get_user_model
from addresses.models import Address
from products.models import Product

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
    ("cash_in_delivery","Cash In Delivery"),
    ("neft","NEFT"),
)

PAYMENT_STATUS = (
    ("done","Done"),
    ("pending","Pending"),
)

class Cart(models.Model):
    order_id = models.CharField(max_length=255,null=True,blank=True)
    cart_status = models.CharField(max_length=200,choices=ORDER_STATUS,null=True,blank=True)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='rtg_last_modified_user_cart', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_id

    def save(self, *args,**kwargs):
        super(Cart, self).save()
        self.order_id = "RTG/ORDER/%s"%(self.pk)
        super(Cart, self).save()

class CartProductMapping(models.Model):
    cart = models.ForeignKey(Cart,related_name='rt_cart_list',on_delete=models.CASCADE)
    cart_product = models.ForeignKey(Product, related_name='rtg_cart_product_mapping', on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=0)
    qty_error_msg = models.CharField(max_length=255,null=True,blank=True,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.cart_product.product_name

class Order(models.Model):
    #user = models.ForeignKey(get_user_model(), related_name='rt_user_order', null=True, blank=True,on_delete=models.CASCADE)
    seller_shop = models.ForeignKey(Shop, related_name='rtg_seller_shop_order',null=True,blank=True,on_delete=models.CASCADE)
    buyer_shop = models.ForeignKey(Shop, related_name='rtg_buyer_shop_order',null=True,blank=True,on_delete=models.CASCADE)
    ordered_cart = models.ForeignKey(Cart,related_name='rtg_order_cart_mapping',on_delete=models.CASCADE)
    order_no = models.CharField(max_length=255, null=True, blank=True)
    billing_address = models.ForeignKey(Address,related_name='rtg_billing_address_order',null=True,blank=True,on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(Address,related_name='rtg_shipping_address_order',null=True,blank=True,on_delete=models.CASCADE)
    total_mrp = models.FloatField(default=0)
    total_discount_amount = models.FloatField(default=0)
    total_tax_amount = models.FloatField(default=0)
    total_final_amount = models.FloatField(default=0)
    order_status = models.CharField(max_length=50,choices=ORDER_STATUS)
    ordered_by = models.ForeignKey(get_user_model(), related_name='rtg_ordered_by_user', null=True, blank=True,on_delete=models.CASCADE)
    received_by = models.ForeignKey(get_user_model(), related_name='rtg_received_by_user', null=True, blank=True,on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='rtg_order_modified_user', null=True,blank=True, on_delete=models.CASCADE)
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
    shipped_by = models.ForeignKey(get_user_model(), related_name='rtg_shipped_product_ordered_by_user', null=True, blank=True,on_delete=models.CASCADE)
    received_by = models.ForeignKey(get_user_model(), related_name='rtg_ordered_product_received_by_user', null=True, blank=True,on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='rtg_last_modified_user_order', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args,**kwargs):
        super(OrderedProduct, self).save()
        self.invoice_no = "RTG/INVOICE/%s"%(self.pk)
        super(OrderedProduct, self).save()

    def __str__(self):
        return self.invoice_no or self.id

class OrderedProductMapping(models.Model):
    ordered_product = models.ForeignKey(OrderedProduct,related_name='rtg_order_product_order_product_mapping',null=True,blank=True,on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='rtg_product_order_product',null=True,blank=True, on_delete=models.CASCADE)
    shipped_qty = models.PositiveIntegerField(default=0)
    delivered_qty = models.PositiveIntegerField(default=0)
    returned_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='rtg_last_modified_user_order_product', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class Note(models.Model):
    order = models.ForeignKey(Order, related_name='rtg_order_note',null=True,blank=True,on_delete=models.CASCADE)
    ordered_product = models.ForeignKey(OrderedProduct, related_name='rtg_order_product_note',null=True, blank=True, on_delete=models.CASCADE)
    note_type = models.CharField(max_length=255,choices=NOTE_TYPE_CHOICES)
    amount = models.FloatField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='rtg_last_modified_user_note',null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
