import logging
import json
from functools import wraps
from copy import deepcopy
from decimal import Decimal
import datetime

from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from django.urls import reverse
from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist

from addresses.models import Address
from retailer_to_sp.models import CartProductMapping, Order, Cart
from retailer_to_gram.models import (CartProductMapping as GramMappedCartProductMapping)
from coupon.models import RuleSetProductMapping, Coupon, CouponRuleSet
from shops.models import Shop, PosShopUserMapping
from wms.models import PosInventory, PosInventoryChange, PosInventoryState
from marketing.models import RewardPoint, RewardLog, Referral, ReferralCode
from global_config.models import GlobalConfig
from rest_auth.utils import AutoUser
from products.models import Product

from .common_validators import validate_user_type_for_pos_shop
from pos import error_code
from pos.models import RetailerProduct, ShopCustomerMap, RetailerProductImage, ProductChange, ProductChangeFields, \
    PosCart, PosCartProductMapping, Vendor, PosReturnGRNOrder, MeasurementUnit, MeasurementCategory

ORDER_STATUS_MAP = {
    1: Order.ORDERED,
    2: Order.PARTIALLY_RETURNED,
    3: Order.FULLY_RETURNED,
    4: Order.CANCELLED
}

ONLINE_ORDER_STATUS_MAP = {
    1: [Order.ORDERED],
    2: [Order.OUT_FOR_DELIVERY, Order.PICKUP_CREATED],
    3: [Order.DELIVERED, Order.PARTIALLY_RETURNED, Order.FULLY_RETURNED, Order.CLOSED, Order.CANCELLED],
    4: [Order.CANCELLED],
    5: [Order.OUT_FOR_DELIVERY],
    6: [Order.PICKUP_CREATED],
    7: [Order.DELIVERED],
    8: [Order.PARTIALLY_RETURNED],
    9: [Order.FULLY_RETURNED]
}

ECOM_ORDER_STATUS_MAP = {
    1: [Order.ORDERED, Order.PICKUP_CREATED],
    2: [Order.OUT_FOR_DELIVERY],
    3: [Order.DELIVERED],
    4: [Order.PARTIALLY_RETURNED],
    5: [Order.FULLY_RETURNED],
    6: [Order.CLOSED],
    7: [Order.CANCELLED]
}

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


class RetailerProductCls(object):

    @classmethod
    def create_retailer_product(cls, shop_id, name, mrp, selling_price, linked_product_id, sku_type, description,
                                product_ean_code, user, event_type, pack_type, measure_cat_id, event_id=None,
                                product_status='active', offer_price=None, offer_sd=None, offer_ed=None,
                                product_ref=None, online_enabled=True, online_price=None, purchase_pack_size=1,
                                is_visible=False, initial_purchase_value=None):
        """
            General Response For API
        """
        product_status = 'active' if product_status is None else product_status
        product = RetailerProduct.objects.create(shop_id=shop_id, name=name, linked_product_id=linked_product_id,
                                                 mrp=mrp, sku_type=sku_type, selling_price=selling_price,
                                                 offer_price=offer_price, offer_start_date=offer_sd,
                                                 offer_end_date=offer_ed, description=description,
                                                 product_ean_code=product_ean_code, status=product_status,
                                                 product_ref=product_ref, product_pack_type=pack_type,
                                                 measurement_category_id=measure_cat_id,
                                                 online_enabled=online_enabled, online_price=online_price,
                                                 purchase_pack_size=purchase_pack_size, is_deleted=is_visible,
                                                 initial_purchase_value=initial_purchase_value)
        event_id = product.sku if not event_id else event_id
        # Change logs
        ProductChangeLogs.product_create(product, user, event_type, event_id)
        return product

    @classmethod
    def create_images(cls, product, images):
        if images:
            count = 0
            for image in images:
                if image.name == 'gmfact_image.jpeg':
                    count += 1
                    image.name = str(product.sku) + '_' + str(count) + '_' + image.name
                RetailerProductImage.objects.create(product=product, image=image)

    @classmethod
    def copy_images(cls, product, images):
        """
        Params :
            product : retailer product instance for which images are to be created
            images : RetailerProductImage queryset
        """
        for image in images:
            RetailerProductImage.objects.create(product=product, image=image.image)

    @classmethod
    def update_images(cls, product, images):
        if images:
            for image in images:
                image.name = str(product.sku) + '_' + image.name
                RetailerProductImage.objects.create(product=product, image=image)

    @classmethod
    def update_price(cls, product_id, selling_price, product_status, user, event_type, event_id):
        product = RetailerProduct.objects.filter(id=product_id).last()
        old_product = deepcopy(product)
        product.selling_price = selling_price
        product.status = product_status
        product.save()
        # Change logs
        ProductChangeLogs.product_update(product, old_product, user, event_type, event_id)

    @classmethod
    def update_mrp(cls, product_id, product_mrp, user, event_type, event_id):
        product = RetailerProduct.objects.filter(id=product_id).last()
        old_product = deepcopy(product)
        product.mrp = product_mrp
        product.save()
        # Change logs
        ProductChangeLogs.product_update(product, old_product, user, event_type, event_id)

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
        if sku_type == 4:
            return 'DISCOUNTED'

    @classmethod
    def is_discounted_product_exists(cls, product):
        return hasattr(product, 'discounted_product')

    @classmethod
    def is_discounted_product_available(cls, product):
        return hasattr(product, 'discounted_product') and product.discounted_product.status == 'active'


