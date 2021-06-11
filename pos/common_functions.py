import logging
import json

from rest_framework.response import Response
from rest_framework import status
from django.urls import reverse
from django.db.models import Q

from retailer_to_sp.models import CartProductMapping, Order
from retailer_to_gram.models import (CartProductMapping as GramMappedCartProductMapping)
from coupon.models import RuleSetProductMapping, Coupon, CouponRuleSet
from shops.models import Shop
from accounts.models import User
from wms.models import PosInventory, PosInventoryChange, PosInventoryState

from pos.models import RetailerProduct, UserMappedShop, RetailerProductImage

ORDER_STATUS_MAP = {
    1: Order.ORDERED,
    2: Order.PARTIALLY_RETURNED,
    3: Order.FULLY_RETURNED,
    4: Order.CANCELLED
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
    def create_images(cls, product, images):
        if images:
            count = 0
            for image in images:
                if image.name == 'gmfact_image.jpeg':
                    count += 1
                    image.name = str(product.sku) + '_' + str(count) + '_' + image.name
                RetailerProductImage.objects.create(product=product, image=image)

    @classmethod
    def update_images(cls, product, images):
        if images:
            for image in images:
                image.name = str(product.sku) + '_' + image.name
                RetailerProductImage.objects.create(product=product, image=image)

    @classmethod
    def update_price(cls, product_id, selling_price):
        product = RetailerProduct.objects.filter(id=product_id).last()
        product.selling_price = selling_price
        product.save()

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
    def stock_inventory(cls, pid, i_state, f_state, qty, user, transaction_id, transaction_type):
        """
            Create/Update available inventory for product
        """
        i_state_obj = PosInventoryState.objects.get(inventory_state=i_state)
        f_state_obj = i_state_obj if i_state == f_state else PosInventoryState.objects.get(inventory_state=f_state)
        pos_inv, created = PosInventory.objects.get_or_create(product_id=pid, inventory_state=f_state_obj)
        if not created and qty == pos_inv.quantity:
            return
        qty_change = qty - pos_inv.quantity
        pos_inv.quantity = qty
        pos_inv.save()
        PosInventoryCls.create_inventory_change(pid, qty_change, transaction_type, transaction_id, i_state_obj,
                                                f_state_obj, user)

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
        PosInventoryCls.create_inventory_change(pid, qty, transaction_type, transaction_id, i_state_obj, f_state_obj,
                                                user)

    @classmethod
    def qty_transaction(cls, pid, state_obj, qty, transaction_id):
        pos_inv, _ = PosInventory.objects.select_for_update().get_or_create(product_id=pid, inventory_state=state_obj)
        info_logger.info('initial ' + str(state_obj) + ' inv for product ' + str(pid) + ': ' + str(transaction_id) + ' ' + str(pos_inv.quantity))
        pos_inv.quantity = pos_inv.quantity + qty
        pos_inv.save()
        info_logger.info('final ' + str(state_obj) + ' inv for product ' + str(pid) + ': ' + str(transaction_id) + ' ' + str(pos_inv.quantity))

    @classmethod
    def create_inventory_change(cls, pid, qty, transaction_type, transaction_id, i_state_obj, f_state_obj, user):
        PosInventoryChange.objects.create(product_id=pid, quantity=qty, transaction_type=transaction_type,
                                          transaction_id=transaction_id, initial_state=i_state_obj,
                                          final_state=f_state_obj, changed_by=user)


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
    elif cart_type == 'basic':
        if CartProductMapping.objects.filter(cart=cart, retailer_product=product).exists():
            CartProductMapping.objects.filter(cart=cart, retailer_product=product).delete()


def get_pos_shop(user):
    return Shop.objects.filter(Q(shop_owner=user) | Q(related_users=user), shop_type__shop_type='f', approval_status=2,
                               pos_enabled=1).last()


def get_shop_id_from_token(user):
    """
        Get shop_id from user
    """
    shop = get_pos_shop(user)
    if not shop:
        return "No Approved Franchise Shop exists for the User!"
    return shop.id


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
        json.dumps(request.data, default=lambda skip_image: 'images')
    except Exception as e:
        error_logger.error(e)
        msg = {'is_success': False,
               'message': "Invalid Data Format",
               'response_data': None}
        return msg


def update_pos_customer(ph_no, shop_id, email, name, is_whatsapp):
    customer, created = User.objects.get_or_create(phone_number=ph_no)
    if created:
        create_user_shop_mapping(customer, shop_id)
    customer.email = email if email and not customer.email else customer.email
    customer.first_name = name if name and not customer.first_name else customer.first_name
    customer.is_whatsapp = True if is_whatsapp else False
    customer.save()
    return customer
