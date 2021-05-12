import logging
import json
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.urls import reverse

from pos.models import RetailerProduct, UserMappedShop
from retailer_to_sp.models import CartProductMapping, Order
from retailer_to_gram.models import (CartProductMapping as GramMappedCartProductMapping)
from coupon.models import RuleSetProductMapping, Coupon, CouponRuleSet
from shops.models import Shop

ORDER_STATUS_MAP = {
    1: Order.ORDERED,
    2: Order.CANCELLED,
    3: Order.PARTIALLY_REFUNDED,
    4: Order.FULLY_REFUNDED
}

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


class RetailerProductCls(object):

    @classmethod
    def create_retailer_product(cls, shop_id, name, mrp, selling_price, linked_product_id, sku_type, description, product_ean_code, status='active'):
        """
            General Response For API
        """
        if status is None:
            status = 'active'
        return RetailerProduct.objects.create(shop_id=shop_id, name=name, linked_product_id=linked_product_id,
                                              mrp=mrp, sku_type=sku_type, selling_price=selling_price, description=description,
                                              product_ean_code=product_ean_code, status=status)

    @classmethod
    def get_sku_type(cls, sku_type):
        """
            Get SKU_TYPE
        """
        if sku_type == 1:
            return 'CREATED'
        if sku_type == 2:
            return 'LINKED'
        if sku_type == 3:
            return 'LINKED_EDITED'


class OffersCls(object):
    @classmethod
    def rule_set_creation(cls, rulename, start_date, expiry_date, discount_qty_amount=None, discount_obj=None,
                          free_product_obj=None, free_product_qty=None):
        """
           rule_set Creation for Offer/Coupon
        """
        if CouponRuleSet.objects.filter(rulename=rulename):
            ruleset = f"cannot create a Offer with {rulename}, already exists"
        else:
            ruleset = CouponRuleSet.objects.create(rulename=rulename, start_date=start_date,
                                                   expiry_date=expiry_date, is_active=True,
                                                   cart_qualifying_min_sku_value=discount_qty_amount,
                                                   discount=discount_obj,
                                                   free_product=free_product_obj,
                                                   free_product_qty=free_product_qty
                                                   )
        return ruleset

    @classmethod
    def rule_set_product_mapping(cls, rule_id, retailer_primary_product, purchased_product_qty, retailer_free_product,
                                 free_product_qty, combo_offer_name, start_date, expiry_date):
        """
            rule_set Mapping with product for combo offer
        """
        RuleSetProductMapping.objects.create(rule_id=rule_id, retailer_primary_product=retailer_primary_product,
                                             purchased_product_qty=purchased_product_qty, retailer_free_product=
                                             retailer_free_product, free_product_qty=free_product_qty,
                                             combo_offer_name=combo_offer_name, start_date=start_date,
                                             expiry_date=expiry_date, is_active=True)

    @classmethod
    def rule_set_cart_mapping(cls, rule_id, coupon_type, coupon_name, coupon_code, shop, start_date, expiry_date):
        """
            rule_set cart mapping for coupon creation
        """
        Coupon.objects.create(rule_id=rule_id, coupon_name=coupon_name, coupon_type=coupon_type,
                              shop=shop, start_date=start_date, expiry_date=expiry_date, coupon_code=coupon_code,
                              is_active=True)


def get_response(msg, data=None, success=False, extra_params=None):
    """
        General Response For API
    """
    if success:
        ret = {"is_success": True, "message": msg, "response_data": data}
    else:
        if data:
            ret = {"is_success": True, "message": msg, "response_data": data}
        else:
            ret = {"is_success": False, "message": msg, "response_data": None}
    if extra_params:
        ret.update(extra_params)
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


def get_shop_id_from_token(request):
    """
        If Token is valid get shop_id from token
    """
    if request.user.id:
        if Shop.objects.filter(shop_owner_id=request.user.id, shop_type__shop_type='f').exists():
            shop = Shop.objects.filter(shop_owner_id=request.user.id, shop_type__shop_type='f')
        else:
            if Shop.objects.filter(related_users=request.user.id, shop_type__shop_type='f').exists():
                shop = Shop.objects.filter(related_users=request.user.id, shop_type__shop_type='f')
            else:
                return "Please Provide a Valid TOKEN"
        return int(shop.values()[0].get('id'))
    return "Please provide Token"


def serializer_error(serializer):
    """
        Serializer Error Method
    """
    errors = []
    for field in serializer.errors:
        for error in serializer.errors[field]:
            if 'non_field_errors' in field:
                result = error
            else:
                result = ''.join('{} : {}'.format(field, error))
            errors.append(result)
    msg = {'is_success': False,
           'error_message': errors[0] if len(errors) == 1 else [error for error in errors],
           'response_data': None}
    return msg


def order_search(orders, search_text):
    """
        Order Listing Based On Search
    """
    order = orders.filter(Q(order_no__icontains=search_text) |
                          Q(ordered_cart__id__icontains=search_text) |
                          Q(buyer__phone_number__icontains=search_text))
    return order


def create_user_shop_mapping(user, shop_id):
    """
       while registration of user, store
       shop_id of seller shop with user in UserMappedShop
    """
    if not UserMappedShop.objects.filter(user=user).exists():
        UserMappedShop.objects.create(user=user, shop_id=shop_id)


def get_invoice_and_link(shipment, host):
    """
        Return invoice no and link for shipment
    """
    invoice_no = shipment.invoice_no
    invoice_link = "{0}{1}".format(host, reverse('download_invoice_sp', args=[shipment.id]))
    return {'invoice_no': invoice_no, 'invoice_link': invoice_link}


def validate_data_format(request):
    """
        Validating Entered data,
        Convert python data(request.data) in to a JSON string,
    """
    try:
        # Checking if Entered Data is in the Right Format except images
        # the result is a JSON string, which is valid Data
        json.dumps(request.data, default=lambda skip_image: 'images')
    except Exception as e:
        error_logger.error(e)
        msg = {'is_success': False,
               'error_message': "Invalid Data Format",
               'response_data': None}
        return msg