class OffersCls(object):
    @classmethod
    def rule_set_creation(cls, rulename, start_date, expiry_date, discount_qty_amount=None, discount_obj=None,
                          free_product_obj=None, free_product_qty=None):
        if CouponRuleSet.objects.filter(rulename=rulename):
            ruleset = "Offer with same Order Value and Discount Detail already exists"
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
        coupon = Coupon.objects.create(rule_id=rule_id, coupon_name=coupon_name, coupon_type=coupon_type,
                                       shop=shop, start_date=start_date, expiry_date=expiry_date,
                                       coupon_code=coupon_code,
                                       is_active=True)
        return coupon


class PosInventoryCls(object):

    @classmethod
    def stock_inventory(cls, pid, i_state, f_state, qty, user, transaction_id, transaction_type, remarks=None):
        """
            Create/Update available inventory for product
        """
        i_state_obj = PosInventoryState.objects.get(inventory_state=i_state)
        f_state_obj = i_state_obj if i_state == f_state else PosInventoryState.objects.get(inventory_state=f_state)
        pos_inv, created = PosInventory.objects.get_or_create(product_id=pid, inventory_state=f_state_obj)
        if not created and Decimal(qty) == pos_inv.quantity:
            return
        i_qty, f_qty = None, None
        if transaction_type == PosInventoryChange.STOCK_UPDATE:
            i_qty = pos_inv.quantity
            f_qty = pos_inv.quantity
            qty_change = pos_inv.quantity
            if i_qty == f_qty:
                info_logger.info(f"POS|stock_inventory|initial quantity {i_qty} and final quantity {f_qty} is same")
                return
        else:
            qty_change = Decimal(qty) - pos_inv.quantity
            pos_inv.quantity = Decimal(qty)
            pos_inv.save()
        PosInventoryCls.create_inventory_change(pid, qty_change, transaction_type, transaction_id, i_state_obj,
                                                f_state_obj, user, i_qty, f_qty, remarks)

    @classmethod
    def app_stock_inventory(cls, pid, i_state, f_state, qty, user, transaction_id, transaction_type, remarks=None):
        """
            Create/Update available inventory for product
        """
        i_state_obj = PosInventoryState.objects.get(inventory_state=i_state)
        f_state_obj = i_state_obj if i_state == f_state else PosInventoryState.objects.get(inventory_state=f_state)
        pos_inv, created = PosInventory.objects.get_or_create(product_id=pid, inventory_state=f_state_obj)
        if not created and Decimal(qty) == pos_inv.quantity:
            return
        i_qty, f_qty = None, None
        if transaction_type == PosInventoryChange.STOCK_UPDATE:
            i_qty = pos_inv.quantity
            f_qty = Decimal(qty)
            if i_qty == f_qty:
                info_logger.info(f"POS|stock_inventory|initial quantity {i_qty} and final quantity {f_qty} is same")
                return
        qty_change = Decimal(qty) - pos_inv.quantity
        pos_inv.quantity = Decimal(qty)
        pos_inv.save()
        PosInventoryCls.create_inventory_change(pid, qty_change, transaction_type, transaction_id, i_state_obj,
                                                f_state_obj, user, i_qty, f_qty, remarks)

    @classmethod
    def order_inventory(cls, pid, i_state, f_state, qty, user, transaction_id, transaction_type):
        """
            Manage Order related product inventory (Order creation, cancellations, returns)
        """
        # Subtract qty from initial state inventory
        i_state_obj = PosInventoryState.objects.get(inventory_state=i_state)
        PosInventoryCls.qty_transaction(pid, i_state_obj, -1 * qty, transaction_id)
        # Add qty to final state inventory
        f_state_obj = i_state_obj if i_state == f_state else PosInventoryState.objects.get(inventory_state=f_state)
        PosInventoryCls.qty_transaction(pid, f_state_obj, qty, transaction_id)
        # Record inventory change
        qty = qty * -1 if i_state == PosInventoryState.AVAILABLE else qty
        PosInventoryCls.create_inventory_change(pid, qty, transaction_type, transaction_id, i_state_obj, f_state_obj,
                                                user)

    @classmethod
    def qty_transaction(cls, pid, state_obj, qty, transaction_id):
        pos_inv, _ = PosInventory.objects.select_for_update().get_or_create(product_id=pid, inventory_state=state_obj)
        info_logger.info(
            'initial ' + str(state_obj) + ' inv for product ' + str(pid) + ': ' + str(transaction_id) + ' ' + str(
                pos_inv.quantity))
        pos_inv.quantity = pos_inv.quantity + qty
        pos_inv.save()
        info_logger.info(
            'final ' + str(state_obj) + ' inv for product ' + str(pid) + ': ' + str(transaction_id) + ' ' + str(
                pos_inv.quantity))

    @classmethod
    def create_inventory_change(cls, pid, qty, transaction_type, transaction_id, i_state_obj, f_state_obj, user,
                                initial_qty=None, final_qty=None, remarks=None):
        PosInventoryChange.objects.create(product_id=pid, quantity=qty, transaction_type=transaction_type,
                                          transaction_id=transaction_id, initial_state=i_state_obj,
                                          final_state=f_state_obj, changed_by=user, initial_qty=initial_qty,
                                          final_qty=final_qty, remarks=remarks)

    @classmethod
    def grn_inventory(cls, pid, i_state, f_state, qty, user, transaction_id, transaction_type, po_pack_size):
        """
            Manage GRN related product inventory
        """
        i_state_obj = PosInventoryState.objects.get(inventory_state=i_state)
        f_state_obj = i_state_obj if i_state == f_state else PosInventoryState.objects.get(inventory_state=f_state)
        pos_inv, created = PosInventory.objects.get_or_create(product_id=pid, inventory_state=f_state_obj)
        inv_qty = po_pack_size * qty
        pos_inv.quantity = pos_inv.quantity + inv_qty
        pos_inv.save()
        PosInventoryCls.create_inventory_change(pid, inv_qty, transaction_type, transaction_id, i_state_obj,
                                                f_state_obj,
                                                user)

    @classmethod
    def get_available_inventory(cls, pid, state):
        """
        Returns stock for any product in the given state
        Params:
            pid : product id
            state: inventory state ('new', 'available', 'ordered')
        """
        inventory_object = PosInventory.objects.filter(product_id=pid, inventory_state__inventory_state=state).last()
        return inventory_object.quantity if inventory_object else 0


