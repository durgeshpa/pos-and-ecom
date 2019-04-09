import datetime
import csv
import codecs
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.urls import reverse
from django.utils import timezone
from django.db import models
from django.db.models import Sum

from shops.models import Shop, ParentRetailerMapping
from products.models import Product, ProductVendorMapping
from brand.models import Brand, Vendor
from addresses.models import Address, City, State
from retailer_to_gram.models import (
    Cart as GramMapperRetialerCart,
    Order as GramMapperRetialerOrder
)
from retailer_backend.common_function import (
    po_pattern, grn_pattern,
    brand_note_pattern, brand_debit_note_pattern
)
from sp_to_gram.models import (
    Cart as SpPO,
    CartProductMapping as SpPOProducts,
    Order as SpOrder,
    OrderedProduct as SpGRNOrder,
    OrderedProductMapping as SpGRNOrderProductMapping
)
from base.models import (BaseOrder, BaseCart, BaseShipment)
#from gram_to_brand.forms import GRNOrderProductForm

ITEM_STATUS = (
    ("partially_delivered", "Partially Delivered"),
    ("delivered", "Delivered"),
)

BEST_BEFORE_MONTH_CHOICE = (
    (0,'0 Month'),
    (1,'1 Month'),
    (2, '2 Month'),
    (3, '3 Month'),
    (4, '4 Month'),
    (5, '5 Month'),
    (6, '6 Month'),
    (7, '7 Month'),
    (8, '8 Month'),
    (9, '9 Month'),
    (10, '10 Month'),
    (11, '11 Month'),
)

BEST_BEFORE_YEAR_CHOICE = (
    (0, '0 Year'),
    (1, '1 Year'),
    (2, '2 Year'),
    (3, '3 Year'),
    (4, '4 Year'),
    (5, '5 Year'),
)

