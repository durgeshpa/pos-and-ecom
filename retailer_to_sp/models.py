import datetime
import logging
from decimal import Decimal

from celery.task import task
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, FloatField, Sum
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html, format_html_join
from django.utils.crypto import get_random_string

from accounts.middlewares import get_current_user
from addresses.models import Address
from retailer_backend.common_function import (
    order_id_pattern, brand_credit_note_pattern, getcredit_note_id,
    retailer_sp_invoice
)
from .utils import (order_invoices, order_shipment_status, order_shipment_amount, order_shipment_details_util,
                    order_shipment_date, order_delivery_date, order_cash_to_be_collected, order_cn_amount,
                    order_damaged_amount, order_delivered_value, order_shipment_status_reason,
                    picking_statuses, picker_boys, picklist_ids)
from shops.models import Shop, ShopNameDisplay
from brand.models import Brand
from addresses.models import Address
from brand.models import Brand
from otp.sms import SendSms
from products.models import Product, ProductPrice
from retailer_backend.common_function import (brand_credit_note_pattern,
                                              getcredit_note_id,
                                              order_id_pattern,
                                              retailer_sp_invoice)
from shops.models import Shop, ShopNameDisplay

from .utils import (order_invoices, order_shipment_amount,
                    order_shipment_details_util, order_shipment_status)

from accounts.models import UserWithName, User
from django.core.validators import RegexValidator
from django.contrib.postgres.fields import JSONField
from analytics.post_save_signal import get_order_report
from coupon.models import Coupon, CusotmerCouponUsage
from django.db.models import Sum
from django.db.models import Q



# from sp_to_gram.models import (OrderedProduct as SPGRN, OrderedProductMapping as SPGRNProductMapping)

logger = logging.getLogger(__name__)

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

MESSAGE_STATUS = (
    ("pending", "Pending"),
    ("resolved", "Resolved"),
)
SELECT_ISSUE = (
    ("Cancellation", "cancellation"),
    ("Return", "return"),
    ("Others", "others")
)