def api_response(msg, data=None, status_code=status.HTTP_406_NOT_ACCEPTABLE, success=False, extra_params=None):
    ret = {"is_success": success, "message": msg, "response_data": data}
    if extra_params:
        ret.update(extra_params)
    return Response(ret, status=status_code)


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
    elif cart_type in ['basic', 'ecom']:
        if CartProductMapping.objects.filter(cart=cart, retailer_product=product).exists():
            CartProductMapping.objects.filter(cart=cart, retailer_product=product).delete()


def serializer_error(serializer):
    """
        Serializer Error Method
    """
    errors = []
    for field in serializer.errors:
        for error in serializer.errors[field]:
            result = error if 'non_field_errors' in field else ''.join('{} : {}'.format(field, error))
            errors.append(result)
    return errors[0]


def create_user_shop_mapping(user, shop_id):
    """
       while registration of user, store
       shop_id of seller shop with user in ShopCustomerMap
    """
    if not ShopCustomerMap.objects.filter(user=user, shop_id=shop_id).exists():
        ShopCustomerMap.objects.create(user=user, shop_id=shop_id)


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
        json.dumps(request.data, default=lambda skip_image: 'images')
    except Exception as e:
        error_logger.error(e)
        msg = {'is_success': False,
               'message': "Invalid Data Format",
               'response_data': None}
        return msg


def update_customer_pos_cart(ph_no, shop_id, changed_by, email=None, name=None, is_whatsapp=None, is_mlm=False,
                             used_referral_code=None):
    customer = AutoUser.create_update_user(ph_no, email, name, is_whatsapp)
    create_user_shop_mapping(customer, shop_id)
    if is_mlm:
        ReferralCode.register_user_for_mlm(customer, changed_by, used_referral_code)
    return customer


