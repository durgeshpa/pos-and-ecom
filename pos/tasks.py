import logging
from celery.task import task
from elasticsearch import Elasticsearch

from django.db import transaction

from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix
from pos.models import RetailerProduct
from wms.models import PosInventory, PosInventoryState
from global_config.models import GlobalConfig
from marketing.models import RewardPoint, Referral, RewardLog
from accounts.models import User

es = Elasticsearch(["https://search-gramsearch-7ks3w6z6mf2uc32p3qc4ihrpwu.ap-south-1.es.amazonaws.com"])
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


def create_es_index(index):
    return "{}-{}".format(es_prefix, index)


@task
def update_shop_retailer_product_es(shop_id, product_id, **kwargs):
    """
        Update RetailerProduct elastic data on any change
        shop_id - id of the particular shop that the product belongs to
        product_id - RetailerProduct id
    """
    try:
        if shop_id:
            if product_id and RetailerProduct.objects.filter(id=product_id).exists():
                products = RetailerProduct.objects.filter(id=product_id)
            else:
                products = RetailerProduct.objects.filter(id=product_id, shop_id=shop_id)
            update_es(products, shop_id)
    except Exception as e:
        info_logger.info(e)


def update_es(products, shop_id):
    """
        Update retailer products in es
    """
    for product in products:
        info_logger.info(product)
        margin = None
        if product.mrp and product.selling_price:
            margin = round(((product.mrp - product.selling_price) / product.mrp) * 100, 2)
        product_img = product.retailer_product_image.all()
        product_images = [
            {
                "image_id": p_i.id,
                "image_name": p_i.image_name,
                "image_alt": p_i.image_alt_text,
                "image_url": p_i.image.url
            }
            for p_i in product_img
        ]
        # get brand and category from linked GramFactory product
        brand = ''
        category = ''
        if product.linked_product and product.linked_product.parent_product:
            brand = str(product.linked_product.product_brand)
            if product.linked_product.parent_product.parent_product_pro_category:
                category = [str(c.category) for c in
                            product.linked_product.parent_product.parent_product_pro_category.filter(status=True)]

        inv_available = PosInventoryState.objects.get(inventory_state=PosInventoryState.AVAILABLE)
        pos_inv = PosInventory.objects.filter(product=product, inventory_state=inv_available).last()
        stock_qty = pos_inv.quantity if pos_inv else 0
        params = {
            'id': product.id,
            'name': product.name,
            'mrp': product.mrp,
            'ptr': product.selling_price,
            'margin': margin,
            'product_images': product_images,
            'brand': brand,
            'category': category,
            'ean': product.product_ean_code,
            'status': product.status,
            'created_at': product.created_at,
            'modified_at': product.modified_at,
            'description': product.description if product.description else "",
            'linked_product_id': product.linked_product.id if product.linked_product else '',
            'stock_qty': stock_qty
        }
        es.index(index=create_es_index('rp-{}'.format(shop_id)), id=params['id'], body=params)


@task()
def order_loyalty_points(amount, user_id, tid, changed_by=None):
    """
        Loyalty points to buyer, user who referred buyer and ancestor referrers of user who referred buyer
    """
    try:
        with transaction.atomic():
            user = User.objects.get(id=user_id)
            if changed_by:
                changed_by = User.objects.get(id=changed_by)
            # Buyer Rewards
            order_buyer_points(amount, user, tid, changed_by)

            # Reward Referrer Direct and Indirect
            referral_obj = Referral.objects.filter(referral_to_user=user).last()
            if referral_obj:
                parent_referrer = referral_obj.referral_by_user
                # direct reward to user who referred buyer
                order_direct_referrer_points(amount, parent_referrer, tid, referral_obj.user_count_considered, changed_by)

                # indirect reward to ancestor referrers
                order_indirect_referrer_points(amount, parent_referrer, tid, referral_obj.user_count_considered, changed_by)
    except Exception as e:
        error_logger.error("Rewards not processed for order {} exception {}".format(tid, e))


def order_buyer_points(amount, user, tid, changed_by=None):
    """
        Loyalty points to buyer on placing order
    """
    # Calculate number of points
    points = get_loyalty_points(amount, 'self_reward_percent')

    # Add to user direct reward points
    reward_obj = RewardPoint.objects.filter(reward_user=user).last()
    if reward_obj:
        reward_obj.direct_earned += points
        reward_obj.save()
    else:
        RewardPoint.objects.create(reward_user=user, direct_earned=points)

    # Log transaction
    create_reward_log(user, 'purchase_reward', tid, points, changed_by)


def order_direct_referrer_points(amount, user, tid, count_considered, changed_by=None):
    """
        Loyalty points to user who referred buyer
    """
    # Calculate number of points
    points = get_loyalty_points(amount, 'direct_reward_percent')

    # Add to user direct reward points
    reward_obj = RewardPoint.objects.filter(reward_user=user).last()
    if reward_obj:
        if not count_considered:
            reward_obj.direct_users = 1
        reward_obj.direct_earned += points
        reward_obj.save()
    else:
        RewardPoint.objects.create(reward_user=user, direct_users=1, direct_earned=points)

    # Log transaction
    create_reward_log(user, 'direct_reward', tid, points, changed_by)


def order_indirect_referrer_points(amount, user, tid, count_considered, changed_by=None):
    """
        Loyalty points to ancestor referrers of user who referred buyer
        user: user who referred buyer
    """
    # Calculate number of points
    points = get_loyalty_points(amount, 'indirect_reward_percent')

    # Record Number of ancestors
    referral_obj_indirect = Referral.objects.filter(referral_to_user=user).last()
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
        for ancestor in users:
            reward_obj = RewardPoint.objects.filter(reward_user=ancestor).last()
            if reward_obj:
                if not count_considered:
                    reward_obj.indirect_users += 1
                reward_obj.indirect_earned += points_per_user
                reward_obj.save()
            else:
                RewardPoint.objects.create(reward_user=ancestor, indirect_users=1, indirect_earned=points_per_user)

            # Log transaction
            create_reward_log(ancestor, 'indirect_reward', tid, points_per_user, changed_by)


def get_loyalty_points(amount, key):
    """
        Loyalty points for an amount based on percentage (key)
    """
    factor = GlobalConfig.objects.get(key=key).value / 100
    return int(float(amount) * factor)


def create_reward_log(user, t_type, tid, points, changed_by=None):
    """
        Log transaction on reward points
    """
    RewardLog.objects.create(reward_user=user, transaction_type=t_type, transaction_id=tid, points=points,
                             changed_by=changed_by)