class Po_Message(models.Model):
    created_by = models.ForeignKey(get_user_model(), related_name='created_by_user_message', null=True,blank=True, on_delete=models.CASCADE)
    message = models.TextField(max_length=1000,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Cart(BaseCart):
    """PO Generation"""
    APPROVAL_AWAITED = "WAIT"
    FINANCE_APPROVED = "APRW"
    UNAPPROVED = "RJCT"
    SENT_TO_BRAND = "SENT"
    PARTIAL_DELIVERED = "PDLV"
    DELIVERED = "DLVR"
    CANCELED = "CNCL"
    ORDER_STATUS = (
        (SENT_TO_BRAND, "Send To Brand"),
        (APPROVAL_AWAITED, "Waiting For Finance Approval"),
        (FINANCE_APPROVED, "Finance Approved"),
        (UNAPPROVED, "Finance Not Approved"),
        (PARTIAL_DELIVERED, "Partial Delivered"),
        (DELIVERED, "Delivered"),
        (CANCELED, "Canceled"),
    )

    brand = models.ForeignKey(
        Brand, related_name='brand_order', on_delete=models.CASCADE
    )
    supplier_state = models.ForeignKey(
        State, related_name='state_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    supplier_name = models.ForeignKey(
        Vendor, related_name='buyer_vendor_order',
        null=True, blank=True, on_delete=models.CASCADE
    )
    gf_shipping_address = models.ForeignKey(
        Address, related_name='shipping_address_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    gf_billing_address = models.ForeignKey(
        Address, related_name='billing_address_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    products = models.ManyToManyField(
        Product, through='gram_to_brand.CartProductMapping'
    )
    po_no = models.CharField(max_length=255, null=True, blank=True)
    po_status = models.CharField(
        max_length=200, choices=ORDER_STATUS,
        null=True, blank=True
    )
    po_raised_by = models.ForeignKey(
        get_user_model(), related_name='po_raise_user_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='last_modified_user_cart',
        null=True, blank=True, on_delete=models.CASCADE
    )
    po_creation_date = models.DateField(auto_now_add=True)
    po_validity_date = models.DateField()
    po_message = models.ForeignKey(
        Po_Message, related_name='po_message_dt',
        on_delete=models.CASCADE, null=True, blank=True
    )
    payment_term = models.TextField(null=True,blank=True)
    delivery_term = models.TextField(null=True,blank=True)
    po_amount = models.FloatField(default=0)
    cart_product_mapping_csv = models.FileField(
        upload_to='gram/brand/cart_product_mapping_csv',
        null=True, blank=True
    )
    is_approve = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "PO Generation"
        permissions = (
            ("can_approve_and_disapprove", "Can approve and dis-approve"),
        )

    def clean(self):
        super(Cart, self).clean()
        if self.po_validity_date and self.po_validity_date < datetime.date.today():
            raise ValidationError(_("Po validity date cannot be in the past!"))

    def __str__(self):
        return str(self.po_no)

    @property
    def products_sample_file(self):
        if (
            self.cart_product_mapping_csv
            and hasattr(self.cart_product_mapping_csv, 'url')
        ):
            url = """<h3><a href="%s" target="_blank">
                    Download Products List</a></h3>""" % \
                  (
                      reverse(
                          'admin:products_vendor_mapping',
                          args=(self.supplier_name_id,)
                      )
                  )
        else:
            url = """<h3><a href="#">Download Products List</a></h3>"""
        return url

    @property
    def po_amount(self):
        self.cart_list.aggregate(sum('total_price'))



class CartProductMapping(models.Model):
    cart = models.ForeignKey(Cart,related_name='cart_list',on_delete=models.CASCADE)
    cart_product = models.ForeignKey(Product, related_name='cart_product_mapping', on_delete=models.CASCADE)
    _tax_percentage = models.FloatField(db_column="tax_percentage", null=True)
    #Todo Remove
    inner_case_size = models.PositiveIntegerField(default=0, null=True,blank=True)
    case_size= models.PositiveIntegerField(default=0,null=True,blank=True)
    number_of_cases = models.FloatField(default=0,null=True,blank=True)
    scheme = models.FloatField(default=0, null=True, blank=True, help_text='data into percentage %')

    no_of_pieces = models.PositiveIntegerField(null=True,blank=True)
    vendor_product = models.ForeignKey(ProductVendorMapping, related_name='vendor_products',null=True,blank=True, on_delete=models.CASCADE)
    price = models.FloatField( verbose_name='Brand To Gram Price')

    def __str__(self):
        return str('')

    class Meta:
        verbose_name = "Select Product"
        unique_together = ('cart', 'cart_product')

    @property
    def tax_percentage(self):
        return  self._tax_percentage if self._tax_percentage else '-'

    @tax_percentage.setter
    def tax_percentage(self, value):
        self._tax_percentage = value

    def calculate_tax_percentage(self):
        tax_percentage = [field.tax.tax_percentage for field in self.cart_product.product_pro_tax.all()]
        tax_percentage = sum(tax_percentage)
        return tax_percentage

    @property
    def qty(self):
        if self.vendor_product:
            return int(self.no_of_pieces)
        return int(int(self.cart_product.product_inner_case_size) * int(self.cart_product.product_case_size) * float(self.number_of_cases))

    @property
    def total_price(self):
        if self.vendor_product:
            return float(self.no_of_pieces)*float(self.vendor_product.product_price)
        return float(self.qty) * float(self.price)

    @property
    def gf_code(self):
        return self.cart_product.product_gf_code

    @property
    def case_sizes(self):
        if self.vendor_product:
            return self.vendor_product.case_size
        return self.cart_product.product_case_size

    @property
    def no_of_cases(self):
        if self.vendor_product:
            return int(self.no_of_pieces) // int(self.vendor_product.case_size)
        return self.number_of_cases

    @property
    def total_no_of_pieces(self):
        if self.vendor_product:
            return int(self.no_of_pieces)
        return self.qty

    @property
    def sub_total(self):
        if self.vendor_product:
            return float(self.qty)* float(self.vendor_product.product_price)
        return self.total_price

    def __str__(self):
        return self.cart_product.product_name

    def save(self, *args, **kwargs):
        if not self.tax_percentage or self.tax_percentage == "-":
            self.tax_percentage = self.calculate_tax_percentage()

        # if Product mapping exists
        productVendorObj = ProductVendorMapping.objects.filter(vendor=self.cart.supplier_name, product=self.cart_product)
        if productVendorObj.filter(product_price=self.price,status=True).exists():
            self.vendor_product = productVendorObj.filter(product_price=self.price,status=True).last()
        else:
            case_size = productVendorObj.last().case_size if productVendorObj.exists() else self.cart_product.product_case_size
            mrp = productVendorObj.last().product_mrp if productVendorObj.exists() else None
            self.vendor_product = ProductVendorMapping.objects.create(vendor=self.cart.supplier_name,
                                                product=self.cart_product, case_size=case_size,
                                                product_price=self.price, product_mrp=mrp, status=True)

        super(CartProductMapping, self).save(*args, **kwargs)

@receiver(post_save, sender=Cart)
def create_cart_product_mapping(sender, instance=None, created=False, **kwargs):
    if created:
        instance.po_no = po_pattern(sender,
                                    'po_no',
                                    instance.pk,
                                    instance.gf_billing_address_id,
                                    )
        instance.save()
        if instance.cart_product_mapping_csv:
            reader = csv.reader(codecs.iterdecode(instance.cart_product_mapping_csv, 'utf-8'))
            for id,row in enumerate(reader):
                for row in reader:
                    if row[0] and row[4] and row[5] :
                        product = Product.objects.get(id=int(row[0]))

                        vendor_product = ProductVendorMapping.objects.filter(vendor=instance.supplier_name,product_id=row[0]).last()
                        if vendor_product and (vendor_product.case_size == row[2] or vendor_product.product_price == row[5]):
                            vendor_product_dt = vendor_product
                        else:
                            vendor_product_dt = ProductVendorMapping.objects.create(vendor=instance.supplier_name,
                                                                product_id=row[0], product_price=row[5],
                                                                product_mrp=row[4], case_size=row[2], status=True)

                        CartProductMapping.objects.create(cart=instance,cart_product_id = row[0],
                         no_of_pieces = int(vendor_product_dt.case_size)*int(row[3]),
                         price=float(row[5]),vendor_product=vendor_product_dt)

    order = Order.objects.get_or_create(ordered_cart=instance, order_no=instance.po_no)


class Order(BaseOrder):
    ordered_cart = models.OneToOneField(Cart,related_name='order_cart_mapping',on_delete=models.CASCADE)
    order_no = models.CharField(verbose_name='PO Number', max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.order_no) or str(self.id)

    @property
    def total_final_amount(self):
        return self.ordered_cart.po_amount

    @property
    def order_status(self):
        return self.ordered_cart.po_status

    class Meta:
        verbose_name = _("Add GRN")
        verbose_name_plural = _("Add GRN")


class GRNOrder(BaseShipment): #Order Shipment
    order = models.ForeignKey(Order,verbose_name='PO Number',related_name='order_grn_order',on_delete=models.CASCADE,null=True,blank=True )
    invoice_no = models.CharField(max_length=255)
    e_way_bill_no = models.CharField(max_length=255, blank=True, null=True)
    e_way_bill_document = models.FileField(null=True,blank=True)
    grn_id = models.CharField(max_length=255,null=True,blank=True)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_grn_order', null=True,blank=True, on_delete=models.CASCADE)
    grn_date = models.DateField(auto_now_add=True)
    brand_invoice = models.FileField(null=True,blank=True,upload_to='brand_invoice')
    products = models.ManyToManyField(Product,through='GRNOrderProductMapping')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return str(self.grn_id)

    class Meta:
        verbose_name = _("View GRN Detail")
        verbose_name_plural = _("View GRN Details")


@receiver(post_save, sender=GRNOrder)
def create_grn_id(sender, instance=None, created=False, **kwargs):
    if created:
        instance.grn_id = grn_pattern(instance.pk)
        instance.save()
        # SP auto ordered product creation
        connected_shops = ParentRetailerMapping.objects.filter(
            parent=instance.order.ordered_cart.gf_shipping_address.shop_name,
            status=True
        )
        for shop in connected_shops:
            if shop.retailer.shop_type.shop_type == 'sp':
                sp_po = SpPO.objects.create(
                    shop=shop.retailer,
                    po_validity_date=datetime.date.today() + timedelta(days=15)
                )


class GRNOrderProductMapping(models.Model):
    grn_order = models.ForeignKey(GRNOrder,related_name='grn_order_grn_order_product',null=True,blank=True,on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='product_grn_order_product',null=True,blank=True, on_delete=models.CASCADE)
    product_invoice_price = models.FloatField(default=0)
    product_invoice_qty = models.PositiveIntegerField(default=0)
    manufacture_date = models.DateField(null=True,blank=True)
    expiry_date = models.DateField(null=True,blank=False)
    delivered_qty = models.PositiveIntegerField(default=0)
    available_qty = models.PositiveIntegerField(default=0)
    returned_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_grn_order_product', null=True,blank=True, on_delete=models.CASCADE)
    vendor_product = models.ForeignKey(ProductVendorMapping, related_name='vendor_grn_products', null=True, blank=True,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str('')

    class Meta:
        verbose_name = _("GRN Product Detail")

    @property
    def po_product_quantity(self):
        return self.grn_order.order.ordered_cart.cart_list.filter(cart_product=self.product).last().qty if self.product else ''

    @property
    def po_product_price(self):
        if self.vendor_product:
            return self.vendor_product.product_price
        return self.grn_order.order.ordered_cart.cart_list.filter(cart_product=self.product).last().price if self.product else ''

    @property
    def already_grned_product(self):
        already_grn = self.product.product_grn_order_product.filter(grn_order__order=self.grn_order.order).aggregate(Sum('delivered_qty'))
        return 0 if already_grn.get('delivered_qty__sum') == None else already_grn.get('delivered_qty__sum')
        #

    @property
    def ordered_qty(self):
        return self.grn_order.order.ordered_cart.cart_list.last(cart_product=self.product).qty if self.product else ''

    @property
    def best_before_year(self):
        return 0

    @property
    def best_before_month(self):
        return 0
    # @property
    # def available_qty(self):
    #     return self.delivered_qty

    # @available_qty.setter
    # def available_qty(self, value):
    #     return self._available_qty = value

    def clean(self):
        super(GRNOrderProductMapping, self).clean()
        total_items= self.delivered_qty + self.returned_qty
        diff = self.po_product_quantity - self.already_grned_product

        self.already_grn = self.delivered_qty
        if self.product_invoice_qty <= diff:
            if self.product_invoice_qty < total_items:
                raise ValidationError(_('Product invoice quantity cannot be less than the sum of delivered quantity and returned quantity'))
            elif total_items < self.product_invoice_qty:
                raise ValidationError(_('Product invoice quantity must be equal to the sum of delivered quantity and returned quantity'))
        else:
            raise ValidationError(_('Product invoice quantity cannot be greater than the difference of PO product quantity and already_grned_product'))
        if self.manufacture_date :
            if self.manufacture_date >= datetime.date.today():
                raise ValidationError(_("Manufactured Date cannot be greater than or equal to today's date"))
            # elif self.expiry_date < self.manufacture_date:
            #     raise ValidationError(_("Expiry Date cannot be less than manufacture date"))
        # else:
        #     raise ValidationError(_("Please enter all the field values"))
        if self.delivered_qty and float(self.po_product_price) != float(self.product_invoice_price):
            raise ValidationError(_("Po_Product_Price and Po_Invoice_Price are not similar"))


    def save(self, *args, **kwargs):
        if not self.vendor_product and self.grn_order.order.ordered_cart.cart_list.filter(cart_product=self.product).last().vendor_product:
            self.vendor_product = self.grn_order.order.ordered_cart.cart_list.filter(cart_product=self.product).last().vendor_product

        super(GRNOrderProductMapping, self).save(*args, **kwargs)

class BrandNote(models.Model):
    NOTE_TYPE_CHOICES = (
        ("debit_note","Debit Note"),
    )

    brand_note_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='Debit Note ID')
    grn_order = models.ForeignKey(GRNOrder, related_name='grn_order_brand_note', null=True, blank=True,on_delete=models.CASCADE)
    note_type = models.CharField(max_length=255,choices=NOTE_TYPE_CHOICES, default='debit_note')
    amount = models.FloatField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_brand_note',null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    def __str__(self):
        return self.brand_note_id

    class Meta:
        verbose_name = _("Debit Note")
        verbose_name_plural = _("Debit Notes")


@receiver(post_save, sender=GRNOrderProductMapping)
def create_debit_note(sender, instance=None, created=False, **kwargs):
    if created:
        if instance.returned_qty > 0:
            debit_note = BrandNote.objects.filter(grn_order = instance.grn_order)
            if debit_note.exists():
                debit_note = debit_note.last()
                debit_note.brand_note_id = brand_debit_note_pattern(
                        BrandNote, 'brand_note_id', debit_note, instance.grn_order.order.ordered_cart.gf_billing_address_id)
                debit_note.order = instance.grn_order.order
                debit_note.amount= debit_note.amount + (instance.returned_qty * instance.po_product_price)
                debit_note.save()
            else:
                debit_note = BrandNote.objects.create(
                    brand_note_id=brand_debit_note_pattern(
                        BrandNote, 'brand_note_id', None, instance.grn_order.order.ordered_cart.gf_billing_address_id),
                grn_order = instance.grn_order, amount = instance.returned_qty * instance.po_product_price, status=True)

        instance.available_qty = instance.delivered_qty
        instance.save()
        # SP auto ordered product creation
        connected_shops = ParentRetailerMapping.objects.filter(
            parent=instance.grn_order.order.ordered_cart.gf_shipping_address.shop_name,
            status=True
        )
        for shop in connected_shops:
            if shop.retailer.shop_type.shop_type == 'sp':
                sp_po = SpPO.objects.filter(
                    shop=shop.retailer
                ).last()
                sp_cpm = SpPOProducts.objects.create(
                    cart=sp_po,
                    cart_product=instance.product,
                    case_size=instance.product.product_case_size,
                    number_of_cases=instance.grn_order.order. \
                              ordered_cart.cart_list.filter
                              (
                              cart_product=instance.product
                          ).last().number_of_cases,
                    qty=int(instance.delivered_qty),
                    #scheme=item.scheme,
                    price=instance.grn_order.order.\
                    ordered_cart.cart_list.filter
                    (
                        cart_product=instance.product
                    ).last().price,
                    total_price=float(instance.delivered_qty) * instance.grn_order.order.\
                    ordered_cart.cart_list.filter
                    (
                        cart_product=instance.product
                    ).last().price,
                )
                sp_order = SpOrder.objects.filter(
                    ordered_cart=sp_po
                ).last()
                sp_grn_orders = SpGRNOrder.objects.filter(
                    order=sp_order
                )
                if sp_grn_orders.exists():
                    sp_grn_order = sp_grn_orders.last()
                else:
                    sp_grn_order = SpGRNOrder.objects.create(order=sp_order)
                SpGRNOrderProductMapping.objects.create(
                    ordered_product=sp_grn_order,
                    product=instance.product,
                    manufacture_date=instance.manufacture_date,
                    expiry_date=instance.expiry_date,
                    shipped_qty=instance.delivered_qty,
                    available_qty=instance.available_qty,
                    ordered_qty=instance.grn_order.order.ordered_cart.\
                        cart_list.filter(cart_product=instance.product).last().qty,
                    delivered_qty=instance.delivered_qty,
                    returned_qty=instance.returned_qty,
                    damaged_qty=instance.damaged_qty
                )
        # ends here
        instance.available_qty = 0
        instance.save()


class OrderedProductReserved(models.Model):
    RESERVED = "reserved"
    ORDERED = "ordered"
    FREE = "free"
    RESERVE_STATUS = (
        (RESERVED, "Reserved"),
        (ORDERED, "Ordered"),
        (FREE, "Free"),
    )
    order_product_reserved = models.ForeignKey(GRNOrderProductMapping, related_name='retiler_order_product_order_product_reserved',null=True, blank=True, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='retiler_product_order_product_reserved', null=True, blank=True,on_delete=models.CASCADE)
    cart = models.ForeignKey(GramMapperRetialerCart, related_name='retiler_ordered_retailer_cart',null=True,blank=True,on_delete=models.CASCADE)
    reserved_qty = models.PositiveIntegerField(default=0)
    order_reserve_end_time = models.DateTimeField(null=True,blank=True,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    reserve_status = models.CharField(max_length=100,choices=RESERVE_STATUS,default=RESERVED)

    def save(self):
        self.order_reserve_end_time = timezone.now() + timedelta(minutes=int(settings.BLOCKING_TIME_IN_MINUTS))
        super(OrderedProductReserved, self).save()

    def __str__(self):
        return str(self.order_reserve_end_time)

    class Meta:
        verbose_name = _("Ordered Product Reserved")
        verbose_name_plural = _("Ordered Product Reserved")


class PickList(models.Model):
    order = models.ForeignKey(GramMapperRetialerOrder, related_name='pick_list_order',null=True,blank=True,on_delete=models.CASCADE)
    cart = models.ForeignKey(GramMapperRetialerCart, related_name='pick_list_cart', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Pick List")
        verbose_name_plural = _("Pick List")


class PickListItems(models.Model):
    pick_list = models.ForeignKey(PickList, related_name='pick_list_items_pick_list',on_delete=models.CASCADE)
    grn_order = models.ForeignKey(GRNOrder, related_name='pick_list_cart', on_delete=models.CASCADE, verbose_name='GRN No')
    product = models.ForeignKey(Product, related_name='pick_product', null=True, blank=True,on_delete=models.CASCADE)
    pick_qty = models.PositiveIntegerField(default=0)
    return_qty = models.PositiveIntegerField(default=0)
    damage_qty = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
