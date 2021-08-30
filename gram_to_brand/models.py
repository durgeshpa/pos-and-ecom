import datetime
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from django.db import models, transaction
from django.db.models import Sum, F
from model_utils import Choices

from products.models import Product, ProductVendorMapping, ParentProduct
from products.utils import vendor_product_mapping
from brand.models import Brand, Vendor
from addresses.models import Address, State
from retailer_to_gram.models import (Cart as GramMapperRetailerCart, Order as GramMapperRetailerOrder)
from base.models import (BaseOrder, BaseCart, BaseShipment)
from shops.models import Shop, ParentRetailerMapping
from wms.models import WarehouseAssortment

ITEM_STATUS = (
    ("partially_delivered", "Partially Delivered"),
    ("delivered", "Delivered"),
)

BEST_BEFORE_MONTH_CHOICE = (
    (0, '0 Month'),
    (1, '1 Month'),
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
    created_by = models.ForeignKey(get_user_model(), related_name='created_by_user_message', null=True, blank=True,
                                   on_delete=models.CASCADE)
    message = models.TextField(max_length=1000, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Cart(BaseCart):
    """
        PO Generation
    """
    OPEN = "OPEN"
    APPROVAL_AWAITED = "WAIT"
    FINANCE_APPROVED = "APRW"
    DISAPPROVED = "RJCT"
    SENT_TO_BRAND = "SENT"
    PARTIAL_DELIVERED = "PDLV"
    PARTIAL_DELIVERED_CLOSE = "PDLC"
    DELIVERED = "DLVR"
    CANCELED = "CNCL"
    PARTIAL_RETURN = 'PARR'
    CLOSE = "CLS"
    PENDING_APPROVAL = 'PDA'
    ORDER_STATUS = (
        (OPEN, "Open"),
        (APPROVAL_AWAITED, "Waiting For Finance Approval"),
        (FINANCE_APPROVED, "Finance Approved"),
        (DISAPPROVED, "Finance Disapproved"),
        (PARTIAL_DELIVERED, "Partial Delivered"),
        (PARTIAL_DELIVERED_CLOSE, "Partial Delivered and Closed"),
        (PARTIAL_RETURN, "Partial Return"),
        (DELIVERED, "Completely delivered and Closed"),
        (CANCELED, "Canceled"),
        (CLOSE, "Closed"),
        (PENDING_APPROVAL, "Pending for approval"),
    )
    CART_TYPE_CHOICE = Choices((1, 'MANUAL', 'Manual'),(2, 'AUTO', 'Auto'))

    brand = models.ForeignKey(Brand, related_name='brand_order', on_delete=models.CASCADE)
    supplier_state = models.ForeignKey(State, related_name='state_cart', null=True, blank=True,
                                       on_delete=models.CASCADE)
    supplier_name = models.ForeignKey(Vendor, related_name='buyer_vendor_order', null=True, blank=True,
                                      on_delete=models.CASCADE)
    gf_shipping_address = models.ForeignKey(Address, related_name='shipping_address_cart', null=True, blank=True,
                                            on_delete=models.CASCADE)
    gf_billing_address = models.ForeignKey(Address, related_name='billing_address_cart', null=True, blank=True,
                                           on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, through='gram_to_brand.CartProductMapping')
    po_no = models.CharField(max_length=255, null=True, blank=True)
    po_status = models.CharField(max_length=200, choices=ORDER_STATUS, null=True, blank=True)
    po_raised_by = models.ForeignKey(get_user_model(), related_name='po_raise_user_cart', null=True, blank=True,
                                     on_delete=models.CASCADE)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_cart', null=True,
                                         blank=True, on_delete=models.CASCADE)
    po_creation_date = models.DateField(auto_now_add=True)
    po_validity_date = models.DateField()
    po_message = models.ForeignKey(Po_Message, related_name='po_message_dt', on_delete=models.CASCADE, null=True,
                                   blank=True)
    payment_term = models.TextField(null=True, blank=True)
    delivery_term = models.TextField(null=True, blank=True)
    po_amount = models.FloatField(default=0)
    cart_product_mapping_csv = models.FileField(upload_to='gram/brand/cart_product_mapping_csv', null=True, blank=True)
    is_approve = models.BooleanField(default=False, blank=True, null=True)
    is_vendor_notified = models.BooleanField(default=False, blank=True)
    is_warehouse_notified = models.BooleanField(default=False, blank=True)
    po_delivery_date = models.DateField(null=True)
    cart_type = models.PositiveSmallIntegerField(choices=CART_TYPE_CHOICE, default=CART_TYPE_CHOICE.MANUAL)
    approved_by = models.ForeignKey(get_user_model(), related_name='user_approved_carts', null=True, blank=True,
                                    on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "PO Generation"
        permissions = (
            ("can_approve_and_disapprove", "Can approve and dis-approve"),
            ("can_create_po", "Can create po"),
        )

    def __init__(self, *args, **kwargs):
        super(Cart, self).__init__(*args, **kwargs)
        self._old_cart_product_mapping_csv = self.cart_product_mapping_csv

    def __str__(self):
        return str(self.po_no)

    def clean(self):
        super(Cart, self).clean()
        if self.po_validity_date and self.po_validity_date < datetime.date.today():
            raise ValidationError(_("Po validity date cannot be in the past!"))

    @property
    def products_sample_file(self):
        """
            Sample file containing products mapped to vendor
        """
        if self.supplier_name:
            url = """<h3><a href="%s">Download Products List</a></h3>""" % \
                  (reverse('admin:products_vendor_mapping', args=(self.supplier_name_id,)))
        else:
            url = """<h3><a href="#">Download Products List</a></h3>"""
        return url

    @property
    def po_amount(self):
        self.cart_list.aggregate(sum('total_price'))


class CartProductMapping(models.Model):
    cart = models.ForeignKey(Cart, related_name='cart_list', on_delete=models.CASCADE)
    cart_parent_product = models.ForeignKey(ParentProduct, related_name='cart_parent_product_mapping',
                                            on_delete=models.CASCADE, default=None, null=True)
    cart_product = models.ForeignKey(Product, related_name='cart_product_mapping', on_delete=models.CASCADE)
    _tax_percentage = models.FloatField(db_column="tax_percentage", null=True)
    # Todo Remove
    inner_case_size = models.PositiveIntegerField(default=0, null=True, blank=True)
    case_size = models.PositiveIntegerField(default=0, null=True, blank=True)
    number_of_cases = models.FloatField(default=0, null=True, blank=True)
    scheme = models.FloatField(default=0, null=True, blank=True, help_text='data into percentage %')
    no_of_pieces = models.PositiveIntegerField(null=True, blank=True)
    vendor_product = models.ForeignKey(ProductVendorMapping, related_name='vendor_products', null=True, blank=True,
                                       on_delete=models.CASCADE)
    price = models.FloatField(verbose_name='Brand To Gram Price')
    per_unit_price = models.FloatField(default=0, null=True, blank=True)
    is_grn_done = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Select Product"
        unique_together = ('cart', 'cart_product')

    def __str__(self):
        return self.cart_product.product_name

    @property
    def tax_percentage(self):
        """
            Get tax percentage for product
        """
        return self._tax_percentage if self._tax_percentage else '-'

    @tax_percentage.setter
    def tax_percentage(self, value):
        """
            Set product tax percentage for cart
        """
        self._tax_percentage = value

    @property
    def qty(self):
        """
            Qty of product added
        """
        return int(self.no_of_pieces) if self.vendor_product else int(
            int(self.cart_product.product_inner_case_size) * int(self.cart_product.product_case_size) * float(
                self.number_of_cases))

    @property
    def total_price(self):
        """
            Total price of this product added in cart
        """
        if self.vendor_product:
            piece_price = self.vendor_product.product_price
            pack_price = self.vendor_product.product_price_pack
            return float(self.no_of_pieces) * float(piece_price) if piece_price else float(self.no_of_pieces) * float(
                pack_price)
        return float(self.qty) * float(self.price)

    @property
    def gf_code(self):
        return self.cart_product.product_gf_code

    @property
    def no_of_cases(self):
        """
            No of cases of product added to cart
        """
        return (int(self.no_of_pieces) // int(
            self.vendor_product.case_size)) if self.vendor_product else self.number_of_cases

    @property
    def total_no_of_pieces(self):
        """
            Total no of pieces of cart product
        """
        return int(self.no_of_pieces) if self.vendor_product else self.qty

    @property
    def sub_total(self):
        """
            Cart product subtotal
        """
        if self.vendor_product:
            piece_price = self.vendor_product.product_price
            pack_price = self.vendor_product.product_price_pack
            return round(float(self.qty) * float(piece_price), 2) if piece_price else round(
                float(self.qty) * (float(pack_price) / float(self.vendor_product.case_size)), 2)
        return self.total_price

    @property
    def sku(self):
        """
            Cart product SKU number
        """
        return self.cart_product.product_sku

    @property
    def mrp(self):
        """
            Product mrp
        """
        return round(self.vendor_product.product_mrp, 2) if self.vendor_product else '-'

    def case_sizes(self):
        """
            Case size for product and vendor
        """
        return self.vendor_product.case_size if self.vendor_product else self.cart_product.product_case_size

    def calculate_tax_percentage(self):
        """
            Cart Product Tax Percentage
        """
        tax_percentage = [field.tax.tax_percentage for field in self.cart_product.product_pro_tax.all()]
        return sum(tax_percentage)

    def per_unit_prices(self):
        """
            Price of one piece of product
        """
        piece_price = self.vendor_product.product_price
        pack_price = self.vendor_product.product_price_pack
        per_unit_price = piece_price if piece_price else (
            round(float(pack_price) / float(self.vendor_product.case_size), 6) if pack_price else None)
        return per_unit_price

    def brand_to_gram_price_units(self):
        """
            Price unit, per pack or per piece
        """
        return self.vendor_product.brand_to_gram_price_unit if self.vendor_product else '-'

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # Tax Percentage
            if not self.tax_percentage or self.tax_percentage == "-":
                self.tax_percentage = self.calculate_tax_percentage()
            # Map To Vendor Product
            supplier, product, price = self.cart.supplier_name, self.cart_product, self.price
            product_vendor = ProductVendorMapping.objects.filter(vendor=supplier, product=product)

            if product_vendor.filter(product_price=price, status=True).exists():
                self.vendor_product = product_vendor.filter(product_price=price, status=True).last()
            elif product_vendor.filter(product_price_pack=price, status=True).exists():
                self.vendor_product = product_vendor.filter(product_price_pack=price, status=True).last()
            else:
                product_vendor_obj = product_vendor.last()
                mrp, case_size, unit = None, None, None
                if product_vendor_obj:
                    mrp, case_size, unit = product_vendor_obj.product_mrp, product_vendor_obj.case_size, \
                                           product_vendor_obj.brand_to_gram_price_unit
                self.vendor_product = vendor_product_mapping(supplier, product.id, price, mrp, case_size, unit)
            self.per_unit_price = self.per_unit_prices()
            self.case_size = self.case_sizes()
            super(CartProductMapping, self).save(*args, **kwargs)


class Order(BaseOrder):
    ordered_cart = models.OneToOneField(Cart, related_name='order_cart_mapping', on_delete=models.CASCADE)
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


class GRNOrder(BaseShipment):  # Order Shipment
    order = models.ForeignKey(Order, verbose_name='PO Number', related_name='order_grn_order', on_delete=models.CASCADE,
                              null=True, blank=True)
    invoice_no = models.CharField(max_length=255)
    invoice_date = models.DateField(null=True)
    invoice_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')
    tcs_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')
    # e_way_bill_no = models.CharField(max_length=255, blank=True, null=True)
    # e_way_bill_document = models.FileField(null=True,blank=True)
    grn_id = models.CharField(max_length=255, null=True, blank=True)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_grn_order', null=True,
                                         blank=True, on_delete=models.CASCADE)
    grn_date = models.DateField(auto_now_add=True)
    # brand_invoice = models.FileField(null=True,blank=True,upload_to='brand_invoice')
    products = models.ManyToManyField(Product, through='GRNOrderProductMapping')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.grn_id)

    @property
    def warehouse(self):
        gf_shop = self.order.ordered_cart.gf_shipping_address.shop_name
        prm_obj = ParentRetailerMapping.objects.select_related(
            'parent', 'parent__shop_type', 'retailer', 'retailer__shop_type').filter(
            parent=gf_shop, status=True, retailer__shop_type__shop_type='sp', retailer__status=True).\
            only('id', 'parent', 'parent__shop_name', 'parent__shop_type', 'parent__status', 'retailer__shop_name',
                 'retailer__status', 'retailer__shop_type', 'retailer__shop_type__shop_type', 'retailer__id').last()
        return prm_obj.retailer if prm_obj else None

    def clean(self):
        super(GRNOrder, self).clean()
        today = datetime.date.today()

        if float(self.invoice_amount) <= 0:
            raise ValidationError(_("Invoice Amount must be positive"))

        if self.invoice_date and self.invoice_date > today:
            raise ValidationError(_("Invoice Date must not be greater than today"))

    class Meta:
        verbose_name = _("View GRN Detail")
        verbose_name_plural = _("View GRN Details")


