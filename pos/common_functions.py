from rest_framework.response import Response
from rest_framework import status

from pos.models import RetailerProduct
from retailer_to_sp.models import CartProductMapping
from retailer_to_gram.models import (CartProductMapping as GramMappedCartProductMapping)
from coupon.models import RuleSetProductMapping, Coupon, CouponRuleSet


class RetailerProductCls(object):

    @classmethod
    def create_retailer_product(cls, shop_id, name, mrp, selling_price, linked_product_id, sku_type, description):
        """
            General Response For API
        """
        RetailerProduct.objects.create(shop_id=shop_id, name=name, linked_product_id=linked_product_id,
                                       mrp=mrp, sku_type=sku_type, selling_price=selling_price, description=description)


class OffersCls(object):
    @classmethod
    def rule_set_cretion(cls, ruleset_type, rulename, start_date, expiry_date, discount_qty_amount=None, discount_obj=None):
        """
           rule_set Creation for Offer/Coupon
        """
        ruleset = CouponRuleSet.objects.create(ruleset_type=ruleset_type, rulename=rulename, all_users=True,
                                               start_date=start_date, expiry_date=expiry_date, is_active=True,
                                               discount_qty_amount=discount_qty_amount, discount=discount_obj)
        return ruleset

    @classmethod
    def rule_set_product_mapping(cls, rule_id, retailer_primary_product, purchased_product_qty, retailer_free_product,
                                 free_product_qty, combo_offer_name, start_date, expiry_date, shop):
        """
            rule_set Mapping with product for combo offer
        """
        RuleSetProductMapping.objects.create(rule_id=rule_id, retailer_primary_product=retailer_primary_product,
                                             purchased_product_qty=purchased_product_qty, retailer_free_product=
                                             retailer_free_product, free_product_qty=free_product_qty,
                                             combo_offer_name=combo_offer_name, start_date=start_date,
                                             expiry_date=expiry_date, shop=shop)

    @classmethod
    def rule_set_cart_mapping(cls, rule_id, coupon_type, coupon_name, shop, start_date, expiry_date):
        """
            rule_set cart mapping for coupon creation
        """
        Coupon.objects.create(rule_id=rule_id, coupon_name=coupon_name, coupon_type=coupon_type,
                              shop=shop, start_date=start_date, expiry_date=expiry_date)


def get_response(msg, data=None):
    """
        General Response For API
    """
    if data:
        ret = {"is_success": True, "message": msg, "response_data": data}
    else:
        ret = {"is_success": False, "message": msg, "response_data": None}
    return Response(ret, status=status.HTTP_200_OK)


def delete_cart_mapping(cart, product, cart_type='retail'):
    """
        Delete Cart items
    """
    if cart_type == 'retail':
        if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
            CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
    elif cart_type == 'retail_gf':
        if GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
            GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
    elif cart_type == 'basic':
        if CartProductMapping.objects.filter(cart=cart, retailer_product=product).exists():
            CartProductMapping.objects.filter(cart=cart, retailer_product=product).delete()