class PosCartCls(object):

    @classmethod
    def refresh_prices(cls, cart_products):
        for cart_product in cart_products:
            product = cart_product.retailer_product
            if product.offer_price and product.offer_start_date and product.offer_end_date and \
                    product.offer_start_date <= datetime.date.today() <= product.offer_end_date:
                cart_product.selling_price = cart_product.retailer_product.offer_price
            elif cart_product.cart.cart_type == 'ECOM' and cart_product.retailer_product.online_enabled and cart_product.retailer_product.online_price:
                cart_product.selling_price = cart_product.retailer_product.online_price
            else:
                cart_product.selling_price = cart_product.retailer_product.selling_price
            cart_product.save()
        return cart_products

    @classmethod
    def out_of_stock_items(cls, cart_products, remove_unavailable=0):
        out_of_stock_items = []

        for cart_product in cart_products:
            product = cart_product.retailer_product
            available_inventory = PosInventoryCls.get_available_inventory(product.id, PosInventoryState.AVAILABLE)
            if available_inventory < cart_product.qty:
                if remove_unavailable:
                    CartProductMapping.objects.filter(id=cart_product.id).delete()
                else:
                    out_of_stock_items += [{
                        "id": product.id,
                        "name": product.name,
                        "qty": cart_product.qty,
                        "available_qty": available_inventory,
                        "mrp": product.mrp,
                        "selling_price": cart_product.selling_price,
                    }]
        return out_of_stock_items


    @classmethod
    def product_deleled(cls, cart_products, remove_deleted=0):
        deleted_items = []

        # if cart_products.filter(retailer_product__is_deleted=True).exists():
        deleled_cart_products = cart_products.filter(retailer_product__is_deleted=True)
        for cart_product in deleled_cart_products:
            product = cart_product.retailer_product
            if remove_deleted:
                CartProductMapping.objects.filter(id=cart_product.id).delete()
            else:
                deleted_items += [{
                    "id": product.id,
                    "name": product.name,
                    "qty": cart_product.qty,
                    "mrp": product.mrp,
                    "selling_price": cart_product.selling_price,
                }]
        return deleted_items


