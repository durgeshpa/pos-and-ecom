from coupon.models import Coupon, RuleSetProductMapping, CouponRuleSet
from retailer_to_sp.models import Cart, OrderedProduct, OrderedProductMapping, CartProductMapping, OrderReturn,\
    ReturnItems


class RetailerCouponRuleSet(CouponRuleSet):
    class Meta:
        proxy = True
        verbose_name = 'Coupon Ruleset'


class RetailerRuleSetProductMapping(RuleSetProductMapping):
    class Meta:
        proxy = True
        verbose_name = 'Coupon Ruleset Product Mapping'


class RetailerCoupon(Coupon):
    class Meta:
        proxy = True
        verbose_name = 'Coupon'


class RetailerCart(Cart):
    class Meta:
        proxy = True
        verbose_name = 'Cart'


class RetailerCartProductMapping(CartProductMapping):
    class Meta:
        proxy = True
        verbose_name = 'Cart Product Mapping'


class RetailerOrderedProduct(OrderedProduct):
    class Meta:
        proxy = True
        verbose_name = 'Order'


class RetailerOrderedProductMapping(OrderedProductMapping):
    class Meta:
        proxy = True
        verbose_name = 'Ordered Product Mapping'


class RetailerOrderReturn(OrderReturn):
    class Meta:
        proxy = True
        verbose_name = 'Return'

    @property
    def order_no(self):
        return self.order.order_no


class RetailerReturnItems(ReturnItems):
    class Meta:
        proxy = True
        verbose_name = 'Return Item'

    def __str__(self):
        return ''



# class InventoryStatePos(PosInventoryState):
#     class Meta:
#         proxy = True
#         verbose_name = 'Inventory State'
#
#
# class InventoryPos(PosInventory):
#     class Meta:
#         proxy = True
#         verbose_name = 'Inventory'
#
#
# class InventoryChangePos(PosInventoryChange):
#     class Meta:
#         proxy = True
#         verbose_name = 'Inventory Change'
