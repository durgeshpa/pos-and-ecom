from django.db import models
from products.models import Product

from shops.models import Shop
from brand.models import Brand
from django.contrib.auth import get_user_model
from addresses.models import Address,City

ORDER_STATUS = (
    ("ordered_to_brand","Ordered To Brand"),
    ("partially_delivered","Partially Delivered"),
    ("delivered","Delivered"),
)
ITEM_STATUS = (
    ("partially_delivered","Partially Delivered"),
    ("delivered","Delivered"),
)

class Cart(models.Model):
    brand = models.ForeignKey(Brand, related_name='brand_order', on_delete=models.CASCADE)
    city = models.ForeignKey(City, related_name='city_cart',null=True, blank=True,on_delete=models.CASCADE)
    buyer_shop = models.ForeignKey(Shop, related_name='buyer_shop_order', null=True, blank=True,on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(Address, related_name='shipping_address_cart', null=True, blank=True,on_delete=models.CASCADE)
    billing_address = models.ForeignKey(Address, related_name='billing_address_cart', null=True, blank=True,on_delete=models.CASCADE)
    order_id = models.CharField(max_length=255,null=True,blank=True)
    shop = models.ForeignKey(Shop,related_name='shop_cart',null=True,blank=True,on_delete=models.CASCADE)
    cart_status = models.CharField(max_length=200,choices=ORDER_STATUS,null=True,blank=True)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_cart', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

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

class Order(models.Model):
    shop = models.ForeignKey(Shop, related_name='shop_order',null=True,blank=True,on_delete=models.CASCADE)
    ordered_cart = models.ForeignKey(Cart,related_name='order_cart_mapping',on_delete=models.CASCADE)
    order_no = models.CharField(max_length=255, null=True, blank=True)
    billing_address = models.ForeignKey(Address,related_name='billing_address_order',null=True,blank=True,on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(Address,related_name='shipping_address_order',null=True,blank=True,on_delete=models.CASCADE)
    #ordered_shipment = models.ManyToManyField(CarOrderShipmentMapping,related_name='order_shipment_mapping')
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

    def __str__(self):
        return self.order_no or str(self.id)

class OrderItem(models.Model):
    order = models.ForeignKey(Order,related_name='order_order_item',on_delete=models.CASCADE)
    ordered_product = models.ForeignKey(Product, related_name='product_order_item', on_delete=models.CASCADE)
    ordered_qty = models.PositiveIntegerField(default=0)
    ordered_product_status = models.CharField(max_length=50,choices=ITEM_STATUS,null=True,blank=True)
    ordered_price = models.FloatField(default=0)
    item_status = models.CharField(max_length=255,choices=ITEM_STATUS)
    #changed_price = models.FloatField(default=0)
    total_delivered_qty = models.PositiveIntegerField(default=0)
    total_returned_qty = models.PositiveIntegerField(default=0)
    total_damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_order', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class GRNOrder(models.Model):
    order = models.ForeignKey(Order,related_name='order_grn_order',on_delete=models.CASCADE,null=True,blank=True)
    order_item = models.ForeignKey(OrderItem,related_name='order_item_grn_order',on_delete=models.CASCADE,null=True,blank=True)
    invoice_no = models.CharField(max_length=255)
    grn_id = models.CharField(max_length=255,null=True,blank=True)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_grn_order', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args,**kwargs):
        super(GRNOrder, self).save()
        self.grn_id = "BRAND/GRN/%s"%(self.pk)
        super(GRNOrder, self).save()

class GRNOrderProductMapping(models.Model):
    grn_order = models.ForeignKey(GRNOrder,related_name='grn_order_grn_order_product',null=True,blank=True,on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='product_grn_order_product',null=True,blank=True, on_delete=models.CASCADE)
    changed_price = models.FloatField(default=0)
    manufacture_date = models.DateField(null=True,blank=True)
    expiry_date = models.DateField(null=True,blank=True)
    available_qty = models.PositiveIntegerField(default=0)
    ordered_qty = models.PositiveIntegerField(default=0)
    delivered_qty = models.PositiveIntegerField(default=0)
    returned_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_grn_order_product', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class OrderHistory(models.Model):
    #shop = models.ForeignKey(Shop, related_name='shop_order',null=True,blank=True,on_delete=models.CASCADE)
    seller_shop = models.ForeignKey(Shop, related_name='gf_seller_shop_order_history', null=True, blank=True,on_delete=models.CASCADE)
    buyer_shop = models.ForeignKey(Shop, related_name='gf_buyer_shop_order_history', null=True, blank=True,on_delete=models.CASCADE)
    ordered_cart = models.ForeignKey(Cart,related_name='order_cart_mapping_history',on_delete=models.CASCADE)
    order_no = models.CharField(max_length=255, null=True, blank=True)
    billing_address = models.ForeignKey(Address,related_name='billing_address_order_history',null=True,blank=True,on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(Address,related_name='shipping_address_order_history',null=True,blank=True,on_delete=models.CASCADE)
    total_mrp = models.FloatField(default=0)
    total_discount_amount = models.FloatField(default=0)
    total_tax_amount = models.FloatField(default=0)
    total_final_amount = models.FloatField(default=0)
    order_status = models.CharField(max_length=50,choices=ORDER_STATUS)
    ordered_by = models.ForeignKey(get_user_model(), related_name='brand_order_by_user_history', null=True, blank=True,on_delete=models.CASCADE)
    received_by = models.ForeignKey(get_user_model(), related_name='brand_received_by_user_history', null=True, blank=True,on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='brand_order_modified_user_history', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_no or str(self.id)

class GRNOrderProductHistory(models.Model):
    order = models.ForeignKey(Order, related_name='order_grn_order_history', on_delete=models.CASCADE, null=True, blank=True)
    order_item = models.ForeignKey(OrderItem, related_name='order_item_grn_order_history', on_delete=models.CASCADE, null=True,blank=True)
    invoice_no = models.CharField(max_length=255)
    grn_id = models.CharField(max_length=255, null=True, blank=True)
    grn_order = models.ForeignKey(GRNOrder, related_name='grn_order_grn_order_product_history', null=True, blank=True,on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='product_grn_order_product_history', null=True, blank=True,on_delete=models.CASCADE)
    changed_price = models.FloatField(default=0)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    available_qty = models.PositiveIntegerField(default=0)
    ordered_qty = models.PositiveIntegerField(default=0)
    delivered_qty = models.PositiveIntegerField(default=0)
    returned_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_grn_order_product_history',null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


    # def __init__(self, *args, **kwargs):
    #     super(OrderShipment, self).__init__(*args, **kwargs)
    #     self.__total__ = None



# class Shipment(models.Model):
#     order = models.ForeignKey(Order,related_name='order_shipment')
#     cart = models.ForeignKey(Cart,related_name='cart_shipment')
#     order_shipment = models.ForeignKey(OrderShipment,related_name='order_shipment')