class RewardCls(object):

    @classmethod
    def get_user_redeemable_points(cls, user):
        value_factor = GlobalConfig.objects.get(key='used_reward_factor').value
        points = 0
        if user and ReferralCode.is_marketing_user(user):
            obj = RewardPoint.objects.filter(reward_user=user).last()
            if obj:
                points = max(obj.direct_earned + obj.indirect_earned - obj.points_used, 0)
        return points, value_factor

    @classmethod
    def checkout_redeem_points(cls, cart, redeem_points, use_all=None):
        value_factor = GlobalConfig.objects.get(key='used_reward_factor').value
        if cart.buyer and ReferralCode.is_marketing_user(cart.buyer):
            obj = RewardPoint.objects.filter(reward_user=cart.buyer).last()
            if obj:
                points = max(obj.direct_earned + obj.indirect_earned - obj.points_used, 0)
                if use_all is not None:
                    redeem_points = points if int(use_all) else 0
                redeem_points = min(redeem_points, points, int(cart.order_amount_after_discount * value_factor))
            else:
                redeem_points = 0
        else:
            redeem_points = 0
        max_redeem_points = GlobalConfig.objects.filter(key='max_redeem_points').last()
        if max_redeem_points and max_redeem_points.value:
            if redeem_points > max_redeem_points.value:
                redeem_points = max_redeem_points.value
        cart.redeem_points = redeem_points
        cart.redeem_factor = value_factor
        cart.save()

    @classmethod
    def reward_detail_cart(cls, cart, points):
        data = dict()
        data['redeem_applied'] = 1 if points else 0
        data['available_points'], data['value_factor'] = RewardCls.get_user_redeemable_points(cart.buyer)
        data['max_applicable_points'] = min(data['available_points'],
                                            int(cart.order_amount_after_discount * data['value_factor']))
        max_redeem_points = GlobalConfig.objects.filter(key='max_redeem_points').last()
        if max_redeem_points and max_redeem_points.value:
            if data['max_applicable_points'] > max_redeem_points.value:
                data['max_applicable_points'] = max_redeem_points.value
        data['cart_redeem_points'] = points
        return data

    @classmethod
    def order_buyer_points(cls, amount, user, tid, t_type, changed_by=None):
        """
            Loyalty points to buyer on placing order
        """
        # Calculate number of points
        points = RewardCls.get_loyalty_points(amount, 'direct_reward_percent')

        if not points:
            return 0
        # Add to user direct reward points
        reward_obj = RewardPoint.objects.select_for_update().filter(reward_user=user).last()
        if reward_obj:
            reward_obj.direct_earned += points
            reward_obj.save()
            # Log transaction
            RewardCls.create_reward_log(user, t_type, tid, points, changed_by)
        return points

    @classmethod
    def order_direct_referrer_points(cls, amount, user, tid, t_type, count_considered, changed_by=None):
        """
            Loyalty points to user who referred buyer
        """
        # Calculate number of points
        points = RewardCls.get_loyalty_points_indirect(amount, 'indirect_reward_percent')

        if not points:
            return
        # Add to user direct reward points
        reward_obj = RewardPoint.objects.select_for_update().filter(reward_user=user).last()
        if reward_obj:
            if not count_considered:
                reward_obj.direct_users += 1
            reward_obj.indirect_earned += points
            reward_obj.save()
            # Log transaction
            RewardCls.create_reward_log(user, t_type, tid, points, changed_by)

    @classmethod
    def order_indirect_referrer_points(cls, amount, user, tid, t_type, count_considered, changed_by=None):
        """
            Loyalty points to ancestor referrers of user who referred buyer
            user: user who referred buyer
        """
        # Calculate number of points
        points = RewardCls.get_loyalty_points_indirect(amount, 'indirect_reward_percent')

        if not points:
            return
        # Record Number of ancestors
        referral_obj_indirect = Referral.objects.select_for_update().filter(referral_to_user=user).last()
        total_users = 0
        users = []
        while referral_obj_indirect is not None and referral_obj_indirect.referral_by_user:
            total_users += 1
            ancestor_user = referral_obj_indirect.referral_by_user
            referral_obj_indirect = Referral.objects.filter(referral_to_user=ancestor_user).last()
            users += [ancestor_user]

        # Add to each ancestor's indirect reward points
        if total_users > 0:
            points_per_user = int(points / total_users)
            if not points_per_user:
                return
            for ancestor in users:
                reward_obj = RewardPoint.objects.select_for_update().filter(reward_user=ancestor).last()
                if reward_obj:
                    if not count_considered:
                        reward_obj.indirect_users += 1
                    reward_obj.indirect_earned += points_per_user
                    reward_obj.save()
                    # Log transaction
                    RewardCls.create_reward_log(ancestor, t_type, tid, points_per_user, changed_by)

    @classmethod
    def get_loyalty_points(cls, amount, key):
        """
            Loyalty points for an amount based on percentage (key)
        """
        factor = GlobalConfig.objects.get(key=key).value / 100
        return int(float(amount) * factor)

    @classmethod
    def get_loyalty_points_indirect(cls, amount, key):
        """
            Loyalty points for an amount based on percentage (key)
        """
        factor = GlobalConfig.objects.get(key=key).value / 200
        return int(float(amount) * factor)

    @classmethod
    def create_reward_log(cls, user, t_type, tid, points, changed_by=None, discount=0):
        """
            Log transaction on reward points
        """
        RewardLog.objects.create(reward_user=user, transaction_type=t_type, transaction_id=tid, points=points,
                                 changed_by=changed_by, discount=discount)

    @classmethod
    def redeem_points_on_order(cls, points, redeem_factor, user, changed_by, tid):
        """
            Deduct from loyalty points if used for order
        """
        # Add to user used points
        reward_obj = RewardPoint.objects.select_for_update().filter(reward_user=user).last()
        reward_obj.points_used += int(points)
        reward_obj.save()
        # Log transaction
        RewardCls.create_reward_log(user, 'order_debit', tid, int(points) * -1, changed_by, round(points / redeem_factor, 2))

    @classmethod
    def adjust_points_on_return_cancel(cls, points_credit, user, tid, t_type_credit, t_type_debit, changed_by,
                                       new_order_value, order_no, return_ids=None):
        # Credit redeem points
        if points_credit:
            # Undo from points used
            reward_obj = RewardPoint.objects.select_for_update().filter(reward_user=user).last()
            reward_obj.points_used -= points_credit
            reward_obj.save()
            # Log transaction
            RewardCls.create_reward_log(user, t_type_credit, tid, points_credit, changed_by)

        # Debit points (credited on placing order) based on remaining order value
        credit_log = RewardLog.objects.filter(transaction_id=order_no, transaction_type='order_credit').last()
        points_debit = credit_log.points if credit_log else 0

        if t_type_debit == 'order_return_debit' and points_debit:
            points_debit -= RewardCls.get_loyalty_points(new_order_value, 'direct_reward_percent')

            points_already_debited = 0
            points_already_debited_log = RewardLog.objects.filter(transaction_id__in=return_ids,
                                                                  transaction_type='order_return_debit')
            if points_already_debited_log:
                points_already_debited = points_already_debited_log.aggregate(points=Sum('points'))['points']

            points_debit -= points_already_debited * -1

        if points_debit:
            # Deduct from user direct reward points
            reward_obj = RewardPoint.objects.select_for_update().filter(reward_user=user).last()
            reward_obj.direct_earned -= points_debit
            reward_obj.save()

            # Log transaction
            RewardCls.create_reward_log(user, t_type_debit, tid, points_debit * -1, changed_by)

        reward_obj = RewardPoint.objects.select_for_update().filter(reward_user=user).last()
        net_available = reward_obj.direct_earned + reward_obj.indirect_earned - reward_obj.points_used if reward_obj else 0
        return points_credit, points_debit, net_available


def filter_pos_shop(user):
    return Shop.objects.filter(shop_type__shop_type='f', status=True, approval_status=2, 
                               pos_enabled=True, pos_shop__user=user, pos_shop__status=True)