class Document(models.Model):
    grn_order = models.ForeignKey(GRNOrder, related_name='grn_order_images', null=True, blank=True,
                                  on_delete=models.CASCADE)
    document_number = models.CharField(max_length=255, null=True, blank=True)
    document_image = models.FileField(null=True, blank=True, upload_to='brand_invoice')


class GRNOrderProductMapping(models.Model):
    grn_order = models.ForeignKey(GRNOrder, related_name='grn_order_grn_order_product', null=True, blank=True,
                                  on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='product_grn_order_product', null=True, blank=True,
                                on_delete=models.CASCADE)
    product_invoice_price = models.FloatField(default=0)
    product_invoice_qty = models.PositiveIntegerField(default=0)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=False)
    delivered_qty = models.PositiveIntegerField(default=0)
    available_qty = models.PositiveIntegerField(default=0)
    returned_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_grn_order_product',
                                         null=True, blank=True, on_delete=models.CASCADE)
    vendor_product = models.ForeignKey(ProductVendorMapping, related_name='vendor_grn_products', null=True, blank=True,
                                       on_delete=models.CASCADE)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    barcode_id = models.CharField(max_length=15, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str('')

    class Meta:
        verbose_name = _("GRN Product Detail")

    @property
    def po_product_quantity(self):
        return self.grn_order.order.ordered_cart.cart_list.filter(
            cart_product=self.product).last().qty if self.product else ''

    @property
    def po_product_price(self):
        if self.vendor_product:
            if self.vendor_product.product_price:
                return self.vendor_product.product_price
            else:
                return self.vendor_product.product_price_pack
        return self.grn_order.order.ordered_cart.cart_list.filter(
            cart_product=self.product).last().price if self.product else ''

    @property
    def already_grned_product(self):
        already_grn = self.product.product_grn_order_product.filter(grn_order__order=self.grn_order.order).aggregate(
            Sum('delivered_qty')).get('delivered_qty__sum')
        return already_grn if already_grn else 0

    @property
    def warehouse(self):
        gf_shop = self.grn_order.order.ordered_cart.gf_shipping_address.shop_name
        prm_obj = ParentRetailerMapping.objects.select_related(
            'parent', 'parent__shop_type', 'retailer', 'retailer__shop_type').filter(
            parent=gf_shop, status=True, retailer__shop_type__shop_type='sp', retailer__status=True). \
            only('id', 'parent', 'parent__shop_name', 'parent__shop_type', 'parent__status', 'retailer__shop_name',
                 'retailer__status', 'retailer__shop_type', 'retailer__shop_type__shop_type', 'retailer__id').last()
        return prm_obj.retailer if prm_obj else None

    @property
    def zone_id(self):
        gf_shop = self.grn_order.order.ordered_cart.gf_shipping_address.shop_name
        prm_obj = ParentRetailerMapping.objects.select_related(
            'parent', 'parent__shop_type', 'retailer', 'retailer__shop_type').filter(
            parent=gf_shop, status=True, retailer__shop_type__shop_type='sp', retailer__status=True). \
            only('id', 'parent', 'parent__shop_name', 'parent__shop_type', 'parent__status', 'retailer__shop_name',
                 'retailer__status', 'retailer__shop_type', 'retailer__shop_type__shop_type', 'retailer__id').last()
        whc_assrtment_obj = WarehouseAssortment.objects.select_related(
            'warehouse', 'warehouse__shop_owner', 'warehouse__shop_type', 'warehouse__shop_type__shop_sub_type',
            'product', 'zone').filter(warehouse=prm_obj.retailer, product=self.product.parent_product).last()
        return whc_assrtment_obj.zone if whc_assrtment_obj else None

    @property
    def zone(self):
        gf_shop = self.grn_order.order.ordered_cart.gf_shipping_address.shop_name
        prm_obj = ParentRetailerMapping.objects.select_related('retailer', 'retailer__shop_type').filter(
            parent=gf_shop, status=True, retailer__shop_type__shop_type='sp', retailer__status=True).last()
        whc_assrtment_obj = WarehouseAssortment.objects.select_related('product', 'warehouse').filter(
            warehouse=prm_obj.retailer, product=self.product.parent_product).last()
        return str(whc_assrtment_obj.zone) if whc_assrtment_obj else "-"

    @property
    def already_returned_product(self):
        already_returned = self.product.product_grn_order_product.filter(
            grn_order__order=self.grn_order.order).aggregate(Sum('returned_qty')).get('returned_qty__sum')
        return already_returned if already_returned else 0

    @property
    def ordered_qty(self):
        return self.grn_order.order.ordered_cart.cart_list.last(cart_product=self.product).qty if self.product else ''

    @property
    def best_before_year(self):
        return 0

    @property
    def best_before_month(self):
        return 0

    @property
    def product_mrp(self):
        return self.vendor_product.product_mrp if self.vendor_product else '-'

    def clean(self):
        super(GRNOrderProductMapping, self).clean()
        self.already_grn = self.delivered_qty
        if self.delivered_qty and float(self.po_product_price) != float(self.product_invoice_price):
            raise ValidationError(_("Po_Product_Price and Po_Invoice_Price are not similar"))

    def save(self, *args, **kwargs):
        if not self.vendor_product and self.grn_order.order.ordered_cart.cart_list.filter(
                cart_product=self.product).last().vendor_product:
            self.vendor_product = self.grn_order.order.ordered_cart.cart_list.filter(
                cart_product=self.product).last().vendor_product
        if self.expiry_date and not self.batch_id and self.delivered_qty:
            self.batch_id = '{}{}'.format(self.product.product_sku, self.expiry_date.strftime('%d%m%y'))
        if self.barcode_id is None:
            if len(str(self.product_id)) == 1:
                product_id = '0000' + str(self.product_id)
            elif len(str(self.product_id)) == 2:
                product_id = '000' + str(self.product_id)
            elif len(str(self.product_id)) == 3:
                product_id = '00' + str(self.product_id)
            elif len(str(self.product_id)) == 4:
                product_id = '0' + str(self.product_id)
            else:
                product_id = str(self.product_id)
            if self.expiry_date is None:
                expiry_date = '000000'
            else:
                expiry_date = datetime.datetime.strptime(str(self.expiry_date), '%Y-%m-%d').strftime('%d%m%y')
            self.barcode_id = str("2" + product_id + str(expiry_date))
        super(GRNOrderProductMapping, self).save(*args, **kwargs)


class BrandNote(models.Model):
    NOTE_TYPE_CHOICES = (
        ("debit_note", "Debit Note"),
    )

    brand_note_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='Debit Note ID')
    grn_order = models.ForeignKey(GRNOrder, related_name='grn_order_brand_note', null=True, blank=True,
                                  on_delete=models.CASCADE)
    note_type = models.CharField(max_length=255, choices=NOTE_TYPE_CHOICES, default='debit_note')
    amount = models.FloatField(default=0)
    last_modified_by = models.ForeignKey(get_user_model(), related_name='last_modified_user_brand_note', null=True,
                                         blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    def __str__(self):
        return self.brand_note_id

    class Meta:
        verbose_name = _("Debit Note")
        verbose_name_plural = _("Debit Notes")


class OrderedProductReserved(models.Model):
    RESERVED = "reserved"
    ORDERED = "ordered"
    FREE = "free"
    RESERVE_STATUS = (
        (RESERVED, "Reserved"),
        (ORDERED, "Ordered"),
        (FREE, "Free"),
    )
    order_product_reserved = models.ForeignKey(GRNOrderProductMapping,
                                               related_name='retiler_order_product_order_product_reserved', null=True,
                                               blank=True, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='retiler_product_order_product_reserved', null=True, blank=True,
                                on_delete=models.CASCADE)
    cart = models.ForeignKey(GramMapperRetailerCart, related_name='retiler_ordered_retailer_cart', null=True,
                             blank=True, on_delete=models.CASCADE)
    reserved_qty = models.PositiveIntegerField(default=0)
    order_reserve_end_time = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    reserve_status = models.CharField(max_length=100, choices=RESERVE_STATUS, default=RESERVED)

    def save(self):
        self.order_reserve_end_time = timezone.now() + timedelta(minutes=int(settings.BLOCKING_TIME_IN_MINUTS))
        super(OrderedProductReserved, self).save()

    def __str__(self):
        return str(self.order_reserve_end_time)

    class Meta:
        verbose_name = _("Ordered Product Reserved")
        verbose_name_plural = _("Ordered Product Reserved")


class PickList(models.Model):
    order = models.ForeignKey(GramMapperRetailerOrder, related_name='pick_list_order', null=True, blank=True,
                              on_delete=models.CASCADE)
    cart = models.ForeignKey(GramMapperRetailerCart, related_name='pick_list_cart', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Pick List")
        verbose_name_plural = _("Pick List")


class PickListItems(models.Model):
    pick_list = models.ForeignKey(PickList, related_name='pick_list_items_pick_list', on_delete=models.CASCADE)
    grn_order = models.ForeignKey(GRNOrder, related_name='pick_list_cart', on_delete=models.CASCADE,
                                  verbose_name='GRN No')
    product = models.ForeignKey(Product, related_name='pick_product', null=True, blank=True, on_delete=models.CASCADE)
    pick_qty = models.PositiveIntegerField(default=0)
    return_qty = models.PositiveIntegerField(default=0)
    damage_qty = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class VendorShopMapping(models.Model):
    vendor = models.OneToOneField(Vendor, related_name='vendor_shop_mapping', on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, related_name='shop_vendor_mappings', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
