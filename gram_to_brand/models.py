from django.db import models
from products.models import Product

from shops.models import Shop
from brand.models import Brand, Vendor
from django.contrib.auth import get_user_model
from addresses.models import Address,City,State
from datetime import datetime, timedelta
from django.utils import timezone
from retailer_to_gram.models import Cart as GramMapperRetialerCart,Order as GramMapperRetialerOrder
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.urls import reverse
import datetime, csv, codecs, re


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

class Po_Message(models.Model):
    created_by = models.ForeignKey(get_user_model(), related_name='created_by_user_message', null=True,blank=True, on_delete=models.CASCADE)
    message = models.TextField(max_length=1000,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class Cart(models.Model):
    brand = models.ForeignKey(Brand, related_name='brand_order', on_delete=models.CASCADE)
    supplier_state = models.ForeignKey(State, related_name='state_cart',null=True, blank=True,on_delete=models.CASCADE)
    supplier_name = models.ForeignKey(Vendor, related_name='buyer_vendor_order', null=True, blank=True,on_delete=models.CASCADE)
    gf_shipping_address = models.ForeignKey(Address, related_name='shipping_address_cart', null=True, blank=True,on_delete=models.CASCADE)
    gf_billing_address = models.ForeignKey(Address, related_name='billing_address_cart', null=True, blank=True,on_delete=models.CASCADE)
    po_no = models.CharField(max_length=255,null=True,blank=True)
    shop = models.ForeignKey(Shop,related_name='shop_cart',null=True,blank=True,on_delete=models.CASCADE)
    po_status = models.CharField(max_length=200,choices=ORDER_STATUS,null=True,blank=True)
    po_raised_by = models.ForeignKey(get_user_model(), related_name='po_raise_user_cart', null=True,blank=True, on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_cart', null=True,blank=True, on_delete=models.CASCADE)
    po_creation_date = models.DateField(auto_now_add=True)
    po_validity_date = models.DateField()
    po_message = models.ForeignKey(Po_Message, related_name='po_message_dt', on_delete=models.CASCADE,null=True,blank=True)
    payment_term = models.TextField(null=True,blank=True)
    delivery_term = models.TextField(null=True,blank=True)
    po_amount = models.FloatField(default=0)
    cart_product_mapping_csv = models.FileField(upload_to='gram/brand/cart_product_mapping_csv', null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @property
    def products_sample_file(self):
        if self.cart_product_mapping_csv and hasattr(self.cart_product_mapping_csv, 'url'):
            url = """<h3><a href="%s" target="_blank">Download Products List</a></h3>""" % (reverse('admin:products_vendor_mapping',args=(self.supplier_name_id,)))
        else:
            url="""<h3><a href="#">Download Products List</a></h3>"""
        return url

    class Meta:
        verbose_name = "PO Generation"
        permissions = (
            ("can_approve_and_disapprove", "Can approve and dis-approve"),
        )

@receiver(pre_save, sender=Cart)
def create_po_no(sender, instance=None, created=False, **kwargs):
    if instance._state.adding:
        last_cart = Cart.objects.last()
        if last_cart:
            last_cart_po_no_increment = str(int(last_cart.po_no.rsplit('/', 1)[-1]) + 1).zfill(len(last_cart.po_no.rsplit('/', 1)[-1]))
        else:
            last_cart_po_no_increment = '00001'
        instance.po_no = "ADT/PO/07/%s"%(last_cart_po_no_increment)

class CartProductMapping(models.Model):
    cart = models.ForeignKey(Cart,related_name='cart_list',on_delete=models.CASCADE)
    cart_product = models.ForeignKey(Product, related_name='cart_product_mapping', on_delete=models.CASCADE)
    case_size= models.PositiveIntegerField(default=0)
    number_of_cases = models.PositiveIntegerField()
    qty= models.PositiveIntegerField(default=0)
    scheme = models.FloatField(default=0,null=True,blank=True,help_text='data into percentage %')
    price = models.FloatField( verbose_name='Brand To Gram Price')
    total_price= models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Select Product"

    def clean(self):
        if self.number_of_cases:
             self.total_price= self.case_size * self.number_of_cases * self.price
             self.qty = self.case_size * self.number_of_cases

    def __str__(self):
        return self.cart_product.product_name

@receiver(post_save, sender=Cart)
def create_cart_product_mapping(sender, instance=None, created=False, **kwargs):
    if created:
        if instance.cart_product_mapping_csv:
            reader = csv.reader(codecs.iterdecode(instance.cart_product_mapping_csv, 'utf-8'))
            for id,row in enumerate(reader):
                for row in reader:
                    if row[3]:
                        CartProductMapping.objects.create(cart=instance,cart_product_id = row[0], case_size= int(row[2]),
                         number_of_cases = int(row[3]),scheme = float(row[4]) if row[4] else None, price=float(row[5])
                         , total_price = float(row[2])*float(row[3])*float(row[5]))


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

@receiver(post_save, sender=CartProductMapping)
def create_order(sender, instance=None, created=False, **kwargs):
    if created:
        order = Order.objects.filter(ordered_cart=instance.cart)
        if order.exists():
            order = order.last()
            order.total_final_amount = order.total_final_amount+instance.total_price
            order.save()
        else:
            Order.objects.create(ordered_cart=instance.cart, order_no=instance.cart.po_no, billing_address=instance.cart.gf_billing_address,
            shipping_address=instance.cart.gf_shipping_address, total_final_amount=instance.total_price)

class OrderItem(models.Model):
    order = models.ForeignKey(Order,related_name='order_order_item',on_delete=models.CASCADE,verbose_name='po no')
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

    class Meta:
        verbose_name = "Purchase Order Item List"

class GRNOrder(models.Model):
    order = models.ForeignKey(Order,related_name='order_grn_order',on_delete=models.CASCADE,null=True,blank=True )
    order_item = models.ForeignKey(OrderItem,related_name='order_item_grn_order',on_delete=models.CASCADE,null=True,blank=True)
    invoice_no = models.CharField(max_length=255)
    grn_id = models.CharField(max_length=255,null=True,blank=True)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_grn_order', null=True,blank=True, on_delete=models.CASCADE)
    grn_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.grn_id)

@receiver(pre_save, sender=GRNOrder)
def create_grn_id(sender, instance=None, created=False, **kwargs):
    if instance._state.adding:
        import datetime
        current_year = datetime.date.today().strftime('%y')
        next_year = str(int(current_year) + 1)
        last_grn_order = GRNOrder.objects.last()
        if last_grn_order:
            last_grn_order_id_increment = str(int(last_grn_order.grn_id.rsplit('/', 1)[-1])+1)
        else:
            last_grn_order_id_increment = '1'
        instance.grn_id = "%s-%s/%s"%(current_year,next_year,last_grn_order_id_increment)



class GRNOrderProductMapping(models.Model):
    grn_order = models.ForeignKey(GRNOrder,related_name='grn_order_grn_order_product',null=True,blank=True,on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='product_grn_order_product',null=True,blank=True, on_delete=models.CASCADE)
    po_product_quantity= models.PositiveIntegerField(default=0, verbose_name='PO Product Quantity',blank=True )
    po_product_price= models.FloatField(default=0, verbose_name='PO Product Price',blank=True )
    already_grned_product= models.PositiveIntegerField(default=0, verbose_name='Already GRNed Product Quantity',blank=True)
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

    def clean(self):
         sum= self.delivered_qty + self.returned_qty
         if self.product_invoice_qty <= self.po_product_quantity:
             if self.product_invoice_qty < sum:
               raise ValidationError(_('Product invoice quantity cannot be less than the sum of delivered quantity and returned quantity'))
         else:
             raise ValidationError(_('Product invoice quantity cannot be greater than PO product quantity'))

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
    brand_note_id = models.CharField(max_length=255, null=True, blank=True)
    order = models.ForeignKey(Order, related_name='order_brand_note',null=True,blank=True,on_delete=models.CASCADE)
    grn_order = models.ForeignKey(GRNOrder, related_name='grn_order_brand_note', null=True, blank=True,on_delete=models.CASCADE)
    note_type = models.CharField(max_length=255,choices=NOTE_TYPE_CHOICES)
    amount = models.FloatField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_brand_note',null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.brand_note_id

@receiver(pre_save, sender=BrandNote)
def create_brand_note_id(sender, instance=None, created=False, **kwargs):
    if instance._state.adding:
        import datetime
        current_year = datetime.date.today().strftime('%y')
        next_year = str(int(current_year) + 1)
        today_date = datetime.date.today().strftime('%d%m%y')
        if instance.note_type == 'debit_note':
            last_brand_note = BrandNote.objects.filter(note_type="debit_note").last()
            if last_brand_note:
                last_brand_note_id_increment = str(int(last_brand_note.brand_note_id.rsplit('/', 1)[-1])+1)
            else:
                last_brand_note_id_increment = '1'
            instance.brand_note_id = "%s/%s"%(today_date,last_brand_note_id_increment)

        elif instance.note_type == 'credit_note':
            last_brand_note = BrandNote.objects.filter(note_type="credit_note").last()
            if last_brand_note:
                last_brand_note_id_increment = str(int(last_brand_note.brand_note_id.rsplit('/', 1)[-1]) + 1).zfill(len(last_brand_note.brand_note_id.rsplit('/', 1)[-1]))
            else:
                last_brand_note_id_increment = '00001'
            instance.brand_note_id = "ADT/CN/%s"%(last_brand_note_id_increment)

class OrderedProductReserved(models.Model):
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