def check_return_status(view_func):
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        status = request.GET.get('status')
        if not status:
            kwargs['status'] = PosReturnGRNOrder.RETURNED
            # return api_response("No status Selected!")
        elif status not in ['RETURNED', 'CANCELLED', 'Returned', 'Cancelled']:
            return api_response("invalid status Selected!")
        else:
            kwargs['status'] = status.upper()
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


def check_pos_shop(view_func):
    """
        Decorator to validate pos request
    """

    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        # data format
        if request.method == 'POST':
            msg = validate_data_format(request)
            if msg:
                return api_response(msg)
        app_type = request.META.get('HTTP_APP_TYPE', None)
        shop_id = request.META.get('HTTP_SHOP_ID', None)
        if not shop_id:
            return api_response("No Shop Selected!")
        # E-commerce
        if app_type == '3':
            shop = Shop.objects.filter(id=shop_id).last()
            if not shop:
                return api_response("Shop not available!")
            if not shop.online_inventory_enabled:
                return api_response("Franchise Shop Is Not Online Enabled!")
        else:
            qs = filter_pos_shop(request.user)
            qs = qs.filter(id=shop_id)
            shop = qs.last()
            if not shop:
                return api_response("Franchise Shop Id Not Approved / Invalid!")
        kwargs['shop'] = shop
        kwargs['app_type'] = app_type
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


def pos_check_permission(view_func):
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        if not PosShopUserMapping.objects.filter(shop=kwargs['shop'], user=self.request.user, status=True,
                                                 user_type='manager').exists():
            return api_response("You are not authorised to make this change!")
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


def pos_check_permission_delivery_person(view_func):
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        if not PosShopUserMapping.objects.filter(shop=kwargs['shop'], user=self.request.user, status=True,
                                                 user_type__in=['manager', 'cashier', 'store_manager']).exists():
            return api_response("You are not authorised to make this change!")
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


class ProductChangeLogs(object):

    @classmethod
    def product_create(cls, instance, user, event_type, event_id):
        product_changes = {}
        product_change_cols = ProductChangeFields.COLUMN_CHOICES
        for product_change_col in product_change_cols:
            product_changes[product_change_col[0]] = [None, getattr(instance, product_change_col[0])]
        ProductChangeLogs.create_product_log(instance, event_type, event_id, user, product_changes)

    @classmethod
    def product_update(cls, product, old_instance, user, event_type, event_id):
        instance = RetailerProduct.objects.get(id=product.id)
        product_changes, product_change_cols = {}, ProductChangeFields.COLUMN_CHOICES
        for product_change_col in product_change_cols:
            old_value = getattr(old_instance, product_change_col[0])
            new_value = getattr(instance, product_change_col[0])
            if str(old_value) != str(new_value):
                product_changes[product_change_col[0]] = [old_value, new_value]
        ProductChangeLogs.create_product_log(instance, event_type, event_id, user, product_changes)

    @classmethod
    def create_product_log(cls, product, event_type, event_id, user, product_changes):
        if product_changes:
            product_change_obj = ProductChange.objects.create(product=product, event_type=event_type, event_id=event_id,
                                                              changed_by=user)
            for col in product_changes:
                ProductChangeFields.objects.create(product_change=product_change_obj, column_name=col,
                                                   old_value=product_changes[col][0], new_value=product_changes[col][1])


