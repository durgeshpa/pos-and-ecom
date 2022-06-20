import datetime

from django.db.models import Q, Count

from coupon.models import Coupon, RuleSetProductMapping, CusotmerCouponUsage


def get_applicable_product_coupons(product_ids, cart_value=None):
    # Get all the RuleSetProductMapping entries for given products ids
    queryset = RuleSetProductMapping.objects.all()
    if cart_value:
        queryset = queryset.filter(Q(rule__cart_qualifying_min_sku_value=0)|
                                         Q(cart_qualifying_min_sku_item=0)|
                                         Q(cart_qualifying_min_sku_value__gte=cart_value))
    queryset = queryset.filter(purchased_product_coupon_id__in=product_ids,
                               rule__is_active=True,
                               rule__expiry_date__gte=datetime.datetime.now(),
                               rule__coupon_ruleset__is_active=True,
                               rule__coupon_ruleset__expiry_date__gte=datetime.datetime.now()
                               ).exclude(rule__coupon_ruleset__shop__shop_type__shop_type='f')
    applicable_coupon_data = queryset.values_list('rule__coupon_ruleset__id', 'rule__coupon_ruleset__coupon_name',
                                                  'rule__coupon_ruleset__coupon_code',
                                                  'rule__coupon_ruleset__limit_per_user_per_day',
                                                  'rule__discount_qty_amount', 'rule__discount_qty_step',
                                                  'rule__free_item__id', 'rule__free_item__product_name',
                                                  )
    return applicable_coupon_data


def get_applicable_brand_coupons(brand_ids):
    pass

def get_coupon_usage(buyer_shop, product_ids):
    queryset = CusotmerCouponUsage.objects.filter(shop=buyer_shop,
                                                  product_id__in=product_ids,
                                                  created_at__date=datetime.datetime.date()).values('product_id')\
                                          .annotate(cnt=Count('id'))
    coupon_usage_data = {d['product_id']: d['cnt'] for d in queryset}
    return coupon_usage_data
