import datetime
from decimal import Decimal
from datetime import timedelta

from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, m2m_changed
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.db import models, transaction
from django.db.models import Sum, Q
import logging
import math

from shops.models import Shop, ParentRetailerMapping, ShopInvoicePattern
from brand.models import Brand
from products.models import Product, ProductPrice
from retailer_to_sp.models import Cart as RetailerCart
from addresses.models import Address, City, State
from retailer_to_sp.models import Note as CreditNote, OrderedProduct as RetailerShipment, OrderedProductMapping as RetailerShipmentMapping, Trip, Commercial
from retailer_backend.common_function import (
    order_id_pattern, brand_credit_note_pattern, getcredit_note_id, discounted_credit_note_pattern
)
from sp_to_gram.tasks import update_shop_product_es
logger = logging.getLogger(__name__)
from dateutil.relativedelta import relativedelta
from celery.task import task



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
            shipping_address = Address.objects.filter(shop_name=instance.cart.shop,address_type='shipping').last()
            billing_address = Address.objects.filter(shop_name=instance.cart.shop,address_type='billing').last()
            Order.objects.create(ordered_cart=instance.cart, order_no=instance.cart.po_no,billing_address=billing_address,
                 shipping_address=shipping_address,total_final_amount=instance.total_price,order_status='ordered_to_gram')

