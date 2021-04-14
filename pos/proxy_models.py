from coupon.models import Coupon, RuleSetProductMapping, CouponRuleSet
from retailer_to_sp.models import Cart, Order


class RetailerCouponRuleSet(CouponRuleSet):
    class Meta:
        proxy = True


class RetailerRuleSetProductMapping(RuleSetProductMapping):
    class Meta:
        proxy = True


class RetailerCoupon(Coupon):
    class Meta:
        proxy = True


class RetailerCart(Cart):
    class Meta:
        proxy = True


class RetailerOrder(Order):
    class Meta:
        proxy = True
