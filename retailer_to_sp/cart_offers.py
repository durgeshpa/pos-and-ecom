import datetime
import logging

from django.db.models import Q, Count

from coupon.models import Coupon, RuleSetProductMapping, CusotmerCouponUsage, RuleSetBrandMapping
from retailer_to_sp.models import CartOffers

date = datetime.datetime.now()
# Logger
info_logger = logging.getLogger('file-info')

def get_applicable_product_coupons(product_ids, cart_value=None):
    # Get all the RuleSetProductMapping entries for given products ids
    queryset = RuleSetProductMapping.objects.all()
    if cart_value:
        queryset = queryset.filter(Q(rule__cart_qualifying_min_sku_value=0)|
                                         Q(cart_qualifying_min_sku_item=0)|
                                         Q(cart_qualifying_min_sku_value__gte=cart_value))
    queryset = queryset.filter(purchased_product_id__in=product_ids,
                               rule__is_active=True,
                               rule__expiry_date__gte=date,
                               rule__coupon_ruleset__is_active=True,
                               rule__coupon_ruleset__expiry_date__gte=date
                               ).exclude(rule__coupon_ruleset__shop__shop_type__shop_type='f')
    applicable_coupon_data = queryset.values_list('rule__coupon_ruleset__id', 'rule__coupon_ruleset__coupon_name',
                                                  'rule__coupon_ruleset__coupon_code',
                                                  'rule__coupon_ruleset__limit_per_user_per_day',
                                                  'rule__discount_qty_amount', 'rule__discount_qty_step',
                                                  'rule__free_item__id', 'rule__free_item__product_name',
                                                  'purchased_product_id', 'rule', 'rule__discount'
                                                  )
    return {p['purchased_product_id']: p for p in applicable_coupon_data}


def get_applicable_brand_coupons(brand_ids):
    queryset = RuleSetBrandMapping.filter(brand_id__in=brand_ids,
                               rule__is_active=True,
                               rule__expiry_date__gte=date,
                               rule__coupon_ruleset__is_active=True,
                               rule__coupon_ruleset__expiry_date__gte=date
                               ).exclude(rule__coupon_ruleset__shop__shop_type__shop_type='f')
    applicable_coupon_data = queryset.values_list('rule__coupon_ruleset__id', 'rule__coupon_ruleset__coupon_name',
                                                  'rule__coupon_ruleset__coupon_code',
                                                  'rule__coupon_ruleset__limit_per_user_per_day',
                                                  'rule__discount_qty_amount', 'rule__discount_qty_step',
                                                  'purchased_product_id', 'rule', 'rule__discount',
                                                  'rule__cart_qualifying_min_sku_value',
                                                  'rule__cart_qualifying_min_sku_item'
                                                  )
    return {p['brand_id']: p for p in applicable_coupon_data}


def get_applicable_cart_coupons():
    qs = Coupon.objects.filter(coupon_type='cart', is_active=True, expiry_date__gte=date)\
                       .exclude(shop__shop_type__shop_type='f').order_by('rule__cart_qualifying_min_sku_value')\
                       .values_list('id', 'coupon_name', 'coupon_code', 'limit_per_user_per_day',
                                    'rule__discount_qty_amount', 'rule__discount_qty_step', 'rule', 'rule__discount',
                                    'rule__cart_qualifying_min_sku_value', 'rule__cart_qualifying_min_sku_item',
                                    'rule__discount__discount_value', 'rule__discount__is_percentage')
    return qs


def get_coupon_usage(buyer_shop, product_ids):
    queryset = CusotmerCouponUsage.objects.filter(shop=buyer_shop,
                                                  product_id__in=product_ids,
                                                  created_at__date=datetime.datetime.date()).values('product_id')\
                                          .annotate(cnt=Count('id'))
    coupon_usage_data = {d['product_id']: d['cnt'] for d in queryset}
    return coupon_usage_data


def save_cart_offers(cart, offers_dict):
    CartOffers.objects.filter(cart=cart).delete()
    info_logger.info(f"Remove existing offers | Cart {cart}")
    cart_offers = []
    if offers_dict.get('catalog'):
        for item_id, offer in offers_dict['catalog']:
            cart_offers.append(CartOffers(cart=cart, item_id=item_id, brand_id=offer['brand_id'],
                                          offer_type=offer['type'], offer_sub_type=offer['sub_type'],
                                          coupon=offer['coupon_id'], discount=offer['discount_value'],
                                          free_product=offer['free_item'], free_product_qty=offer['free_item'],
                                          cart_discount=offer['cart_discount'], brand_discount=offer['brand_discount'],
                                          sub_total=offer['discounted_product_subtotal_after_sku_discount']))
    if offers_dict.get('brand'):
        for brand_id, offer in offers_dict['brand']:
            cart_offers.append(CartOffers(cart=cart, brand_id=brand_id, offer_type=offer['type'],
                                          offer_sub_type=offer['sub_type'], coupon=offer['coupon_id'],
                                          discount=offer['discount_value'], sub_total=offer['brand_product_subtotals']))
    elif offers_dict.get('cart'):
        offer = offers_dict.get('cart')
        cart_offers.append(CartOffers(cart=cart, offer_type=offer['type'], offer_sub_type=offer['sub_type'],
                                      coupon=offer['coupon_id'], discount=offer['discount_value'],
                                      sub_total=offer['cart_value']))
    else:
        offer = offers_dict.get('none')
        cart_offers.append(CartOffers(cart=cart, offer_type=offer['type'], offer_sub_type=offer['sub_type'],
                                      entice_text=offer['entice_text']))

    CartOffers.objects.bulk_create(cart_offers)
    info_logger.info(f"Offers created | Cart {cart}")