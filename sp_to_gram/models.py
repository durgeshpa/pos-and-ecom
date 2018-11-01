from django.db import models

# Create your models here.
from shops.models import Shop
from brand.models import Brand
from django.contrib.auth import get_user_model
from addresses.models import Address
from products.models import Product
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from retailer_to_sp.models import Cart as RetailerCart

ORDER_STATUS = (
    ("ordered_to_gram","Ordered To Gramfactory"),
    ("order_shipped","Order Shipped From Gramfactory"),
    ("partially_delivered","Partially Delivered"),
    ("delivered","Delivered"),
)
ITEM_STATUS = (
    ("partially_delivered","Partially Delivered"),
    ("delivered","Delivered"),
)

class Cart(models.Model):
    order_id = models.CharField(max_length=255,null=True,blank=True)
    shop = models.ForeignKey(Shop,related_name='sp_shop_cart',null=True,blank=True,on_delete=models.CASCADE)
    billing_address = models.ForeignKey(Address, related_name='sp_billing_address_cart', null=True, blank=True,on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(Address, related_name='sp_shipping_address_cart', null=True, blank=True,on_delete=models.CASCADE)
    cart_status = models.CharField(max_length=200,choices=ORDER_STATUS,null=True,blank=True)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='sp_last_modified_user_cart', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_id

    def save(self, *args,**kwargs):
        self.cart_status = 'ordered_to_gram'
        super(Cart, self).save()
        self.order_id = "GRAM/ORDER/%s"%(self.pk)
        super(Cart, self).save()

class CartProductMapping(models.Model):
    cart = models.ForeignKey(Cart,related_name='sp_cart_list',on_delete=models.CASCADE)
    cart_product = models.ForeignKey(Product, related_name='sp_cart_product_mapping', on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.cart_product.product_name

class Order(models.Model):
    shop = models.ForeignKey(Shop, related_name='sp_shop_order',null=True,blank=True,on_delete=models.CASCADE)
    ordered_cart = models.ForeignKey(Cart,related_name='sp_order_cart_mapping',on_delete=models.CASCADE)
    order_no = models.CharField(max_length=255, null=True, blank=True)
    billing_address = models.ForeignKey(Address,related_name='sp_billing_address_order',null=True,blank=True,on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(Address,related_name='sp_shipping_address_order',null=True,blank=True,on_delete=models.CASCADE)
    total_mrp = models.FloatField(default=0)
    total_discount_amount = models.FloatField(default=0)
    total_tax_amount = models.FloatField(default=0)
    total_final_amount = models.FloatField(default=0)
    order_status = models.CharField(max_length=50,choices=ORDER_STATUS)
    ordered_by = models.ForeignKey(get_user_model(), related_name='sp_ordered_by_user', null=True, blank=True,on_delete=models.CASCADE)
    received_by = models.ForeignKey(get_user_model(), related_name='sp_received_by_user', null=True, blank=True,on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='sp_order_modified_user', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_no or str(self.id)

class OrderedProduct(models.Model):
    order = models.ForeignKey(Order,related_name='sp_order_order_product',on_delete=models.CASCADE,null=True,blank=True)
    invoice_no = models.CharField(max_length=255,null=True,blank=True)
    vehicle_no = models.CharField(max_length=255,null=True,blank=True)
    shipped_by = models.ForeignKey(get_user_model(), related_name='sp_shipped_product_ordered_by_user', null=True, blank=True,on_delete=models.CASCADE)
    received_by = models.ForeignKey(get_user_model(), related_name='sp_ordered_product_received_by_user', null=True, blank=True,on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='sp_last_modified_user_order', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args,**kwargs):
        super(OrderedProduct, self).save()
        self.invoice_no = "SP/INVOICE/%s"%(self.pk)
        super(OrderedProduct, self).save()

class OrderedProductMapping(models.Model):
    ordered_product = models.ForeignKey(OrderedProduct,related_name='sp_order_product_order_product_mapping',null=True,blank=True,on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='sp_product_order_product',null=True,blank=True, on_delete=models.CASCADE)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    shipped_qty = models.PositiveIntegerField(default=0)
    available_qty = models.PositiveIntegerField(default=0)
    ordered_qty = models.PositiveIntegerField(default=0)
    delivered_qty = models.PositiveIntegerField(default=0)
    returned_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='sp_last_modified_user_order_product', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class OrderedProductReserved(models.Model):
    order_product_reserved = models.ForeignKey(OrderedProductMapping, related_name='sp_order_product_order_product_reserved',null=True, blank=True, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='sp_product_order_product_reserved', null=True, blank=True,on_delete=models.CASCADE)
    cart = models.ForeignKey(RetailerCart, related_name='sp_ordered_retailer_cart',null=True,blank=True,on_delete=models.CASCADE)
    reserved_qty = models.PositiveIntegerField(default=0)
    #order_reserve_start_time = models.DateTimeField(auto_now_add=True)
    order_reserve_end_time = models.DateTimeField(null=True,blank=True,editable=False)
    #order_reserve_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self):
        self.order_reserve_end_time = timezone.now() + timedelta(minutes=int(settings.BLOCKING_TIME_IN_MINUTS))
        super(OrderedProductReserved, self).save()

    def __str__(self):
        return str(self.order_reserve_end_time)




