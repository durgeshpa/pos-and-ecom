from coupon.models import Coupon, RuleSetProductMapping, CouponRuleSet
from retailer_to_sp.models import Cart, OrderedProduct, OrderedProductMapping, Order
from wms.models import PosInventory, PosInventoryChange, PosInventoryState


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


class RetailerOrderedProduct(OrderedProduct):
    class Meta:
        proxy = True


class RetailerOrderedProductMapping(OrderedProductMapping):
    class Meta:
        proxy = True


class InventoryStatePos(PosInventoryState):
    class Meta:
        proxy = True
        verbose_name = 'Inventory State'


class InventoryPos(PosInventory):
    class Meta:
        proxy = True
        verbose_name = 'Inventory'


class InventoryChangePos(PosInventoryChange):
    class Meta:
        proxy = True
        verbose_name = 'Inventory Change'
