from django.db import models
from products.models import Product

from shops.models import Shop
from brand.models import Brand
from django.contrib.auth import get_user_model

ORDER_STATUS = (
    ("ordered_to_brand","Ordered To Brand"),
    ("partially_delivered","Partially Delivered"),
    ("delivered","Delivered"),
)
CART_STATUS = (
    ("ordered_to_brand","Ordered To Brand"),
    ("partially_delivered","Partially Delivered"),
    ("delivered","Delivered"),
)

class Cart(models.Model):
    brand = models.ForeignKey(Brand, related_name='brand_order', on_delete=models.CASCADE)
    order_id = models.CharField(max_length=255,null=True,blank=True)
    shop = models.ForeignKey(Shop,related_name='shop_cart',null=True,blank=True,on_delete=models.CASCADE)
    cart_status = models.CharField(max_length=200,choices=CART_STATUS,null=True,blank=True)

    def save(self, *args,**kwargs):
        self.cart_status = 'ordered_to_brand'
        super(Cart, self).save()
        self.order_id = "BRAND/ORDER/%s"%(self.pk)
        super(Cart, self).save()

class CartProductMapping(models.Model):
    cart = models.ForeignKey(Cart,related_name='cart_list',on_delete=models.CASCADE)
    cart_product = models.ForeignKey(Product, related_name='cart_product_mapping', on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=0)
    price = models.FloatField(default=0)

    def __str__(self):
        return self.cart_product.product_name

class CarOrderShipmentMapping(models.Model):
    cart = models.ForeignKey(Cart,related_name='car_order_shipment',on_delete=models.CASCADE,null=True,blank=True)
    #cart = models.ForeignKey(Cart,related_name='order_shipment',on_delete=models.CASCADE,null=True,blank=True)
    invoice_no = models.CharField(max_length=255)
    batch_no = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class OrderShipment(models.Model):
    cart_product_ship = models.ForeignKey(CartProductMapping, related_name='cart_product_mapping_shipment',null=True,blank=True,on_delete=models.CASCADE)
    car_order_shipment_mapping = models.ForeignKey(CarOrderShipmentMapping,related_name='car_order_shipment_mapping_shipment',null=True,blank=True,on_delete=models.CASCADE)
    cart_products = models.ForeignKey(Product, related_name='order_product_shipment',null=True,blank=True, on_delete=models.CASCADE)
    delivered_qty = models.PositiveIntegerField(default=0)
    changed_price = models.FloatField(default=0)
    manufacture_date = models.DateField(null=True,blank=True)
    expiry_date = models.DateField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        super(OrderShipment, self).__init__(*args, **kwargs)
        self.__total__ = None


class Order(models.Model):
    shop = models.ForeignKey(Shop, related_name='shop_order',on_delete=models.CASCADE)
    ordered_cart = models.ForeignKey(Cart,related_name='order_cart_mapping',on_delete=models.CASCADE)
    ordered_shipment = models.ManyToManyField(CarOrderShipmentMapping,related_name='order_shipment_mapping')
    total_mrp = models.FloatField(default=0)
    total_discount_amount = models.FloatField(default=0)
    total_tax_amount = models.FloatField(default=0)
    total_final_amount = models.FloatField(default=0)
    order_status = models.CharField(max_length=50,choices=ORDER_STATUS)
    ordered_by = models.ForeignKey(get_user_model(), related_name='brand_order_by_user', null=True, blank=True,on_delete=models.CASCADE)
    received_by = models.ForeignKey(get_user_model(), related_name='brand_received_by_user', null=True, blank=True,on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='brand_order_modified_user', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

# class Shipment(models.Model):
#     order = models.ForeignKey(Order,related_name='order_shipment')
#     cart = models.ForeignKey(Cart,related_name='cart_shipment')
#     order_shipment = models.ForeignKey(OrderShipment,related_name='order_shipment')