class OrderedProduct(models.Model): #GRN
    DISABLED = "DIS"
    ENABLED = "ENA"
    EXPIRED = "EXP"
    ADJUSTEMENT = "ADJ"

    GRN_STATUS = (
        (DISABLED, "Disabled"),
        (ENABLED, "Enabled"),
        (EXPIRED, "Expired"),
        (ADJUSTEMENT, "Adjustment"),
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

    class Meta:
        verbose_name = _('Invoices')
        verbose_name_plural = _('Invoices')

    def save(self, *args,**kwargs):
        super(OrderedProduct, self).save()
        self.invoice_no = "SP/INVOICE/%s"%(self.pk)
        super(OrderedProduct, self).save()

class OrderedProductMapping(models.Model): #GRN Product
    shop = models.ForeignKey(Shop, related_name='shop_grn_list', null=True, blank=True, on_delete=models.DO_NOTHING)
    ordered_product = models.ForeignKey(OrderedProduct,related_name='sp_order_product_order_product_mapping',null=True,blank=True,on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='sp_product_order_product',null=True,blank=True, on_delete=models.CASCADE)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    shipped_qty = models.PositiveIntegerField(default=0)
    available_qty = models.PositiveIntegerField(default=0)
    ordered_qty = models.PositiveIntegerField(default=0)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    delivered_qty = models.PositiveIntegerField(default=0)
    returned_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    perished_qty = models.PositiveIntegerField(default=0)
    lossed_qty = models.PositiveIntegerField(default=0)
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

    def save(self, *args, **kwargs):
        if self.ordered_product and self.ordered_product.order:
            self.shop = self.ordered_product.order.ordered_cart.shop
        elif self.ordered_product and self.ordered_product.credit_note:
            self.shop = self.ordered_product.credit_note.shop
        super().save(*args, **kwargs)

    @property
    def sp_available_qty(self):
        return int(self.available_qty) - (int(self.damaged_qty) + int(self.lossed_qty) + int(self.perished_qty))

    @classmethod
    def get_shop_stock(cls, shop, show_available=False):
        if show_available:
            shop_stock = cls.objects.filter(
                    Q(shop=shop),
                    Q(expiry_date__gt=datetime.datetime.today()),
                    Q(available_qty__gt=0),
                ).exclude(
                        Q(ordered_product__status=OrderedProduct.DISABLED)
                    )
            return shop_stock

        else:
            shop_stock = cls.objects.filter(
                    Q(shop=shop),
                    Q(expiry_date__gt=datetime.datetime.today())
                ).exclude(
                        Q(ordered_product__status=OrderedProduct.DISABLED)
                    )
            return shop_stock

    @classmethod
    def get_brand_in_shop_stock(cls, shop, brand, show_available=False):
        if show_available:
            shop_stock = cls.objects.filter(
                    Q(shop=shop),
                    Q(expiry_date__gt=datetime.datetime.today()),
                    Q(available_qty__gt=0),
                    Q(product=Product.objects.get(id=brand.id))
                ).exclude(
                        Q(ordered_product__status=OrderedProduct.DISABLED)
                    )
        else:
            shop_stock = cls.objects.filter(
                    Q(shop=shop),
                    Q(expiry_date__gt=datetime.datetime.today()),
                    Q(product__product_brand__brand_parent=brand)
                ).exclude(
                        Q(ordered_product__status=OrderedProduct.DISABLED)
                    )
        return shop_stock


    @classmethod
    def get_shop_stock_expired(cls, shop):
        shop_stock = cls.objects.filter(
                Q(shop=shop),
                Q(expiry_date__lte=datetime.datetime.today())
            ).exclude(
                    Q(ordered_product__status=OrderedProduct.DISABLED)
                )
        return shop_stock

    @classmethod
    def get_product_availability(cls, shop, product):
        product_availability = cls.objects.filter(
                Q(product=product),
                Q(shop=shop),
                Q(expiry_date__gt=datetime.datetime.today())
            ).exclude(
                    Q(ordered_product__status=OrderedProduct.DISABLED)
                )
        return product_availability

    @classmethod
    def get_expired_product_qty(cls, shop, product):
        product_expired = cls.objects.filter(
                Q(product=product),
                Q(shop=shop),
                Q(expiry_date__lte=datetime.datetime.today())
            ).exclude(
                    Q(ordered_product__status=OrderedProduct.DISABLED)
                )
        return product_expired

class OrderedProductReserved(models.Model):
    RESERVED = "reserved"
    ORDERED = "ordered"
    FREE = "free"
    CLEARING = "clearing"
    ORDER_CANCELLED = 'order_cancelled'
    RESERVE_STATUS = (
        (RESERVED, "Reserved"),
        (ORDERED, "Ordered"),
        (FREE, "Free"),
        (ORDER_CANCELLED, 'Order Cancelled')
    )
    order_product_reserved = models.ForeignKey(
        OrderedProductMapping,
        related_name='sp_order_product_order_product_reserved', null=True,
        blank=True, on_delete=models.CASCADE, verbose_name='GRN Product')
    product = models.ForeignKey(Product, related_name='sp_product_order_product_reserved', null=True, blank=True,on_delete=models.CASCADE)
    cart = models.ForeignKey(RetailerCart, related_name='sp_ordered_retailer_cart',null=True,blank=True,on_delete=models.CASCADE)
    reserved_qty = models.PositiveIntegerField(default=0)
    shipped_qty = models.PositiveIntegerField(default=0)
    order_reserve_end_time = models.DateTimeField(null=True,blank=True,editable=False)
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

class StockAdjustment(models.Model):
    ENABLED = "ENB"
    DISABLED = "DIS"
    STATUS_CHOICES = (
        (ENABLED, "ENABLED"),
        (DISABLED, "DISABLED")
        )
    shop = models.ForeignKey(Shop, related_name='shop_stock_adjustment', on_delete=models.CASCADE)
    grn_product = models.ManyToManyField(OrderedProductMapping, related_name='stock_adjustment', through='StockAdjustmentMapping')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default=ENABLED)

