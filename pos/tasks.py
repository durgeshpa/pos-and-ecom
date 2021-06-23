import logging
import sys
from celery.task import task
from elasticsearch import Elasticsearch

from django.db import transaction

from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix
from pos.models import RetailerProduct
from wms.models import PosInventory, PosInventoryState
from marketing.models import RewardPoint, Referral
from accounts.models import User
from pos.common_functions import RewardCls

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


def order_loyalty_points_credit(amount, user_id, tid, t_type_b, t_type_i, changed_by=None, shop_id=None):
    """
        Loyalty points to buyer, user who referred buyer and ancestor referrers of user who referred buyer
    """
    try:
        with transaction.atomic():
            user = User.objects.get(id=user_id)

            if changed_by:
                changed_by = User.objects.get(id=changed_by)
            # Buyer Rewards
            points_credit = RewardCls.order_buyer_points(amount, user, tid, t_type_b, changed_by)

            # Reward Referrer Direct and Indirect
            referral_obj = Referral.objects.filter(referral_to_user=user).last()
            if referral_obj:
                parent_referrer = referral_obj.referral_by_user
                # direct reward to user who referred buyer
                RewardCls.order_direct_referrer_points(amount, parent_referrer, tid, t_type_i, referral_obj.user_count_considered,
                                                       changed_by)

                # indirect reward to ancestor referrers
                RewardCls.order_indirect_referrer_points(amount, parent_referrer, tid, t_type_i,
                                                         referral_obj.user_count_considered, changed_by)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        error_logger.error("Rewards not processed for order {} exception {} Line No {}".format(tid, e, exc_tb.tb_lineno))