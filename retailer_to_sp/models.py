import datetime
import logging
import csv
import codecs
import math
from decimal import Decimal

from django.db import models, transaction
from django.db.models import F, FloatField, Sum, Func, Q, Case, Value, When, Count
from django.db.models.signals import post_save
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.dispatch import receiver
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html_join, format_html
from model_utils import Choices
from django.core.validators import MinValueValidator, MaxValueValidator

from celery.task import task
from accounts.middlewares import get_current_user
from retailer_backend import common_function as CommonFunction
from retailer_backend.validators import PercentageValidator
from .bulk_order_clean import bulk_order_validation
from .common_function import reserved_args_json_data
from .utils import (order_invoices, order_shipment_status, order_shipment_amount, order_shipment_details_util,
                    order_shipment_date, order_delivery_date, order_cash_to_be_collected, order_cn_amount,
                    order_damaged_amount, order_delivered_value, order_shipment_status_reason,
                    picking_statuses, picker_boys, picklist_ids, picklist_refreshed_at, qc_areas, zones, qc_desks,
                    qc_executives)

from addresses.models import Address

from wms.models import PickupBinInventory, Pickup, BinInventory, InventoryType, InventoryState, Bin, Zone, QCArea, \
    BaseTimestampUserModel, Crate
from wms.common_functions import common_on_return_and_partial, \
    get_expiry_date, OrderManagement, product_batch_inventory_update_franchise, get_stock
from brand.models import Brand
from otp.sms import SendSms
from products.models import Product, ProductPrice, Repackaging, SuperStoreProductPrice
from shops.models import Shop
from accounts.models import UserWithName, User
from coupon.models import Coupon, CusotmerCouponUsage
from retailer_backend import common_function
from global_config.views import get_config, get_config_fofo_shop

today = datetime.datetime.today()

logger = logging.getLogger(__name__)

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')

ITEM_STATUS = (
    ("partially_delivered", "Partially Delivered"),
    ("delivered", "Delivered"),
)

NOTE_TYPE_CHOICES = (
    ("debit_note", "Debit Note"),
    ("credit_note", "Credit Note"),
)

PAYMENT_MODE_CHOICES = (
    ("cash_on_delivery", "Cash On Delivery"),
    ("neft", "NEFT"),
    ("credit", "credit")
)
AUTO = 'AUTO'
RETAIL = 'RETAIL'
BULK = 'BULK'
DISCOUNTED = 'DISCOUNTED'
BASIC = 'BASIC'
ECOM = 'EC0M'
SUPERSTORE = 'SUPERSTORE'

BULK_ORDER_STATUS = (
    (AUTO, 'Auto'),
    (RETAIL, 'Retail'),
    (BULK, 'Bulk'),
    (DISCOUNTED, 'Discounted'),
)
MESSAGE_STATUS = (
    ("pending", "Pending"),
    ("resolved", "Resolved"),
)
SELECT_ISSUE = (
    ("Cancellation", "cancellation"),
    ("Return", "return"),
    ("Others", "others")
)

PAYMENT_STATUS = (
    ('PENDING', 'Pending'),
    ('PARTIALLY_PAID', 'Partially_paid'),
    ('PAID', 'Paid'),
)

PAYMENT_MODE = (
    ('CREDIT', 'Credit'),
    ('INSTANT_PAYMENT', 'Instant_payment'),
)

CART_TYPES = (
    (RETAIL, 'Retail'),
    (BULK, 'Bulk'),
    (DISCOUNTED, 'Discounted'),
    (BASIC, 'Basic'),
    (ECOM, 'Ecom'),
    (SUPERSTORE, 'Super Store')
)


def generate_picklist_id(pincode):
    if PickerDashboard.objects.exists():
        last_picking = PickerDashboard.objects.last()
        picklist_id = last_picking.picklist_id
        new_picklist_id = "PIK/" + str(pincode)[-2:] + "/" + str(int(picklist_id.split('/')[2]) + 1)
    else:
        new_picklist_id = "PIK/" + str(pincode)[-2:] + "/" + str(1)

    return new_picklist_id


class RoundAmount(Func):
    function = "ROUND"
    template = "%(function)s(%(expressions)s::numeric, 0)"