class PosAddToCart(object):

    @staticmethod
    def validate_request_body(view_func):

        @wraps(view_func)
        def _wrapped_view_func(self, request, *args, **kwargs):
            shop, cart_id = kwargs['shop'], kwargs['pk'] if 'pk' in kwargs else None

            # Check if existing or new cart
            cart = None
            if cart_id:
                cart = Cart.objects.filter(id=cart_id, seller_shop=shop, cart_type='BASIC').last()
                if not cart:
                    return api_response("Cart Doesn't Exist")
                elif cart.cart_status == Cart.ORDERED:
                    return api_response("Order already placed on this cart!", None, status.HTTP_406_NOT_ACCEPTABLE,
                                        False, {'error_code': error_code.CART_NOT_ACTIVE})
                elif cart.cart_status == Cart.DELETED:
                    return api_response("This cart was deleted!", None, status.HTTP_406_NOT_ACCEPTABLE,
                                        False, {'error_code': error_code.CART_NOT_ACTIVE})
                elif cart.cart_status not in [Cart.ACTIVE, Cart.PENDING]:
                    return api_response("Active Cart Doesn't Exist!")

            # Quantity check
            qty = request.data.get('qty')
            if qty is None or int(qty) < 0 or (int(qty) == 0 and not cart_id):
                return api_response("Qty Invalid!")

            # Either existing product OR info for adding new product
            product = None
            new_product_info = dict()
            # Adding new product in catalogue and cart
            if not request.data.get('product_id'):
                # User permission check
                pos_shop_user_obj = validate_user_type_for_pos_shop(shop, request.user)
                if 'error' in pos_shop_user_obj:
                    if 'Unauthorised user.' in pos_shop_user_obj['error']:
                        return api_response('Unauthorised user to add new product.')
                    return api_response(pos_shop_user_obj['error'])

                # Provided product info check
                name, sp, ean, mrp = request.data.get('product_name'), request.data.get('selling_price'), \
                                     request.data.get('product_ean_code'), request.data.get('product_mrp')
                if not name or not sp or not ean or not mrp:
                    return api_response("Please provide product_id OR product_name, product_ean_code, "
                                        "selling_price and product_mrp!")
                if sp > mrp:
                    return api_response("Selling Price should be equal to OR less than MRP!")

                # Linked product check
                linked_pid = request.data.get('linked_product_id') if request.data.get('linked_product_id') else None
                new_product_info['type'] = 1
                if linked_pid:
                    linked_product = Product.objects.filter(id=linked_pid).last()
                    if not linked_product:
                        return api_response(f"GramFactory product not found for given {linked_pid}")
                    new_product_info['type'] = 2

                new_product_info['name'], new_product_info['sp'], new_product_info['linked_pid'], new_product_info['mrp'] = \
                    name, sp, linked_pid, mrp
                new_product_info['ean'] = ean
                product_pack_type = 'packet'
            # Add by Product Id
            else:
                try:
                    product = RetailerProduct.objects.get(id=request.data.get('product_id'), shop=shop)
                except ObjectDoesNotExist:
                    return api_response("Product Not Found!")

                price_change = request.data.get('price_change')
                mrp_change = int(self.request.data.get('mrp_change')) if self.request.data.get('mrp_change') else 0

                # Check If MRP and Selling price Change
                if price_change in [1, 2] and mrp_change == 1:
                    # User permission check
                    pos_shop_user_obj = validate_user_type_for_pos_shop(shop, self.request.user)
                    if 'error' in pos_shop_user_obj:
                        if 'Unauthorised user.' in pos_shop_user_obj['error']:
                            return api_response('Unauthorised user to update product price.')
                        return api_response(pos_shop_user_obj['error'])

                    # Price, MRP update check
                    selling_price = request.data.get('selling_price')
                    product_mrp = self.request.data.get('product_mrp')
                    if not selling_price:
                        return api_response("Please provide selling price to change price")
                    if not product_mrp:
                        return api_response("Please provide mrp to change product mrp")
                    if Decimal(selling_price) > Decimal(product_mrp):
                        return api_response("Selling Price should be equal to OR less than MRP")

                # Check If MRP Change
                elif mrp_change == 1:
                    # User permission check
                    pos_shop_user_obj = validate_user_type_for_pos_shop(shop, self.request.user)
                    if 'error' in pos_shop_user_obj:
                        if 'Unauthorised user.' in pos_shop_user_obj['error']:
                            return api_response('Unauthorised user to update product price.')
                        return api_response(pos_shop_user_obj['error'])
                    # MRP update check
                    product_mrp = self.request.data.get('product_mrp')
                    if not product_mrp:
                        return api_response("Please provide mrp to change product mrp")
                    if product.selling_price and product.selling_price > product_mrp:
                        return api_response("MRP should be equal to OR greater than Selling Price")

                # Check if selling price is less than equal to mrp if price change
                elif price_change in [1, 2]:
                    # User permission check
                    pos_shop_user_obj = validate_user_type_for_pos_shop(shop, self.request.user)
                    if 'error' in pos_shop_user_obj:
                        if 'Unauthorised user.' in pos_shop_user_obj['error']:
                            return api_response('Unauthorised user to update product price.')
                        return api_response(pos_shop_user_obj['error'])

                    # Price update check
                    selling_price = request.data.get('selling_price')
                    if not selling_price:
                        return api_response("Please provide selling price to change price")
                    if product.mrp and Decimal(selling_price) > product.mrp:
                        return api_response("Selling Price should be equal to OR less than MRP")

                # If adding discounted product for given product
                add_discounted = request.data.get('add_discounted', None)
                if add_discounted and product.sku_type != 4:
                    if RetailerProductCls.is_discounted_product_available(product):
                        product = product.discounted_product
                    else:
                        return api_response("Discounted product not available")

                # check_discounted = request.data.get('check_discounted', None)
                # if check_discounted and RetailerProductCls.is_discounted_product_exists(
                #         product) and product.discounted_product.status == 'active':
                #     return api_response('Discounted product found', self.serialize_product(product),
                #                         status.HTTP_300_MULTIPLE_CHOICES, False)

                # Check discounted product
                if product.sku_type == 4:
                    discounted_stock = PosInventoryCls.get_available_inventory(product.id, PosInventoryState.AVAILABLE)
                    if product.status != 'active':
                        return api_response("The discounted product is de-activated!")
                    elif discounted_stock < Decimal(qty):
                        return api_response("The discounted product has only {} quantity in stock!".format(discounted_stock))

                product_pack_type = product.product_pack_type

            # qty w.r.t pack type
            kwargs['conversion_unit_id'] = None
            if product_pack_type == 'packet':
                qty = int(qty)
            else:
                qty, kwargs['conversion_unit_id'] = get_default_qty(self.request.data.get('qty_unit'),
                                                                    product, qty)

            # Return with objects
            kwargs['product'] = product
            kwargs['new_product_info'] = new_product_info
            kwargs['quantity'] = qty
            kwargs['cart'] = cart
            return view_func(self, request, *args, **kwargs)

        return _wrapped_view_func

    @staticmethod
    def validate_request_body_ecom(view_func):

        @wraps(view_func)
        def _wrapped_view_func(self, request, *args, **kwargs):
            shop = kwargs['shop']
            # Quantity check
            qty = request.data.get('qty')
            if qty is None or not str(qty).isdigit() or qty < 0:
                return api_response("Qty Invalid!")

            # Product check
            try:
                product = RetailerProduct.objects.get(id=request.data.get('product_id'), status='active',
                                                      shop=kwargs['shop'], online_enabled=True)
            except ObjectDoesNotExist:
                return api_response("Product Not Found!")

            # Inventory check
            cart_product = CartProductMapping.objects.filter(cart__cart_type='ECOM', cart__buyer=self.request.user,
                                                             retailer_product=product, product_type=1,
                                                             cart__seller_shop=kwargs['shop'],
                                                             cart__cart_status='active').last()
            existing_cart_qty = 0
            if cart_product:
                existing_cart_qty = cart_product.qty
            if qty > existing_cart_qty and shop.online_inventory_enabled:
                available_inventory = PosInventoryCls.get_available_inventory(product.id, PosInventoryState.AVAILABLE)
                if available_inventory < qty:
                    return api_response("You cannot add any more quantities for this product!")

            # Return with objects
            kwargs['product'] = product
            kwargs['quantity'] = qty
            return view_func(self, request, *args, **kwargs)

        return _wrapped_view_func


