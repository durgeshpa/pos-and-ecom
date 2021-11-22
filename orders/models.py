from django.db import models
from products.models import Product
from base.models import BaseModel
from shops.models import Shop, Warehouse
from brand.models import Brand, Vendor
from django.contrib.auth import get_user_model
from addresses.models import Address,City,State
from datetime import datetime, timedelta
from django.utils import timezone
from retailer_to_gram.models import Cart as GramMapperRetialerCart,Order as GramMapperRetialerOrder
from django.conf import settings

ORDER_STATUS = (
    ("ordered_to_brand","Ordered To Brand"),
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

class Cart(BaseModel):
	INCOMPLETE = 'INC'
	CREATED = 'ORD'
	CART_STATUS_CHOICES = (
		(INCOMPLETE, "Incomplete"),
		(ORDER_CREATED, "Order Created")
	)
	buyer = models.ForeignKey(Shop, related_name="shoping_cart", on_delete=models.DO_NOTHING)
	supplier = models.ForeignKey(Shop, related_name="shoping_cart", on_delete=models.DO_NOTHING)
	cart_item = models.ManyToManyField(Product, through='CartProductMapping')
	cart_user = models.ForeignKey(get_user_model(), null=, blank=True, on_delete=models.CASCADE)
	cart_status = models.CharField(max_length=3, choices=ORDER_STATUS,null=True,blank=True)

	@property
	def total(self):
		return self._total

class CartProductMapping(models.Model):#Todo To be add Product
    cart = models.ForeignKey(Cart,related_name='cart_list',on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='product_cart', on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=0)
    scheme = models.FloatField(default=0,null=True,blank=True,help_text='data into percentage %')
    price = models.DecimalField(default=0, verbose_name='sold at price')

    class Meta:
        verbose_name = "Select Product"

    def __str__(self):
        return self.cart_product.product_name

class WareHouseCart(Cart):
	pass
class SPCart(Cart):
	pass

class VendorCart(Cart):
    po_creation_date = models.DateField(auto_now_add=True)
    po_validity_date = models.DateField(null=True, blank=True)
    payment_term = models.TextField(null=True,blank=True)
    delivery_term = models.TextField(null=True,blank=True)

    class Meta:
        verbose_name = "PO Generation"

    def save(self, *args,**kwargs):
        self.cart_status = 'ordered_to_brand'
        super(VendorCart, self).save()
        self.po_no = "BRAND/ORDER/%s"%(self.pk)
        super(Cart, self).save()


class Order(BaseModel):
	PENDING = "PND"
	DISPATCHED = "DSP"
	PARTIAL_DELIVERED = "PDV"
	DELIVERED = "DLV"
	CANCELLED = "CAN"
	ORDER_STATUS = (
		(PENDING, "Pending"),
		(DISPATCHED, "Order Dispatched"),
		(PARTIAL_DELIVERED, "Partially Delivered"),
		(DELIVERED, "Order Delivered"),
		(CANCELLED, "Order Cancelled"),
	)
	order_number = models.CharField(max_length=100, null=True, blank=True)
	cart = models.ForeignKey(Cart, on_delete=models.DO_NOTHING)
    order_status = models.CharField(max_length=200,choices=ORDER_STATUS,null=True,blank=True)


class ProductOrder(Order):

    class Meta:
        verbose_name = "ProductOrder"
        verbose_name_plural = "Product Orders"

    def __str__(self):
        pass
    


# class Cart(models.Model):
#     # brand = models.ForeignKey(Brand, related_name='brand_order', on_delete=models.CASCADE)
#     # supplier_state = models.ForeignKey(State, related_name='state_cart',null=True, blank=True,on_delete=models.CASCADE) #Todo to be removed
#     # supplier_name = models.ForeignKey(Vendor, related_name='buyer_vendor_order', null=True, blank=True,on_delete=models.CASCADE)
#     # gf_shipping_address = models.ForeignKey(Address, related_name='shipping_address_cart', null=True, blank=True,on_delete=models.CASCADE)
#     # gf_billing_address = models.ForeignKey(Address, related_name='billing_address_cart', null=True, blank=True,on_delete=models.CASCADE)
#     po_no = models.CharField(max_length=255,null=True,blank=True)
#     shop = models.ForeignKey(Shop,related_name='shop_cart',null=True,blank=True,on_delete=models.CASCADE)
#     po_status = models.CharField(max_length=200,choices=ORDER_STATUS,null=True,blank=True)
#     po_raised_by = models.ForeignKey(get_user_model(), related_name='po_raise_user_cart', null=True,blank=True, on_delete=models.CASCADE)
#     last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_cart', null=True,blank=True, on_delete=models.CASCADE)
#     po_creation_date = models.DateField(auto_now_add=True)
#     po_validity_date = models.DateField()
#     payment_term = models.TextField(null=True,blank=True)
#     delivery_term = models.TextField(null=True,blank=True)
#     po_amount = models.FloatField(default=0) #Todo To be removed

#     class Meta:
#         verbose_name = "PO Generation"

#     def save(self, *args,**kwargs):
#         self.cart_status = 'ordered_to_brand'
#         super(Cart, self).save()
#         self.po_no = "BRAND/ORDER/%s"%(self.pk)
#         super(Cart, self).save()


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
        return str(self.order_no) or str(self.id)

class OrderItem(models.Model):# Todo To be redesign
    order = models.ForeignKey(Order,related_name='order_order_item',on_delete=models.CASCADE,verbose_name='po no')
    ordered_product = models.ForeignKey(Product, related_name='product_order_item', on_delete=models.CASCADE)
    ordered_qty = models.PositiveIntegerField(default=0)
    ordered_product_status = models.CharField(max_length=50,choices=ITEM_STATUS,null=True,blank=True)#Todo Removed
    ordered_price = models.FloatField(default=0)
    item_status = models.CharField(max_length=255,choices=ITEM_STATUS)
    #changed_price = models.FloatField(default=0)
    total_delivered_qty = models.PositiveIntegerField(default=0)
    total_returned_qty = models.PositiveIntegerField(default=0)
    total_damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_order', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Purchase Order Item List"

class GRNOrder(models.Model):
    order = models.ForeignKey(Order,related_name='order_grn_order',on_delete=models.CASCADE,null=True,blank=True,verbose_name='po no')
    order_item = models.ForeignKey(OrderItem,related_name='order_item_grn_order',on_delete=models.CASCADE,null=True,blank=True)
    invoice_no = models.CharField(max_length=255)
    grn_id = models.CharField(max_length=255,null=True,blank=True)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_grn_order', null=True,blank=True, on_delete=models.CASCADE)
    grn_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    #Todo Add Prodcuts with Many to many

    def save(self, *args,**kwargs):
        super(GRNOrder, self).save()
        self.grn_id = "BRAND/GRN/%s"%(self.pk)
        super(GRNOrder, self).save()

    class Meta:
        verbose_name = "Add Edit GRN Order"


class GRNOrderProductMapping(models.Model):
    grn_order = models.ForeignKey(GRNOrder,related_name='grn_order_grn_order_product',null=True,blank=True,on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='product_grn_order_product',null=True,blank=True, on_delete=models.CASCADE)
    product_invoice_price = models.FloatField(default=0)
    product_invoice_qty = models.PositiveIntegerField(default=0)
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


class BrandNote(models.Model):
    order = models.ForeignKey(Order, related_name='order_brand_note',null=True,blank=True,on_delete=models.CASCADE)
    grn_order = models.ForeignKey(GRNOrder, related_name='grn_order_brand_note', null=True, blank=True,on_delete=models.CASCADE)
    note_type = models.CharField(max_length=255,choices=NOTE_TYPE_CHOICES)
    amount = models.FloatField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_brand_note',null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class OrderedProductReserved(models.Model):#TODO Should be handled through cart status.
    order_product_reserved = models.ForeignKey(GRNOrderProductMapping, related_name='retiler_order_product_order_product_reserved',null=True, blank=True, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='retiler_product_order_product_reserved', null=True, blank=True,on_delete=models.CASCADE)
    cart = models.ForeignKey(GramMapperRetialerCart, related_name='retiler_ordered_retailer_cart',null=True,blank=True,on_delete=models.CASCADE)
    reserved_qty = models.PositiveIntegerField(default=0)
    order_reserve_end_time = models.DateTimeField(null=True,blank=True,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self):
        self.order_reserve_end_time = timezone.now() + timedelta(minutes=int(settings.BLOCKING_TIME_IN_MINUTS))
        super(OrderedProductReserved, self).save()

    def __str__(self):
        return str(self.order_reserve_end_time)

class PickList(models.Model):
    order = models.ForeignKey(GramMapperRetialerOrder, related_name='pick_list_order',null=True,blank=True,on_delete=models.CASCADE)
    cart = models.ForeignKey(GramMapperRetialerCart, related_name='pick_list_cart', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

class PickListItems(models.Model):
    pick_list = models.ForeignKey(PickList, related_name='pick_list_items_pick_list',on_delete=models.CASCADE)
    grn_order = models.ForeignKey(GRNOrder, related_name='pick_list_cart', on_delete=models.CASCADE, verbose_name='GRN No')
    product = models.ForeignKey(Product, related_name='pick_product', null=True, blank=True,on_delete=models.CASCADE)
    pick_qty = models.PositiveIntegerField(default=0)
    return_qty = models.PositiveIntegerField(default=0)
    damage_qty = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

