import datetime
from datetime import timedelta

from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.db import models

from shops.models import Shop, ParentRetailerMapping
from brand.models import Brand
from products.models import Product
from retailer_to_sp.models import Cart as RetailerCart
from addresses.models import Address, City, State
from retailer_to_sp.models import Note as CreditNote, OrderedProduct as RetailerShipment

ORDER_STATUS = (
    ("ordered_to_gram", "Ordered To Gramfactory"),
    ("order_shipped", "Order Shipped From Gramfactory"),
    ("partially_delivered", "Partially Delivered"),
    ("delivered", "Delivered"),
)

ITEM_STATUS = (
    ("partially_delivered", "Partially Delivered"),
    ("delivered", "Delivered"),
)


class Cart(models.Model):
    shop = models.ForeignKey(
        Shop, related_name='sp_shop_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    po_no = models.CharField(max_length=255, null=True, blank=True)
    po_status = models.CharField(
        max_length=200, choices=ORDER_STATUS,
        null=True, blank=True
    )
    po_raised_by = models.ForeignKey(
        get_user_model(), related_name='po_raise_sp_user_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='last_modified_sp_user_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    po_creation_date = models.DateField(auto_now_add=True)
    po_validity_date = models.DateField()
    payment_term = models.TextField(null=True, blank=True)
    delivery_term = models.TextField(null=True, blank=True)
    po_amount = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "PO Generation"

    def __str__(self):
        return self.po_no

    def clean(self):
        if (
            self.po_validity_date
            and self.po_validity_date
        ) < datetime.date.today():
            raise ValidationError(_("Po validity date cannot be in the past!"))


@receiver(pre_save, sender=Cart)
def create_po_no(sender, instance=None, created=False, **kwargs):
    if instance._state.adding:
        last_cart = Cart.objects.last()
        if last_cart:
            last_cart_po_no_increment = str(
                int(last_cart.po_no.rsplit('/', 1)[-1]) + 1).zfill(
                len(last_cart.po_no.rsplit('/', 1)[-1])
            )
        else:
            last_cart_po_no_increment = '00001'
        instance.po_no = "ADT/PO/07/%s" % (last_cart_po_no_increment)
        instance.po_status = "ordered_to_gram"


class CartProductMapping(models.Model):
    cart = models.ForeignKey(Cart,related_name='sp_cart_list',on_delete=models.CASCADE)
    cart_product = models.ForeignKey(Product, related_name='sp_cart_product_mapping', on_delete=models.CASCADE)
    case_size = models.PositiveIntegerField()
    number_of_cases = models.PositiveIntegerField()
    qty = models.PositiveIntegerField(default=0)
    scheme = models.FloatField(default=0, null=True, blank=True, help_text='data into percentage %')
    price = models.FloatField()
    total_price = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Select Product"

    def clean(self):
        if self.number_of_cases:
            self.qty = int(self.cart_product.product_inner_case_size) * int(self.case_size) * int(self.number_of_cases)
            self.total_price = float(self.qty) * self.price

    def __str__(self):
        return self.cart_product.product_name

    @property
    def gf_code(self):
        return self.cart_product.product_gf_code

    @property
    def ean_number(self):
        if self.cart_product.product_ean_code:
            return self.cart_product.product_ean_code
        return str("-")

    @property
    def taxes(self):
        taxes = [field.tax.tax_name for field in self.cart_product.product_pro_tax.all()]
        if not taxes:
            return str("-")
        return taxes

class Order(models.Model):
    #shop = models.ForeignKey(Shop, related_name='sp_shop_order',null=True,blank=True,on_delete=models.CASCADE)
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

@receiver(post_save, sender=CartProductMapping)
def create_order(sender, instance=None, created=False, **kwargs):
    if created:
        order = Order.objects.filter(ordered_cart=instance.cart)
        if order.exists():
            order = order.last()
            order.total_final_amount = order.total_final_amount+instance.total_price
            order.save()
        else:
            shipping_address = Address.objects.get(shop_name=instance.cart.shop,address_type='shipping')
            billing_address = Address.objects.get(shop_name=instance.cart.shop,address_type='billing')
            Order.objects.create(ordered_cart=instance.cart, order_no=instance.cart.po_no,billing_address=billing_address,
                 shipping_address=shipping_address,total_final_amount=instance.total_price,order_status='ordered_to_gram')

class OrderedProduct(models.Model): #GRN
    DISABLED = "DIS"
    ENABLED = "ENA"
    EXPIRED = "EXP"
    GRN_STATUS = (
        (DISABLED, "Disabled"),
        (ENABLED, "Enabled"),
        (EXPIRED, "Expired"),
        )
    order = models.ForeignKey(Order,related_name='sp_order_order_product',on_delete=models.CASCADE,null=True,blank=True)
    invoice_no = models.CharField(max_length=255,null=True,blank=True)
    credit_note = models.ForeignKey(CreditNote, related_name='grn_list', null=True, blank=True, on_delete=models.CASCADE)
    vehicle_no = models.CharField(max_length=255,null=True,blank=True)
    shipped_by = models.ForeignKey(get_user_model(), related_name='sp_shipped_product_ordered_by_user', null=True, blank=True,on_delete=models.CASCADE)
    received_by = models.ForeignKey(get_user_model(), related_name='sp_ordered_product_received_by_user', null=True, blank=True,on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='sp_last_modified_user_order', null=True,blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=5, choices=GRN_STATUS, default=ENABLED)

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

    class Meta:
        permissions = (
            ("delivery_from_gf", "Can Delivery From GF"),
            ("warehouse_shipment", "Can Warehouse Shipment"),
        )

    def clean(self):
        if self.manufacture_date :
            if self.manufacture_date >= datetime.date.today():
                raise ValidationError(_("Manufactured Date cannot be greater than or equal to today's date"))
            elif self.expiry_date < self.manufacture_date:
                raise ValidationError(_("Expiry Date cannot be less than manufacture date"))

class OrderedProductReserved(models.Model):
    RESERVED = "reserved"
    ORDERED = "ordered"
    FREE = "free"
    RESERVE_STATUS = (
        (RESERVED, "Reserved"),
        (ORDERED, "Ordered"),
        (FREE, "Free"),
    )
    order_product_reserved = models.ForeignKey(OrderedProductMapping, related_name='sp_order_product_order_product_reserved',null=True, blank=True, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='sp_product_order_product_reserved', null=True, blank=True,on_delete=models.CASCADE)
    cart = models.ForeignKey(RetailerCart, related_name='sp_ordered_retailer_cart',null=True,blank=True,on_delete=models.CASCADE)
    reserved_qty = models.PositiveIntegerField(default=0)
    #order_reserve_start_time = models.DateTimeField(auto_now_add=True)
    order_reserve_end_time = models.DateTimeField(null=True,blank=True,editable=False)
    #order_reserve_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    reserve_status = models.CharField(max_length=100, choices=RESERVE_STATUS, default=RESERVED)

    def save(self):
        self.order_reserve_end_time = timezone.now() + timedelta(minutes=int(settings.BLOCKING_TIME_IN_MINUTS))
        super(OrderedProductReserved, self).save()

    def __str__(self):
        return str(self.order_reserve_end_time)

class SpNote(models.Model):

    debit_note = 'debit_note'
    credit_note = 'credit_note'

    NOTE_TYPE_CHOICES = (
        (debit_note, "Debit Note"),
        (credit_note, "Credit Note"),
    )
    brand_note_id = models.CharField(max_length=255, null=True, blank=True)
    order = models.ForeignKey(Order, related_name='order_sp_note',null=True,blank=True,on_delete=models.CASCADE)
    grn_order = models.ForeignKey(OrderedProduct, related_name='grn_order_sp_note', null=True, blank=True,on_delete=models.CASCADE)
    note_type = models.CharField(max_length=255,choices=NOTE_TYPE_CHOICES)
    amount = models.FloatField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_sp_note',null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.brand_note_id

@receiver(pre_save, sender=SpNote)
def create_brand_note_id(sender, instance=None, created=False, **kwargs):
    if instance._state.adding:
        import datetime
        current_year = datetime.date.today().strftime('%y')
        next_year = str(int(current_year) + 1)
        today_date = datetime.date.today().strftime('%d%m%y')
        if instance.note_type == 'debit_note':
            last_brand_note = SpNote.objects.filter(note_type="debit_note").last()
            if last_brand_note:
                last_brand_note_id_increment = str(int(last_brand_note.brand_note_id.rsplit('/', 1)[-1])+1)
            else:
                last_brand_note_id_increment = '1'
            instance.brand_note_id = "%s/%s"%(today_date,last_brand_note_id_increment)

        elif instance.note_type == 'credit_note':
            last_brand_note = SpNote.objects.filter(note_type="credit_note").last()
            if last_brand_note:
                last_brand_note_id_increment = str(int(last_brand_note.brand_note_id.rsplit('/', 1)[-1]) + 1).zfill(len(last_brand_note.brand_note_id.rsplit('/', 1)[-1]))
            else:
                last_brand_note_id_increment = '00001'
            instance.brand_note_id = "ADT/CN/%s"%(last_brand_note_id_increment)

@receiver(post_save, sender=RetailerShipment)
def create_credit_note(sender, instance=None, created=False, **kwargs):
    if instance.rt_order_product_order_product_mapping.all().aggregate(Sum('returned_qty')).get('returned_qty__sum') > 0:
        invoice_prefix = instance.order.seller_shop.invoce_pattern.filter(status=Shop.ACTIVE).last().pattern
        last_credit_note = Note.objects.last()
        if last_credit_note:
            note_id = int(getcredit_note_id(last_credit_note.credit_note_id, invoice_prefix))
            note_id += 1
        else:
            note_id = 1

        credit_amount = 0
        cur_cred_note = brand_credit_note_pattern(note_id, invoice_prefix)
        if instance.credit_note.count():
            credit_note = instance.credit_note.last()
        else:
            credit_note = Note.objects.create(
                credit_note_id=brand_credit_note_pattern(note_id, invoice_prefix),
                shipment = instance,
                amount = 0,
                status=True)
        SPGRN.objects.filter(credit_note=credit_note).update(status=SPGRN.DISABLED)
        credit_grn = SPGRN.objects.create(credit_note=credit_note)
        credit_grn.save()

        for item in instance.rt_order_product_order_product_mapping.all():
            grn_item = SPGRNProductMapping.objects.create(
                ordered_product=credit_grn,
                product=item.product,
                shipped_qty=item.returned_qty,
                available_qty=item.returned_qty - item.damaged_qty,
                ordered_qty = item.returned_qty,
                )
            grn_item.save()
            credit_amount += int(item.returned_qty) * int(item.product.product_inner_case_size) * float(item.product.product_pro_price.filter(
                shop__shop_type__shop_type='sp', status=True
                ).last().price_to_retailer)

        credit_note.amount = credit_amount
        credit_note.save()
 