def get_default_qty(given_qty_unit, product, qty):
    default_unit = MeasurementUnit.objects.get(category=product.measurement_category, default=True)
    qty_unit = default_unit
    if given_qty_unit:
        try:
            qty_unit = MeasurementUnit.objects.get(unit=given_qty_unit)
        except:
            qty_unit = default_unit
    qty = round(round(Decimal(qty), 3) * qty_unit.conversion / default_unit.conversion, 3)
    return qty, qty_unit.id


def create_po_franchise(user, order_no, seller_shop, buyer_shop, products):
    bill_add = Address.objects.filter(shop_name=seller_shop, address_type='billing').last()
    vendor, created = Vendor.objects.get_or_create(company_name=seller_shop.shop_name)
    if created:
        vendor.vendor_name, vendor.address, vendor.pincode = 'PepperTap', bill_add.address_line1, bill_add.pincode
        vendor.city, vendor.state = bill_add.city, bill_add.state
        vendor.save()
    with transaction.atomic():
        cart, created = PosCart.objects.get_or_create(vendor=vendor, retailer_shop=buyer_shop, gf_order_no=order_no)
        cart.last_modified_by = user
        if created:
            cart.raised_by = user
        cart.save()
        product_ids = []
        for product in products:
            retailer_product = RetailerProduct.objects.filter(linked_product=product.cart_product, shop=buyer_shop,
                                                              is_deleted=False, product_ref__isnull=True).last()
            product_ids += [retailer_product.id]
            mapping, _ = PosCartProductMapping.objects.get_or_create(cart=cart, product=retailer_product)
            if not mapping.is_grn_done:
                mapping.price = product.get_cart_product_price(seller_shop.id, buyer_shop.id).get_per_piece_price(
                    product.no_of_pieces)
                if retailer_product.product_pack_type == 'loose':
                    measurement_category = MeasurementCategory.objects.get(
                        category=retailer_product.measurement_category.category.lower())
                    mapping.qty_conversion_unit = MeasurementUnit.objects.get(category=measurement_category,
                                                                              default=True)
                mapping.pack_size = retailer_product.purchase_pack_size
                mapping.qty = product.no_of_pieces
                mapping.is_bulk = True
                mapping.save()
        PosCartProductMapping.objects.filter(cart=cart, is_grn_done=False).exclude(product_id__in=product_ids).delete()
    return created, cart.po_no


def generate_debit_note_number(returned_obj, billing_address_instance):
    return "DNPR" + str(returned_obj.pr_number) + str(billing_address_instance)