class Cart(models.Model):
    ACTIVE = "active"
    PENDING = "pending"
    DELETED = "deleted"
    ORDERED = "ordered"
    ORDER_SHIPPED = "order_shipped"
    PARTIALLY_DELIVERED = "partially_delivered"
    DELIVERED = "delivered"
    CLOSED = "closed"
    RESERVED = "reserved"
    CART_STATUS = (
        (ACTIVE, "Active"),
        (PENDING, "Pending"),
        (DELETED, "Deleted"),
        (ORDERED, "Ordered"),
        (ORDER_SHIPPED, "Dispatched"),
        (PARTIALLY_DELIVERED, "Partially Delivered"),
        (DELIVERED, "Delivered"),
        (CLOSED, "Closed"),
        (RESERVED, "Reserved")
    )
    cart_no = models.CharField(max_length=255, null=True, unique=True)
    order_id = models.CharField(max_length=255, null=True, blank=True)
    seller_shop = models.ForeignKey(
        Shop, related_name='rt_seller_shop_cart',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    buyer_shop = models.ForeignKey(
        Shop, related_name='rt_buyer_shop_cart',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    buyer = models.ForeignKey(User, related_name='rt_buyer_cart', null=True, blank=True, on_delete=models.DO_NOTHING)
    cart_status = models.CharField(
        max_length=200, choices=CART_STATUS,
        null=True, blank=True, db_index=True
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_cart',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    offers = JSONField(null=True, blank=True)
    # cart_coupon_error_msg = models.CharField(
    #     max_length=255, null=True,
    #     blank=True, editable=False
    # )
    approval_status = models.BooleanField(default=False, null=True)
    cart_type = models.CharField(
        max_length=50, choices=CART_TYPES, null=True, default=RETAIL)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    redeem_points = models.IntegerField(default=0)
    redeem_factor = models.FloatField(default=0)

    class Meta:
        verbose_name = 'Order Items Detail'
        permissions = [("can_approve_bulk_type", "Can approve Bulk type orders")]
    
    def __str__(self):
        return "{}".format(self.id)

    @property
    def subtotal(self):
        try:
            if self.cart_type in ['BASIC', 'ECOM']:
                return round(self.rt_cart_list.aggregate(
                    subtotal_sum=Sum(F('selling_price') * F('qty'),
                                     output_field=FloatField()))['subtotal_sum'], 2)
            else:
                return round(self.rt_cart_list.aggregate(
                    subtotal_sum=Sum(F('cart_product_price__selling_price') * F('no_of_pieces'),
                                     output_field=FloatField()))['subtotal_sum'], 2)
        except:
            return None

    @property
    def redeem_points_value(self):
        redeem_points_value = 0
        if self.redeem_factor:
            redeem_points_value = round(self.redeem_points / self.redeem_factor, 2)
        return redeem_points_value

    @property
    def offer_discount(self):
        return round(float(self.subtotal) - float(self.order_amount) - float(self.redeem_points_value), 2)

    @property
    def order_amount_after_discount(self):
        item_effective_total = 0
        for m in self.rt_cart_list.all():
            item_effective_total += (m.item_effective_prices * float(m.no_of_pieces))
        order_amount = round(float(item_effective_total), 2)
        return order_amount

    @property
    def order_amount(self):
        item_effective_total = 0
        for m in self.rt_cart_list.all():
            item_effective_total += (m.item_effective_prices * float(m.no_of_pieces))
        redeem_points_value = 0
        if self.redeem_factor:
            redeem_points_value = round(self.redeem_points / self.redeem_factor, 2)
        # else:
        #     for m in self.rt_cart_list.all():
        #         if m.cart_product_price:
        #             item_effective_total += (m.cart_product_price.price_to_retailer * m.no_of_pieces)
        order_amount = round(float(item_effective_total) - float(redeem_points_value), 2)
        return order_amount

    @property
    def mrp_subtotal(self):
        try:
            if self.cart_type in ['BASIC', 'ECOM']:
                return round(self.rt_cart_list.aggregate(
                    subtotal_sum=Sum(F('retailer_product__mrp') * F('no_of_pieces'), output_field=FloatField()))[
                                 'subtotal_sum'], 2)
            elif self.cart_type == 'SUPERSTORE':
                return 0.00
            else:
                return round(self.rt_cart_list.aggregate(
                    subtotal_sum=Sum(F('cart_product_price__mrp') * F('no_of_pieces'), output_field=FloatField()))[
                                 'subtotal_sum'], 2)
        except:
            return None

    @property
    def qty_sum(self):
        return self.rt_cart_list.aggregate(qty_sum=Sum('qty'))['qty_sum']

    def total_no_of_sku_pieces(self):
        return self.rt_cart_list.aggregate(no_of_pieces_sum=Sum('no_of_pieces'))['no_of_pieces_sum']

    def total_sku(self):
        return self.rt_cart_list.count()

    @property
    def no_of_pieces_sum(self):
        return self.rt_cart_list.aggregate(qty_sum=Sum('no_of_pieces'))['no_of_pieces_sum']

    def offers_applied(self):
        offers_list = []
        discount_value = 0
        shop = self.seller_shop
        cart_products = self.rt_cart_list.all()
        date = datetime.datetime.now()
        discount_sum_sku = 0
        discount_sum_brand = 0
        sum = 0
        buyer_shop = self.buyer_shop
        if cart_products:
            if self.cart_status in ['active', 'pending']:
                cart_value = 0
                for product in cart_products:
                    shop_price = product.cart_product.get_current_shop_price(self.seller_shop, self.buyer_shop)
                    cart_value += Decimal(Decimal(shop_price.get_per_piece_price(product.qty))
                                        * product.no_of_pieces) if shop_price else 0
            if self.cart_status in ['ordered']:
                cart_value = 0
                for product in cart_products:
                    price = product.cart_product_price
                    cart_value += Decimal(Decimal(price.get_per_piece_price(product.qty))
                                        * product.no_of_pieces) if price else 0

            for m in cart_products:
                if m.cart_product.get_current_shop_price(shop, buyer_shop) == None:
                    CartProductMapping.objects.filter(cart__id=self.id, cart_product__id=m.cart_product.id).delete()
                    continue
                parent_product_brand = m.cart_product.parent_product.parent_brand if m.cart_product.parent_product else None
                if parent_product_brand:
                    parent_brand = parent_product_brand.brand_parent.id if parent_product_brand.brand_parent else None
                else:
                    parent_brand = None
                product_brand_id = m.cart_product.parent_product.parent_brand.id if m.cart_product.parent_product else None
                brand_coupons = Coupon.objects.filter(coupon_type='brand', is_active=True,
                                                      expiry_date__gte=date).filter(
                    Q(rule__brand_ruleset__brand=product_brand_id) | Q(
                        rule__brand_ruleset__brand=parent_brand)).order_by('rule__cart_qualifying_min_sku_value')
                b_list = [x.coupon_name for x in brand_coupons]
                cart_coupons = Coupon.objects.filter(coupon_type='cart', is_active=True,
                                                     expiry_date__gte=date).exclude(shop__shop_type__shop_type='f').order_by(
                    'rule__cart_qualifying_min_sku_value')
                c_list = [x.coupon_name for x in cart_coupons]
                sku_qty = int(m.qty)
                sku_no_of_pieces = int(m.cart_product.product_inner_case_size) * int(m.qty)
                price = m.cart_product.get_current_shop_price(shop, buyer_shop)
                sku_ptr = price.get_per_piece_price(sku_qty)
                coupon_times_used = CusotmerCouponUsage.objects.filter(shop=buyer_shop, product=m.cart_product,
                                                                       created_at__date=date.date()).count() if CusotmerCouponUsage.objects.filter(
                    shop=buyer_shop, product=m.cart_product, created_at__date=date.date()) else 0
                for n in m.cart_product.purchased_product_coupon.filter(rule__is_active=True,
                                                                        rule__expiry_date__gte=date,
                                                                        ).exclude(rule__coupon_ruleset__shop__shop_type__shop_type='f'):
                    for o in n.rule.coupon_ruleset.filter(is_active=True, expiry_date__gte=date).exclude(shop__shop_type__shop_type='f'):
                        if o.rule.cart_qualifying_min_sku_value and not o.rule.cart_qualifying_min_sku_item:
                            if cart_value < o.rule.cart_qualifying_min_sku_value:
                                continue
                        if o.limit_per_user_per_day > coupon_times_used:
                            if n.rule.discount_qty_amount > 0:
                                if sku_qty >= n.rule.discount_qty_step:
                                    free_item = n.free_product.product_name
                                    discount_qty_step_multiple = int((sku_qty) / n.rule.discount_qty_step)
                                    free_item_amount = int((n.rule.discount_qty_amount) * discount_qty_step_multiple)
                                    sum += (sku_ptr * sku_no_of_pieces)
                                    offers_list.append(
                                        {'type': 'free', 'sub_type': 'discount_on_product', 'coupon_id': o.id,
                                         'coupon': o.coupon_name, 'discount_value': 0, 'coupon_code': o.coupon_code,
                                         'item': m.cart_product.product_name, 'item_sku': m.cart_product.product_sku,
                                         'item_id': m.cart_product.id, 'free_item': free_item,
                                         'free_item_amount': free_item_amount, 'coupon_type': 'catalog',
                                         'discounted_product_subtotal': (sku_ptr * sku_no_of_pieces),
                                         'discounted_product_subtotal_after_sku_discount': (sku_ptr * sku_no_of_pieces),
                                         'brand_id': m.cart_product.product_brand.id,
                                         'applicable_brand_coupons': b_list, 'applicable_cart_coupons': c_list})
                            elif (n.rule.discount_qty_step >= 1) and (n.rule.discount != None):
                                if sku_qty >= n.rule.discount_qty_step:
                                    if n.rule.discount.is_percentage == False:
                                        discount_value = n.rule.discount.discount_value
                                    elif n.rule.discount.is_percentage == True and (n.rule.discount.max_discount == 0):
                                        discount_value = round(
                                            ((n.rule.discount.discount_value / 100) * sku_no_of_pieces * sku_ptr), 2)
                                    elif n.rule.discount.is_percentage == True and (n.rule.discount.max_discount > (
                                            (n.rule.discount.discount_value / 100) * (sku_no_of_pieces * sku_ptr))):
                                        discount_value = round(
                                            ((n.rule.discount.discount_value / 100) * sku_no_of_pieces * sku_ptr), 2)
                                    elif n.rule.discount.is_percentage == True and (n.rule.discount.max_discount < (
                                            (n.rule.discount.discount_value / 100) * (sku_no_of_pieces * sku_ptr))):
                                        discount_value = n.rule.discount.max_discount
                                    discount_sum_sku += round(discount_value, 2)
                                    discounted_product_subtotal = round((sku_no_of_pieces * sku_ptr) - discount_value,
                                                                        2)
                                    sum += discounted_product_subtotal
                                    offers_list.append(
                                        {'type': 'discount', 'sub_type': 'discount_on_product', 'coupon_id': o.id,
                                         'coupon': o.coupon_name, 'coupon_code': o.coupon_code,
                                         'item': m.cart_product.product_name, 'item_sku': m.cart_product.product_sku,
                                         'item_id': m.cart_product.id, 'discount_value': discount_value,
                                         'discount_total_sku': discount_sum_sku, 'coupon_type': 'catalog',
                                         'discounted_product_subtotal': discounted_product_subtotal,
                                         'discounted_product_subtotal_after_sku_discount': discounted_product_subtotal,
                                         'brand_id': m.cart_product.product_brand.id,
                                         'applicable_brand_coupons': b_list, 'applicable_cart_coupons': c_list})
                if not any(d['item_id'] == m.cart_product.id for d in offers_list):
                    offers_list.append({'type': 'no offer', 'sub_type': 'no offer', 'item': m.cart_product.product_name,
                                        'item_sku': m.cart_product.product_sku, 'item_id': m.cart_product.id,
                                        'discount_value': 0, 'discount_total_sku': discount_sum_sku,
                                        'coupon_type': 'catalog',
                                        'discounted_product_subtotal': round((sku_ptr * sku_no_of_pieces), 2),
                                        'discounted_product_subtotal_after_sku_discount': round(
                                            (sku_ptr * sku_no_of_pieces), 2),
                                        'brand_id': product_brand_id, 'cart_or_brand_level_discount': 0,
                                        'applicable_brand_coupons': b_list, 'applicable_cart_coupons': c_list})
            brand_coupons = Coupon.objects.filter(coupon_type='brand', is_active=True, expiry_date__gte=date).order_by(
                '-rule__cart_qualifying_min_sku_value')
            array = list(filter(lambda d: d['coupon_type'] in 'catalog', offers_list))
            discount_value_brand = 0
            brands_specific_list = []
            for brand_coupon in brand_coupons:
                brands_list = []
                brand_product_subtotals = 0
                for brand in brand_coupon.rule.brand_ruleset.filter(rule__is_active=True, rule__expiry_date__gte=date):
                    brands_list = []
                    brand_product_subtotals = 0
                    offer_brand = brand.brand
                    offer_brand_id = brand.brand.id
                    if offer_brand_id in brands_specific_list:
                        continue
                    brands_list.append(offer_brand_id)
                    brands_specific_list.append(offer_brand_id)
                    sub_brands_list = Brand.objects.filter(brand_parent_id=offer_brand_id)
                    if sub_brands_list:
                        for sub_brands in sub_brands_list:
                            brands_list.append(sub_brands.id)
                    for i in array:
                        if i['brand_id'] in brands_list:
                            brand_product_subtotals += i['discounted_product_subtotal']
                    if brand_coupon.rule.cart_qualifying_min_sku_value and not brand_coupon.rule.cart_qualifying_min_sku_item:
                        if brand_product_subtotals >= brand_coupon.rule.cart_qualifying_min_sku_value:
                            if brand_coupon.rule.discount.is_percentage == False:
                                discount_value_brand = brand_coupon.rule.discount.discount_value
                                discount_sum_brand += round(brand_coupon.rule.discount.discount_value, 2)
                                offers_list.append(
                                    {'type': 'discount', 'sub_type': 'discount_on_brand', 'coupon_id': brand_coupon.id,
                                     'coupon': brand_coupon.coupon_name, 'coupon_code': brand_coupon.coupon_code,
                                     'brand_name': offer_brand.brand_name, 'brand_id': offer_brand.id,
                                     'discount_value': discount_value_brand, 'coupon_type': 'brand',
                                     'brand_product_subtotals': brand_product_subtotals,
                                     'discount_sum_brand': discount_sum_brand})
                            elif brand_coupon.rule.discount.is_percentage == True and (
                                    brand_coupon.rule.discount.max_discount == 0 or (
                                    brand_coupon.rule.discount.max_discount >= (
                                    (brand_coupon.rule.discount.discount_value / 100) * brand_product_subtotals))):
                                discount_value_brand = round(
                                    (brand_coupon.rule.discount.discount_value / 100) * brand_product_subtotals, 2)
                                discount_sum_brand += round(discount_value_brand, 2)
                                offers_list.append(
                                    {'type': 'discount', 'sub_type': 'discount_on_brand', 'coupon_id': brand_coupon.id,
                                     'coupon': brand_coupon.coupon_name, 'coupon_code': brand_coupon.coupon_code,
                                     'brand_name': offer_brand.brand_name, 'brand_id': offer_brand.id,
                                     'discount_value': discount_value_brand, 'coupon_type': 'brand',
                                     'brand_product_subtotals': brand_product_subtotals,
                                     'discount_sum_brand': discount_sum_brand})
                            elif brand_coupon.rule.discount.is_percentage == True and (
                                    brand_coupon.rule.discount.max_discount < (
                                    (brand_coupon.rule.discount.discount_value / 100) * brand_product_subtotals)):
                                discount_value_brand = brand_coupon.rule.discount.max_discount
                                discount_sum_brand += round(brand_coupon.rule.discount.max_discount, 2)
                                offers_list.append(
                                    {'type': 'discount', 'sub_type': 'discount_on_brand', 'coupon_id': brand_coupon.id,
                                     'coupon': brand_coupon.coupon_name, 'coupon_code': brand_coupon.coupon_code,
                                     'brand_name': offer_brand.brand_name, 'brand_id': offer_brand.id,
                                     'discount_value': discount_value_brand, 'coupon_type': 'brand',
                                     'brand_product_subtotals': brand_product_subtotals,
                                     'discount_sum_brand': discount_sum_brand})
                        else:
                            brands_specific_list.pop()
            array1 = list(filter(lambda d: d['coupon_type'] in 'brand', offers_list))
            discount_value_cart = 0
            cart_coupons = Coupon.objects.filter(coupon_type='cart', is_active=True, expiry_date__gte=date).\
                exclude(shop__shop_type__shop_type='f').order_by(
                '-rule__cart_qualifying_min_sku_value')
            cart_coupon_list = []
            i = 0
            coupon_applied = False
            cart_value = float(cart_value) - float(discount_sum_sku)

            cart_items_count = self.rt_cart_list.count()
            for cart_coupon in cart_coupons:
                if cart_coupon.rule.cart_qualifying_min_sku_value and not cart_coupon.rule.cart_qualifying_min_sku_item:
                    cart_coupon_list.append(cart_coupon)
                    i += 1
                    if cart_value >= cart_coupon.rule.cart_qualifying_min_sku_value:
                        coupon_applied = True
                        if cart_coupon.rule.discount.is_percentage == False:
                            discount_value_cart = cart_coupon.rule.discount.discount_value
                            offers_list.append(
                                {'type': 'discount', 'sub_type': 'discount_on_cart', 'coupon_id': cart_coupon.id,
                                 'coupon': cart_coupon.coupon_name, 'coupon_code': cart_coupon.coupon_code,
                                 'discount_value': float(discount_value_cart), 'coupon_type': 'cart'})
                        elif cart_coupon.rule.discount.is_percentage == True and (
                                cart_coupon.rule.discount.max_discount == 0):
                            discount_value_cart = round((Decimal(cart_coupon.rule.discount.discount_value) / 100) *
                                                        Decimal(cart_value), 2)
                            offers_list.append(
                                {'type': 'discount', 'sub_type': 'discount_on_cart', 'coupon_id': cart_coupon.id,
                                 'coupon': cart_coupon.coupon_name, 'coupon_code': cart_coupon.coupon_code,
                                 'discount_value': float(discount_value_cart), 'coupon_type': 'cart'})
                        elif cart_coupon.rule.discount.is_percentage == True and (
                                round(Decimal(cart_coupon.rule.discount.max_discount)) >= (
                                Decimal(cart_coupon.rule.discount.discount_value / 100) * Decimal(cart_value))):
                            discount_value_cart = round(Decimal(cart_coupon.rule.discount.discount_value / 100) *
                                                        Decimal(cart_value), 2)
                            offers_list.append(
                                {'type': 'discount', 'sub_type': 'discount_on_cart', 'coupon_id': cart_coupon.id,
                                 'coupon': cart_coupon.coupon_name, 'coupon_code': cart_coupon.coupon_code,
                                 'discount_value': float(discount_value_cart), 'coupon_type': 'cart'})
                        elif cart_coupon.rule.discount.is_percentage == True and (
                                cart_coupon.rule.discount.max_discount < (
                                Decimal(cart_coupon.rule.discount.discount_value / 100) * Decimal(cart_value))):
                            discount_value_cart = cart_coupon.rule.discount.max_discount
                            offers_list.append(
                                {'type': 'discount', 'sub_type': 'discount_on_cart', 'coupon_id': cart_coupon.id,
                                 'coupon': cart_coupon.coupon_name, 'coupon_code': cart_coupon.coupon_code,
                                 'discount_value': float(discount_value_cart), 'coupon_type': 'cart'})
                        break

            entice_text = ''
            if coupon_applied:
                next_index = 2
            else:
                next_index = 1
            if i > 1:
                next_cart_coupon_min_value = cart_coupon_list[i - next_index].rule.cart_qualifying_min_sku_value
                next_cart_coupon_min_value_diff = round(next_cart_coupon_min_value - cart_value + discount_value_cart,
                                                        2)
                next_cart_coupon_discount = cart_coupon_list[i - next_index].rule.discount.discount_value if \
                    cart_coupon_list[i - next_index].rule.discount.is_percentage == False else (
                        str(cart_coupon_list[i - next_index].rule.discount.discount_value) + '%')
                entice_text = "Shop for Rs %s more to avail a discount of Rs %s on the entire cart" % (
                    next_cart_coupon_min_value_diff, next_cart_coupon_discount) if cart_coupon_list[
                                                                                       i - next_index].rule.discount.is_percentage == False else "Shop for Rs %s more to avail a discount of %s on the entire cart" % (
                    next_cart_coupon_min_value_diff, next_cart_coupon_discount)
                offers_list.append(
                    {'entice_text': entice_text, 'coupon_type': 'none', 'type': 'none', 'sub_type': 'none'})
            elif i == 1 and not coupon_applied:
                next_cart_coupon_min_value = cart_coupon_list[i - next_index].rule.cart_qualifying_min_sku_value
                next_cart_coupon_min_value_diff = round(Decimal(next_cart_coupon_min_value) - Decimal(cart_value), 2)
                next_cart_coupon_discount = cart_coupon_list[i - next_index].rule.discount.discount_value if \
                    cart_coupon_list[i - next_index].rule.discount.is_percentage == False else (
                        str(cart_coupon_list[i - next_index].rule.discount.discount_value) + '%')
                entice_text = "Shop for Rs %s more to avail a discount of Rs %s on the entire cart" % (
                    next_cart_coupon_min_value_diff, next_cart_coupon_discount) if cart_coupon_list[
                                                                                       i - next_index].rule.discount.is_percentage == False else "Shop for Rs %s more to avail a discount of %s on the entire cart" % (
                    next_cart_coupon_min_value_diff, next_cart_coupon_discount)
                offers_list.append(
                    {'entice_text': entice_text, 'coupon_type': 'none', 'type': 'none', 'sub_type': 'none'})
            else:
                entice_text = ''
                offers_list.append(
                    {'entice_text': entice_text, 'coupon_type': 'none', 'type': 'none', 'sub_type': 'none'})

            if discount_sum_brand < discount_value_cart:
                for product in cart_products:
                    for i in array:
                        if product.cart_product.id == i['item_id']:
                            discounted_price_subtotal = float(round(
                                ((Decimal(i['discounted_product_subtotal']) / Decimal(cart_value)) * Decimal(discount_value_cart)), 2))
                            i.update({'cart_or_brand_level_discount': discounted_price_subtotal})
                            discounted_product_subtotal = float(round(
                                Decimal(i['discounted_product_subtotal']) - Decimal(discounted_price_subtotal), 2))
                            i.update({'discounted_product_subtotal': discounted_product_subtotal})
                            offers_list[:] = [coupon for coupon in offers_list if coupon.get('coupon_type') != 'brand']
            else:
                for product in cart_products:
                    for i in array:
                        for j in array1:
                            brand_parent = product.cart_product.product_brand.brand_parent.id if product.cart_product.product_brand.brand_parent else None
                            if product.cart_product.id == i['item_id'] and product.cart_product.product_brand.id == j[
                                'brand_id'] or product.cart_product.id == i['item_id'] and brand_parent == j[
                                'brand_id']:
                                discounted_price_subtotal = float(round(((i['discounted_product_subtotal'] / j[
                                    'brand_product_subtotals']) * j['discount_value']), 2))
                                i.update({'cart_or_brand_level_discount': discounted_price_subtotal})
                                discounted_product_subtotal = float(round(
                                    i['discounted_product_subtotal'] - discounted_price_subtotal, 2))
                                i.update({'discounted_product_subtotal': discounted_product_subtotal})
                                offers_list[:] = [coupon for coupon in offers_list if
                                                  coupon.get('coupon_type') != 'cart']

        return offers_list

    def save(self, *args, **kwargs):
        if self.cart_status == self.ORDERED:
            if self.cart_type not in ['BASIC', 'ECOM', 'SUPERSTORE']:
                for cart_product in self.rt_cart_list.all():
                    cart_product.get_cart_product_price(self.seller_shop.id, self.buyer_shop.id)
        super().save(*args, **kwargs)

    @property
    def buyer_contact_no(self):
        return self.buyer.phone_number if self.buyer else self.buyer_shop.shop_owner.phone_number

    @property
    def seller_contact_no(self):
        return self.seller_shop.shop_owner.phone_number

    @property
    def date(self):
        return self.created_at.date()

    @property
    def time(self):
        return self.created_at.time()


class BulkOrder(models.Model):
    cart = models.OneToOneField(Cart, related_name='rt_bulk_cart_list', null=True,
                                on_delete=models.DO_NOTHING
                                )
    seller_shop = models.ForeignKey(
        Shop, related_name='rt_bulk_seller_shop_cart',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    buyer_shop = models.ForeignKey(
        Shop, related_name='rt_bulk_buyer_shop_cart',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    billing_address = models.ForeignKey(
        Address, related_name='rt_billing_address_bulk_order',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    shipping_address = models.ForeignKey(
        Address, related_name='rt_shipping_address_bulk_order',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    order_type = models.CharField(max_length=50, choices=BULK_ORDER_STATUS[1:], null=True)
    cart_products_csv = models.FileField(
        upload_to='retailer/sp/cart_products_csv',
        null=True, blank=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.cart.rt_order_cart_mapping.order_no

    @property
    def cart_products_sample_file(self):
        if (
                self.cart_products_csv
                and hasattr(self.cart_products_csv, 'url')
        ):
            url = """<h3><a href="%s" target="_blank">
                    Download Products List</a></h3>""" % \
                  (
                      reverse(
                          'admin:cart_products_mapping',
                          args=(self.seller_shop_id,)
                      )
                  )
        else:
            url = """<h3><a href="#">Download Products List</a></h3>"""
        return url

    def cart_product_list_status(self, error_dict):
        order_status_info = []
        info_logger.info(f"[retailer_to_sp:models.py:BulkOrder]-cart_product_list_status function called")
        error_dict[str('cart_id')] = str(self.cart_id)
        order_status_info.extend([error_dict])
        if self.order_type == 'DISCOUNTED':
            status = "Discounted Order"
        else:
            status = "Bulk Order"
        url = f"""<h2 style="color:blue;"><a href="%s" target="_blank">
                            Download {status} List Status</a></h2>""" % \
              (
                  reverse(
                      'admin:cart_products_list_status',
                      args=(order_status_info)
                  )
              )
        return url

    def clean(self, *args, **kwargs):
        if self.cart_products_csv:
            availableQuantity, error_dict = \
                bulk_order_validation(self.cart_products_csv, self.order_type,
                                      self.seller_shop, self.buyer_shop)
            info_logger.info(f"Available_Qty_of_Ordered_SKUs:{availableQuantity}")
            if len(error_dict) > 0:
                if self.cart_products_csv and self.order_type:
                    self.save()
                    error_logger.info(f"Order can't placed for SKUs:"
                                      f"{error_dict}")
                    raise ValidationError(mark_safe(f"Order can't placed for some SKUs, Please click the "
                                                    f"below Link for seeing the status"
                                                    f"{self.cart_product_list_status(error_dict)}"))
            else:
                super(BulkOrder, self).clean(*args, **kwargs)

    @property
    def cart_offers(self):
        if self.cart.cart_type != 'DISCOUNTED':
            offer_list = self.cart.offers_applied()
        else:
            offer_list = []
            for item in self.cart.rt_cart_list.all():
                product_total = float(item.no_of_pieces) * float(item.item_effective_prices)
                offer = {
                    "coupon_type": "catalog",
                    "type": "none",
                    "available_type": "none",
                    'item_id': item.cart_product_id,
                    'product_subtotal': product_total,
                    'discounted_product_subtotal': product_total
                }
                offer_list.append(offer)
        return offer_list


    def save(self, *args, **kwargs):
        if self.pk is None:
            self.cart = Cart.objects.create(seller_shop=self.seller_shop, buyer_shop=self.buyer_shop,
                                            cart_status='ordered', cart_type=self.order_type)
            super().save(*args, **kwargs)


@receiver(post_save, sender=BulkOrder)
def create_bulk_order(sender, instance=None, created=False, **kwargs):
    info_logger.info("Post save for Bulk Order called")
    with transaction.atomic():
        if created:
            products_available = {}
            if instance.cart_products_csv:
                reader = csv.reader(codecs.iterdecode(instance.cart_products_csv,
                                                      'utf-8', errors='ignore'))

                rows = [row for id, row in enumerate(reader) if id]
                for row in rows:
                    product = Product.objects.get(product_sku=row[0])
                    product_price = product.get_current_shop_price(instance.seller_shop,
                                                                   instance.buyer_shop)
                    ordered_qty = int(row[2])
                    ordered_pieces = ordered_qty * int(product.product_inner_case_size)

                    shop = Shop.objects.filter(id=instance.seller_shop_id).last()
                    inventory_type = InventoryType.objects.filter(inventory_type='normal').last()
                    product_qty_dict = get_stock(shop, inventory_type, [product.id])

                    available_quantity = 0
                    if product_qty_dict.get(product.id) is not None:
                        available_quantity = product_qty_dict[product.id]

                    product_available = int(
                        int(available_quantity) / int(product.product_inner_case_size))

                    if product_available >= ordered_qty:
                        products_available[product.id] = ordered_pieces
                        discounted_price = 0
                        if instance.order_type == 'DISCOUNTED':
                            discounted_price = float(row[3])
                        try:
                            CartProductMapping.objects.create(cart=instance.cart, cart_product_id=product.id,
                                                              qty=ordered_qty,
                                                              no_of_pieces=ordered_pieces,
                                                              cart_product_price=product_price,
                                                              discounted_price=discounted_price)
                        except Exception as error:
                            error_logger.info(f"error while creating CartProductMapping in "
                                              f"Bulk Order post_save method {error}")
                    else:
                        continue

            if len(products_available) > 0:
                reserved_args = reserved_args_json_data(instance.seller_shop.id, instance.cart.cart_no,
                                                        products_available, 'reserved', None, None)
                info_logger.info(f"reserved_bulk_order:{reserved_args}")
                OrderManagement.create_reserved_order(reserved_args)
                info_logger.info("reserved_bulk_order_success")
                instance.cart.offers = instance.cart_offers
                instance.cart.save()
                order, _ = Order.objects.get_or_create(ordered_cart=instance.cart)
                order.ordered_cart = instance.cart
                order.seller_shop = instance.seller_shop
                order.buyer_shop = instance.buyer_shop
                order.billing_address = instance.billing_address
                order.shipping_address = instance.shipping_address
                user = get_current_user()
                order.ordered_by = user
                order.last_modified_by = user
                order.received_by = user
                order.order_status = 'ordered'
                order.save()
                reserved_args = reserved_args_json_data(instance.seller_shop.id, instance.cart.cart_no,
                                                        None, 'ordered', order.order_status, order.order_no)
                sku_id = [i.cart_product.id for i in instance.cart.rt_cart_list.all()]
                info_logger.info(f"ordered_bulk_order:{reserved_args}")
                OrderManagement.release_blocking(reserved_args, sku_id)
                info_logger.info("ordered_bulk_order_success")
            else:
                error_logger.info(f"No products available for which order can be placed.")


class CartProductMapping(models.Model):
    cart = models.ForeignKey(Cart, related_name='rt_cart_list', null=True,
                             on_delete=models.DO_NOTHING
                             )
    cart_product = models.ForeignKey(
        Product, related_name='rt_cart_product_mapping', null=True,
        on_delete=models.DO_NOTHING
    )
    retailer_product = models.ForeignKey(
        "pos.RetailerProduct", related_name='rt_cart_retailer_product', null=True,
        on_delete=models.DO_NOTHING
    )
    product_type = models.IntegerField(choices=((0, 'Free'), (1, 'Purchased')), default=1)
    cart_product_price = models.ForeignKey(
        ProductPrice, related_name='rt_cart_product_price_mapping',
        on_delete=models.DO_NOTHING, null=True, blank=True
    )
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    qty = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    no_of_pieces = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    qty_error_msg = models.CharField(
        max_length=255, null=True,
        blank=True, editable=False
    )
    capping_error_msg = models.CharField(
        max_length=255, null=True,
        blank=True, editable=False
    )
    effective_price = models.FloatField(default=0)
    discounted_price = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)
    qty_conversion_unit = models.ForeignKey("pos.MeasurementUnit", related_name='rt_unit_cart_mapping',
                                            null=True, on_delete=models.DO_NOTHING)

    def __str__(self):
        return self.cart_product.product_name if self.cart_product else self.retailer_product.name

    @property
    def product_case_size(self):
        return 1 if self.retailer_product else self.cart_product.product_case_size.product_case_size

    @property
    def product_inner_case_size(self):
        return 1 if self.retailer_product else self.cart_product.product_inner_case_size

    @property
    def cart_product_case_size(self):
        """
        This will return the cart products case size at the time product was added to the cart.
        This wont be changed if in future product's case size is changed
        """
        return self.no_of_pieces/self.qty

    @property
    def order_number(self):
        return self.cart.order_id

    @property
    def cart_product_sku(self):
        return self.retailer_product.sku if self.retailer_product else self.cart_product.product_sku

    @property
    def item_effective_prices(self):
        item_effective_price = 0
        if self.retailer_product:
            if self.cart.offers and self.product_type:
                array = list(filter(lambda d: d['coupon_type'] in 'catalog', self.cart.offers))
                for i in array:
                    if int(self.retailer_product.id) == int(i['item_id']):
                        item_effective_price = (float(i.get('discounted_product_subtotal', 0))) / float(self.no_of_pieces)
            else:
                item_effective_price = float(self.selling_price) if self.selling_price else 0
        else:
            if self.cart.cart_type == 'SUPERSTORE':
                item_effective_price =  self.cart_product.super_store_product_price.last().selling_price
            else:
                try:
                    if self.cart.offers:
                        array = list(filter(lambda d: d['coupon_type'] in 'catalog', self.cart.offers))
                        for i in array:
                            if self.cart_product.id == i['item_id']:
                                item_effective_price = (i.get('discounted_product_subtotal', 0)) / float(self.no_of_pieces)
                    else:
                        product_price = self.cart_product.get_current_shop_price(self.cart.seller_shop_id,
                                                                                self.cart.buyer_shop_id)
                        item_effective_price = float(product_price.get_per_piece_price(self.qty))
                except Exception as e:
                    logger.exception("Cart product price not found")
        return item_effective_price

    @property
    def applicable_slab_price(self):
        """
        Returns applicable slab price for any cart based on the cart products quantity(per pack)
        """
        product_price = self.cart_product.get_current_shop_price(self.cart.seller_shop_id, self.cart.buyer_shop_id)
        applicable_slab_price = product_price.get_applicable_slab_price_per_pack(self.qty, self.cart_product_case_size)
        return applicable_slab_price

    def set_cart_product_price(self, seller_shop_id, buyer_shop_id):
        if self.cart_product:
            self.cart_product_price = self.cart_product. \
                get_current_shop_price(seller_shop_id, buyer_shop_id)
            self.save()

    def get_cart_product_price(self, seller_shop_id, buyer_shop_id):
        if not self.cart_product_price:
            self.set_cart_product_price(seller_shop_id, buyer_shop_id)
        return self.cart_product_price

    def clean(self, *args, **kwargs):
        if self.discounted_price > self.cart_product_price.get_per_piece_price(self.qty):
            raise ValidationError("Discounted Price of %s can't be more than Product Price." % (self.cart_product))
        else:
            super(CartProductMapping, self).clean(*args, **kwargs)

    # def save(self, *args, **kwargs):
    #
    #     super().save(*args, **kwargs)


class Order(models.Model):
    ACTIVE = 'active'
    PENDING = 'pending'
    DELETED = 'deleted'
    ORDERED = 'ordered'
    PAYMENT_PENDING = 'PAYMENT_PENDING'
    PAYMENT_FAILED = 'PAYMENT_FAILED'
    PAYMENT_APPROVED = 'PAYMENT_APPROVED'
    PAYMENT_COD = 'PAYMENT_COD'
    PAYMENT_DONE_APPROVAL_PENDING = 'payment_done_approval_pending'
    OPDP = 'opdp'
    DISPATCHED = 'dispatched'
    PARTIAL_DELIVERED = 'p_delivered'
    DELIVERED = 'delivered'
    CLOSED = 'closed'
    PDAP = 'payment_done_approval_pending'
    ORDER_PLACED_DISPATCH_PENDING = 'opdp'
    PARTIALLY_SHIPPED_AND_CLOSED = 'partially_shipped_and_closed'
    DENIED_AND_CLOSED = 'denied_and_closed'
    DISPATCH_PENDING = 'DISPATCH_PENDING'
    PARTIAL_SHIPMENT_CREATED = 'par_ship_created'
    FULL_SHIPMENT_CREATED = 'full_ship_created'
    COMPLETED = 'completed'
    READY_TO_DISPATCH = 'ready_to_dispatch'
    CANCELLED = 'CANCELLED'
    PICKING_PARTIAL_COMPLETE = 'PICKING_PARTIAL_COMPLETE'
    MOVED_TO_QC = 'MOVED_TO_QC'
    PARTIAL_MOVED_TO_QC = 'PARTIAL_MOVED_TO_QC'
    PICKING_COMPLETE = 'picking_complete'
    PICKING_ASSIGNED = 'PICKING_ASSIGNED'
    PICKUP_CREATED = 'PICKUP_CREATED'
    PARTIALLY_RETURNED = 'partially_returned'
    FULLY_RETURNED = 'fully_returned'
    PICKED = 'picked'
    OUT_FOR_DELIVERY = 'out_for_delivery'
    QC_FAILED = 'QC_FAILED'
    ORDER_STATUS = (
        (ORDERED, 'Order Placed'),  # 1
        (DISPATCH_PENDING, 'Dispatch Pending'),  # 2
        (ACTIVE, "Active"),
        (PENDING, "Pending"),
        (DELETED, "Deleted"),
        (DISPATCHED, "Dispatched"),
        (PAYMENT_PENDING, "Payment Pending"),
        (PAYMENT_FAILED, "Payment Failed"),
        (PAYMENT_APPROVED, "Payment Approved"),
        (PAYMENT_COD, "Payment COD"),
        (PARTIAL_DELIVERED, "Partially Delivered"),
        (DELIVERED, "Delivered"),
        (CLOSED, "Closed"),
        (PDAP, "Payment Done Approval Pending"),
        (ORDER_PLACED_DISPATCH_PENDING, "Order Placed Dispatch Pending"),
        ('PARTIALLY_SHIPPED', 'Partially Shipped'),  # 3
        ('SHIPPED', 'Shipped'),  # 4
        (CANCELLED, 'Cancelled'),
        ('DENIED', 'Denied'),
        (PAYMENT_DONE_APPROVAL_PENDING, "Payment Done Approval Pending"),
        (OPDP, "Order Placed Dispatch Pending"),
        (PARTIALLY_SHIPPED_AND_CLOSED, "Partially shipped and closed"),
        (DENIED_AND_CLOSED, 'Denied and Closed'),
        (PARTIAL_SHIPMENT_CREATED, 'Partial Shipment Created'),
        (FULL_SHIPMENT_CREATED, 'Full Shipment Created'),
        (READY_TO_DISPATCH, 'Ready to Dispatch'),
        (COMPLETED, 'Completed'),
        (PICKING_PARTIAL_COMPLETE, 'Picking Partial Complete'),
        (MOVED_TO_QC, 'Moved To QC Area'),
        (PARTIAL_MOVED_TO_QC, 'Partially Moved To QC Area'),
        (PICKING_COMPLETE, 'Picking Complete'),
        (PICKING_ASSIGNED, 'Picking Assigned'),
        (PICKUP_CREATED, 'Pickup Created'),
        (PARTIALLY_RETURNED, 'Partially Returned'),
        (FULLY_RETURNED, 'Fully Returned'),
        (PICKED, 'Order Processing'),
        (OUT_FOR_DELIVERY, 'Out For Delivery'),
        (QC_FAILED, 'QC Failed')
    )

    CASH_NOT_AVAILABLE = 'cna'
    SHOP_CLOSED = 'sc'
    RESCHEDULED_BY_SELLER = 'rbs'
    UNABLE_TO_ATTEMPT = 'uta'
    WRONG_ORDER = 'wo'
    ITEM_MISS_MATCH = 'imm'
    DAMAGED_ITEM = 'di'
    LEFT_AT_WAREHOUSE = 'law'
    BEFORE_DELIVERY_CANCELLED = 'bdc'
    NEAR_EXPIRY = 'ne'
    RATE_ISSUE = 'ri'
    ALREADY_PURCHASED = 'ap'
    GST_ISSUE = 'gi'
    CLEANLINESS = 'cl'
    CUSTOMER_CANCEL = 'cc'
    CUSTOMER_UNAVAILABLE = 'cu'
    MANUFACTURING_DEFECT = 'md'
    SHORT = 's'

    CANCELLATION_REASON = (
        (CASH_NOT_AVAILABLE, 'Cash not available'),
        (SHOP_CLOSED, 'Shop Closed'),
        (RESCHEDULED_BY_SELLER, 'Rescheduled by seller'),
        (UNABLE_TO_ATTEMPT, 'Unable to attempt'),
        (WRONG_ORDER, 'Wrong Order'),
        (ITEM_MISS_MATCH, 'Item miss match'),
        (DAMAGED_ITEM, 'Damaged item'),
        (LEFT_AT_WAREHOUSE, 'Left at Warehouse'),
        (BEFORE_DELIVERY_CANCELLED, 'Before Delivery Cancelled'),
        (NEAR_EXPIRY, 'Near Expiry'),
        (RATE_ISSUE, 'Rate issue'),
        (ALREADY_PURCHASED, 'Already Purchased'),
        (GST_ISSUE, 'GST Issue'),
        (CLEANLINESS, 'Item not clean'),
        (CUSTOMER_CANCEL, 'Cancelled by customer'),
        (CUSTOMER_UNAVAILABLE, 'Customer not available'),
        (MANUFACTURING_DEFECT, 'Manufacturing Defect'),
        (SHORT, 'Item short'),
        ('1','Customer not responding'),
        ('2','Stock NA'),
        ('3','Out of Range'),
        ('4','Retailer Order'),
        ('5','Others')
    )

    DELIVERY_CHOICE = ( ('1', 'Self Pick'),
                        ('2', 'Home Delivery')
                       )

    POS_WALKIN = 'pos_walkin'
    POS_ECOMM = 'pos_ecomm'
    POS_SUPERSTORE = 'pos_superstore'

    ORDER_APP_TYPE = (
        (POS_WALKIN, 'Pos Walkin'),  # 1
        (POS_ECOMM, 'Pos Ecomm'), # 2
        (POS_SUPERSTORE, 'Pos Super Store')
    )
    # Todo Remove
    seller_shop = models.ForeignKey(
        Shop, related_name='rt_seller_shop_order',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    # Todo Remove
    buyer_shop = models.ForeignKey(
        Shop, related_name='rt_buyer_shop_order',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    buyer = models.ForeignKey(User, related_name='rt_buyer_order', null=True, blank=True, on_delete=models.DO_NOTHING)
    ordered_cart = models.OneToOneField(
        Cart, related_name='rt_order_cart_mapping', null=True,
        on_delete=models.DO_NOTHING
    )
    order_no = models.CharField(max_length=255, null=True, blank=True)
    billing_address = models.ForeignKey(
        Address, related_name='rt_billing_address_order',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    shipping_address = models.ForeignKey(
        Address, related_name='rt_shipping_address_order',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    total_mrp = models.FloatField(default=0)
    order_amount = models.FloatField(default=0)
    total_discount_amount = models.FloatField(default=0)
    total_tax_amount = models.FloatField(default=0)
    order_status = models.CharField(max_length=50, choices=ORDER_STATUS)
    cancellation_reason = models.CharField(
        max_length=50, choices=CANCELLATION_REASON,
        null=True, blank=True, verbose_name='Reason for Cancellation',
    )
    order_closed = models.BooleanField(default=False, null=True, blank=True)
    order_app_type = models.CharField(max_length=50, choices=ORDER_APP_TYPE, null=True, blank=True)
    ordered_by = models.ForeignKey(
        get_user_model(), related_name='rt_ordered_by_user',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    received_by = models.ForeignKey(
        get_user_model(), related_name='rt_received_by_user',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_order_modified_user',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    estimate_delivery_time = models.CharField(max_length=50, null=True, blank=True)
    pick_list_pdf = models.FileField(upload_to='shop_photos/shop_name/documents/', null=True, blank=True)
    points_added = models.IntegerField(default=0, null=True)
    delivery_person = models.ForeignKey(UserWithName, null=True, on_delete=models.DO_NOTHING, verbose_name='Delivery Boy')
    dispatch_delivery = models.BooleanField(default=False)
    dispatch_center = models.ForeignKey(Shop, related_name='dispatch_center_orders', null=True, blank=True,
                                        on_delete=models.DO_NOTHING)
    delivery_option = models.CharField(max_length=50, choices=DELIVERY_CHOICE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    latitude = models.DecimalField(max_digits=30, decimal_places=15, null=True,blank=True, verbose_name='Latitude For Ecommerce order')
    longitude = models.DecimalField(max_digits=30, decimal_places=15, null=True,blank=True, verbose_name='Longitude For Ecommerce order')

    def __str__(self):
        return self.order_no or str(self.id)

    class Meta:
        ordering = ['-created_at']

    def payments(self):
        if hasattr(self, 'payment_objects'):
            return self.payment_objects
        else:
            payment_mode = []
            payment_amount = []
            payments = self.rt_payment.all().values('paid_amount', 'payment_choice')
            if payments:
                for payment in payments:
                    payment_mode.append(dict(PAYMENT_MODE_CHOICES)[payment.get('payment_choice')])
                    payment_amount.append(float(payment.get('paid_amount')))
            self.payment_objects = payment_mode, payment_amount
            return self.payment_objects

    @property
    def total_final_amount(self):
        return self.ordered_cart.order_amount

    @property
    def total_mrp_amount(self):
        return self.ordered_cart.mrp_subtotal

    @property
    def payment_mode(self):
        payment_mode, _ = self.payments()
        return payment_mode

    @property
    def paid_amount(self):
        _, payment_amount = self.payments()
        return payment_amount

    @property
    def total_paid_amount(self):
        _, payment_amount = self.payments()
        return sum(payment_amount)

    def shipments(self):
        if hasattr(self, 'shipment_objects'):
            return self.shipment_objects
        self.shipment_objects = self.rt_order_order_product.select_related('trip').all()
        return self.shipment_objects

    def picker_dashboards(self):
        if hasattr(self, 'picker_dashboard_objects'):
            return self.picker_dashboard_objects
        self.picker_dashboard_objects = self.picker_order.all()
        return self.picker_dashboard_objects

    @property
    def picking_status(self):
        return picking_statuses(self.picker_dashboards())

    @property
    def picklist_refreshed_at(self):
        return picklist_refreshed_at(self.picker_dashboards())

    @property
    def picker_boy(self):
        return picker_boys(self.picker_dashboards())

    @property
    def picklist_id(self):
        return picklist_ids(self.picker_dashboards())

    @property
    def qc_area(self):
        return qc_areas(self.picker_dashboards())

    @property
    def qc_desk(self):
        return qc_desks(self.picker_dashboards())

    @property
    def qc_executive(self):
        return qc_executives(self.picker_dashboards())

    @property
    def zone(self):
        return zones(self.picker_dashboards())

    @property
    def pickup_completed_at(self):
        pickup_object = Pickup.objects.filter(pickup_type_id=self.order_no,
                                              status='picking_complete')
        if pickup_object.exists():
            return pickup_object.last().completed_at

    @property
    def invoice_no(self):
        return order_invoices(self.shipments())

    @property
    def shipment_status(self):
        return order_shipment_status(self.shipments())

    @property
    def shipment_status_reason(self):
        return order_shipment_status_reason(self.shipments())

    @property
    def order_shipment_amount(self):
        return order_shipment_amount(self.shipments())

    @property
    def order_shipment_details(self):
        return order_shipment_details_util(self.shipments())

    # @property
    # def shipment_returns(self):
    #     return self._shipment_returns

    # @property
    # def picking_status(self):
    #     return "-"

    @property
    def picker_name(self):
        return "-"

    @property
    def shipment_date(self):
        return order_shipment_date(self.shipments())

    @property
    def invoice_amount(self):
        return order_shipment_amount(self.shipments())

    @property
    def delivery_date(self):
        return order_delivery_date(self.shipments())

    @property
    def cn_amount(self):
        return order_cn_amount(self.shipments())

    @property
    def cash_collected(self):
        return order_cash_to_be_collected(self.shipments())

    @property
    def damaged_amount(self):
        return order_damaged_amount(self.shipments())

    @property
    def pincode(self):
        return self.shipping_address.pincode if self.shipping_address else '-'

    @property
    def city(self):
        return self.shipping_address.city.city_name if self.shipping_address else '-'

    # @property
    # def delivered_value(self):
    #     return order_delivered_value(self.shipments())

    def ordered_amount(self):
        invoice_amount = 0
        for s in self.shipments():
            invoice_amount += s.invoice_amount
        return invoice_amount

    @property
    def buyer_shop_with_mobile(self):
        try:
            if self.buyer_shop:
                return "%s - %s" % (self.buyer_shop, self.buyer_shop.shop_owner.phone_number)
            return "-"
        except:
            return "-"

    @property
    def trip_id(self):
        trips = []
        curr_trip = ''
        for s in self.shipments():
            curr_dispatch_no = ''
            if s.last_trip:
                curr_dispatch_no = s.last_trip.dispatch_no
                curr_trip = '<b>' + s.last_trip.dispatch_no + '</b><br>'
            trips += LastMileTripShipmentMapping.objects.filter(shipment=s). \
                values_list('trip__dispatch_no', flat=True).distinct()
            trips += DispatchTripShipmentMapping.objects.filter(shipment=s). \
                values_list('trip__dispatch_no', flat=True).distinct()
            trips += s.rescheduling_shipment.values_list('trip__dispatch_no', flat=True).distinct()
            trips += s.not_attempt_shipment.values_list('trip__dispatch_no', flat=True).distinct()
            while curr_dispatch_no in trips:
                trips.remove(curr_dispatch_no)
        return format_html("<b>{}</b>".format(curr_trip)) + format_html_join("", "{}<br>", ((t,) for t in trips))

    @property
    def ecom_estimated_delivery_time(self):
        if self.ordered_cart.cart_type == 'ECOM' and self.order_status in [Order.ORDERED, Order.PICKUP_CREATED,
                                                                           Order.OUT_FOR_DELIVERY]:
            order_placed_at = self.created_at
            # delivery_span = get_config("pos_order_delivery_time_hours", None)
            delivery_span = get_config_fofo_shop('Maximum Delivery time', self.ordered_cart.seller_shop.id)
            return (order_placed_at.replace(minute=0, second=0) + datetime.timedelta(
                hours=int(delivery_span))).strftime("%b %d, %Y %-I:%M %p") if delivery_span else None
        return None


class Trip(models.Model):
    READY = 'READY'
    CANCELLED = 'CANCELLED'
    STARTED = 'STARTED'
    COMPLETED = 'COMPLETED'
    RETURN_VERIFIED = 'CLOSED'
    PAYMENT_VERIFIED = 'TRANSFERRED'

    TRIP_STATUS = (
        (READY, 'Ready'),
        (CANCELLED, 'Cancelled'),
        (STARTED, 'Started'),
        (COMPLETED, 'Completed'),
        (RETURN_VERIFIED, 'Return Verified'),
        (PAYMENT_VERIFIED, 'Payment Verified'),
    )

    seller_shop = models.ForeignKey(
        Shop, related_name='trip_seller_shop', null=True,
        on_delete=models.DO_NOTHING
    )
    source_shop = models.ForeignKey(Shop, related_name='trip_source_shop', null=True, on_delete=models.DO_NOTHING)
    dispatch_no = models.CharField(max_length=50, null=True, unique=True)
    delivery_boy = models.ForeignKey(
        UserWithName, related_name='order_delivered_by_user', null=True,
        on_delete=models.DO_NOTHING, verbose_name='Delivery Boy'
    )
    vehicle_no = models.CharField(max_length=50)
    trip_status = models.CharField(max_length=100, default=READY, choices=TRIP_STATUS)
    e_way_bill_no = models.CharField(max_length=50, blank=True, null=True)
    starts_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    received_amount = models.DecimalField(blank=True, null=True,
                                          max_digits=19, decimal_places=2)
    opening_kms = models.PositiveIntegerField(default=0, null=True, blank=True,
                                              verbose_name="Vehicle Opening Trip(Kms)")
    closing_kms = models.PositiveIntegerField(default=0, null=True, blank=True,
                                              verbose_name="Vehicle Closing Trip(Kms)")
    no_of_crates = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="Total crates shipped")
    no_of_packets = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="Total packets shipped")
    no_of_sacks = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="Total sacks shipped")
    no_of_crates_check = models.PositiveIntegerField(default=0, null=True, blank=True,
                                                     verbose_name="Total crates collected")
    no_of_packets_check = models.PositiveIntegerField(default=0, null=True, blank=True,
                                                      verbose_name="Total packets collected")
    no_of_sacks_check = models.PositiveIntegerField(default=0, null=True, blank=True,
                                                    verbose_name="Total sacks collected")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(get_user_model(), related_name='last_mile_trip_created_by',
                                   null=True, blank=True, on_delete=models.DO_NOTHING)
    modified_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(get_user_model(), related_name='last_mile_trip_updated_by',
                                   null=True, blank=True, on_delete=models.DO_NOTHING)
    weight = models.FloatField(null=True, default=0, verbose_name="Trip weight")

    def __str__(self):
        if self.delivery_boy:
            delivery_boy_identifier = self.delivery_boy.first_name if self.delivery_boy.first_name else self.delivery_boy.phone_number
        else:
            delivery_boy_identifier = "--"
        return "{} -> {}".format(
            self.dispatch_no,
            delivery_boy_identifier
        )

    def get_crates_packets_sacks(self):
        data = self.rt_invoice_trip.aggregate(
            crates_shipped=Sum('no_of_crates'),
            packets_shipped=Sum('no_of_packets'),
            sacks_shipped=Sum('no_of_sacks'),
            crates_collected=Sum('no_of_crates_check'),
            packets_collected=Sum('no_of_packets_check'),
            sacks_collected=Sum('no_of_sacks_check'))
        return data

    @property
    def total_crates_shipped(self):
        return self.get_crates_packets_sacks().get('crates_shipped')

    @property
    def total_packets_shipped(self):
        return self.get_crates_packets_sacks().get('packets_shipped')

    @property
    def total_sacks_shipped(self):
        return self.get_crates_packets_sacks().get('sacks_shipped')

    @property
    def total_crates_collected(self):
        return self.get_crates_packets_sacks().get('crates_collected')

    @property
    def total_packets_collected(self):
        return self.get_crates_packets_sacks().get('packets_collected')

    @property
    def total_sacks_collected(self):
        return self.get_crates_packets_sacks().get('sacks_collected')

    def create_dispatch_no(self):
        date = datetime.date.today().strftime('%d%m%y')
        shop = self.seller_shop_id
        shop_id_date = "%s/%s" % (shop, date)
        last_dispatch_no = Trip.objects.filter(
            dispatch_no__contains=shop_id_date)
        if last_dispatch_no.exists():
            dispatch_attempt = int(
                last_dispatch_no.last().dispatch_no.split('/')[-1])
            dispatch_attempt += 1
        else:
            dispatch_attempt = 1
        final_dispatch_no = "%s/%s/%s" % (
            'DIS', shop_id_date,
            dispatch_attempt)
        self.dispatch_no = final_dispatch_no

    def cash_to_be_collected(self):
        cash_to_be_collected = []
        trip_shipments = self.rt_invoice_trip.all()
        for shipment in trip_shipments:
            cash_to_be_collected.append(
                float(shipment.cash_to_be_collected()))
        return round(sum(cash_to_be_collected),2)

    def cash_collected_by_delivery_boy(self):
        cash_to_be_collected = []
        shipment_status_list = ['FULLY_DELIVERED_AND_COMPLETED', 'PARTIALLY_DELIVERED_AND_COMPLETED',
                                'FULLY_RETURNED_AND_COMPLETED', 'RESCHEDULED']
        trip_shipments = self.rt_invoice_trip.filter(shipment_status__in=shipment_status_list)
        for shipment in trip_shipments:
            cash_to_be_collected.append(
                float(shipment.cash_to_be_collected()))
        return round(sum(cash_to_be_collected), 2)

    def total_paid_amount(self):
        from payments.models import ShipmentPayment
        trip_shipments = self.rt_invoice_trip.exclude(
            shipment_payment__parent_order_payment__parent_payment__payment_status='cancelled')
        total_amount = cash_amount = online_amount = 0
        if trip_shipments.exists():
            shipment_payment_data = ShipmentPayment.objects.filter(shipment__in=trip_shipments) \
                .aggregate(Sum('paid_amount'))
            shipment_payment_cash = ShipmentPayment.objects.filter(shipment__in=trip_shipments,
                                                                   parent_order_payment__parent_payment__payment_mode_name="cash_payment") \
                .aggregate(Sum('paid_amount'))
            shipment_payment_online = ShipmentPayment.objects.filter(shipment__in=trip_shipments,
                                                                     parent_order_payment__parent_payment__payment_mode_name="online_payment") \
                .aggregate(Sum('paid_amount'))

            if shipment_payment_data['paid_amount__sum']:
                total_amount = round(shipment_payment_data['paid_amount__sum'], 2)  # sum_paid_amount
            if shipment_payment_cash['paid_amount__sum']:
                cash_amount = round(shipment_payment_data['paid_amount__sum'], 2)  # sum_paid_amount
            if shipment_payment_online['paid_amount__sum']:
                online_amount = round(shipment_payment_data['paid_amount__sum'], 2)  # sum_paid_amount
        return total_amount, cash_amount, online_amount

    @property
    def trip_amount(self):
        return self.last_mile_trip_shipments_details.filter(~Q(shipment_status='CANCELLED')) \
            .annotate(invoice_amount=RoundAmount(F('shipment__invoice__invoice_total'))) \
            .aggregate(trip_amount=Sum(F('invoice_amount'), output_field=FloatField())).get('trip_amount')

    @property
    def total_received_amount(self):
        total_payment, _c, _o = self.total_paid_amount()
        return total_payment

    @property
    def received_cash_amount(self):
        _t, cash_payment, _o = self.total_paid_amount()
        return cash_payment

    @property
    def received_online_amount(self):
        _t, _c, online_payment = self.total_paid_amount()
        return online_payment

    @property
    def cash_to_be_collected_value(self):
        return self.cash_to_be_collected()

    @property
    def total_trip_shipments(self):
        return self.rt_invoice_trip.count()

    @property
    def total_delivered_shipments(self):
        delivered_status_list = ['PARTIALLY_DELIVERED_AND_COMPLETED','FULLY_DELIVERED_AND_COMPLETED',
                                 'PARTIALLY_DELIVERED_AND_VERIFIED', 'FULLY_DELIVERED_AND_VERIFIED',
                                 'PARTIALLY_DELIVERED_AND_CLOSED', 'FULLY_DELIVERED_AND_CLOSED']
        return self.rt_invoice_trip.filter(shipment_status__in=delivered_status_list).count()


    @property
    def total_returned_shipments(self):
        returned_status_list = ['FULLY_RETURNED_AND_COMPLETED', 'FULLY_RETURNED_AND_VERIFIED',
                                'FULLY_RETURNED_AND_CLOSED']
        return self.rt_invoice_trip.filter(shipment_status__in=returned_status_list).count()


    @property
    def total_pending_shipments(self):
        return self.rt_invoice_trip.filter(shipment_status='OUT_FOR_DELIVERY').count()

    @property
    def total_rescheduled_shipments(self):
        return self.rescheduling_shipment_trip.count()

    @property
    def total_trip_amount_value(self):
        return self.trip_amount

    # @property
    def trip_weight(self):
        queryset = self.rt_invoice_trip.all()
        weight = sum([item.shipment_weight for item in queryset])  # Definitely takes more memory.
        # weight = self.rt_order_product_order_product_mapping.all().aggregate(Sum('product.weight_value'))['weight_value__sum']
        if weight != 0:
            weight /= 1000
        weight = round(weight, 2)
        return str(weight) + " Kg"

    __trip_status = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__trip_status = self.trip_status

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.create_dispatch_no()
        if self.trip_status != self.__trip_status and self.trip_status == self.STARTED:
            # self.trip_amount = self.total_trip_amount()
            self.starts_at = datetime.datetime.now()
        elif self.trip_status == self.COMPLETED:
            self.completed_at = datetime.datetime.now()
        super().save(*args, **kwargs)

    def dispathces(self):
        return mark_safe("<a href='/admin/retailer_to_sp/cart/trip-planning/%s/change/'>%s<a/>" % (self.pk,
                                                                                                   self.dispatch_no)
                         )

    @property
    def current_trip_status(self):
        trip_status = self.trip_status
        if trip_status:
            return str(self.get_trip_status_display())
        return str("-------")

    @property
    def no_of_shipments(self):
        return self.last_mile_trip_shipments_details.exclude(
            shipment_status__in=[DispatchTripShipmentMapping.LOADING_FOR_DC,
                                 DispatchTripShipmentMapping.CANCELLED]).count()

    @property
    def trip_id(self):
        return self.id

    @property
    def total_return_amount(self):
        return self.rt_invoice_trip.all().count()

    def get_trip_weight(self):
        trip_weight = 0
        shipments_loaded = self.last_mile_trip_shipments_details.filter(~Q(shipment_status='CANCELLED'))
        for shipment_mapping in shipments_loaded:
            packages_loaded = shipment_mapping.last_mile_trip_shipment_mapped_packages.filter(
                                ~Q(package_status__in=['CANCELLED', 'MISSING_AT_LOADING', 'DAMAGED_AT_LOADING']))
            for package_mapping in packages_loaded:
                package_weight = package_mapping.shipment_packaging.packaging_details.all()\
                                .aggregate(total_weight=Sum(F('ordered_product__product__weight_value') * F('quantity'),
                                           output_field=FloatField())).get('total_weight')
                trip_weight += package_weight if package_weight else 0
        return trip_weight

    def get_package_data(self):
        data = {'no_of_crates': 0, 'no_of_packs': 0, 'no_of_sacks': 0}
        shipments_loaded = self.last_mile_trip_shipments_details.filter(~Q(shipment_status='CANCELLED'))
        for shipment_mapping in shipments_loaded:
            packages_loaded = shipment_mapping.last_mile_trip_shipment_mapped_packages.filter(
                                ~Q(package_status__in=['CANCELLED', 'MISSING_AT_LOADING', 'DAMAGED_AT_LOADING']))
            shipment_data = packages_loaded.aggregate(
                    no_of_crates=Sum(Case(When(shipment_packaging__packaging_type=ShipmentPackaging.CRATE, then=1),
                                          default=Value('0'), output_field=models.IntegerField(), )),
                    no_of_packs=Sum(Case(When(shipment_packaging__packaging_type=ShipmentPackaging.BOX, then=1),
                                         default=Value('0'), output_field=models.IntegerField(), )),
                    no_of_sacks=Sum(Case(When(shipment_packaging__packaging_type=ShipmentPackaging.SACK, then=1),
                                         default=Value('0'), output_field=models.IntegerField(), ))
                )
            data['no_of_crates'] += shipment_data['no_of_crates'] if shipment_data.get('no_of_crates') else 0
            data['no_of_packs'] += shipment_data['no_of_packs'] if shipment_data.get('no_of_packs') else 0
            data['no_of_sacks'] += shipment_data['no_of_sacks'] if shipment_data.get('no_of_sacks') else 0
        return data


class OrderedProduct(models.Model):  # Shipment
    CLOSED = "closed"
    READY_TO_SHIP = "READY_TO_SHIP"
    RESCHEDULED = "RESCHEDULED"
    NOT_ATTEMPT = "NOT_ATTEMPT"
    DELIVERED = "DELIVERED"
    PARTIALLY_QC_PASSED = "PARTIALLY_QC_PASSED"
    QC_REJECTED = "QC_REJECTED"
    QC_STARTED = "QC_STARTED"
    SHIPMENT_CREATED = 'SHIPMENT_CREATED'
    READY_TO_DISPATCH = 'READY_TO_DISPATCH'
    OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY'
    MOVED_TO_DISPATCH = 'MOVED_TO_DISPATCH'
    IN_TRANSIT_TO_DISPATCH = 'IN_TRANSIT_TO_DISPATCH'
    FULLY_DELIVERED_AND_COMPLETED = 'FULLY_DELIVERED_AND_COMPLETED'
    FULLY_DELIVERED_AND_VERIFIED = 'FULLY_DELIVERED_AND_VERIFIED'
    PARTIALLY_DELIVERED_AND_COMPLETED = 'PARTIALLY_DELIVERED_AND_COMPLETED'
    PARTIALLY_DELIVERED_AND_VERIFIED = 'PARTIALLY_DELIVERED_AND_VERIFIED'
    FULLY_RETURNED_AND_COMPLETED = 'FULLY_RETURNED_AND_COMPLETED'
    FULLY_RETURNED_AND_VERIFIED = 'FULLY_RETURNED_AND_VERIFIED'

    FULLY_RETURNED_AND_CLOSED = 'FULLY_RETURNED_AND_CLOSED'
    PARTIALLY_DELIVERED_AND_CLOSED = 'PARTIALLY_DELIVERED_AND_CLOSED'
    FULLY_DELIVERED_AND_CLOSED = 'FULLY_DELIVERED_AND_CLOSED'
    CANCELLED = 'CANCELLED'
    SHIPMENT_STATUS = (
        (SHIPMENT_CREATED, 'QC Pending'),
        (READY_TO_SHIP, 'QC Passed'),
        (PARTIALLY_QC_PASSED, 'Partially QC Passed'),
        (QC_REJECTED, 'QC Rejected'),
        (MOVED_TO_DISPATCH, 'Moved to dispatch'),
        (IN_TRANSIT_TO_DISPATCH, 'In Transit to Dispatch'),
        (READY_TO_DISPATCH, 'Ready to Dispatch'),
        (OUT_FOR_DELIVERY, 'Out for Delivery'),
        (FULLY_RETURNED_AND_COMPLETED, 'Fully Returned and Completed'),
        (PARTIALLY_DELIVERED_AND_COMPLETED, 'Partially Delivered and Completed'),
        (FULLY_DELIVERED_AND_COMPLETED, 'Fully Delivered and Completed'),
        (FULLY_RETURNED_AND_VERIFIED, 'Fully Returned and Verified'),
        (PARTIALLY_DELIVERED_AND_VERIFIED, 'Partially Delivered and Verified'),
        (FULLY_DELIVERED_AND_VERIFIED, 'Fully Delivered and Verified'),
        (FULLY_RETURNED_AND_CLOSED, 'Fully Returned and Closed'),
        (PARTIALLY_DELIVERED_AND_CLOSED, 'Partially Delivered and Closed'),
        (FULLY_DELIVERED_AND_CLOSED, 'Fully Delivered and Closed'),
        (CANCELLED, 'Cancelled'),
        (CLOSED, 'Closed'),
        (RESCHEDULED, 'Rescheduled'),
        (DELIVERED, 'Delivered'),
        (QC_STARTED, 'QC Started'),
        (NOT_ATTEMPT, 'Not Attempt')
    )

    CASH_NOT_AVAILABLE = 'cash_not_available'
    SHOP_CLOSED = 'shop_closed'
    RESCHEDULED_BY_SELLER = 'recheduler_by_seller'
    UNABLE_TO_ATTEMPT = 'unable_to_attempt'
    WRONG_ORDER = 'wrong_order'
    ITEM_MISS_MATCH = 'item_miss_match'
    DAMAGED_ITEM = 'damaged_item'
    LEFT_AT_WAREHOUSE = 'left_at_warehouse'
    BEFORE_DELIVERY_CANCELLED = 'before_delivery_cancelled'
    NEAR_EXPIRY = 'near_expiry'
    RATE_ISSUE = 'rate_issue'
    ALREADY_PURCHASED = 'already_purchased'
    GST_ISSUE = 'gst_issue'
    CLEANLINESS = 'CLEAN'
    CUSOTMER_CANCEL = 'CUS_CAN'
    CUSTOMER_UNAVAILABLE = 'CUS_AVL'
    MANUFACTURING_DEFECT = "DEFECT"
    SHORT = 'SHORT'
    REASON_NOT_ENTERED_BY_DELIVERY_BOY = 'rsn_not_ent_by_dlv_boy'

    RETURN_REASON = (
        (CASH_NOT_AVAILABLE, 'Cash not available'),
        (SHOP_CLOSED, 'Shop Closed'),
        (RESCHEDULED_BY_SELLER, 'Rescheduled by seller'),
        (UNABLE_TO_ATTEMPT, 'Unable to attempt'),
        (WRONG_ORDER, 'Wrong Order'),
        (ITEM_MISS_MATCH, 'Item miss match'),
        (DAMAGED_ITEM, 'Damaged item'),
        (LEFT_AT_WAREHOUSE, 'Left at Warehouse'),
        (BEFORE_DELIVERY_CANCELLED, 'Before Delivery Cancelled'),
        (NEAR_EXPIRY, 'Near Expiry'),
        (RATE_ISSUE, 'Rate issue'),
        (ALREADY_PURCHASED, 'Already Purchased'),
        (GST_ISSUE, 'GST Issue'),
        (CLEANLINESS, 'Item not clean'),
        (CUSOTMER_CANCEL, 'Cancelled by customer'),
        (CUSTOMER_UNAVAILABLE, 'Customer not available'),
        (MANUFACTURING_DEFECT, 'Manufacturing Defect'),
        (SHORT, 'Item short'),
        (REASON_NOT_ENTERED_BY_DELIVERY_BOY, 'Reason not entered by Delivery Boy')
    )
    order = models.ForeignKey(
        Order, related_name='rt_order_order_product',
        on_delete=models.DO_NOTHING, null=True, blank=True
    )
    shipment_status = models.CharField(
        max_length=50, choices=SHIPMENT_STATUS,
        null=True, blank=True, verbose_name='Current Shipment Status',
        default='SHIPMENT_CREATED'
    )
    return_reason = models.CharField(
        max_length=50, choices=RETURN_REASON,
        null=True, blank=True, verbose_name='Reason for Return',
    )
    invoice_number = models.CharField(max_length=255, null=True, blank=True)
    trip = models.ForeignKey(
        Trip, related_name="rt_invoice_trip",
        null=True, blank=True, on_delete=models.DO_NOTHING,
    )
    received_by = models.ForeignKey(
        get_user_model(), related_name='rt_ordered_product_received_by_user',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_order',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    no_of_crates = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="No. Of Crates Shipped")
    no_of_packets = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="No. Of Packets Shipped")
    no_of_sacks = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="No. Of Sacks Shipped")
    no_of_crates_check = models.PositiveIntegerField(default=0, null=True, blank=True,
                                                     verbose_name="No. Of Crates Collected")
    no_of_packets_check = models.PositiveIntegerField(default=0, null=True, blank=True,
                                                      verbose_name="No. Of Packets Collected")
    no_of_sacks_check = models.PositiveIntegerField(default=0, null=True, blank=True,
                                                    verbose_name="No. Of Sacks Collected")
    is_customer_notified = models.BooleanField(default=False)
    qc_area = models.ForeignKey(QCArea, related_name='qc_area_shipment', null=True, blank=True,
                                on_delete=models.DO_NOTHING)
    current_shop = models.ForeignKey(
        Shop, related_name='shop_shipments',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Invoice Date")

    qc_started_at = models.DateTimeField(null=True, blank=True)
    qc_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Invoice Date")
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Update Delivery/ Returns/ Damage'

    def __str__(self):
        return self.invoice_no

    def clean(self):
        super(OrderedProduct, self).clean()
        if self.no_of_crates_check:
            if self.no_of_crates_check != self.no_of_crates:
                raise ValidationError(
                    _("The number of crates must be equal to the number of crates shipped during shipment"))

    @property
    def packaged_at(self):
        dispatch_trip = self.trip_shipment.last()
        last_mile_trip = self.last_mile_trip_shipment.last()
        if dispatch_trip and last_mile_trip:
            if dispatch_trip.created_at > last_mile_trip.created_at:
                return dispatch_trip.trip.source_shop.pk
            return last_mile_trip.trip.source_shop.pk
        elif dispatch_trip:
            return dispatch_trip.trip.source_shop.pk
        elif last_mile_trip:
            return last_mile_trip.trip.source_shop.pk
        return None

    @property
    def last_trip(self):
        dispatch_trip = self.trip_shipment.last()
        last_mile_trip = self.last_mile_trip_shipment.last()
        if dispatch_trip and last_mile_trip:
            if dispatch_trip.created_at > last_mile_trip.created_at:
                return dispatch_trip.trip
            return last_mile_trip.trip
        elif dispatch_trip:
            return dispatch_trip.trip
        elif last_mile_trip:
            return last_mile_trip.trip
        return None

    @property
    def invoice_subtotal(self):
        return self.rt_order_product_order_product_mapping.all() \
            .aggregate(
            inv_amt=Sum(F('selling_price') * F('shipped_qty'), output_field=FloatField())).get('inv_amt')

    @property
    def invoice_amount_total(self):
        # with redeem points
        return self.rt_order_product_order_product_mapping.all() \
            .aggregate(
            inv_amt=Sum(F('effective_price') * F('shipped_qty'), output_field=FloatField())).get('inv_amt')

    @property
    def invoice_amount_final(self):
        # without rdeeem points
        inv_amt = self.rt_order_product_order_product_mapping.all() \
            .aggregate(
            inv_amt=Sum(F('effective_price') * F('shipped_qty'), output_field=FloatField())).get('inv_amt')
        if inv_amt:
            cart = self.order.ordered_cart
            if cart.redeem_factor:
                inv_amt = max(round(inv_amt - (cart.redeem_points / cart.redeem_factor), 2), 0)
        return inv_amt

    @property
    def invoice_amount(self):
        if hasattr(self, 'invoice'):
            return round(self.invoice.invoice_total)

        return self.rt_order_product_order_product_mapping.all() \
            .aggregate(
            inv_amt=RoundAmount(Sum(F('effective_price') * F('shipped_qty')), output_field=FloatField())).get('inv_amt')

    @property
    def credit_note_amount(self):
        tcs_rate = self.invoice.tcs_percent/100
        credit_note_amount = self.rt_order_product_order_product_mapping.all().aggregate(cn_amt=RoundAmount(
            Sum((F('effective_price') * F('shipped_qty') - F('delivered_qty')), output_field=FloatField())))\
            .get('cn_amt')
        if credit_note_amount:
            return round(credit_note_amount*(1+tcs_rate), 2)
        else:
            return 0


    @property
    def shipment_weight(self):
        try:
            total_weight = self.rt_order_product_order_product_mapping.all() \
                .aggregate(
                total_weight=Sum(F('product__weight_value') * F('shipped_qty'), output_field=FloatField())).get(
                'total_weight')
            if not total_weight:
                return 0
            return total_weight
        except:
            return 0

    @property
    def shipment_address(self):
        if self.order:
            address = self.order.shipping_address
            if address:
                address_line = address.address_line1
                contact = address.address_contact_number
                shop_name = address.shop_name.shop_name
                return str("%s, %s(%s)") % (shop_name, address_line, contact)
        return str("-")

    def payment_approval_status(self):
        if not self.shipment_payment.all().exists():
            return "-"

        non_approved_payment = self.shipment_payment.exclude(
            parent_order_payment__parent_payment__payment_approval_status='approved_and_verified').first()
        if non_approved_payment:
            return non_approved_payment.parent_order_payment.parent_payment.payment_approval_status

        return "approved_and_verified"

    def online_payment_approval_status(self):
        payments = self.shipment_payment.values(
            reference_no=F('parent_order_payment__parent_payment__reference_no'),
            payment_approval_status=F('parent_order_payment__parent_payment__payment_approval_status'),
            payment_id=F('parent_order_payment__parent_payment__id')
        ).exclude(parent_order_payment__parent_payment__payment_mode_name="cash_payment")
        if not payments.exists():
            return "-"
        return format_html_join(
            "", "<a href='/admin/payments/paymentapproval/{}/change/' target='_blank'>{} - {}</a><br><br>",
            ((s.get('payment_id'), s.get('reference_no'), s.get('payment_approval_status')
              ) for s in payments)
        )

    def total_payment(self):
        shipment_payment = self.shipment_payment.exclude(
            parent_order_payment__parent_payment__payment_status='cancelled')
        total_payment = cash_payment = online_payment = 0
        if shipment_payment.exists():
            shipment_payment_data = shipment_payment.aggregate(
                Sum('paid_amount'))  # annotate(sum_paid_amount=Sum('paid_amount'))
            shipment_payment_cash = shipment_payment.filter(
                parent_order_payment__parent_payment__payment_mode_name="cash_payment").aggregate(Sum('paid_amount'))
            shipment_payment_online = shipment_payment.filter(
                parent_order_payment__parent_payment__payment_mode_name="online_payment").aggregate(Sum('paid_amount'))
            if shipment_payment_data['paid_amount__sum']:
                total_payment = round(shipment_payment_data['paid_amount__sum'], 2)  # sum_paid_amount
            if shipment_payment_cash['paid_amount__sum']:
                cash_payment = round(shipment_payment_cash['paid_amount__sum'], 2)  # sum_paid_amount
            if shipment_payment_online['paid_amount__sum']:
                online_payment = round(shipment_payment_online['paid_amount__sum'], 2)  # sum_paid_amount
        return total_payment, cash_payment, online_payment

    @property
    def total_paid_amount(self):
        total_payment, _c, _o = self.total_payment()
        return total_payment

    @property
    def cash_payment(self):
        _t, cash_payment, _o = self.total_payment()
        return cash_payment

    @property
    def online_payment(self):
        _t, _c, online_payment = self.total_payment()
        return online_payment

    @property
    def invoice_city(self):
        if self.order.shipping_address:
            city = self.order.shipping_address.city
            return str(city)
        return str("-")

    def cash_to_be_collected(self):
        # fetch the amount to be collected
        cash_to_be_collected = 0
        tcs_rate = self.invoice.tcs_percent / 100
        if self.order.ordered_cart.approval_status == False:
            for item in self.rt_order_product_order_product_mapping.all():
                effective_price = item.effective_price if item.effective_price else 0
                cash_to_be_collected = cash_to_be_collected + (item.delivered_qty * effective_price)
            return round(float(cash_to_be_collected) * (1+tcs_rate))
        else:
            invoice_amount = self.rt_order_product_order_product_mapping.all() \
                .aggregate(
                inv_amt=RoundAmount(Sum(F('discounted_price') * F('shipped_qty')), output_field=FloatField())).get(
                'inv_amt')
            credit_note_amount = self.rt_order_product_order_product_mapping.all() \
                .aggregate(cn_amt=RoundAmount(Sum((F('discounted_price') * (F('shipped_qty') - F('delivered_qty')))), output_field=FloatField()))\
                .get('cn_amt')
            if self.invoice_amount:
                return round(float(invoice_amount - credit_note_amount) * (1+tcs_rate))
            else:
                return 0

    def total_shipped_pieces(self):
        return self.rt_order_product_order_product_mapping.all() \
            .aggregate(cn_amt=Sum(F('shipped_qty'))).get('cn_amt')

    def total_returned_pieces(self):
        return self.rt_order_product_order_product_mapping.all() \
            .aggregate(cnt=Sum(F('returned_qty') + F('returned_damage_qty'))).get('cnt')

    def sum_amount_tax(self):
        return sum([item.product_tax_amount for item in self.rt_order_product_order_product_mapping.all()])

    def sum_cess(self):
        return sum([item.product_tax_json() for item in self.rt_order_product_order_product_mapping.all()])

    def sum_cgst(self):
        return self.rt_order_product_order_product_mapping.all() \
            .aggregate(cn_amt=RoundAmount(Sum(F('effective_price') * (F('shipped_qty') - F('delivered_qty'))))).get(
            'cn_amt')

    def sum_sgst(self):
        return sum([item.product_tax_json.get('6', {}).get("CESS - 12") for item in
                    self.rt_order_product_order_product_mapping.all()])

    @property
    def invoice_no(self):
        if hasattr(self, 'invoice'):
            return self.invoice.invoice_no
        if self.invoice_number:
            return self.invoice_number
        return "-"

    @property
    def shipment_id(self):
        return self.id

    def picking_data(self):
        if self.picker_shipment.all().exists():
            picker_data = self.picker_shipment.last()
            return [picker_data.get_picking_status_display(), picker_data.picker_boy, picker_data.picklist_id]
        else:
            return ["", "", ""]

    @property
    def picking_status(self):
        return self.picking_data()[0]  # picking_statuses(self.picker_shipment())

    @property
    def picker_boy(self):
        return self.picking_data()[1]

    @property
    def picklist_id(self):
        return self.picking_data()[2]

    @property
    def order_no(self):
        return self.order.order_no

    def damaged_amount(self):
        return self.rt_order_product_order_product_mapping.all() \
            .aggregate(cn_amt=Sum(F('effective_price') * F('damaged_qty'))).get('cn_amt')

    def clean(self):
        super(OrderedProduct, self).clean()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.order.ordered_cart.cart_type == 'AUTO':
            if self.shipment_status == OrderedProduct.MOVED_TO_DISPATCH:
                CommonFunction.generate_invoice_number(self,
                            self.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)
        if self.order.ordered_cart.cart_type == 'BASIC':
            if self.shipment_status == OrderedProduct.MOVED_TO_DISPATCH:
                CommonFunction.generate_invoice_number(self,
                    self.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)
        elif self.order.ordered_cart.cart_type == 'ECOM':
            if self.shipment_status == OrderedProduct.MOVED_TO_DISPATCH:
                CommonFunction.generate_invoice_number(self,
                    self.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk, "EV")
        elif self.order.ordered_cart.cart_type == 'RETAIL':
            if self.shipment_status == OrderedProduct.MOVED_TO_DISPATCH:
                CommonFunction.generate_invoice_number(self,
                    self.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)
                # populate_data_on_qc_pass(self.order)

        elif self.order.ordered_cart.cart_type == 'DISCOUNTED':
            if self.shipment_status == OrderedProduct.MOVED_TO_DISPATCH:
                CommonFunction.generate_invoice_number_discounted_order(self,
                    self.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)
                # populate_data_on_qc_pass(self.order)
        elif self.order.ordered_cart.cart_type == 'BULK':
            if self.shipment_status == OrderedProduct.MOVED_TO_DISPATCH:
                CommonFunction.generate_invoice_number_bulk_order(self,
                    self.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)
                # populate_data_on_qc_pass(self.order)

        if self.no_of_crates == None:
            self.no_of_crates = 0
        if self.no_of_packets == None:
            self.no_of_packets = 0
        if self.no_of_sacks == None:
            self.no_of_sacks = 0
        
        shipment_payments = self.shipment_payment.all()
        for ship_pay in shipment_payments:
            if ship_pay.parent_order_payment and ship_pay.parent_order_payment.paid_amount:
                ship_pay.paid_amount = ship_pay.parent_order_payment.paid_amount
                ship_pay.save()

        super().save(*args, **kwargs)

    def payments(self):
        if hasattr(self, '_payment_mode'):
            return self._payment_mode, self._payment_amount
        else:
            self._payment_mode = []
            self._payment_amount = []
            if self.order:
                payments = self.order.rt_payment.values('payment_choice', 'paid_amount').all()
                for payment in payments:
                    self._payment_mode.append(dict(PAYMENT_MODE_CHOICES)[payment['payment_choice']])
                    self._payment_amount.append(float(payment['paid_amount']))
        return self._payment_mode, self._payment_amount

    @property
    def payment_mode(self):
        payment_mode, _ = self.payments()
        return payment_mode

    @property
    def is_igst_applicable(self):
        if self.order.shipping_address.state_id == \
                self.order.seller_shop.shop_name_address_mapping.last().state_id:
            return False
        return True


class Invoice(models.Model):
    invoice_no = models.CharField(max_length=255, unique=True, db_index=True)
    shipment = models.OneToOneField(OrderedProduct, related_name='invoice', on_delete=models.DO_NOTHING)
    invoice_sub_total = models.FloatField()
    is_tcs_applicable = models.BooleanField(default=False)
    tcs_percent = models.FloatField(default=0)
    tcs_amount = models.FloatField(default=0)
    invoice_total = models.FloatField()
    invoice_pdf = models.FileField(upload_to='shop_photos/shop_name/documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def __str__(self):
        return self.invoice_no

    @property
    def pdf_name(self):
        return 'Invoice_%s.pdf' % (self.invoice_no)
    
    @property
    def invoice_amount(self):
        return round(self.invoice_total)

    @property
    def is_igst_applicable(self):
        return self.shipment.is_igst_applicable


class PickerDashboard(models.Model):
    PICKING_PENDING, PICKING_ASSIGNED = 'picking_pending', 'picking_assigned'
    PICKING_IN_PROGRESS, PICKING_COMPLETE = 'picking_in_progress', 'picking_complete'
    PICKING_CANCELLED, MOVED_TO_QC = 'picking_cancelled', 'moved_to_qc'
    PICKING_STATUS = (
        (PICKING_PENDING, 'Picking Pending'),
        (PICKING_ASSIGNED, 'Picking Assigned'),
        (PICKING_IN_PROGRESS, 'Picking In Progress'),
        (PICKING_COMPLETE, 'Picking Complete'),
        (PICKING_CANCELLED, 'Picking Cancelled'),
        (MOVED_TO_QC, 'Moved To QC Area'),
    )
    PICKING_TYPE_CHOICE = Choices((1, 'ORDER', 'order'), (2, 'REPACKAGING', 'repackaging'))
    order = models.ForeignKey(Order, related_name="picker_order", on_delete=models.CASCADE, null=True, blank=True)
    repackaging = models.ForeignKey(Repackaging, related_name="picker_repacks", on_delete=models.CASCADE, null=True, blank=True)
    shipment = models.ForeignKey(
        OrderedProduct, related_name="picker_shipment",
        on_delete=models.DO_NOTHING, null=True, blank=True)
    picking_status = models.CharField(max_length=50, choices=PICKING_STATUS, default='picking_pending')
    # make unique to picklist id
    picklist_id = models.CharField(max_length=255, null=True, blank=True)  # unique=True)
    picker_boy = models.ForeignKey(
        UserWithName, related_name='picker_user',
        on_delete=models.DO_NOTHING, verbose_name='Picker Boy',
        null=True, blank=True
    )
    pick_list_pdf = models.FileField(upload_to='shop_photos/shop_name/documents/picker/', null=True, blank=True)
    picker_assigned_date = models.DateTimeField(null=True, blank=True, default="2020-09-29")
    zone = models.ForeignKey(Zone, null=True, blank=True, related_name='pickup_dashboard_zone', on_delete=models.DO_NOTHING)
    qc_area = models.ForeignKey(QCArea, null=True, blank=True, related_name='area_pickings', on_delete=models.DO_NOTHING)
    is_valid = models.BooleanField(default=True)
    refreshed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True)
    moved_to_qc_at = models.DateTimeField(null=True)

    def save(self, *args, **kwargs):
        super(PickerDashboard, self).save(*args, **kwargs)
        if self.picking_status == 'picking_assigned':
            PickerDashboard.objects.filter(id=self.id).update(picker_assigned_date=datetime.datetime.now())
            if self.order:
                Pickup.objects.filter(pickup_type_id=self.order.order_no, zone=self.zone,
                                      status='pickup_creation').update(status='picking_assigned')
            elif self.repackaging:
                Pickup.objects.filter(pickup_type_id=self.repackaging.repackaging_no, zone=self.zone,
                                      status='pickup_creation').update(status='picking_assigned')


    def __str__(self):
        return self.picklist_id if self.picklist_id is not None else str(self.id)

    # class Meta:
    #     unique_together = (('shipment'),('order', 'picking_status'),)


class OrderedProductMapping(models.Model):
    ordered_product = models.ForeignKey(
        OrderedProduct, related_name='rt_order_product_order_product_mapping',
        null=True, on_delete=models.DO_NOTHING
    )
    product = models.ForeignKey(
        Product, related_name='rt_product_order_product',
        null=True, on_delete=models.DO_NOTHING
    )
    retailer_product = models.ForeignKey(
        "pos.RetailerProduct", related_name='rt_retailer_product_order_product',
        null=True, on_delete=models.DO_NOTHING
    )
    product_type = models.IntegerField(choices=((0, 'Free'), (1, 'Purchased')), default=1)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shipped_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name="Shipped Pieces",
                                      validators=[MinValueValidator(0)])
    delivered_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name="Delivered Pieces",
                                        validators=[MinValueValidator(0)])
    returned_qty = models.PositiveIntegerField(default=0, verbose_name="Returned Pieces")
    damaged_qty = models.PositiveIntegerField(default=0, verbose_name="Damaged Pieces")
    returned_damage_qty = models.PositiveIntegerField(default=0, verbose_name="Damaged Return")
    returned_missing_qty = models.PositiveIntegerField(default=0, verbose_name="Damaged Missing")
    expired_qty = models.PositiveIntegerField(default=0, verbose_name="Expired Pieces")
    missing_qty = models.PositiveIntegerField(default=0, verbose_name="Missing Pieces")
    rejected_qty = models.PositiveIntegerField(default=0, verbose_name="Rejected Pieces")
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_order_product',
        null=True, on_delete=models.DO_NOTHING
    )
    product_tax_json = JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    effective_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    discounted_price = models.DecimalField(default=0, max_digits=10, decimal_places=2, null=True, blank=False)
    delivered_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    cancellation_date = models.DateTimeField(null=True, blank=True)
    picked_pieces = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name="Picked Pieces",
                                        validators=[MinValueValidator(0)])
    is_qc_done = models.BooleanField(default=False)
    is_return_verified = models.BooleanField(default=False)
    initial_returned_qty = models.PositiveIntegerField(default=0, verbose_name="Initially Returned Quantity",
                                                       help_text="Returned damaged by delivery boy")
    initial_delivered_qty = models.PositiveIntegerField(default=0, verbose_name="Initially Delivered Quantity",
                                                        help_text="Shipped - initial returned qty")

    def clean(self):
        super(OrderedProductMapping, self).clean()
        returned_qty = int(self.returned_qty)
        damaged_qty = int(self.damaged_qty)

        # if self.returned_qty > 0 or self.damaged_qty > 0:
        #     already_shipped_qty = int(self.shipped_qty)
        #     if sum([returned_qty, damaged_qty]) > already_shipped_qty:
        #         raise ValidationError(
        #             _('Sum of returned and damaged pieces should be '
        #               'less than no. of pieces to ship'),
        #         )

    @property
    def product_weight(self):
        if self.retailer_product:
            return 0
        if self.product.weight_value:
            weight = self.product.weight_value * self.shipped_qty
            return weight
        else:
            return 0

    @property
    def ordered_qty(self):
        if self.ordered_product:
            if self.retailer_product:
                no_of_pieces = self.ordered_product.order.ordered_cart.rt_cart_list.filter(
                    retailer_product=self.retailer_product, product_type=self.product_type).values('no_of_pieces')
            else:
                no_of_pieces = self.ordered_product.order.ordered_cart.rt_cart_list.filter(
                    cart_product=self.product).values('no_of_pieces')
            no_of_pieces = no_of_pieces.first().get('no_of_pieces')
            return str(int(no_of_pieces))
        return str("-")

    ordered_qty.fget.short_description = "Ordered Pieces"

    @property
    def already_shipped_qty(self):
        qs = OrderedProductMapping.objects.filter(ordered_product__in=self.ordered_product.order.rt_order_order_product.all())
        if self.retailer_product:
            qs = qs.filter(retailer_product=self.retailer_product, product_type=self.product_type)
        else:
            qs = qs.filter(product=self.product)
        already_shipped_qty = qs.aggregate(Sum('delivered_qty')).get('delivered_qty__sum', 0)
        return already_shipped_qty if already_shipped_qty else 0

    already_shipped_qty.fget.short_description = "Delivered Qty"

    @property
    def shipped_quantity_including_current(self):
        all_ordered_product = self.ordered_product.order.rt_order_order_product.filter(
            created_at__lte=self.ordered_product.created_at)  # all()
        qty = OrderedProductMapping.objects.filter(
            ordered_product__in=all_ordered_product,
            product=self.product)
        shipped_qty = qty.aggregate(
            Sum('shipped_qty')).get('shipped_qty__sum', 0)

        shipped_qty = shipped_qty if shipped_qty else 0
        return shipped_qty

    @property
    def to_be_shipped_qty(self):
        all_ordered_product = self.ordered_product.order.rt_order_order_product.all()
        qty = OrderedProductMapping.objects.filter(ordered_product__in=all_ordered_product)
        if self.retailer_product:
            qty = qty.filter(retailer_product=self.retailer_product, product_type=self.product_type)
        else:
            qty = qty.filter(product=self.product)
        to_be_shipped_qty = qty.aggregate(
            Sum('shipped_qty')).get('shipped_qty__sum', 0)
        to_be_shipped_qty = to_be_shipped_qty if to_be_shipped_qty else 0
        return to_be_shipped_qty

    to_be_shipped_qty.fget.short_description = "Already Shipped Qty"

    @property
    def shipped_qty_exclude_current1(self):
        all_ordered_product = self.ordered_product.order.rt_order_order_product.filter(
            created_at__lt=self.created_at)  # all()
        all_ordered_product_exclude_current = all_ordered_product.exclude(id=self.ordered_product_id)
        to_be_shipped_qty = OrderedProductMapping.objects.filter(
            ordered_product__in=all_ordered_product_exclude_current,
            product=self.product).aggregate(
            Sum('shipped_qty')).get('shipped_qty__sum', 0)
        to_be_shipped_qty = to_be_shipped_qty if to_be_shipped_qty else 0
        return to_be_shipped_qty

    @property
    def shipped_qty_exclude_current(self):
        all_ordered_product = self.ordered_product.order.rt_order_order_product.all()
        all_ordered_product_exclude_current = all_ordered_product.exclude(id=self.ordered_product_id)
        to_be_shipped_qty = OrderedProductMapping.objects.filter(
            ordered_product__in=all_ordered_product_exclude_current)
        if self.retailer_product:
            to_be_shipped_qty = to_be_shipped_qty.filter(retailer_product=self.retailer_product,
                                                         product_type=self.product_type)
        else:
            to_be_shipped_qty = to_be_shipped_qty.filter(product=self.product)
        to_be_shipped_qty = to_be_shipped_qty.aggregate(
            Sum('shipped_qty')).get('shipped_qty__sum', 0)
        to_be_shipped_qty = to_be_shipped_qty if to_be_shipped_qty else 0
        return to_be_shipped_qty

    @property
    def gf_code(self):
        if self.product:
            gf_code = self.product.product_gf_code
            return str(gf_code)
        return str("-")

    @property
    def mrp(self):
        if self.retailer_product:
            return self.retailer_product.mrp
        if self.product.product_mrp:
            return self.product.product_mrp
        return self.ordered_product.order.ordered_cart.rt_cart_list \
            .get(cart_product=self.product).cart_product_price.mrp

    @property
    def price_to_retailer(self):
        if self.ordered_product.order.ordered_cart.cart_type == 'DISCOUNTED':
            cart_product_mapping = self.ordered_product.order.ordered_cart.rt_cart_list.get(cart_product=self.product)
            shipped_qty_in_pack = math.ceil(self.shipped_qty / cart_product_mapping.cart_product_case_size)
            ptr = cart_product_mapping.cart_product_price.get_per_piece_price(shipped_qty_in_pack)
            return ptr
        else:
            if self.effective_price:
                return float(self.effective_price)
            return self.ordered_product.order.ordered_cart.rt_cart_list.get(cart_product=self.product).item_effective_prices

    def set_effective_price(self):
        try:
            cart_product_mapping = self.ordered_product.order.ordered_cart.rt_cart_list.get(cart_product=self.product)
            shipper_qty_in_pack = math.ceil(self.shipped_qty / cart_product_mapping.cart_product_case_size)
            effective_price = cart_product_mapping.cart_product_price.get_per_piece_price(shipper_qty_in_pack)
            OrderedProductMapping.objects.filter(id=self.id).update(effective_price=effective_price)
        except:
            pass

    def set_discounted_price(self):
        try:
            discounted_price = self.ordered_product.order.ordered_cart.rt_cart_list \
                .get(cart_product=self.product).discounted_price
            OrderedProductMapping.objects.filter(id=self.id).update(discounted_price=discounted_price)
        except:
            pass

    @property
    def cash_discount(self):
        return self.ordered_product.order.ordered_cart.rt_cart_list \
            .get(cart_product=self.product).cart_product_price.cash_discount

    @property
    def loyalty_incentive(self):
        return self.ordered_product.order.ordered_cart.rt_cart_list \
            .get(cart_product=self.product).cart_product_price.loyalty_incentive

    @property
    def margin(self):
        return self.ordered_product.order.ordered_cart.rt_cart_list \
            .get(cart_product=self.product).cart_product_price.margin

    @property
    def ordered_product_status(self):
        return self.ordered_product.shipment_status

    @property
    def product_short_description(self):
        return self.product.product_short_description

    @property
    def basic_rate(self):
        get_tax_val = self.get_product_tax_json() / 100
        basic_rate = (float(self.effective_price) - float(self.product_cess_amount)) / (float(get_tax_val) + 1)
        return basic_rate

    @property
    def return_rate(self):
        """This function returns the basic rate at which credit note is to be generated"""
        return self.basic_rate

    @property
    def product_credit_amount(self):
        return round((float(float(self.shipped_qty) - float(self.delivered_qty)) * float(self.effective_price)), 2)

    @property
    def product_credit_amount_per_unit(self):
        return self.effective_price

    @property
    def basic_rate_discounted(self):
        get_tax_val = self.get_product_tax_json() / 100
        basic_rate = (float(self.effective_price - self.discounted_price)) / (float(get_tax_val) + 1)
        return round(basic_rate, 2)

    @property
    def base_price(self):
        # return float(self.basic_rate) * float(self.shipped_qty)
        get_tax_val = self.get_product_tax_json() / 100
        return (float(self.effective_price) * float(self.shipped_qty)) / (float(get_tax_val) + 1)

    @property
    def product_tax_amount(self):
        get_tax_val = self.get_product_tax_json() / 100
        return round((self.base_price * float(get_tax_val)), 2)
        # return round((float(self.basic_rate) * float(self.shipped_qty)) * float(get_tax_val), 2)

    @property
    def total_product_cess_amount(self):
        product_special_cess = float(self.product_cess_amount) * (int(self.shipped_qty))
        return round(float(product_special_cess), 2)

    @property
    def product_cess_amount(self):
        if self.product.product_special_cess is None:
            return 0.0
        else:
            product_special_cess = float(self.product.product_special_cess)
            return round(float(product_special_cess), 2)

    @property
    def product_tax_return_amount(self):
        get_tax_val = self.get_product_tax_json() / 100
        return round(float(self.basic_rate * (self.returned_qty + self.returned_damage_qty)) * float(get_tax_val), 2)

    @property
    def product_tax_discount_amount(self):
        get_tax_val = self.get_product_tax_json() / 100
        return round(float(self.basic_rate_discounted * float(self.delivered_qty)) * float(get_tax_val), 2)

    @property
    def product_sub_total(self):
        return round(float(self.effective_price * self.shipped_qty), 2)

    @property
    def product_total_price(self):
        return round(float(self.selling_price * self.shipped_qty), 2)

    def get_shop_specific_products_prices_sp(self):
        return self.product.product_pro_price.filter(
            seller_shop__shop_type__shop_type='sp', status=True
        ).last()

    def get_products_gst_tax(self):
        return self.product.product_pro_tax.filter(tax__tax_type='gst')

    def get_products_gst_cess(self):
        return self.product.product_pro_tax.filter(tax__tax_type='cess')

    def get_products_tcs(self):
        return self.product.product_pro_tax.filter(tax__tax_type='tcs')

    def get_products_gst(self):
        queryset = self.product.product_pro_tax.filter(tax__tax_type='gst')
        if queryset.exists():
            return queryset.values_list('tax__tax_percentage', flat=True).first()
        else:
            return 0

    def get_products_gst_cess_tax(self):
        queryset = self.product.product_pro_tax.filter(tax__tax_type='cess')
        if queryset.exists():
            return queryset.values_list('tax__tax_percentage', flat=True).first()
        else:
            return 0

    def get_products_gst_surcharge(self):
        queryset = self.product.product_pro_tax.filter(tax__tax_type='surcharge')
        if queryset.exists():
            return queryset.values_list('tax__tax_percentage', flat=True).first()
        else:
            return 0

    def set_product_tax_json(self):
        # if self.product.parent_product:
        #     product_tax = {}
        #     product_tax['tax_sum'] = self.product.parent_product.gst + self.product.parent_product.cess + \
        #                          self.product.parent_product.surcharge
        #     self.product_tax_json = product_tax
        # else:
        #     product_tax_query = self.product.product_pro_tax.values('product', 'tax', 'tax__tax_name',
        #                                                             'tax__tax_percentage')
        #     product_tax = {i['tax']: [i['tax__tax_name'], i['tax__tax_percentage']] for i in product_tax_query}
        #     product_tax['tax_sum'] = product_tax_query.aggregate(tax_sum=Sum('tax__tax_percentage'))['tax_sum']
        #     self.product_tax_json = product_tax
        product_tax_query = self.product.product_pro_tax.values('product', 'tax', 'tax__tax_name',
                                                                'tax__tax_percentage')
        product_tax = {i['tax']: [i['tax__tax_name'], i['tax__tax_percentage']] for i in product_tax_query}
        product_tax['tax_sum'] = product_tax_query.aggregate(tax_sum=Sum('tax__tax_percentage'))['tax_sum']
        self.product_tax_json = product_tax
        self.save()

    # def product_taxes(self):
    #     for tax in self.product.product_pro_tax.values('product', 'tax', 'tax__tax_name','tax__tax_percentage'):

    def get_product_tax_json(self):
        if not self.product_tax_json:
            self.set_product_tax_json()
        return self.product_tax_json.get('tax_sum')

    def get_effective_price(self):
        return round(self.effective_price, 2)

    def get_discounted_price(self):
        return round(self.discounted_price, 2)

    def return_pkg(self):
        return ShipmentPackagingMapping.objects.filter(ordered_product=self,
                                                       shipment_packaging__movement_type=ShipmentPackaging.RETURNED)


    def save(self, *args, **kwargs):
        if self.retailer_product:
            cart_product_mapping = self.ordered_product.order.ordered_cart.rt_cart_list.filter(
                retailer_product=self.retailer_product,
                product_type=self.product_type).last()
        else:
            cart_product_mapping = self.ordered_product.order.ordered_cart.rt_cart_list.filter(
                cart_product=self.product).last()
        if not self.effective_price:
            self.effective_price = cart_product_mapping.item_effective_prices

        self.discounted_price = cart_product_mapping.discounted_price
        if self.delivered_qty > 0:
            self.delivered_at_price = self.effective_price
        super().save(*args, **kwargs)


class Dispatch(OrderedProduct):
    class Meta:
        proxy = True


class DispatchProductMapping(OrderedProductMapping):
    class Meta:
        proxy = True
        verbose_name = _("To be Ship product")
        verbose_name_plural = _("To be Ship products")


class Shipment(OrderedProduct):
    class Meta:
        proxy = True
        verbose_name = _("Plan Shipment")
        verbose_name_plural = _("Plan Shipment")


class OrderedProductBatch(models.Model):
    REJECTION_REASON_CHOICE = Choices((1,'Near Expiry'), (2, 'Not Clean'), (3, 'Damaged'), (4, 'Expired'),
                                      (10, 'Other'))
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    bin_ids = models.CharField(max_length=17, null=True, blank=True, verbose_name='bin_id')
    pickup_inventory = models.ForeignKey(PickupBinInventory, null=True, related_name='rt_pickup_bin_inv',
                                         on_delete=models.DO_NOTHING)
    ordered_product_mapping = models.ForeignKey(OrderedProductMapping, null=True,
                                                related_name='rt_ordered_product_mapping', on_delete=models.DO_NOTHING)
    pickup = models.ForeignKey(Pickup, null=True, blank=True, on_delete=models.DO_NOTHING)
    bin = models.ForeignKey(BinInventory, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(0)],
                                   verbose_name='NO. OF PIECES TO SHIP')
    ordered_pieces = models.CharField(max_length=10, null=True, blank=True)
    delivered_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(0)],
                                        verbose_name="Delivered Pieces")
    already_shipped_qty = models.PositiveIntegerField(default=0)
    expiry_date = models.CharField(max_length=30, null=True, blank=True)
    returned_qty = models.PositiveIntegerField(default=0, verbose_name="Returned Pieces")
    damaged_qty = models.PositiveIntegerField(default=0, verbose_name="Damaged Pieces")
    returned_damage_qty = models.PositiveIntegerField(default=0, verbose_name="Damaged Return")
    returned_missing_qty = models.PositiveIntegerField(default=0, verbose_name="Damaged Missing")
    pickup_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name="Picked Pieces",
                                          validators=[MinValueValidator(0)])
    expired_qty = models.PositiveIntegerField(default=0, verbose_name="Expired Pieces")
    missing_qty = models.PositiveIntegerField(default=0, verbose_name="Missing Pieces")
    rejected_qty = models.PositiveIntegerField(default=0, verbose_name="Rejected Pieces")
    reason_for_rejection = models.PositiveIntegerField(choices=REJECTION_REASON_CHOICE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


    def clean(self, *args, **kwargs):
        if self.rejected_qty > 0 and self.reason_for_rejection is None:
            raise ValidationError(_('Please provide the reason for rejecting the item/s'))
        else:
            super(OrderedProductBatch, self).clean(*args, **kwargs)

    # def save(self, *args, **kwargs):
    #     if (self.delivered_qty or self.returned_qty or self.damaged_qty) and self.pickup_quantity != sum(
    #             [self.quantity, self.damaged_qty, self.expired_qty]):
    #         raise ValidationError(_('Picked quantity sum mismatched with picked pieces'))
    #     else:
    #         super().save(*args, **kwargs)


class ShipmentProductMapping(OrderedProductMapping):
    class Meta:
        proxy = True
        verbose_name = _("To be Ship product")
        verbose_name_plural = _("To be Ship products")

    def clean(self):
        ordered_qty = int(self.ordered_qty)
        shipped_qty = int(self.shipped_qty)
        max_qty_allowed = ordered_qty - int(self.shipped_qty_exclude_current)
        if max_qty_allowed < shipped_qty:
            raise ValidationError(
                _('Max. allowed Qty: %s') % max_qty_allowed,
            )

ShipmentProductMapping._meta.get_field('shipped_qty').verbose_name = 'No. of Pieces to Ship'


class ShipmentRescheduling(models.Model):
    CASH_NOT_AVAILABLE = 'cash_not_available'
    SHOP_CLOSED = 'shop_closed'
    RESCHEDULED_BY_SELLER = 'recheduler_by_seller'
    UNABLE_TO_ATTEMPT = 'unable_to_attempt'
    WRONG_ORDER = 'wrong_order'
    ITEM_MISS_MATCH = 'item_miss_match'
    DAMAGED_ITEM = 'damaged_item'

    RESCHEDULING_REASON = (
        (CASH_NOT_AVAILABLE, 'Cash not available'),
        (SHOP_CLOSED, 'Shop Closed'),
        (RESCHEDULED_BY_SELLER, 'Rescheduled by seller'),
        (UNABLE_TO_ATTEMPT, 'Unable to attempt')
    )

    shipment = models.ForeignKey(
        OrderedProduct, related_name='rescheduling_shipment',
        blank=False, null=True, on_delete=models.DO_NOTHING
    )
    trip = models.ForeignKey(
        Trip, related_name="rescheduling_shipment_trip",
        null=True, blank=False, on_delete=models.DO_NOTHING,
    )
    rescheduling_reason = models.CharField(
        max_length=50, choices=RESCHEDULING_REASON,
        blank=False, verbose_name='Reason for Rescheduling',
    )
    rescheduling_date = models.DateField(blank=False)
    rescheduled_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        get_user_model(),
        related_name='rescheduled_by',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Shipment Rescheduling'

    def __str__(self):
        return str("%s --> %s") % (self.shipment.invoice_no,
                                   self.rescheduling_date)

    def save(self, *args, **kwargs):
        self.created_by = get_current_user()
        # if self._state.adding is False:
        #     self.rescheduled_count += 1
        super().save(*args, **kwargs)


class ShipmentNotAttempt(models.Model):
    UNABLE_TO_ATTEMPT = 'unable_to_attempt'
    WRONG_ORDER = 'wrong_order'
    WRONG_DELIVERY_ADDRESS = 'wrong_delivery_address'
    ITEM_MISS_MATCH = 'item_miss_match'
    DIFFERENT_ROUTE = 'damaged_item'
    DAMAGED_ITEM = 'damaged_item'
    MORE_ITEMS_TO_CARRY = 'more_items_to_carry'

    NOT_ATTEMPT_REASON = (
        (UNABLE_TO_ATTEMPT, 'UNABLE TO ATTEMPT'),
        (WRONG_ORDER, 'WRONG ORDER'),
        (WRONG_DELIVERY_ADDRESS, 'WRONG DELIVERY ADDRESS'),
        (ITEM_MISS_MATCH, 'ITEM MISS MATCH'),
        (DIFFERENT_ROUTE, 'DIFFERENT ROUTE'),
        (DAMAGED_ITEM, 'DAMAGED ITEM'),
        (MORE_ITEMS_TO_CARRY, 'MORE ITEMS TO CARRY')
    )

    shipment = models.ForeignKey(
        OrderedProduct, related_name='not_attempt_shipment',
        blank=False, null=True, on_delete=models.DO_NOTHING
    )
    trip = models.ForeignKey(
        Trip, related_name="not_attempt_shipment_trip",
        null=True, blank=False, on_delete=models.DO_NOTHING,
    )
    not_attempt_reason = models.CharField(
        max_length=50, choices=NOT_ATTEMPT_REASON,
        blank=False, verbose_name='Reason for Not Attempt',
    )
    created_by = models.ForeignKey(
        get_user_model(),
        related_name='delivery_person',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Shipment Not Attempt'

    def __str__(self):
        return str(self.shipment.invoice_no)

    def save(self, *args, **kwargs):
        self.created_by = get_current_user()
        super().save(*args, **kwargs)


class Commercial(Trip):
    class Meta:
        proxy = True
        verbose_name = _("Commercial")
        verbose_name_plural = _("Commercial")

    def clean(self):
        pass
        # shipment_status_list = ['FULLY_RETURNED_AND_VERIFIED', 'PARTIALLY_DELIVERED_AND_VERIFIED',
        #                         'FULLY_DELIVERED_AND_VERIFIED']
        # super(Commercial, self).clean()
        # for shipment in self.rt_invoice_trip:
        #     if shipment.shipment_status not in shipment_status_list:
        #         raise ValidationError(_("Some shipments are not in Verified stage. Please verify them before closing "
        #                                 "the trip"))
        #         break

    def change_shipment_status(self):
        self.rt_invoice_trip.update(
            shipment_status=Case(
                When(shipment_status='FULLY_RETURNED_AND_VERIFIED',
                     then=Value('FULLY_RETURNED_AND_CLOSED')),
                When(shipment_status='PARTIALLY_DELIVERED_AND_VERIFIED',
                     then=Value('PARTIALLY_DELIVERED_AND_CLOSED')),
                When(shipment_status='FULLY_DELIVERED_AND_VERIFIED',
                     then=Value('FULLY_DELIVERED_AND_CLOSED')),
                default=F('shipment_status')))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.trip_status == Trip.PAYMENT_VERIFIED:
            self.change_shipment_status()


class CustomerCare(models.Model):
    order_id = models.ForeignKey(
        Order, on_delete=models.DO_NOTHING, null=True, blank=True
    )
    phone_number = models.CharField(max_length=10, blank=True, null=True)
    complaint_id = models.CharField(max_length=255, null=True, blank=True)
    email_us = models.URLField(default='help@gramfactory.com')
    issue_date = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    issue_status = models.CharField(
        max_length=20, choices=MESSAGE_STATUS,
        default='pending', null=True, blank=True
    )
    select_issue = models.CharField(
        verbose_name="Issue", max_length=100,
        choices=SELECT_ISSUE, null=True, blank=True
    )
    complaint_detail = models.CharField(max_length=2000, null=True)

    def __str__(self):
        return self.complaint_id or "--"

    @property
    def contact_number(self):
        if self.phone_number:
            return self.phone_number

    @property
    def seller_shop(self):
        if self.order_id:
            return self.order_id.seller_shop

    @property
    def retailer_shop(self):
        if self.order_id:
            return self.order_id.buyer_shop

    @property
    def retailer_name(self):
        if self.order_id:
            if self.order_id.buyer_shop:
                if self.order_id.buyer_shop.shop_owner.first_name:
                    return self.order_id.buyer_shop.shop_owner.first_name
        if self.phone_number:
            if User.objects.filter(phone_number=self.phone_number).exists():
                username = User.objects.get(phone_number=self.phone_number).first_name
                return username

    @property
    def comment_display(self):
        return format_html_join(
            "", "{}<br><br>",
            ((c.comment,
              ) for c in self.customer_care_comments.all())
        )

    comment_display.fget.short_description = 'Comments'

    @property
    def comment_date_display(self):
        return format_html_join(
            "", "{}<br><br>",
            ((c.created_at,
              ) for c in self.customer_care_comments.all())
        )

    comment_date_display.fget.short_description = 'Comment Date'

    def save(self, *args, **kwargs):
        super(CustomerCare, self).save()
        self.complaint_id = "CustomerCare/Message/%s" % self.pk
        super(CustomerCare, self).save()


class ResponseComment(models.Model):
    customer_care = models.ForeignKey(CustomerCare, related_name='customer_care_comments', null=True, blank=True,
                                      on_delete=models.DO_NOTHING)
    comment = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Comment Date")

    def __str__(self):
        return ''


class Payment(models.Model):
    PAYMENT_DONE_APPROVAL_PENDING = "payment_done_approval_pending"
    CASH_COLLECTED = "cash_collected"
    APPROVED_BY_FINANCE = "approved_by_finance"
    PAYMENT_STATUS = (
        (PAYMENT_DONE_APPROVAL_PENDING, "Payment done approval pending"),
        (CASH_COLLECTED, "Cash Collected"),
        (APPROVED_BY_FINANCE, "Approved by finance")
    )

    order_id = models.ForeignKey(
        Order, related_name='rt_payment',
        on_delete=models.DO_NOTHING, null=True
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')
    payment_choice = models.CharField(verbose_name="Payment Mode", max_length=30, choices=PAYMENT_MODE_CHOICES,
                                      default='cash_on_delivery')
    neft_reference_number = models.CharField(max_length=255, null=True, blank=True)
    imei_no = models.CharField(max_length=100, null=True, blank=True)
    payment_status = models.CharField(max_length=50, null=True, blank=True, choices=PAYMENT_STATUS,
                                      default=PAYMENT_DONE_APPROVAL_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Payment, self).save()
        self.name = "Payment/%s" % self.pk
        super(Payment, self).save()


class Return(models.Model):
    invoice_no = models.ForeignKey(
        OrderedProduct, on_delete=models.DO_NOTHING,
        null=True, verbose_name='Shipment Id'
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    shipped_by = models.ForeignKey(
        get_user_model(),
        related_name='return_shipped_product_ordered_by_user',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    received_by = models.ForeignKey(
        get_user_model(),
        related_name='return_ordered_product_received_by_user',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='return_last_modified_user_order',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        super(Return, self).save()
        self.name = "Return/%s" % self.pk
        super(Return, self).save()


class ReturnProductMapping(models.Model):
    return_id = models.ForeignKey(
        Return, related_name='rt_product_return_product_mapping',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    returned_product = models.ForeignKey(
        Product, related_name='rt_product_return_product',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    total_returned_qty = models.PositiveIntegerField(default=0)
    reusable_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    last_modified_by = models.ForeignKey(
        get_user_model(),
        related_name='return_last_modified_user_return_product',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    manufacture_date = models.DateField()
    expiry_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str('')

    def clean(self):
        super(ReturnProductMapping, self).clean()
        total_returned_qty = self.reusable_qty + self.damaged_qty
        if total_returned_qty != self.total_returned_qty:
            raise ValidationError(
                """Sum of Reusable quantity and damaged
                quantity must be equal to total returned quantity"""
            )

    def get_shop_specific_products_prices_sp_return(self):
        return self.returned_product.product_pro_price.filter(
            shop__shop_type__shop_type='sp', status=True
        )

    def get_products_gst_tax_return(self):
        return self.returned_product.product_pro_tax.filter(
            tax__tax_type='gst'
        )

    def get_products_gst_cess_return(self):
        return self.returned_product.product_pro_tax.filter(
            tax__tax_type='cess'
        )


class Note(models.Model):
    RETURN = 'RETURN'
    DISCOUNTED = 'DISCOUNTED'

    CREDIT_NOTE_CHOICES = (
        (RETURN, 'Return'),
        (DISCOUNTED, 'Discounted'),
    )
    shop = models.ForeignKey(Shop, related_name='credit_notes', null=True, blank=True, on_delete=models.DO_NOTHING)
    credit_note_id = models.CharField(max_length=255, null=True, blank=True)
    shipment = models.ForeignKey(OrderedProduct, null=True, blank=True, on_delete=models.DO_NOTHING,
                                 related_name='credit_note')
    note_type = models.CharField(
        max_length=255, choices=NOTE_TYPE_CHOICES, default='credit_note'
    )
    amount = models.FloatField(default=0)
    tcs_amount = models.FloatField(default=0)
    note_total = models.FloatField()
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_note',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    credit_note_type = models.CharField(max_length=50, choices=CREDIT_NOTE_CHOICES, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Credit Note"
        verbose_name_plural = "Credit Notes"

    def __str__(self):
        return str(self.credit_note_id)

    @property
    def invoice_no(self):
        if self.shipment:
            return self.shipment.invoice_no

    @property
    def note_amount(self):
        if self.shipment:
            return round(self.note_total)

    @property
    def is_igst_applicable(self):
        return self.shipment.is_igst_applicable



class Feedback(models.Model):
    STAR1 = '1'
    STAR2 = '2'
    STAR3 = '3'
    STAR4 = '4'
    STAR5 = '5'

    STAR_CHOICE = (
        (STAR1, '1 Star'),
        (STAR2, '2 Star'),
        (STAR3, '3 Star'),
        (STAR4, '4 Star'),
        (STAR5, '5 Star'),
    )
    user = models.ForeignKey(get_user_model(), related_name='user_feedback',
                             on_delete=models.CASCADE)
    shipment = models.OneToOneField(OrderedProduct,
                                    related_name='shipment_feedback',
                                    on_delete=models.CASCADE)
    delivery_experience = models.CharField(max_length=2, choices=STAR_CHOICE,
                                           null=True, blank=True)
    overall_product_packaging = models.CharField(max_length=2,
                                                 choices=STAR_CHOICE,
                                                 null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=False)


class OrderReturn(models.Model):
    PAYMENT_MODE_POS = (
        ('cash', 'Cash Payment'),
        ('online', 'Online Payment'),
        ('credit', 'Credit Payment')
    )
    RETURN_STATUS = (
        ('created', "Created"),
        ('completed', "Completed")
    )
    WRONG_ORDER = 0
    ITEM_MISS_MATCH = 1
    DAMAGED_ITEM = 2
    NEAR_EXPIRY = 3
    MANUFACTURING_DEFECT = 4
    RETURN_REASON = (
        (WRONG_ORDER, 'Wrong Order'),
        (ITEM_MISS_MATCH, 'Item miss match'),
        (DAMAGED_ITEM, 'Damaged item'),
        (NEAR_EXPIRY, 'Near Expiry'),
        (MANUFACTURING_DEFECT, 'Manufacturing Defect'),
    )
    order = models.ForeignKey(Order, related_name='rt_return_order', on_delete=models.DO_NOTHING)
    processed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.DO_NOTHING)
    offers = JSONField(null=True, blank=True)
    free_qty_map = JSONField(null=True, blank=True)
    return_reason = models.CharField(
        max_length=50, choices=RETURN_REASON,
        null=True, blank=True, verbose_name='Reason for Return',
    )
    refund_amount = models.FloatField(default=0)
    refund_points = models.IntegerField(default=0)
    discount_adjusted = models.FloatField(default=0)
    refund_mode = models.CharField(max_length=50, choices=PAYMENT_MODE_POS, default="cash")
    status = models.CharField(max_length=200, choices=RETURN_STATUS, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @property
    def return_value(self):
        return_value = 0
        for item in self.rt_return_list.all():
            return_value += item.return_value
        return return_value


class CreditNote(models.Model):
    credit_note_id = models.CharField(max_length=30)
    order_return = models.ForeignKey(OrderReturn, related_name="credit_note_order_return_mapping",
                                     on_delete=models.DO_NOTHING, unique=True)
    credit_note_pdf = models.FileField(upload_to='shop_photos/shop_name/documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @property
    def pdf_name(self):
        return "CreditNote_%s.pdf" % (self.credit_note_id)


class ReturnItems(models.Model):
    return_id = models.ForeignKey(OrderReturn, related_name='rt_return_list', on_delete=models.DO_NOTHING)
    ordered_product = models.ForeignKey(OrderedProductMapping, related_name='rt_return_ordered_product',
                                        on_delete=models.DO_NOTHING)
    return_qty = models.DecimalField(max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @property
    def return_value(self):
        return self.return_qty * self.ordered_product.selling_price


def update_full_part_order_status(shipment):
    shipment_products_dict = shipment.order.rt_order_order_product \
        .aggregate(shipped_qty=Sum('rt_order_product_order_product_mapping__shipped_qty'))
    cart_products_dict = shipment.order.ordered_cart.rt_cart_list \
        .aggregate(total_no_of_pieces=Sum('no_of_pieces'))
    total_shipped_qty = shipment_products_dict.get('shipped_qty')
    ordered_qty = cart_products_dict.get('total_no_of_pieces')
    order = shipment.order
    if ordered_qty == total_shipped_qty:
        order.order_status = Order.FULL_SHIPMENT_CREATED
    else:
        order.order_status = Order.PARTIAL_SHIPMENT_CREATED
    order.save()


@task
def assign_update_picker_to_shipment(shipment_id):
    shipment = OrderedProduct.objects.get(pk=shipment_id)
    if shipment.shipment_status == "SHIPMENT_CREATED" and shipment.order.ordered_cart.cart_type not in ['BASIC', 'ECOM']:
        # assign shipment to picklist
        # tbd : if manual(by searching relevant picklist id) or automated
        if shipment.order.picker_order.filter(picking_status="picking_assigned", shipment__isnull=True).exists():
            picker_lists = shipment.order.picker_order.filter(picking_status="picking_assigned",
                                                              shipment__isnull=True).update(shipment=shipment)
        elif shipment.shipment_status == OrderedProduct.READY_TO_SHIP:
            if shipment.picker_shipment.all().exists():
                shipment.picker_shipment.all().update(picking_status="picking_complete")


def add_to_putaway_on_partail(shipment_id):
    shipment = OrderedProduct.objects.get(pk=shipment_id)
    flag = "partial_shipment"
    common_on_return_and_partial(shipment, flag)


def add_to_putaway_on_return(shipment_id):
    shipment = OrderedProduct.objects.get(pk=shipment_id)
    flag = "return"
    common_on_return_and_partial(shipment, flag)


# @receiver(post_save, sender=OrderedProduct)
# def update_picking_status(sender, instance=None, created=False, **kwargs):
#     '''
#     Method to update picking status
#     '''
#     # assign_update_picker_to_shipment.delay(instance.id)
#     assign_update_picker_to_shipment(instance.id)


# @receiver(post_save, sender=Order)
# def assign_picklist(sender, instance=None, created=False, **kwargs):
#     '''
#     Method to update picking status
#     '''
#     #assign shipment to picklist once SHIPMENT_CREATED
#     if created:
#         # assign piclist to order
#         try:
#             pincode = "00" #instance.shipping_address.pincode
#         except:
#             pincode = "00"
#         PickerDashboard.objects.create(
#             order=instance,
#             picking_status="picking_pending",
#             picklist_id= generate_picklist_id(pincode), #get_random_string(12).lower(), ##generate random string of 12 digits
#             )


# post_save.connect(get_order_report, sender=Order)

@receiver(post_save, sender=Order)
def create_order_no(sender, instance=None, created=False, **kwargs):
    """
        Order number creation
        Cart order_id add
    """
    if not instance.order_no and instance.seller_shop and instance.seller_shop:
        if instance.ordered_cart.cart_type in ['RETAIL', 'BASIC', 'AUTO']:
            order_no = common_function.order_id_pattern(
                sender, 'order_no', instance.pk,
                instance.seller_shop.
                    shop_name_address_mapping.filter(
                    address_type='billing').last().pk)
            while Order.objects.filter(order_no=order_no).exists():
                order_no = common_function.order_id_pattern(
                    sender, 'order_no', instance.pk,
                    instance.seller_shop.
                        shop_name_address_mapping.filter(
                        address_type='billing').last().pk)
            instance.order_no = order_no
        if instance.ordered_cart.cart_type in ['ECOM', 'SUPERSTORE']:
            const = "EO" if instance.ordered_cart.cart_type == 'ECOM' else "ST"
            instance.order_no = common_function.order_id_pattern(
                sender, 'order_no', instance.pk,
                instance.seller_shop.
                    shop_name_address_mapping.filter(
                    address_type='billing').last().pk, const)
        elif instance.ordered_cart.cart_type == 'BULK':
            instance.order_no = common_function.order_id_pattern_bulk(
                sender, 'order_no', instance.pk,
                instance.seller_shop.
                    shop_name_address_mapping.filter(
                    address_type='billing').last().pk)
        elif instance.ordered_cart.cart_type == 'DISCOUNTED':
            instance.order_no = common_function.order_id_pattern_discounted(
                sender, 'order_no', instance.pk,
                instance.seller_shop.
                    shop_name_address_mapping.filter(
                    address_type='billing').last().pk)
        instance.save()
        # Update order id in cart
        Cart.objects.filter(id=instance.ordered_cart.id).update(order_id=instance.order_no)


@receiver(post_save, sender=Payment)
def order_notification(sender, instance=None, created=False, **kwargs):
    if created:
        if instance.order_id.buyer_shop.shop_owner.first_name:
            username = instance.order_id.buyer_shop.shop_owner.first_name
        else:
            username = instance.order_id.buyer_shop.shop_owner.phone_number
        order_no = str(instance.order_id)
        total_amount = str(instance.order_id.total_final_amount)
        shop_name = str(instance.order_id.ordered_cart.buyer_shop.shop_name)
        items_count = instance.order_id.ordered_cart.rt_cart_list.count()
        data = {}
        data['username'] = username
        data['phone_number'] = instance.order_id.ordered_by
        data['order_no'] = order_no
        data['items_count'] = items_count
        data['total_amount'] = total_amount
        data['shop_name'] = shop_name

        user_id = instance.order_id.ordered_by.id
        activity_type = "ORDER_RECEIVED"
        from notification_center.models import Template
        template = Template.objects.get(type="ORDER_RECEIVED").id
        # from notification_center.tasks import send_notification
        # send_notification(user_id=user_id, activity_type=template, data=data)
        try:
            message = SendSms(phone=instance.order_id.buyer_shop.shop_owner.phone_number,
                              body="Hi %s, We have received your order no. %s with %s items and totalling to %s Rupees for your shop %s. We will update you further on shipment of the items." \
                                   " Thanks," \
                                   " Team GramFactory" % (username, order_no, items_count, total_amount, shop_name))
            message.send()
        except Exception as e:
            logger.exception("Unable to send SMS for order : {}".format(order_no))


@receiver(post_save, sender=PickerDashboard)
def update_order_status_from_picker(sender, instance=None, created=False, **kwargs):
    if instance.picking_status == PickerDashboard.PICKING_ASSIGNED:
        if instance.order:
            if instance.order.order_status not in [Order.PICKING_PARTIAL_COMPLETE, Order.MOVED_TO_QC,
                                                   Order.PARTIAL_MOVED_TO_QC, Order.PICKING_COMPLETE]:
                instance.order.order_status = Order.PICKING_ASSIGNED
                instance.order.save()
        elif instance.repackaging:
            instance.repackaging.source_picking_status = 'picking_assigned'
            instance.repackaging.save()


# @receiver(post_save, sender=Trip)
# def update_order_status_from_trip(sender, instance=None, created=False,
#                                   **kwargs):
#     '''
#     Changing order status to READY_TO_DISPATCH or DISPATCHED when trip status
#     is READY and STARTED
#     '''
#     if instance.trip_status == Trip.READY:
#         order_ids = instance.rt_invoice_trip.values_list('order', flat=True)
#         Order.objects.filter(id__in=order_ids).update(order_status=Order.READY_TO_DISPATCH)
#     if instance.trip_status == Trip.STARTED:
#         order_ids = instance.rt_invoice_trip.values_list('order', flat=True)
#         Order.objects.filter(id__in=order_ids).update(order_status=Order.DISPATCHED)


@receiver(post_save, sender=OrderedProduct)
def update_order_status_from_shipment(sender, instance=None, created=False,
                                      **kwargs):
    '''
    Changing Order status to COMPLETED when shipment status is in
    ['FULLY_DELIVERED_AND_COMPLETED', 'FULLY_RETURNED_AND_COMPLETED',
     'PARTIALLY_DELIVED_AND_COMPLETED'] and changing to FULL_SHIPMENT_CREATED
    or PARTIAL_SHIPMENT_CREATED when either shipment is removed from trip or
    shipment status is RESCHEDULED.
    '''
    if 'COMPLETED' in instance.shipment_status:
        instance.order.order_status = Order.COMPLETED
        instance.order.save()
    if instance.shipment_status in [OrderedProduct.RESCHEDULED, OrderedProduct.NOT_ATTEMPT]:
        update_full_part_order_status(instance)


def update_last_mile_trip_package_count(trip_id):
    trip = Trip.objects.filter(id=trip_id).last()
    package_data = trip.get_package_data()
    trip.no_of_crates = package_data['no_of_crates']
    trip.no_of_packets = package_data['no_of_packs']
    trip.no_of_sacks = package_data['no_of_sacks']
    trip.save()


def update_dispatch_trip_package_count(trip_id):
    trip = DispatchTrip.objects.filter(id=trip_id).last()
    package_data = trip.get_package_data()
    trip.no_of_crates = package_data['no_of_crates']
    trip.no_of_packets = package_data['no_of_packs']
    trip.no_of_sacks = package_data['no_of_sacks']
    trip.save()


@receiver(post_save, sender=OrderedProduct)
def mark_shipment_cancelled_in_trip_shipment_mapping(sender, instance=None, created=False, **kwargs):
    """
        Changing LastMileTripShipmentMapping & DispatchTripShipmentMapping status to CANCELLED
        when shipment status is CANCELLED.
    """
    if instance.shipment_status == OrderedProduct.CANCELLED:
        last_mile_shipments_mapping = LastMileTripShipmentMapping.objects.filter(
                ~Q(trip__trip_status=Trip.CANCELLED), ~Q(shipment_status=LastMileTripShipmentMapping.CANCELLED),
                shipment=instance)
        if last_mile_shipments_mapping:
            for mapping in last_mile_shipments_mapping:
                mapping.shipment_status = LastMileTripShipmentMapping.CANCELLED
                mapping.save()
                update_last_mile_trip_package_count(mapping.trip.id)
        dispatch_shipments_mapping = DispatchTripShipmentMapping.objects.filter(
                ~Q(trip__trip_status=DispatchTrip.CANCELLED), ~Q(shipment_status=DispatchTripShipmentMapping.CANCELLED),
                shipment=instance)
        if dispatch_shipments_mapping:
            for mapping in dispatch_shipments_mapping:
                mapping.shipment_status = DispatchTripShipmentMapping.CANCELLED
                mapping.save()
                update_dispatch_trip_package_count(mapping.trip.id)


def populate_data_on_qc_pass(order):
    pick_bin_inv = PickupBinInventory.objects.filter(pickup__pickup_type_id=order.order_no)
    for i in pick_bin_inv:
        try:
            ordered_product_mapping = order.rt_order_order_product.all().last().rt_order_product_order_product_mapping.filter(
                product__id=i.pickup.sku.id).first()
            if OrderedProductBatch.objects.filter(batch_id=i.batch_id,
                                                  ordered_product_mapping=ordered_product_mapping).exists():
                shipment_product_batch = OrderedProductBatch.objects.filter(batch_id=i.batch_id,
                                                                            ordered_product_mapping=ordered_product_mapping).last()
                quantity = shipment_product_batch.quantity + i.pickup_quantity
                ordered_pieces = int(shipment_product_batch.ordered_pieces) + i.quantity
                shipment_product_batch.quantity = quantity
                shipment_product_batch.pickup_quantity = quantity
                shipment_product_batch.ordered_pieces = ordered_pieces
                shipment_product_batch.save()
            else:
                shipment_product_batch = OrderedProductBatch.objects.create(
                    batch_id=i.batch_id,
                    bin_ids=i.bin.bin.bin_id,
                    pickup_inventory=i,
                    ordered_product_mapping=ordered_product_mapping,
                    pickup=i.pickup,
                    bin=i.bin,  # redundant
                    quantity=i.pickup_quantity,
                    pickup_quantity=i.pickup_quantity,
                    expiry_date=get_expiry_date(i.batch_id),
                    delivered_qty=ordered_product_mapping.delivered_qty,
                    ordered_pieces=i.quantity
                )
            i.shipment_batch = shipment_product_batch
            i.save()
        except Exception as e:
            pass


# @receiver(post_save, sender=OrderedProductBatch)
# def create_putaway(sender, created=False, instance=None, *args, **kwargs):
#     if instance.returned_qty == 0 and instance.delivered_qty == 0 and created == False and instance.ordered_product_mapping.ordered_product.order.ordered_cart.cart_type not in ['BASIC', 'ECOM']:
#         add_to_putaway_on_partail(instance.ordered_product_mapping.ordered_product.id)


@receiver(post_save, sender=OrderedProductBatch)
def return_putaway(sender, created=False, instance=None, *args, **kwargs):
    complete_shipment_status = ['FULLY_RETURNED_AND_VERIFIED', 'PARTIALLY_DELIVERED_AND_VERIFIED',
                                'FULLY_DELIVERED_AND_VERIFIED']
    if instance.ordered_product_mapping.ordered_product.shipment_status in complete_shipment_status and instance.ordered_product_mapping.ordered_product.order.ordered_cart.cart_type not in ['BASIC', 'ECOM']:
        add_to_putaway_on_return(instance.ordered_product_mapping.ordered_product.id)


# post save method to check the pickup status is cancelled and after that update status cancelled in
# Picker Dashboard Model
@receiver(post_save, sender=Pickup)
def cancel_status_picker_dashboard(sender, instance=None, created=False, *args, **kwargs):
    if instance.status == 'picking_cancelled':
        picker_dashboard = PickerDashboard.objects.filter(order__order_no=instance.pickup_type_id)
        picker_dashboard.update(picking_status='picking_cancelled')


def check_franchise_inventory_update(trip):
    """
        1. Check if products were bought for Franchise Shops.
        2. Add delivered quantity as inventory for all product batches in all shipments to Franchise / Buyer Shop
    """

    if trip.trip_status == Trip.RETURN_VERIFIED:
        shipments = trip.rt_invoice_trip.all()
        for shipment in shipments:
            if (shipment.order.buyer_shop and shipment.order.buyer_shop.shop_type.shop_type == 'f' and
                    shipment.rt_order_product_order_product_mapping.last()):
                warehouse = shipment.order.buyer_shop
                if warehouse.id in [34037, 34016]:
                    info_logger.info("Franchise inventory update after Trip. Shop: {}, Order: {}".format(warehouse, shipment.order))
                    franchise_inventory_update(shipment, warehouse)


def franchise_inventory_update(shipment, warehouse):
    """
        Franchise Inventory update for a single shipment delivered to a Franchise shop after the trip is closed
    """

    initial_type = InventoryType.objects.filter(inventory_type='new').last(),
    final_type = InventoryType.objects.filter(inventory_type='normal').last(),
    initial_stage = InventoryState.objects.filter(inventory_state='new').last(),
    final_stage = InventoryState.objects.filter(inventory_state='total_available').last(),
    from franchise.models import get_default_virtual_bin_id
    bin_obj = Bin.objects.filter(warehouse=warehouse, bin_id=get_default_virtual_bin_id()).last()

    for shipment_product in shipment.rt_order_product_order_product_mapping.all():
        for shipment_product_batch in shipment_product.rt_ordered_product_mapping.all():
            product_batch_inventory_update_franchise(warehouse, bin_obj, shipment_product_batch, initial_type,
                                                     final_type, initial_stage, final_stage)


class DeliveryData(Trip):
    class Meta:
        proxy = True
        verbose_name = 'Delivery Performance Dashboard'
        verbose_name_plural = 'Delivery Performance Dashboard'


class PickerPerformanceData(PickerDashboard):
    class Meta:
        proxy = True
        verbose_name = 'Picker Performance Dashboard'
        verbose_name_plural = 'Picker Performance Dashboard'


class ShipmentPackaging(BaseTimestampUserModel):
    CRATE, SACK, BOX = 'CRATE', 'SACK', 'BOX'
    PACKAGING_TYPE_CHOICES = Choices(
        (CRATE, 'Crate'),
        (SACK, 'Sack'),
        (BOX, 'Box')
    )
    REASON_FOR_REJECTION = Choices((1, 'Package not found'), (2, 'Faulty package'), (10, 'Other'))
    DISPATCH_STATUS_CHOICES = Choices(
        ('PACKED', 'Packed'),
        ('READY_TO_DISPATCH', 'Ready to dispatch'),
        ('REJECTED', 'Rejected'),
        ('DISPATCHED', 'Dispatched'),
        ('DELIVERED', 'Delivered'),
        ('RETURN_VERIFIED', 'Return Verified'),
        ('RETURN_MISSING', 'Return Missing'),
        ('RETURN_DAMAGED', 'Return Damaged'),
    )
    LABEL_MISSING, LABEL_DAMAGED, OTHER = 'LABEL_MISSING', 'LABEL_DAMAGED', 'OTHER'
    RETURN_REMARK_CHOICES = (
        (LABEL_MISSING, 'Label Missing'),
        (LABEL_DAMAGED, 'Label Damaged'),
        (OTHER, 'Other'),
    )
    RETURNED, RESCHEDULED, NOT_ATTEMPT, DISPATCH = 'RETURNED', 'RESCHEDULED', 'NOT_ATTEMPT', 'DISPATCH'
    MOVEMENT_TYPE_CHOICES = (
        (RETURNED, 'Returned'),
        (RESCHEDULED, 'Rescheduled'),
        (NOT_ATTEMPT, 'Not Attempt'),
        (DISPATCH, 'Dispatch'),
    )
    warehouse = models.ForeignKey(Shop, on_delete=models.DO_NOTHING)
    shipment = models.ForeignKey(OrderedProduct, related_name='shipment_packaging', on_delete=models.DO_NOTHING)
    packaging_type = models.CharField(max_length=50, choices=PACKAGING_TYPE_CHOICES)
    crate = models.ForeignKey(Crate, related_name='crates_shipments', null=True, on_delete=models.DO_NOTHING)
    status = models.CharField(max_length=50, choices=DISPATCH_STATUS_CHOICES, default=DISPATCH_STATUS_CHOICES.PACKED)
    reason_for_rejection = models.CharField(max_length=30, choices=REASON_FOR_REJECTION, null=True)
    movement_type = models.CharField(default=DISPATCH, max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    return_remark = models.CharField(max_length=50, choices=RETURN_REMARK_CHOICES, null=True)


class ShipmentPackagingMapping(BaseTimestampUserModel):
    shipment_packaging = models.ForeignKey(ShipmentPackaging, related_name='packaging_details',
                                           on_delete=models.DO_NOTHING)
    ordered_product = models.ForeignKey(OrderedProductMapping, related_name='shipment_product_packaging',
                                        on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField(null=True)
    return_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)
    missing_qty = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)


class ShipmentPackagingBatch(BaseTimestampUserModel):
    shipment_product_packaging = models.ForeignKey(ShipmentPackagingMapping, related_name='packaging_product_details',
                                                   on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50)
    return_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)


class DispatchTrip(BaseTimestampUserModel):
    NEW, STARTED, COMPLETED = 'NEW', 'STARTED', 'COMPLETED'
    UNLOADING, CLOSED, VERIFIED, CANCELLED = 'UNLOADING', 'CLOSED', 'VERIFIED', 'CANCELLED'

    DISPATCH_TRIP_STATUS = (
        (NEW, 'New'),
        (STARTED, 'Started'),
        (COMPLETED, 'Completed'),
        (UNLOADING, 'Unloading'),
        (CLOSED, 'Closed'),
        (VERIFIED, 'Verified'),
        (CANCELLED, 'Cancelled'),
    )

    FORWARD, BACKWARD = 'FORWARD', 'BACKWARD'

    DISPATCH_TRIP_TYPE = (
        (FORWARD, 'Forward'),
        (BACKWARD, 'Backward'),
    )
    seller_shop = models.ForeignKey(Shop, related_name='dispatch_trip_seller_shop', null=True,
                                    on_delete=models.DO_NOTHING)
    source_shop = models.ForeignKey(Shop, related_name='dispatch_trip_source_shop', null=True,
                                    on_delete=models.DO_NOTHING)
    destination_shop = models.ForeignKey(Shop, related_name='dispatch_trip_destination_shop', null=True,
                                         on_delete=models.DO_NOTHING)
    dispatch_no = models.CharField(max_length=50, null=True, unique=True)
    delivery_boy = models.ForeignKey(
        UserWithName, related_name='dispatch_trip_delivered_by_user', null=True,
        on_delete=models.DO_NOTHING, verbose_name='Delivery Boy'
    )
    vehicle_no = models.CharField(max_length=50)
    trip_type = models.CharField(max_length=100, default=FORWARD, choices=DISPATCH_TRIP_TYPE)
    trip_status = models.CharField(max_length=100, default=NEW, choices=DISPATCH_TRIP_STATUS)
    starts_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    opening_kms = models.PositiveIntegerField(default=0, null=True, blank=True,
                                              verbose_name="Vehicle Opening Trip(Kms)")
    closing_kms = models.PositiveIntegerField(default=0, null=True, blank=True,
                                              verbose_name="Vehicle Closing Trip(Kms)")
    weight = models.FloatField(null=True, default=0, verbose_name="Trip weight")
    no_of_empty_crates = models.PositiveIntegerField(default=0, null=True, blank=True,
                                                     verbose_name="Total empty crates shipped")
    no_of_crates = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="Total crates shipped")
    no_of_packets = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="Total packets shipped")
    no_of_sacks = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="Total sacks shipped")
    no_of_crates_check = models.PositiveIntegerField(default=0, null=True, blank=True,
                                                     verbose_name="Total crates collected")
    no_of_packets_check = models.PositiveIntegerField(default=0, null=True, blank=True,
                                                      verbose_name="Total packets collected")
    no_of_sacks_check = models.PositiveIntegerField(default=0, null=True, blank=True,
                                                    verbose_name="Total sacks collected")
    no_of_empty_crates_check = models.PositiveIntegerField(default=0, null=True, blank=True,
                                                    verbose_name="Total empty crates collected")
    weight = models.FloatField(null=True, default=0, verbose_name="Trip weight")

    class Meta:
        permissions = (
            ("can_plan_trip", "Can Plan Trip"),
        )

    def __str__(self):
        del_boy = "--"
        if self.delivery_boy:
            del_boy = self.delivery_boy.first_name if self.delivery_boy.first_name else self.delivery_boy.phone_number
        return "{} -> {}".format(
            self.dispatch_no,
            del_boy
        )

    @property
    def current_trip_status(self):
        trip_status = self.trip_status
        if trip_status:
            return str(self.get_trip_status_display())
        return str("-------")

    @property
    def no_of_shipments(self):
        return self.shipments_details.exclude(shipment_status__in=[DispatchTripShipmentMapping.LOADING_FOR_DC,
                                                                   DispatchTripShipmentMapping.CANCELLED]).count()

    @property
    def trip_id(self):
        return self.id

    def create_dispatch_no(self):
        date = datetime.date.today().strftime('%d%m%y')
        shop = self.source_shop_id
        shop_id_date = "%s/%s" % (shop, date)
        last_dispatch_no = DispatchTrip.objects.filter(
            dispatch_no__contains=shop_id_date)
        if last_dispatch_no.exists():
            dispatch_attempt = int(
                last_dispatch_no.last().dispatch_no.split('/')[-1])
            dispatch_attempt += 1
        else:
            dispatch_attempt = 1
        final_dispatch_no = "%s/%s/%s" % (
            'DIS', shop_id_date,
            dispatch_attempt)
        self.dispatch_no = final_dispatch_no

    @property
    def trip_amount(self):
        return self.shipments_details.filter(~Q(shipment_status='CANCELLED')) \
            .annotate(invoice_amount=RoundAmount(F('shipment__invoice__invoice_total')))\
            .aggregate(trip_amount=Sum(F('invoice_amount'), output_field=FloatField())).get('trip_amount')

    @property
    def trip_weight(self):

        if self.weight != 0:
            weight = self.weight/1000
        weight = round(weight, 2)
        return str(weight) + " Kg"

    __trip_status = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__trip_status = self.trip_status

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.create_dispatch_no()
        if self.trip_status != self.__trip_status and self.trip_status == self.STARTED:
            # self.trip_amount = self.total_trip_amount()
            self.starts_at = datetime.datetime.now()
        elif self.trip_status == self.COMPLETED:
            self.completed_at = datetime.datetime.now()
        super().save(*args, **kwargs)

    def dispathces(self):
        return mark_safe("<a href='/admin/retailer_to_sp/cart/trip-planning/%s/change/'>%s<a/>" % (
            self.pk, self.dispatch_no))

    def get_trip_weight(self):
        trip_weight = 0
        shipments_loaded = self.shipments_details.filter(~Q(shipment_status='CANCELLED'))
        for shipment_mapping in shipments_loaded:
            packages_loaded = shipment_mapping.trip_shipment_mapped_packages.filter(
                                ~Q(package_status__in=['CANCELLED', 'MISSING_AT_LOADING', 'DAMAGED_AT_LOADING']))
            for package_mapping in packages_loaded:
                package_weight = package_mapping.shipment_packaging.packaging_details.all()\
                                .aggregate(total_weight=Sum(F('ordered_product__product__weight_value') * F('quantity'),
                                           output_field=FloatField())).get('total_weight')
                trip_weight += package_weight if package_weight else 0
        return trip_weight

    def get_package_data(self):
        data = {'no_of_crates': 0, 'no_of_packs': 0, 'no_of_sacks': 0}

        shipments_loaded = self.shipments_details.filter(~Q(shipment_status='CANCELLED'))
        for shipment_mapping in shipments_loaded:
            packages_loaded = shipment_mapping.trip_shipment_mapped_packages.filter(
                                ~Q(package_status__in=['CANCELLED', 'MISSING_AT_LOADING', 'DAMAGED_AT_LOADING']))
            shipment_data = packages_loaded.aggregate(
                    no_of_crates=Sum(Case(When(shipment_packaging__packaging_type=ShipmentPackaging.CRATE, then=1),
                                            default=Value('0'), output_field=models.IntegerField(), )),
                    no_of_packs=Sum(Case(When(shipment_packaging__packaging_type=ShipmentPackaging.BOX, then=1),
                                             default=Value('0'), output_field=models.IntegerField(), )),
                    no_of_sacks=Sum(Case(When(shipment_packaging__packaging_type=ShipmentPackaging.SACK, then=1),
                                           default=Value('0'), output_field=models.IntegerField(), ))
                )

            data['no_of_crates'] += shipment_data['no_of_crates'] if shipment_data.get('no_of_crates') else 0
            data['no_of_packs'] += shipment_data['no_of_packs'] if shipment_data.get('no_of_packs') else 0
            data['no_of_sacks'] += shipment_data['no_of_sacks'] if shipment_data.get('no_of_sacks') else 0
        return data

    def total_empty_crates(self):
        empty_crates = self.trip_empty_crates.all().count()
        return empty_crates


class DispatchTripShipmentMapping(BaseTimestampUserModel):
    LOADING_FOR_DC, LOADED_FOR_DC = 'LOADING_FOR_DC', 'LOADED_FOR_DC'
    UNLOADING_AT_DC, UNLOADED_AT_DC = 'UNLOADING_AT_DC', 'UNLOADED_AT_DC'
    CANCELLED = 'CANCELLED'
    SHIPMENT_STATUS = (
        (LOADING_FOR_DC, 'Loading For Dispatch'),
        (LOADED_FOR_DC, 'Loaded For Dispatch'),
        (UNLOADING_AT_DC, 'Unloading At Dispatch'),
        (UNLOADED_AT_DC, 'Unloaded At Dispatch'),
        (CANCELLED, 'Cancelled'),
    )

    OKAY, PARTIALLY_MISSING_DAMAGED = 'OKAY', 'PARTIALLY_MISSING_DAMAGED'
    PARTIALLY_DAMAGED, PARTIALLY_MISSING = 'PARTIALLY_DAMAGED', 'PARTIALLY_MISSING'
    FULLY_DAMAGED, FULLY_MISSING = 'FULLY_DAMAGED', 'FULLY_MISSING'
    SHIPMENT_HEALTH = (
        (OKAY, 'Okay'),
        (PARTIALLY_MISSING_DAMAGED, 'Partially Missing & Damaged'),
        (PARTIALLY_DAMAGED, 'Partially Damaged'),
        (PARTIALLY_MISSING, 'Partially Missing'),
        (FULLY_DAMAGED, 'Fully Damaged'),
        (FULLY_MISSING, 'Fully Missing'),
    )
    trip = models.ForeignKey(DispatchTrip, related_name='shipments_details', on_delete=models.DO_NOTHING)
    shipment = models.ForeignKey(OrderedProduct, related_name='trip_shipment', on_delete=models.DO_NOTHING)
    shipment_status = models.CharField(max_length=100, choices=SHIPMENT_STATUS)
    shipment_health = models.CharField(max_length=100, choices=SHIPMENT_HEALTH)
    loaded_by = models.ForeignKey(User, related_name='dc_shipments_loaded',
                                  null=True, blank=True, on_delete=models.CASCADE)


class DispatchTripShipmentPackages(BaseTimestampUserModel):
    LOADED, UNLOADED = 'LOADED', 'UNLOADED'
    DAMAGED_AT_LOADING, DAMAGED_AT_UNLOADING = 'DAMAGED_AT_LOADING', 'DAMAGED_AT_UNLOADING'
    MISSING_AT_LOADING, MISSING_AT_UNLOADING = 'MISSING_AT_LOADING', 'MISSING_AT_UNLOADING'
    CANCELLED = 'CANCELLED'
    PARTIALLY_VERIFIED, VERIFIED = 'PARTIALLY_VERIFIED', 'VERIFIED'
    PACKAGE_STATUS = (
        (LOADED, 'Loaded'),
        (UNLOADED, 'Unloaded'),
        (DAMAGED_AT_LOADING, 'Damaged At Loading'),
        (DAMAGED_AT_UNLOADING, 'Damaged At Unloading'),
        (MISSING_AT_LOADING, 'Missing At Loading'),
        (MISSING_AT_UNLOADING, 'Missing At Unloading'),
        (CANCELLED, 'Cancelled'),
        (PARTIALLY_VERIFIED, 'Partially Verified'),
        (VERIFIED, 'Verified')
    )
    trip_shipment = models.ForeignKey(DispatchTripShipmentMapping, related_name='trip_shipment_mapped_packages',
                                      on_delete=models.DO_NOTHING)
    shipment_packaging = models.ForeignKey(ShipmentPackaging, related_name='trip_packaging_details',
                                           on_delete=models.DO_NOTHING)
    package_status = models.CharField(max_length=100, choices=PACKAGE_STATUS)


INVOICE_AVAILABILITY_CHOICES = Choices((1, 'ALL', 'All'), (2, 'ADDED', 'Added'), (3, 'NOT_ADDED', 'Not Added'))
PACKAGE_VERIFY_CHOICES = Choices((1, 'OK', 'Okay'), (2, 'DAMAGED', 'Damaged'), (3, 'MISSING', 'Missing'))
TRIP_TYPE_CHOICE = Choices(('LAST_MILE', 'Last Mile trip'), ('DISPATCH_FORWARD', 'Forward Dispatch Trip'),
                           ('DISPATCH_BACKWARD', 'Backward Dispatch Trip'))

RETURN_REMARK_CHOICES = Choices(('LABEL_MISSING', 'Label Missing'),('LABEL_DAMAGED', 'Label Damaged'),
                                ('OTHER', 'Other'))


class LastMileTripShipmentMapping(BaseTimestampUserModel):
    TO_BE_LOADED, LOADING_FOR_DC, LOADED_FOR_DC = 'TO_BE_LOADED', 'LOADING_FOR_DC', 'LOADED_FOR_DC'
    CANCELLED = 'CANCELLED'
    SHIPMENT_STATUS = (
        (TO_BE_LOADED, 'To be Loaded For Dispatch'),
        (LOADING_FOR_DC, 'Loading For Dispatch'),
        (LOADED_FOR_DC, 'Loaded For Dispatch'),
        (CANCELLED, 'Cancelled'),
    )

    OKAY, PARTIALLY_MISSING_DAMAGED = 'OKAY', 'PARTIALLY_MISSING_DAMAGED'
    PARTIALLY_DAMAGED, PARTIALLY_MISSING = 'PARTIALLY_DAMAGED', 'PARTIALLY_MISSING'
    FULLY_DAMAGED, FULLY_MISSING = 'FULLY_DAMAGED', 'FULLY_MISSING'
    SHIPMENT_HEALTH = (
        (OKAY, 'Okay'),
        (PARTIALLY_MISSING_DAMAGED, 'Partially Missing & Damaged'),
        (PARTIALLY_DAMAGED, 'Partially Damaged'),
        (PARTIALLY_MISSING, 'Partially Missing'),
        (FULLY_DAMAGED, 'Fully Damaged'),
        (FULLY_MISSING, 'Fully Missing'),
    )
    trip = models.ForeignKey(Trip, related_name='last_mile_trip_shipments_details', on_delete=models.DO_NOTHING)
    shipment = models.ForeignKey(OrderedProduct, related_name='last_mile_trip_shipment', on_delete=models.DO_NOTHING)
    shipment_status = models.CharField(max_length=100, choices=SHIPMENT_STATUS)
    shipment_health = models.CharField(max_length=100, null=True, blank=True, choices=SHIPMENT_HEALTH)
    loaded_by = models.ForeignKey(User, related_name='last_shipments_loaded',
                                  null=True, blank=True, on_delete=models.CASCADE)


class LastMileTripShipmentPackages(BaseTimestampUserModel):
    LOADED, DAMAGED_AT_LOADING = 'LOADED', 'DAMAGED_AT_LOADING'
    MISSING_AT_LOADING, CANCELLED = 'MISSING_AT_LOADING', 'CANCELLED'
    RETURN_VERIFIED, RETURN_MISSING, RETURN_DAMAGED = 'RETURN_VERIFIED', 'RETURN_MISSING', 'RETURN_DAMAGED'
    PACKAGE_STATUS = (
        (LOADED, 'Loaded'),
        (DAMAGED_AT_LOADING, 'Damaged At Loading'),
        (MISSING_AT_LOADING, 'Missing At Loading'),
        (RETURN_VERIFIED, 'Return Verified'),
        (RETURN_MISSING, 'Return Missing'),
        (RETURN_DAMAGED, 'Return Damaged'),
        (CANCELLED, 'Cancelled'),
    )
    trip_shipment = models.ForeignKey(LastMileTripShipmentMapping,
                                      related_name='last_mile_trip_shipment_mapped_packages',
                                      on_delete=models.DO_NOTHING)
    shipment_packaging = models.ForeignKey(ShipmentPackaging, related_name='last_mile_trip_packaging_details',
                                           on_delete=models.DO_NOTHING)
    package_status = models.CharField(max_length=100, choices=PACKAGE_STATUS, null=True)
    return_remark = models.CharField(max_length=100, choices=RETURN_REMARK_CHOICES, null=True)


class ShopCrate(BaseTimestampUserModel):
    shop = models.ForeignKey(Shop, on_delete=models.DO_NOTHING)
    crate = models.ForeignKey(Crate, related_name='shop_crates', null=True, on_delete=models.DO_NOTHING)
    is_available = models.BooleanField(default=False)

    def __str__(self):
        return str(self.crate) + "-" + str(self.shop)


class DispatchTripCrateMapping(BaseTimestampUserModel):
    LOADED, UNLOADED = 'LOADED', 'UNLOADED'
    DAMAGED_AT_LOADING, DAMAGED_AT_UNLOADING = 'DAMAGED_AT_LOADING', 'DAMAGED_AT_UNLOADING'
    MISSING_AT_UNLOADING = 'MISSING_AT_UNLOADING'
    CRATE_STATUS = (
        (LOADED, 'Loaded'),
        (UNLOADED, 'Unloaded'),
        (DAMAGED_AT_LOADING, 'Damaged At Loading'),
        (DAMAGED_AT_UNLOADING, 'Damaged At Unloading'),
        (MISSING_AT_UNLOADING, 'Missing At Unloading'),
    )
    trip = models.ForeignKey(DispatchTrip, related_name='trip_empty_crates', on_delete=models.DO_NOTHING)
    crate = models.ForeignKey(Crate, related_name='crate_trips', null=True, on_delete=models.DO_NOTHING)
    crate_status = models.CharField(max_length=50, null=True, blank=True, choices=CRATE_STATUS)

    def __str__(self):
        return str(self.crate) + "-" + str(self.trip)

class PickerUserAssignmentLog(models.Model):
    picker_dashboard = models.ForeignKey(PickerDashboard, on_delete=models.DO_NOTHING, related_name='+')
    initial_user = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING, related_name='+', null=True)
    final_user = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING)

    @staticmethod
    def log_user_change(instance, updated_by, last_user_id):
        PickerUserAssignmentLog.objects.create(
            picker_dashboard=instance,
            initial_user_id=last_user_id,
            final_user_id=instance.picker_boy_id,
            created_by=updated_by
        )


class EInvoiceData(Invoice):
    class Meta:
        proxy = True
        verbose_name = 'e-invoice'
        verbose_name_plural = 'e-invoices'


class ENoteData(Note):
    class Meta:
        proxy = True
        verbose_name = 'e-note'
        verbose_name_plural = 'e-notes'


class SearchKeywordLog(models.Model):
    search_term = models.CharField(max_length=100,null=True)
    search_frequency = models.IntegerField()
    def __str__(self):
        return self.search_term


class BuyerPurchaseData(models.Model):
    seller_shop = models.ForeignKey(Shop, related_name='shop_sale', on_delete=models.DO_NOTHING)
    buyer_shop = models.ForeignKey(Shop, related_name='buyer_purchase', on_delete=models.DO_NOTHING)
    fin_year = models.PositiveSmallIntegerField(validators=[MinValueValidator(2019),
                                                            MaxValueValidator(datetime.datetime.now().year)])
    total_purchase = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Buyer Purchase'
        verbose_name_plural = 'Buyer Purchase'