TRIP_STATUS = (
    ('READY', 'Ready'),
    ('CANCELLED', 'Cancelled'),
    ('STARTED', 'Started'),
    ('COMPLETED', 'Completed'),
#   ('READY_FOR_COMMERCIAL', 'Ready for commercial'),
    ('CLOSED', 'Closed'),
    ('TRANSFERRED', 'Transferred')
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

def generate_picklist_id(pincode):

    if PickerDashboard.objects.exists():
        last_picking = PickerDashboard.objects.last()
        picklist_id = last_picking.picklist_id

        new_picklist_id = "PIK/" + str(pincode)[-2:] +"/" +str(int(picklist_id.split('/')[2])+1)

    else:
        new_picklist_id = "PIK/" + str(pincode)[-2:] +"/" +str(1)

    return new_picklist_id


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
    order_id = models.CharField(max_length=255, null=True, blank=True)
    seller_shop = models.ForeignKey(
        Shop, related_name='rt_seller_shop_cart',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    buyer_shop = models.ForeignKey(
        Shop, related_name='rt_buyer_shop_cart',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    cart_status = models.CharField(
        max_length=200, choices=CART_STATUS,
        null=True, blank=True
    )
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_cart',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    offers = JSONField(null=True,blank=True)
    # cart_coupon_error_msg = models.CharField(
    #     max_length=255, null=True,
    #     blank=True, editable=False
    # )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Order Items Detail'

    def __str__(self):
        return "{}".format(self.order_id)

    @property
    def subtotal(self):
        try:
            return round(self.rt_cart_list.aggregate(subtotal_sum=Sum(F('cart_product_price__selling_price') * F('no_of_pieces'),output_field=FloatField()))['subtotal_sum'],2)
        except:
            return None

    @property
    def order_amount(self):
        item_effective_total = 0
        for m in self.rt_cart_list.all():
            item_effective_total += (m.item_effective_prices * m.no_of_pieces)
        # else:
        #     for m in self.rt_cart_list.all():
        #         if m.cart_product_price:
        #             item_effective_total += (m.cart_product_price.price_to_retailer * m.no_of_pieces)
        return round(item_effective_total, 2)

    @property
    def mrp_subtotal(self):
        try:
            return round(self.rt_cart_list.aggregate(subtotal_sum=Sum(F('cart_product_price__mrp') * F('no_of_pieces'),output_field=FloatField()))['subtotal_sum'],2)
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
        offers_list =[]
        discount_value = 0
        shop = self.seller_shop
        cart_products = self.rt_cart_list.all()
        date = datetime.datetime.now()
        discount_sum_sku = 0
        discount_sum_brand = 0
        sum = 0
        buyer_shop = self.buyer_shop
        if cart_products:
            for m in cart_products:
                parent_brand = m.cart_product.product_brand.brand_parent.id if m.cart_product.product_brand.brand_parent else None
                brand_coupons = Coupon.objects.filter(coupon_type = 'brand', is_active = True, expiry_date__gte = date).filter(Q(rule__brand_ruleset__brand = m.cart_product.product_brand.id)| Q(rule__brand_ruleset__brand = parent_brand)).order_by('rule__cart_qualifying_min_sku_value')
                b_list  =  [x.coupon_name for x in brand_coupons]
                cart_coupons = Coupon.objects.filter(coupon_type = 'cart', is_active = True, expiry_date__gte = date).order_by('rule__cart_qualifying_min_sku_value')
                c_list = [x.coupon_name for x in cart_coupons]
                sku_qty = int(m.qty)
                sku_no_of_pieces = int(m.cart_product.product_inner_case_size) * int(m.qty)
                price = m.cart_product.get_current_shop_price(shop, buyer_shop)
                sku_ptr = float(price.selling_price)
                coupon_times_used = CusotmerCouponUsage.objects.filter(shop = buyer_shop, product = m.cart_product, created_at__date = date.date()).count() if CusotmerCouponUsage.objects.filter(shop = buyer_shop, product = m.cart_product, created_at__date = date.date()) else 0
                for n in m.cart_product.purchased_product_coupon.filter(rule__is_active = True, rule__expiry_date__gte = date ):
                    for o in n.rule.coupon_ruleset.filter(is_active=True, expiry_date__gte = date):
                        if o.limit_per_user_per_day > coupon_times_used:
                            if n.rule.discount_qty_amount > 0:
                                if sku_qty >= n.rule.discount_qty_step:
                                    free_item = n.free_product.product_name
                                    discount_qty_step_multiple = int((sku_qty)/n.rule.discount_qty_step)
                                    free_item_amount = int((n.rule.discount_qty_amount) * discount_qty_step_multiple)
                                    sum += (sku_ptr * sku_no_of_pieces)
                                    offers_list.append({'type':'free', 'sub_type':'discount_on_product', 'coupon_id':o.id, 'coupon':o.coupon_name, 'discount_value':0, 'coupon_code':o.coupon_code, 'item':m.cart_product.product_name, 'item_sku':m.cart_product.product_sku, 'item_id':m.cart_product.id, 'free_item':free_item, 'free_item_amount':free_item_amount, 'coupon_type':'catalog', 'discounted_product_subtotal':(sku_ptr * sku_no_of_pieces), 'discounted_product_subtotal_after_sku_discount':(sku_ptr * sku_no_of_pieces), 'brand_id':m.cart_product.product_brand.id, 'applicable_brand_coupons':b_list, 'applicable_cart_coupons':c_list})
                            elif (n.rule.discount_qty_step >=1) and (n.rule.discount != None):
                                if sku_qty >= n.rule.discount_qty_step:
                                    if n.rule.discount.is_percentage == False:
                                        discount_value = n.rule.discount.discount_value
                                    elif n.rule.discount.is_percentage == True and (n.rule.discount.max_discount == 0):
                                        discount_value = round(((n.rule.discount.discount_value/100)* sku_no_of_pieces * sku_ptr), 2)
                                    elif n.rule.discount.is_percentage == True and (n.rule.discount.max_discount > ((n.rule.discount.discount_value/100)* (sku_no_of_pieces * sku_ptr))):
                                        discount_value = round(((n.rule.discount.discount_value/100)* sku_no_of_pieces * sku_ptr), 2)
                                    elif n.rule.discount.is_percentage == True and (n.rule.discount.max_discount < ((n.rule.discount.discount_value/100)* (sku_no_of_pieces * sku_ptr))) :
                                        discount_value = n.rule.discount.max_discount
                                    discount_sum_sku += round(discount_value, 2)
                                    discounted_product_subtotal = round((sku_no_of_pieces * sku_ptr) - discount_value, 2)
                                    sum += discounted_product_subtotal
                                    offers_list.append({'type':'discount', 'sub_type':'discount_on_product', 'coupon_id':o.id, 'coupon':o.coupon_name, 'coupon_code':o.coupon_code, 'item':m.cart_product.product_name, 'item_sku':m.cart_product.product_sku, 'item_id':m.cart_product.id, 'discount_value':discount_value, 'discount_total_sku':discount_sum_sku, 'coupon_type':'catalog', 'discounted_product_subtotal':discounted_product_subtotal, 'discounted_product_subtotal_after_sku_discount':discounted_product_subtotal, 'brand_id':m.cart_product.product_brand.id, 'applicable_brand_coupons':b_list, 'applicable_cart_coupons':c_list})
                if not any(d['item_id'] == m.cart_product.id for d in offers_list):
                    offers_list.append({'type':'no offer', 'sub_type':'no offer', 'item':m.cart_product.product_name, 'item_sku':m.cart_product.product_sku, 'item_id':m.cart_product.id, 'discount_value':0, 'discount_total_sku':discount_sum_sku, 'coupon_type':'catalog', 'discounted_product_subtotal':round((sku_ptr * sku_no_of_pieces), 2), 'discounted_product_subtotal_after_sku_discount':round((sku_ptr * sku_no_of_pieces), 2), 'brand_id':m.cart_product.product_brand.id,'cart_or_brand_level_discount':0, 'applicable_brand_coupons':b_list, 'applicable_cart_coupons':c_list})
            brand_coupons = Coupon.objects.filter(coupon_type = 'brand', is_active = True, expiry_date__gte = date).order_by('-rule__cart_qualifying_min_sku_value')
            array = list(filter(lambda d: d['coupon_type'] in 'catalog', offers_list))
            discount_value_brand = 0
            brands_specific_list = []
            for brand_coupon in brand_coupons:
                brands_list = []
                brand_product_subtotals= 0
                for brand in brand_coupon.rule.brand_ruleset.filter(rule__is_active = True, rule__expiry_date__gte = date ):
                    brands_list = []
                    brand_product_subtotals= 0
                    offer_brand = brand.brand
                    offer_brand_id = brand.brand.id
                    if offer_brand_id in brands_specific_list:
                        continue
                    brands_list.append(offer_brand_id)
                    brands_specific_list.append(offer_brand_id)
                    sub_brands_list = Brand.objects.filter(brand_parent_id = offer_brand_id)
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
                                discount_sum_brand+= round(brand_coupon.rule.discount.discount_value, 2)
                                offers_list.append({'type':'discount', 'sub_type':'discount_on_brand', 'coupon_id':brand_coupon.id, 'coupon':brand_coupon.coupon_name, 'coupon_code':brand_coupon.coupon_code, 'brand_name':offer_brand.brand_name, 'brand_id':offer_brand.id, 'discount_value':discount_value_brand, 'coupon_type':'brand', 'brand_product_subtotals':brand_product_subtotals, 'discount_sum_brand':discount_sum_brand})
                            elif brand_coupon.rule.discount.is_percentage == True and (brand_coupon.rule.discount.max_discount == 0):
                                discount_value_brand = round((brand_coupon.rule.discount.discount_value/100)* brand_product_subtotals, 2)
                                discount_sum_brand+= round(discount_value_brand, 2)
                                offers_list.append({'type':'discount', 'sub_type':'discount_on_brand', 'coupon_id':brand_coupon.id, 'coupon':brand_coupon.coupon_name, 'coupon_code':brand_coupon.coupon_code, 'brand_name':offer_brand.brand_name, 'brand_id':offer_brand.id, 'discount_value':discount_value_brand, 'coupon_type':'brand', 'brand_product_subtotals':brand_product_subtotals, 'discount_sum_brand':discount_sum_brand})
                            elif brand_coupon.rule.discount.is_percentage == True and (brand_coupon.rule.discount.max_discount < ((brand_coupon.rule.discount.discount_value/100)* brand_product_subtotals)) :
                                discount_value_brand = brand_coupon.rule.discount.max_discount
                                discount_sum_brand+= round(brand_coupon.rule.discount.max_discount, 2)
                                offers_list.append({'type':'discount', 'sub_type':'discount_on_brand', 'coupon_id':brand_coupon.id, 'coupon':brand_coupon.coupon_name, 'coupon_code':brand_coupon.coupon_code, 'brand_name':offer_brand.brand_name, 'brand_id':offer_brand.id, 'discount_value':discount_value_brand, 'coupon_type':'brand', 'brand_product_subtotals':brand_product_subtotals, 'discount_sum_brand':discount_sum_brand})
                        else:
                            brands_specific_list.pop()
            array1 = list(filter(lambda d: d['coupon_type'] in 'brand', offers_list))
            discount_value_cart = 0
            cart_coupons = Coupon.objects.filter(coupon_type = 'cart', is_active = True, expiry_date__gte = date).order_by('-rule__cart_qualifying_min_sku_value')
            cart_coupon_list = []
            i = 0
            coupon_applied = False
            if self.cart_status in ['active', 'pending']:
                cart_value = 0
                for product in self.rt_cart_list.all():
                    cart_value += float(product.cart_product.get_current_shop_price(self.seller_shop, self.buyer_shop).selling_price * product.no_of_pieces)
                cart_value -= discount_sum_sku
            if self.cart_status in ['ordered']:
                cart_value = (self.rt_cart_list.aggregate(value=Sum(F('cart_product_price__selling_price') * F('no_of_pieces'),output_field=FloatField()))['value']) - discount_sum_sku
            cart_items_count = self.rt_cart_list.count()
            for cart_coupon in cart_coupons:
                if cart_coupon.rule.cart_qualifying_min_sku_value and not cart_coupon.rule.cart_qualifying_min_sku_item:
                    cart_coupon_list.append(cart_coupon)
                    i+=1
                    if cart_value >=cart_coupon.rule.cart_qualifying_min_sku_value:
                        coupon_applied = True
                        if cart_coupon.rule.discount.is_percentage == False:
                            discount_value_cart = cart_coupon.rule.discount.discount_value
                            offers_list.append({'type':'discount', 'sub_type':'discount_on_cart', 'coupon_id':cart_coupon.id, 'coupon':cart_coupon.coupon_name, 'coupon_code':cart_coupon.coupon_code, 'discount_value':discount_value_cart, 'coupon_type':'cart'})
                        elif cart_coupon.rule.discount.is_percentage == True and (cart_coupon.rule.discount.max_discount == 0):
                            discount_value_cart = round((cart_coupon.rule.discount.discount_value/100)* cart_value, 2)
                            offers_list.append({'type':'discount', 'sub_type':'discount_on_cart', 'coupon_id':cart_coupon.id, 'coupon':cart_coupon.coupon_name, 'coupon_code':cart_coupon.coupon_code, 'discount_value':discount_value_cart, 'coupon_type':'cart'})
                        elif cart_coupon.rule.discount.is_percentage == True and (cart_coupon.rule.discount.max_discount > ((cart_coupon.rule.discount.discount_value/100)* cart_value)):
                            discount_value_cart = round((cart_coupon.rule.discount.discount_value/100)* cart_value, 2)
                            offers_list.append({'type':'discount', 'sub_type':'discount_on_cart', 'coupon_id':cart_coupon.id, 'coupon':cart_coupon.coupon_name, 'coupon_code':cart_coupon.coupon_code, 'discount_value':discount_value_cart, 'coupon_type':'cart'})
                        elif cart_coupon.rule.discount.is_percentage == True and (cart_coupon.rule.discount.max_discount < ((cart_coupon.rule.discount.discount_value/100)* cart_value)) :
                            discount_value_cart = cart_coupon.rule.discount.max_discount
                            offers_list.append({'type':'discount', 'sub_type':'discount_on_cart', 'coupon_id':cart_coupon.id, 'coupon':cart_coupon.coupon_name, 'coupon_code':cart_coupon.coupon_code, 'discount_value':discount_value_cart,  'coupon_type':'cart'})
                        break

            entice_text = ''
            if coupon_applied:
                next_index = 2
            else:
                next_index = 1
            if i > 1:
                next_cart_coupon_min_value = cart_coupon_list[i-next_index].rule.cart_qualifying_min_sku_value
                next_cart_coupon_min_value_diff = round(next_cart_coupon_min_value - cart_value + discount_value_cart,2)
                next_cart_coupon_discount = cart_coupon_list[i-next_index].rule.discount.discount_value if cart_coupon_list[i-next_index].rule.discount.is_percentage == False else (str(cart_coupon_list[i-next_index].rule.discount.discount_value) + '%')
                entice_text = "Shop for Rs %s more to avail a discount of Rs %s on the entire cart" % (next_cart_coupon_min_value_diff, next_cart_coupon_discount) if cart_coupon_list[i-next_index].rule.discount.is_percentage == False else "Shop for Rs %s more to avail a discount of %s on the entire cart" % (next_cart_coupon_min_value_diff, next_cart_coupon_discount)
                offers_list.append({'entice_text':entice_text, 'coupon_type': 'none', 'type': 'none', 'sub_type':'none'})
            elif i==1 and  not coupon_applied:
                next_cart_coupon_min_value = cart_coupon_list[i-next_index].rule.cart_qualifying_min_sku_value
                next_cart_coupon_min_value_diff = round(next_cart_coupon_min_value - cart_value,2)
                next_cart_coupon_discount = cart_coupon_list[i-next_index].rule.discount.discount_value if cart_coupon_list[i-next_index].rule.discount.is_percentage == False else (str(cart_coupon_list[i-next_index].rule.discount.discount_value) + '%')
                entice_text = "Shop for Rs %s more to avail a discount of Rs %s on the entire cart" % (next_cart_coupon_min_value_diff, next_cart_coupon_discount) if cart_coupon_list[i-next_index].rule.discount.is_percentage == False else "Shop for Rs %s more to avail a discount of %s on the entire cart" % (next_cart_coupon_min_value_diff, next_cart_coupon_discount)
                offers_list.append({'entice_text':entice_text, 'coupon_type': 'none', 'type': 'none', 'sub_type':'none'})
            else:
                entice_text = ''
                offers_list.append({'entice_text':entice_text, 'coupon_type': 'none', 'type': 'none', 'sub_type':'none'})

            if discount_sum_brand < discount_value_cart:
                for product in cart_products:
                    for i in array:
                        if product.cart_product.id == i['item_id']:
                            discounted_price_subtotal = round(((i['discounted_product_subtotal'] / cart_value) * discount_value_cart), 2)
                            i.update({'cart_or_brand_level_discount':discounted_price_subtotal})
                            discounted_product_subtotal = round(i['discounted_product_subtotal'] - discounted_price_subtotal, 2)
                            i.update({'discounted_product_subtotal':discounted_product_subtotal})
                            offers_list[:] = [coupon for coupon in offers_list if coupon.get('coupon_type') != 'brand']
            else:
                for product in cart_products:
                    for i in array:
                        for j in array1:
                            brand_parent = product.cart_product.product_brand.brand_parent.id if product.cart_product.product_brand.brand_parent else None
                            if product.cart_product.id == i['item_id'] and product.cart_product.product_brand.id == j['brand_id'] or product.cart_product.id == i['item_id'] and brand_parent == j['brand_id']:
                                discounted_price_subtotal = round(((i['discounted_product_subtotal'] / j['brand_product_subtotals']) * j['discount_value']), 2)
                                i.update({'cart_or_brand_level_discount':discounted_price_subtotal})
                                discounted_product_subtotal = round(i['discounted_product_subtotal'] - discounted_price_subtotal, 2)
                                i.update({'discounted_product_subtotal':discounted_product_subtotal})
                                offers_list[:] = [coupon for coupon in offers_list if coupon.get('coupon_type') != 'cart']


        return offers_list

    def save(self, *args, **kwargs):
        if self.cart_status == self.ORDERED:
            for cart_product in self.rt_cart_list.all():
                cart_product.get_cart_product_price(self.seller_shop.id, self.buyer_shop.id)

        super().save(*args, **kwargs)

    @property
    def buyer_contact_no(self):
        return self.buyer_shop.shop_owner.phone_number

    @property
    def seller_contact_no(self):
        return self.seller_shop.shop_owner.phone_number

    @property
    def date(self):
        return self.created_at.date()

    @property
    def time(self):
        return self.created_at.time()


@receiver(post_save, sender=Cart)
def create_order_id(sender, instance=None, created=False, **kwargs):
    if created:
        instance.order_id = order_id_pattern(
                                    sender, 'order_id', instance.pk,
                                    instance.seller_shop.
                                    shop_name_address_mapping.filter(
                                        address_type='billing').last().pk)
        instance.save()


class CartProductMapping(models.Model):
    cart = models.ForeignKey(Cart, related_name='rt_cart_list',null=True,
                             on_delete=models.DO_NOTHING
    )
    cart_product = models.ForeignKey(
        Product, related_name='rt_cart_product_mapping',null=True,
        on_delete=models.DO_NOTHING
    )
    cart_product_price = models.ForeignKey(
        ProductPrice, related_name='rt_cart_product_price_mapping',
        on_delete=models.DO_NOTHING, null=True, blank=True
    )
    qty = models.PositiveIntegerField(default=0)
    no_of_pieces = models.PositiveIntegerField(default=0)
    qty_error_msg = models.CharField(
        max_length=255, null=True,
        blank=True, editable=False
    )
    effective_price = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.cart_product.product_name

    @property
    def product_case_size(self):
        return self.cart_product.product_case_size.product_case_size

    @property
    def product_inner_case_size(self):
        return self.cart_product.product_inner_case_size

    @property
    def item_effective_prices(self):
        try:
            item_effective_price = 0
            if self.cart.offers:
                array = list(filter(lambda d: d['coupon_type'] in 'catalog', self.cart.offers))
                for i in array:
                    if self.cart_product.id == i['item_id']:
                        item_effective_price = (i.get('discounted_product_subtotal',0)) / self.no_of_pieces
            else:
                item_effective_price = float(self.cart_product_price.selling_price)
        except:
            logger.exception("Cart product price not found")
        return item_effective_price


    def set_cart_product_price(self, seller_shop_id, buyer_shop_id):
        self.cart_product_price = self.cart_product.\
            get_current_shop_price(seller_shop_id, buyer_shop_id)
        self.save()

    def get_cart_product_price(self, seller_shop_id, buyer_shop_id):
        if not self.cart_product_price:
            self.set_cart_product_price(seller_shop_id, buyer_shop_id)
        return self.cart_product_price

    def get_product_latest_mrp(self, shop):
        if self.cart_product_price:
            return self.cart_product_price.mrp
        else:
            return self.cart_product.get_current_shop_price(seller_shop_id, buyer_shop_id).mrp

    # def save(self, *args, **kwargs):
    #
    #     super().save(*args, **kwargs)

class Order(models.Model):
    ACTIVE = 'active'
    PENDING = 'pending'
    DELETED = 'deleted'
    ORDERED = 'ordered'
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

    ORDER_STATUS = (
        (ORDERED, 'Order Placed'),
        ('DISPATCH_PENDING', 'Dispatch Pending'),
        (ACTIVE, "Active"),
        (PENDING, "Pending"),
        (DELETED, "Deleted"),
        (DISPATCHED, "Dispatched"),
        (PARTIAL_DELIVERED, "Partially Delivered"),
        (DELIVERED, "Delivered"),
        (CLOSED, "Closed"),
        (PDAP, "Payment Done Approval Pending"),
        (ORDER_PLACED_DISPATCH_PENDING, "Order Placed Dispatch Pending"),
        ('PARTIALLY_SHIPPED', 'Partially Shipped'),
        ('SHIPPED', 'Shipped'),
        ('CANCELLED', 'Cancelled'),
        ('DENIED', 'Denied'),
        (PAYMENT_DONE_APPROVAL_PENDING, "Payment Done Approval Pending"),
        (OPDP, "Order Placed Dispatch Pending"),
        (PARTIALLY_SHIPPED_AND_CLOSED, "Partially shipped and closed"),
        (DENIED_AND_CLOSED, 'Denied and Closed')
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
        (SHORT, 'Item short')
    )

    #Todo Remove
    seller_shop = models.ForeignKey(
        Shop, related_name='rt_seller_shop_order',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    #Todo Remove
    buyer_shop = models.ForeignKey(
        Shop, related_name='rt_buyer_shop_order',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
    ordered_cart = models.OneToOneField(
        Cart, related_name='rt_order_cart_mapping',null=True,
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
    total_discount_amount = models.FloatField(default=0)
    total_tax_amount = models.FloatField(default=0)
    order_status = models.CharField(max_length=50,choices=ORDER_STATUS)
    #payment_status = models.CharField(max_length=50,choices=PAYMENT_STATUS, null=True, blank=True)
    #intended_mode_of_payment = models.CharField(max_length=50,choices=PAYMENT_MODE, null=True, blank=True)
    cancellation_reason = models.CharField(
        max_length=50, choices=CANCELLATION_REASON,
        null=True, blank=True, verbose_name='Reason for Cancellation',
    )
    order_closed = models.BooleanField(default=False, null=True, blank=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

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
    def picker_boy(self):
        return picker_boys(self.picker_dashboards())

    @property
    def picklist_id(self):
        return picklist_ids(self.picker_dashboards())

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
        if self.buyer_shop:
            return "%s - %s" % (self.buyer_shop, self.buyer_shop.shop_owner.phone_number)
        return "-"

class Trip(models.Model):
    seller_shop = models.ForeignKey(
        Shop, related_name='trip_seller_shop', null=True,
        on_delete=models.DO_NOTHING
    )
    dispatch_no = models.CharField(max_length=50, unique=True)
    delivery_boy = models.ForeignKey(
        UserWithName, related_name='order_delivered_by_user', null=True,
        on_delete=models.DO_NOTHING, verbose_name='Delivery Boy'
    )
    vehicle_no = models.CharField(max_length=50)
    trip_status = models.CharField(max_length=100, choices=TRIP_STATUS)
    e_way_bill_no = models.CharField(max_length=50, blank=True, null=True)
    starts_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    trip_amount = models.DecimalField(blank=True, null=True,
                                    max_digits=19, decimal_places=2)
    received_amount = models.DecimalField(blank=True, null=True,
                                    max_digits=19, decimal_places=2)
    #description = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.delivery_boy:
            delivery_boy_identifier = self.delivery_boy.first_name if self.delivery_boy.first_name else self.delivery_boy.phone_number
        else:
            delivery_boy_identifier = "--"
        return "{} -> {}".format(
            self.dispatch_no,
            delivery_boy_identifier
        )

    @property
    def total_crates_shipped(self):
        sum_crates_shipped = 0
        for m in self.rt_invoice_trip.all():
            sum_crates_shipped+=m.no_of_crates
        return sum_crates_shipped

    @property
    def total_packets_shipped(self):
        sum_packets_shipped = 0
        for m in self.rt_invoice_trip.all():
            sum_packets_shipped+=m.no_of_packets
        return sum_packets_shipped

    @property
    def total_sacks_shipped(self):
        sum_sacks_shipped = 0
        for m in self.rt_invoice_trip.all():
            sum_sacks_shipped+=m.no_of_sacks
        return sum_sacks_shipped

    @property
    def total_crates_collected(self):
        sum_crates_collected = 0
        for m in self.rt_invoice_trip.all():
            sum_crates_collected+=m.no_of_crates_check
        return sum_crates_collected

    @property
    def total_packets_collected(self):
        sum_packets_collected = 0
        for m in self.rt_invoice_trip.all():
            sum_packets_collected+=m.no_of_packets_check
        return sum_packets_collected

    @property
    def total_sacks_collected(self):
        sum_sacks_collected = 0
        for m in self.rt_invoice_trip.all():
            sum_sacks_collected+=m.no_of_sacks_check
        return sum_sacks_collected

    def create_dispatch_no(self):
        date = datetime.date.today().strftime('%d%m%y')
        shop = self.seller_shop_id
        shop_id_date = "%s/%s" % (shop, date)
        last_dispatch_no = Trip.objects.filter(
            dispatch_no__contains=shop_id_date)
        if last_dispatch_no:
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
                shipment.cash_to_be_collected())
        return round(sum(cash_to_be_collected), 2)

    def cash_collected_by_delivery_boy(self):
        cash_to_be_collected = []
        shipment_status_list = ['FULLY_DELIVERED_AND_COMPLETED', 'PARTIALLY_DELIVERED_AND_COMPLETED',
                                'FULLY_RETURNED_AND_COMPLETED', 'RESCHEDULED']
        trip_shipments = self.rt_invoice_trip.filter(shipment_status__in=shipment_status_list)
        for shipment in trip_shipments:
            cash_to_be_collected.append(
                shipment.cash_to_be_collected())
        return round(sum(cash_to_be_collected), 2)

    def total_paid_amount(self):
        from payments.models import ShipmentPayment
        trip_shipments = self.rt_invoice_trip.exclude(shipment_payment__parent_order_payment__parent_payment__payment_status='cancelled')
        total_amount  = cash_amount = online_amount = 0
        if trip_shipments.exists():
            shipment_payment_data = ShipmentPayment.objects.filter(shipment__in=trip_shipments)\
                .aggregate(Sum('paid_amount'))
            shipment_payment_cash = ShipmentPayment.objects.filter(shipment__in=trip_shipments, parent_order_payment__parent_payment__payment_mode_name="cash_payment")\
                .aggregate(Sum('paid_amount'))
            shipment_payment_online = ShipmentPayment.objects.filter(shipment__in=trip_shipments, parent_order_payment__parent_payment__payment_mode_name="online_payment")\
                .aggregate(Sum('paid_amount'))

            if shipment_payment_data['paid_amount__sum']:
                total_amount = round(shipment_payment_data['paid_amount__sum'], 2) #sum_paid_amount
            if shipment_payment_cash['paid_amount__sum']:
                cash_amount = round(shipment_payment_data['paid_amount__sum'], 2) #sum_paid_amount
            if shipment_payment_online['paid_amount__sum']:
                online_amount = round(shipment_payment_data['paid_amount__sum'], 2) #sum_paid_amount
        return total_amount, cash_amount, online_amount

    @property
    def total_received_amount(self):
        total_payment, _c , _o = self.total_paid_amount()
        return total_payment

    @property
    def received_cash_amount(self):
        _t , cash_payment, _o = self.total_paid_amount()
        return cash_payment

    @property
    def received_online_amount(self):
        _t, _c, online_payment= self.total_paid_amount()
        return online_payment

    @property
    def cash_to_be_collected_value(self):
        return self.cash_to_be_collected()

    @property
    def total_trip_shipments(self):
        trip_shipments = self.rt_invoice_trip.count()
        return trip_shipments

    def total_trip_amount(self):
        trip_shipments = self.rt_invoice_trip.all()
        trip_amount = []
        for shipment in trip_shipments:
            invoice_amount = float(shipment.invoice_amount)
            trip_amount.append(invoice_amount)
        amount = round(sum(trip_amount),2)
        return amount

    @property
    def total_trip_amount_value(self):
        return self.total_trip_amount()

    # @property
    def trip_weight(self):
        queryset = self.rt_invoice_trip.all()
        weight = sum([item.shipment_weight for item in queryset]) # Definitely takes more memory.
        #weight = self.rt_order_product_order_product_mapping.all().aggregate(Sum('product.weight_value'))['weight_value__sum']
        if weight != 0:
            weight /= 1000
        weight = round(weight,2)
        return str(weight) + " Kg"

    __trip_status = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__trip_status = self.trip_status

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.create_dispatch_no()
        if self.trip_status != self.__trip_status and self.trip_status == 'STARTED':
            self.trip_amount = self.total_trip_amount()
            self.starts_at = datetime.datetime.now()
        elif self.trip_status == 'COMPLETED':
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
        return self.rt_invoice_trip.all().count()

    @property
    def trip_id(self):
        return self.id

    @property
    def total_return_amount(self):
        return self.rt_invoice_trip.all().count()


class OrderedProduct(models.Model): #Shipment
    CLOSED = "closed"
    READY_TO_SHIP = "READY_TO_SHIP"
    RESCHEDULED = "RESCHEDULED"
    SHIPMENT_STATUS = (
        ('SHIPMENT_CREATED', 'QC Pending'),
        (READY_TO_SHIP, 'QC Passed'),
        ('READY_TO_DISPATCH', 'Ready to Dispatch'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('FULLY_RETURNED_AND_COMPLETED', 'Fully Returned and Completed'),
        ('PARTIALLY_DELIVERED_AND_COMPLETED', 'Partially Delivered and Completed'),
        ('FULLY_DELIVERED_AND_COMPLETED', 'Fully Delivered and Completed'),
        ('FULLY_RETURNED_AND_CLOSED', 'Fully Returned and Closed'),
        ('PARTIALLY_DELIVERED_AND_CLOSED', 'Partially Delivered and Closed'),
        ('FULLY_DELIVERED_AND_CLOSED', 'Fully Delivered and Closed'),
        ('CANCELLED', 'Cancelled'),
        (CLOSED, 'Closed'),
        (RESCHEDULED, 'Rescheduled'),
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
        (MANUFACTURING_DEFECT,'Manufacturing Defect'),
        (SHORT, 'Item short')
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
    invoice_no = models.CharField(max_length=255, null=True, blank=True)
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
    #payment_status = models.CharField(max_length=50,choices=PAYMENT_STATUS, null=True, blank=True)
    #is_payment_approved = models.BooleanField(default=False)
    no_of_crates = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="No. Of Crates Shipped")
    no_of_packets = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="No. Of Packets Shipped")
    no_of_sacks = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="No. Of Sacks Shipped")
    no_of_crates_check = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="No. Of Crates Collected")
    no_of_packets_check = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="No. Of Packets Collected")
    no_of_sacks_check = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name="No. Of Sacks Collected")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Invoice Date")
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Update Delivery/ Returns/ Damage'

    def __init__(self, *args, **kwargs):
        super(OrderedProduct, self).__init__(*args, **kwargs)
        if self.order:
            self._invoice_amount = 0
            self._cn_amount = 0
            self._damaged_amount = 0
            self._delivered_amount = 0
            shipment_products = self.rt_order_product_order_product_mapping.values('product','shipped_qty','returned_qty','damaged_qty').all()
            shipment_map = {i['product']:(i['shipped_qty'], i['returned_qty'], i['damaged_qty']) for i in shipment_products}
            cart_product_map = self.order.ordered_cart.rt_cart_list.filter(cart_product_id__in=shipment_map.keys())
            product_price_map = {i.cart_product.id:(i.item_effective_prices, i.qty) for i in cart_product_map}
            for product, shipment_details in shipment_map.items():
                try:
                    product_price = product_price_map[product][0]
                    shipped_qty, returned_qty, damaged_qty = shipment_details
                    self._invoice_amount += product_price * shipped_qty
                    self._cn_amount += (returned_qty+damaged_qty) * product_price
                    self._damaged_amount += damaged_qty * product_price
                    self._delivered_amount += self._invoice_amount - self._cn_amount
                except Exception as e:
                    logger.exception("Exception occurred {}".format(e))

    def __str__(self):
        return self.invoice_no or str(self.id)

    def clean(self):
        super(OrderedProduct, self).clean()
        if self.no_of_crates_check:
            if self.no_of_crates_check != self.no_of_crates:
                raise ValidationError(_("The number of crates must be equal to the number of crates shipped during shipment"))

    @property
    def shipment_weight(self):
        queryset = self.rt_order_product_order_product_mapping.all()
        weight = sum([item.product_weight for item in queryset]) # Definitely takes more memory.
        #weight = self.rt_order_product_order_product_mapping.all().aggregate(Sum('product.weight_value'))['weight_value__sum']
        return weight

    @property
    def shipment_address(self):
        if self.order:
            address = self.order.shipping_address
            address_line = address.address_line1
            contact = address.address_contact_number
            shop_name = address.shop_name.shop_name
            return str("%s, %s(%s)") % (shop_name, address_line, contact)
        return str("-")

    def payment_approval_status(self):
        payments = self.shipment_payment.all()
        status = "-"
        for payment in payments:
            status = "approved_and_verified"
            payment_status = payment.parent_order_payment.parent_payment.payment_approval_status
            if payment_status == "pending_approval":
                return "pending_approval"
        else:
            return  status

    def online_payment_approval_status(self):
        payments = self.shipment_payment.all().exclude(parent_order_payment__parent_payment__payment_mode_name="cash_payment")
        if not payments.exists():
            return "-"
        return format_html_join(
                "","{} - {}<br><br>",
                        ((s.parent_order_payment.parent_payment.reference_no,
                            s.parent_order_payment.parent_payment.payment_approval_status
                        ) for s in payments)
                )


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

    def total_payment(self):
        from payments.models import ShipmentPayment
        shipment_payment = self.shipment_payment.exclude(parent_order_payment__parent_payment__payment_status='cancelled')
        total_payment = cash_payment = online_payment = 0
        if shipment_payment.exists():
            shipment_payment_data = shipment_payment.aggregate(Sum('paid_amount')) #annotate(sum_paid_amount=Sum('paid_amount'))
            shipment_payment_cash = shipment_payment.filter(parent_order_payment__parent_payment__payment_mode_name="cash_payment").aggregate(Sum('paid_amount'))
            shipment_payment_online = shipment_payment.filter(parent_order_payment__parent_payment__payment_mode_name="online_payment").aggregate(Sum('paid_amount'))
        # shipment_payment = ShipmentPayment.objects.filter(shipment__in=trip_shipments).\
        #     annotate(sum_paid_amount=Sum('paid_amount'))
            if shipment_payment_data['paid_amount__sum']:
                total_payment = round(shipment_payment_data['paid_amount__sum'], 2) #sum_paid_amount
            if shipment_payment_cash['paid_amount__sum']:
                cash_payment = round(shipment_payment_cash['paid_amount__sum'], 2) #sum_paid_amount
            if shipment_payment_online['paid_amount__sum']:
                online_payment = round(shipment_payment_online['paid_amount__sum'], 2) #sum_paid_amount
        return total_payment, cash_payment, online_payment

    @property
    def total_paid_amount(self):
        total_payment, _c , _o = self.total_payment()
        return total_payment

    @property
    def cash_payment(self):
        _t , cash_payment, _o = self.total_payment()
        return cash_payment

    @property
    def online_payment(self):
        _t, _c, online_payment= self.total_payment()
        return online_payment

    @property
    def payment_mode(self):
        payment_mode, _ = self.payments()
        return payment_mode

    @property
    def invoice_city(self):
        city = self.order.shipping_address.city
        return str(city)

    def cash_to_be_collected(self):
        # fetch the amount to be collected
        if self.order.rt_payment.filter(payment_choice='cash_on_delivery').exists():
            return round((self._invoice_amount - self._cn_amount),2)
        return 0

    @property
    def invoice_amount(self):
        if self.order:
            return round(self._invoice_amount)
        return str("-")

    @property
    def shipment_id(self):
        return self.id

    def cn_amount(self):
        return round(self._cn_amount, 2)

    def damaged_amount(self):
        return round(self._damaged_amount, 2)

    def clean(self):
        super(OrderedProduct, self).clean()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.invoice_no and self.shipment_status == OrderedProduct.READY_TO_SHIP:
            self.invoice_no = retailer_sp_invoice(
                                    self.__class__, 'invoice_no',
                                    self.pk, self.order.seller_shop.
                                    shop_name_address_mapping.filter(
                                                    address_type='billing'
                                                    ).last().pk)
        if self.no_of_crates == None:
            self.no_of_crates = 0
        if self.no_of_packets == None:
            self.no_of_packets = 0
        if self.no_of_sacks == None:
            self.no_of_sacks = 0
        super().save(*args, **kwargs)
                # Update Product Tax Mapping End

class PickerDashboard(models.Model):

    PICKING_STATUS = (
        ('picking_pending', 'Picking Pending'),
        ('picking_assigned', 'Picking Assigned'),
        ('picking_in_progress', 'Picking In Progress'),
        ('picking_complete', 'Picking Complete'),
    )

    order = models.ForeignKey(Order, related_name="picker_order", on_delete=models.CASCADE)
    shipment = models.ForeignKey(
        OrderedProduct, related_name="picker_shipment",
        on_delete=models.DO_NOTHING, null=True, blank=True)
    picking_status = models.CharField(max_length=50,choices=PICKING_STATUS, default='picking_pending')
    #make unique to picklist id
    picklist_id = models.CharField(max_length=255, null=True, blank=True)#unique=True)
    picker_boy = models.ForeignKey(
        UserWithName, related_name='picker_user',
        on_delete=models.DO_NOTHING, verbose_name='Picker Boy',
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super(PickerDashboard, self).save(*args, **kwargs)

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
    shipped_qty = models.PositiveIntegerField(default=0, verbose_name="Shipped Pieces")
    delivered_qty = models.PositiveIntegerField(default=0, verbose_name="Delivered Pieces")
    returned_qty = models.PositiveIntegerField(default=0, verbose_name="Returned Pieces")
    damaged_qty = models.PositiveIntegerField(default=0, verbose_name="Damaged Pieces")
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_order_product',
        null=True, on_delete=models.DO_NOTHING
    )
    product_tax_json = JSONField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super(OrderedProductMapping, self).clean()
        returned_qty = int(self.returned_qty)
        damaged_qty = int(self.damaged_qty)

        if self.returned_qty > 0 or self.damaged_qty > 0:
            already_shipped_qty = int(self.shipped_qty)
            if sum([returned_qty, damaged_qty]) > already_shipped_qty:
                raise ValidationError(
                    _('Sum of returned and damaged pieces should be '
                      'less than no. of pieces to ship'),
                )

    @property
    def product_weight(self):
        # sum_a = sum([item.column for item in queryset]) # Definitely takes more memory.
        if self.product.weight_value:
            weight = self.product.weight_value*self.shipped_qty
            return weight
        else:
            return 0

    @property
    def ordered_qty(self):
        if self.ordered_product:
            no_of_pieces = self.ordered_product.order.ordered_cart.rt_cart_list.filter(
                cart_product=self.product).values('no_of_pieces')
            no_of_pieces = no_of_pieces.first().get('no_of_pieces')
            return str(no_of_pieces)
        return str("-")
    ordered_qty.fget.short_description = "Ordered Pieces"

    @property
    def already_shipped_qty(self):
        already_shipped_qty = OrderedProductMapping.objects.filter(
            ordered_product__in=self.ordered_product.order.rt_order_order_product.all(),
            product=self.product).aggregate(
            Sum('delivered_qty')).get('delivered_qty__sum', 0)
        return already_shipped_qty if already_shipped_qty else 0
    already_shipped_qty.fget.short_description = "Delivered Qty"

    @property
    def shipped_quantity_including_current(self):
        all_ordered_product = self.ordered_product.order.rt_order_order_product.filter(created_at__lte=self.ordered_product.created_at)#all()
        #all_ordered_product_exclude_current = all_ordered_product.exclude(id=self.ordered_product_id)
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
        #all_ordered_product_exclude_current = all_ordered_product.exclude(id=self.ordered_product_id)
        qty = OrderedProductMapping.objects.filter(
            ordered_product__in=all_ordered_product,
            product=self.product)
        to_be_shipped_qty = qty.aggregate(
            Sum('shipped_qty')).get('shipped_qty__sum', 0)
        # returned_qty = qty.aggregate(
        #     Sum('returned_qty')).get('returned_qty__sum', 0)
        to_be_shipped_qty = to_be_shipped_qty if to_be_shipped_qty else 0
        # to_be_shipped_qty = to_be_shipped_qty - returned_qty
        return to_be_shipped_qty
    to_be_shipped_qty.fget.short_description = "Already Shipped Qty"


    @property
    def shipped_qty_exclude_current1(self):
        all_ordered_product = self.ordered_product.order.rt_order_order_product.filter(created_at__lt=self.created_at)#all()
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
            ordered_product__in=all_ordered_product_exclude_current,
            product=self.product).aggregate(
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
        return self.ordered_product.order.ordered_cart.rt_cart_list\
            .get(cart_product=self.product).cart_product_price.mrp

    @property
    def price_to_retailer(self):
        return self.ordered_product.order.ordered_cart.rt_cart_list\
            .get(cart_product=self.product).cart_product_price.selling_price

    @property
    def cash_discount(self):
        return self.ordered_product.order.ordered_cart.rt_cart_list\
            .get(cart_product=self.product).cart_product_price.cash_discount

    @property
    def loyalty_incentive(self):
        return self.ordered_product.order.ordered_cart.rt_cart_list\
            .get(cart_product=self.product).cart_product_price.loyalty_incentive

    @property
    def margin(self):
        return self.ordered_product.order.ordered_cart.rt_cart_list\
            .get(cart_product=self.product).cart_product_price.margin

    @property
    def ordered_product_status(self):
        return self.ordered_product.shipment_status

    @property
    def product_short_description(self):
        return self.product.product_short_description

    def get_shop_specific_products_prices_sp(self):
        return self.product.product_pro_price.filter(
            shop__shop_type__shop_type='sp', status=True
        ).last()

    def get_products_gst_tax(self):
        return self.product.product_pro_tax.filter(tax__tax_type='gst')

    def get_products_gst_cess(self):
        return self.product.product_pro_tax.filter(tax__tax_type='cess')

    def set_product_tax_json(self):
        product_tax_query = self.product.product_pro_tax.values('product', 'tax', 'tax__tax_name',
                                                                    'tax__tax_percentage')
        product_tax = {i['tax']: [i['tax__tax_name'], i['tax__tax_percentage']] for i in product_tax_query}
        product_tax['tax_sum'] = product_tax_query.aggregate(tax_sum=Sum('tax__tax_percentage'))['tax_sum']
        self.product_tax_json = product_tax
        self.save()


    def get_product_tax_json(self):
        if not self.product_tax_json:
            self.set_product_tax_json()
        return self.product_tax_json.get('tax_sum')

    def save(self, *args, **kwargs):
        if (self.delivered_qty or self.returned_qty or self.damaged_qty) and self.shipped_qty != sum([self.delivered_qty, self.returned_qty, self.damaged_qty]):
            raise ValidationError(_('delivered, returned, damaged qty sum mismatched with shipped_qty'))
        else:
            super().save(*args, **kwargs)
    #     if self.product_tax_json:
    #         super().save(*args, **kwargs)
    #     else:
    #         try:
    #             product_tax_query = self.product.product_pro_tax.filter(status=True).values('product', 'tax', 'tax__tax_name',
    #                                                                     'tax__tax_percentage')
    #             product_tax = {i['tax']: [i['tax__tax_name'], i['tax__tax_percentage']] for i in product_tax_query}
    #             product_tax['tax_sum'] = product_tax_query.aggregate(tax_sum=Sum('tax__tax_percentage'))['tax_sum']
    #             self.product_tax_json = product_tax
    #         except Exception as e:
    #             logger.exception("Exception occurred while saving product {}".format(e))
    #         super().save(*args, **kwargs)

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
    rescheduling_reason = models.CharField(
        max_length=50, choices=RESCHEDULING_REASON,
        blank=False, verbose_name='Reason for Rescheduling',
    )
    rescheduling_date = models.DateField(blank=False)
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
        super().save(*args, **kwargs)


class Commercial(Trip):
    class Meta:
        proxy = True
        verbose_name = _("Commercial")
        verbose_name_plural = _("Commercial")

    def change_shipment_status(self):
        trip_shipments = self.rt_invoice_trip.all()
        for shipment in trip_shipments:
            if shipment.shipment_status == 'FULLY_RETURNED_AND_COMPLETED':
                shipment.shipment_status = 'FULLY_RETURNED_AND_CLOSED'
            if shipment.shipment_status == 'PARTIALLY_DELIVERED_AND_COMPLETED':
                shipment.shipment_status = 'PARTIALLY_DELIVERED_AND_CLOSED'
            if shipment.shipment_status == 'FULLY_DELIVERED_AND_COMPLETED':
                shipment.shipment_status = 'FULLY_DELIVERED_AND_CLOSED'
            shipment.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.trip_status == 'CLOSED':
            self.change_shipment_status()

    def clean(self):
        if self.received_amount:
            if (self.trip_status == 'CLOSED' and
                    (int(self.received_amount) !=
                        int(self.cash_to_be_collected()))):
                    raise ValidationError(_("Received amount should be equal"
                                            " to Amount to be Collected"
                                            ),)
            if (self.trip_status == 'COMPLETED' and
                    (int(self.received_amount) >
                        int(self.cash_to_be_collected()))):
                    raise ValidationError(_("Received amount should be less"
                                            " than Amount to be Collected"
                                            ),)

class CustomerCare(models.Model):
    order_id = models.ForeignKey(
        Order, on_delete=models.DO_NOTHING, null=True, blank=True
    )
    phone_number = models.CharField( max_length=10, blank=True, null=True)
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
            if User.objects.filter(phone_number = self.phone_number).exists():
                username = User.objects.get(phone_number = self.phone_number).first_name
                return username

    @property
    def comment_display(self):
        return format_html_join(
        "","{}<br><br>",
                ((c.comment,
                ) for c in self.customer_care_comments.all())
        )
    comment_display.fget.short_description = 'Comments'

    @property
    def comment_date_display(self):
        return format_html_join(
        "","{}<br><br>",
                ((c.created_at,
                ) for c in self.customer_care_comments.all())
        )
    comment_date_display.fget.short_description = 'Comment Date'

    def save(self, *args, **kwargs):
        super(CustomerCare, self).save()
        self.complaint_id = "CustomerCare/Message/%s" % self.pk
        super(CustomerCare, self).save()

class ResponseComment(models.Model):
    customer_care = models.ForeignKey(CustomerCare,related_name='customer_care_comments', null=True, blank=True, on_delete=models.DO_NOTHING)
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
        (APPROVED_BY_FINANCE, "Approved by finance"),
    )

    order_id = models.ForeignKey(
        Order, related_name='rt_payment',
        on_delete=models.DO_NOTHING, null=True
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')
    payment_choice = models.CharField(verbose_name="Payment Mode",max_length=30,choices=PAYMENT_MODE_CHOICES,default='cash_on_delivery')
    neft_reference_number = models.CharField(max_length=255, null=True,blank=True)
    imei_no = models.CharField(max_length=100, null=True, blank=True)
    payment_status = models.CharField(max_length=50, null=True, blank=True,choices=PAYMENT_STATUS, default=PAYMENT_DONE_APPROVAL_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args,**kwargs):
        super(Payment, self).save()
        self.name = "Payment/%s" % self.pk
        super(Payment, self).save()


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
        from notification_center.tasks import send_notification
        send_notification(user_id=user_id, activity_type=template, data=data)
        try:
            message = SendSms(phone=instance.order_id.buyer_shop.shop_owner.phone_number,
                              body="Hi %s, We have received your order no. %s with %s items and totalling to %s Rupees for your shop %s. We will update you further on shipment of the items."\
                                  " Thanks," \
                                  " Team GramFactory" % (username, order_no,items_count, total_amount, shop_name))
            message.send()
        except Exception as e:
            logger.exception("Unable to send SMS for order : {}".format(order_no))


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
    shop = models.ForeignKey(Shop, related_name='credit_notes', null=True, blank=True, on_delete=models.DO_NOTHING)
    credit_note_id = models.CharField(max_length=255, null=True, blank=True)
    shipment = models.ForeignKey(OrderedProduct, null=True, blank=True, on_delete=models.DO_NOTHING, related_name='credit_note')
    note_type = models.CharField(
        max_length=255, choices=NOTE_TYPE_CHOICES, default='credit_note'
    )
    amount = models.FloatField(default=0)
    last_modified_by = models.ForeignKey(
        get_user_model(), related_name='rt_last_modified_user_note',
        null=True, blank=True, on_delete=models.DO_NOTHING
    )
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
            return round(self.shipment._cn_amount,2)


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

@task
def assign_update_picker_to_shipment(shipment_id):
   shipment = OrderedProduct.objects.get(pk=shipment_id)
   if shipment.shipment_status == "SHIPMENT_CREATED":
       # assign shipment to picklist
       # tbd : if manual(by searching relevant picklist id) or automated
       picker_lists = shipment.order.picker_order.filter(picking_status="picking_assigned").update(shipment=shipment)
   elif shipment.shipment_status == OrderedProduct.READY_TO_SHIP:
       shipment.picker_shipment.all().update(picking_status="picking_complete")


@receiver(post_save, sender=OrderedProduct)
def update_picking_status(sender, instance=None, created=False, **kwargs):
    '''
    Method to update picking status
    '''
    assign_update_picker_to_shipment.delay(instance.id)


@receiver(post_save, sender=Order)
def assign_picklist(sender, instance=None, created=False, **kwargs):
    '''
    Method to update picking status
    '''
    #assign shipment to picklist once SHIPMENT_CREATED
    if created:
        # assign piclist to order
        try:
            pincode = "00" #instance.shipping_address.pincode
        except:
            pincode = "00"
        PickerDashboard.objects.create(
            order=instance,
            picking_status="picking_pending",
            picklist_id= generate_picklist_id(pincode), #get_random_string(12).lower(), ##generate random string of 12 digits
            )


post_save.connect(get_order_report, sender=Order)


@receiver(post_save, sender=CartProductMapping)
def create_offers(sender, instance=None, created=False, **kwargs):
    if instance.qty and instance.no_of_pieces:
        Cart.objects.filter(id=instance.cart.id).update(offers=instance.cart.offers_applied())

from django.db.models.signals import post_delete

@receiver(post_delete, sender=CartProductMapping)
def create_offers_at_deletion(sender, instance=None, created=False, **kwargs):
    if instance.qty and instance.no_of_pieces:
        Cart.objects.filter(id=instance.cart.id).update(offers=instance.cart.offers_applied())