class StockAdjustmentMapping(models.Model):
    DECREMENT = "dec"
    INCREMENT = "inc"
    ADJUSTMENT_TYPE_CHOICES = (
        (INCREMENT, "Increment"),
        (DECREMENT, "Decrement")
        )
    stock_adjustment = models.ForeignKey(StockAdjustment, on_delete=models.CASCADE, related_name='stock_adjustment_mapping')
    grn_product = models.ForeignKey(OrderedProductMapping, on_delete=models.CASCADE, related_name='stock_adjustment_mapping')
    adjustment_qty = models.PositiveIntegerField()
    adjustment_type = models.CharField(max_length=5, choices=ADJUSTMENT_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

def commit_updates_to_es(shop, product):
    status = product.status
    db_available_products = OrderedProductMapping.get_product_availability(shop, product)
    products_available = db_available_products.aggregate(Sum('available_qty'))['available_qty__sum']
    if products_available is None:
        return
    try:
        available_qty = int(int(products_available)/int(product.product_inner_case_size))
    except Exception as e:
        logger.exception(e)
        return False
    if not available_qty:
        status = False
    update_shop_product_es.delay(shop.id, product.id, available=available_qty, status=status)

@receiver(post_save, sender=OrderedProductMapping)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    transaction.on_commit(lambda: commit_updates_to_es(instance.shop, instance.product))


@receiver(post_save, sender=Product)
def update_elasticsearch_on_product_change(sender, instance=None, created=False, **kwargs):
    product_prices = instance.product_pro_price.filter(status=True)
    for product_price in product_prices:
        transaction.on_commit(lambda: commit_updates_to_es(product_price.seller_shop, product_price.product))


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


@task
def create_credit_note_on_trip_close(trip_id):
    trip = Trip.objects.get(id=trip_id)
    shipments = trip.rt_invoice_trip.all()
    for shipment in shipments:
        if(shipment.rt_order_product_order_product_mapping.last() and
        shipment.rt_order_product_order_product_mapping.all().aggregate(Sum('returned_qty')).get('returned_qty__sum') > 0 or
        shipment.rt_order_product_order_product_mapping.all().aggregate(Sum('returned_damage_qty')).get('returned_damage_qty__sum')>0):
            invoice_prefix = shipment.order.seller_shop.invoice_pattern.filter(status=ShopInvoicePattern.ACTIVE).last().pattern
            last_credit_note = CreditNote.objects.filter(shop=shipment.order.seller_shop, status=True).order_by('credit_note_id').last()
            if last_credit_note:
                note_id = brand_credit_note_pattern(
                            CreditNote, 'credit_note_id', None,
                            shipment.order.seller_shop.
                            shop_name_address_mapping.filter(
                                            address_type='billing'
                                            ).last().pk)
            else:
                note_id = brand_credit_note_pattern(
                            CreditNote, 'credit_note_id', None,
                            shipment.order.seller_shop.
                            shop_name_address_mapping.filter(
                                            address_type='billing'
                                            ).last().pk)

            credit_amount = 0

            #cur_cred_note = brand_credit_note_pattern(note_id, invoice_prefix)
            if shipment.credit_note.filter(credit_note_type = 'RETURN').count():
                credit_note = shipment.credit_note.last()
            else:
                credit_note = CreditNote.objects.create(
                    shop = shipment.order.seller_shop,
                    credit_note_id=note_id,
                    shipment = shipment,
                    amount = 0,
                    credit_note_type = 'RETURN',
                    status=True)
            OrderedProduct.objects.filter(credit_note=credit_note).update(status=OrderedProduct.DISABLED)
            credit_grn = OrderedProduct.objects.create(credit_note=credit_note)
            credit_grn.save()

            manufacture_date = datetime.date.today() - relativedelta(months=+1)
            expiry_date = datetime.date.today() + relativedelta(months=+6)

            for item in shipment.rt_order_product_order_product_mapping.all():
                reserved_order = OrderedProductReserved.objects.filter(cart=shipment.order.ordered_cart,
                                                                     product=item.product, reserve_status=OrderedProductReserved.ORDERED).last()
                grn_item = OrderedProductMapping.objects.create(
                    shop = shipment.order.seller_shop,
                    ordered_product=credit_grn,
                    product=item.product,
                    shipped_qty=item.returned_qty,
                    available_qty=item.returned_qty,
                    damaged_qty=item.returned_damage_qty,
                    ordered_qty = item.returned_qty,
                    delivered_qty = item.returned_qty,
                    manufacture_date= reserved_order.order_product_reserved.manufacture_date if reserved_order else manufacture_date,
                    expiry_date= reserved_order.order_product_reserved.expiry_date if reserved_order else expiry_date,
                    )
                grn_item.save()
                try:
                    credit_amount += ((item.shipped_qty - item.delivered_qty) * float(item.effective_price))
                except Exception as e:
                    logger.exception("Product price not found for {} -- {}".format(item.product, e))

            credit_note.amount = credit_amount
            credit_note.save()
        if shipment.order.ordered_cart.approval_status == True:
            invoice_prefix = shipment.order.seller_shop.invoice_pattern.filter(status=ShopInvoicePattern.ACTIVE).last().pattern
            last_credit_note = CreditNote.objects.filter(shop=shipment.order.seller_shop, status=True).order_by('credit_note_id').last()
            if last_credit_note:
                note_id = discounted_credit_note_pattern(
                            CreditNote, 'credit_note_id', None,
                            shipment.order.seller_shop.
                            shop_name_address_mapping.filter(
                                            address_type='billing'
                                            ).last().pk)
            else:
                note_id = discounted_credit_note_pattern(
                            CreditNote, 'credit_note_id', None,
                            shipment.order.seller_shop.
                            shop_name_address_mapping.filter(
                                            address_type='billing'
                                            ).last().pk)

            credit_amount = 0
            if shipment.credit_note.filter(credit_note_type = 'DISCOUNTED').count():
                credit_note = shipment.credit_note.last()
            else:
                credit_note = CreditNote.objects.create(
                    shop = shipment.order.seller_shop,
                    credit_note_id=note_id,
                    shipment = shipment,
                    amount = 0,
                    credit_note_type = 'DISCOUNTED',
                    status=True)
            for item in shipment.rt_order_product_order_product_mapping.all():
                credit_amount += (float(item.effective_price) - float(item.discounted_price)) * item.delivered_qty
            credit_note.amount = credit_amount
            credit_note.save()


@receiver(post_save, sender=Trip)
def create_offers(sender, instance=None, created=False, **kwargs):
    if instance.trip_status == Trip.RETURN_VERIFIED:
        create_credit_note_on_trip_close(instance.id)


# @receiver(post_save, sender=RetailerShipment)
def create_credit_note(instance=None, created=False, **kwargs):
    if created:
        return None
    if instance.order.ordered_cart.approval_status == True:
        invoice_prefix = instance.order.seller_shop.invoice_pattern.filter(status=ShopInvoicePattern.ACTIVE).last().pattern
        last_credit_note = CreditNote.objects.filter(shop=instance.order.seller_shop, status=True).order_by('credit_note_id').last()
        if last_credit_note:
            note_id = discounted_credit_note_pattern(
                        CreditNote, 'credit_note_id', None,
                        instance.order.seller_shop.
                        shop_name_address_mapping.filter(
                                        address_type='billing'
                                        ).last().pk)
        else:
            note_id = discounted_credit_note_pattern(
                        CreditNote, 'credit_note_id', None,
                        instance.order.seller_shop.
                        shop_name_address_mapping.filter(
                                        address_type='billing'
                                        ).last().pk)

        credit_amount = 0
        if instance.credit_note.count():
            credit_note = instance.credit_note.last()
        else:
            credit_note = CreditNote.objects.create(
                shop = instance.order.seller_shop,
                credit_note_id=note_id,
                shipment = instance,
                amount = 0,
                status=True)
        for item in instance.rt_order_product_order_product_mapping.all():
            cart_product_map = instance.order.ordered_cart.rt_cart_list.filter(cart_product=item.product).last()
            credit_amount += ((cart_product_map.item_effective_prices - cart_product_map.discounted_price) * (item.returned_qty + item.returned_damage_qty))
        credit_note.amount = credit_amount
        credit_note.save()
        # if(instance.rt_order_product_order_product_mapping.last() and
        # instance.rt_order_product_order_product_mapping.all().aggregate(Sum('returned_qty')).get('returned_qty__sum') > 0 or
        # instance.rt_order_product_order_product_mapping.all().aggregate(Sum('damaged_qty')).get('damaged_qty__sum')>0):
        #     invoice_prefix = instance.order.seller_shop.invoice_pattern.filter(status=ShopInvoicePattern.ACTIVE).last().pattern
        #     last_credit_note = CreditNote.objects.filter(shop=instance.order.seller_shop, starts_with = 'GC', status=True).order_by('credit_note_id').last()
        #     if last_credit_note:
        #         note_id = brand_credit_note_pattern(
        #                     CreditNote, 'credit_note_id', None,
        #                     instance.order.seller_shop.
        #                     shop_name_address_mapping.filter(
        #                                     address_type='billing'
        #                                     ).last().pk)
        #     else:
        #         note_id = brand_credit_note_pattern(
        #                     CreditNote, 'credit_note_id', None,
        #                     instance.order.seller_shop.
        #                     shop_name_address_mapping.filter(
        #                                     address_type='billing'
        #                                     ).last().pk)
        #
        #     credit_amount = 0
        #
        #     #cur_cred_note = brand_credit_note_pattern(note_id, invoice_prefix)
        #     if instance.credit_note.count():
        #         credit_note = instance.credit_note.last()
        #     else:
        #         credit_note = CreditNote.objects.create(
        #             shop = instance.order.seller_shop,
        #             credit_note_id=note_id,
        #             shipment = instance,
        #             amount = 0,
        #             status=True)
        #     OrderedProduct.objects.filter(credit_note=credit_note).update(status=OrderedProduct.DISABLED)
        #     credit_grn = OrderedProduct.objects.create(credit_note=credit_note)
        #     credit_grn.save()
        #
        #     manufacture_date = datetime.date.today() - relativedelta(months=+1)
        #     expiry_date = datetime.date.today() + relativedelta(months=+6)
        #
        #     for item in instance.rt_order_product_order_product_mapping.all():
        #         reserved_order = OrderedProductReserved.objects.filter(cart=instance.order.ordered_cart,
        #                                                              product=item.product, reserve_status=OrderedProductReserved.ORDERED).last()
        #         grn_item = OrderedProductMapping.objects.create(
        #             shop = instance.order.seller_shop,
        #             ordered_product=credit_grn,
        #             product=item.product,
        #             shipped_qty=item.returned_qty,
        #             available_qty=item.returned_qty,
        #             damaged_qty=item.damaged_qty,
        #             ordered_qty = item.returned_qty,
        #             delivered_qty = item.returned_qty,
        #             manufacture_date= reserved_order.order_product_reserved.manufacture_date if reserved_order else manufacture_date,
        #             expiry_date= reserved_order.order_product_reserved.expiry_date if reserved_order else expiry_date,
        #             )
        #         grn_item.save()
        #         try:
        #             cart_product_map = instance.order.ordered_cart.rt_cart_list.filter(cart_product=item.product).last()
        #             credit_amount += ((item.returned_qty + item.damaged_qty) * cart_product_map.item_effective_prices)
        #         except Exception as e:
        #             logger.exception("Product price not found for {} -- {}".format(item.product, e))
        #             credit_amount += Decimal(item.returned_qty) * item.product.product_pro_price.filter(
        #                 seller_shop=instance.order.seller_shop, approval_status=ProductPrice.APPROVED
        #                 ).last().selling_price
        #     credit_note.amount = credit_amount
        #     credit_note.save()
