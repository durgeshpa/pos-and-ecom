import logging
import sys
import os
from celery.task import task
from elasticsearch import Elasticsearch
import datetime
from wkhtmltopdf.views import PDFTemplateResponse
from num2words import num2words

from django.db import transaction
from django.core.mail import EmailMessage

from global_config.models import GlobalConfig
from global_config.views import get_config
from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix
from pos.models import RetailerProduct, PosCart
from wms.models import PosInventory, PosInventoryState
from marketing.models import Referral
from accounts.models import User
from pos.common_functions import RewardCls, RetailerProductCls
from marketing.sms import SendSms
from pos.offers import BasicCartOffers

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

        discounted_product_exists = RetailerProductCls.is_discounted_product_exists(product)
        discounted_product_available = True if RetailerProductCls.is_discounted_product_available(product) else False
        discounted_price, discounted_stock = None, None
        if discounted_product_exists:
            discounted_price = product.discounted_product.selling_price
            discounted_inv = PosInventory.objects.filter(product=product.discounted_product,
                                                         inventory_state=inv_available).last()
            discounted_stock = discounted_inv.quantity if discounted_inv else 0

        is_discounted = True if product.sku_type == 4 else False

        offer = BasicCartOffers.get_basic_combo_coupons([product.id], product.shop.id)
        coupons = None
        if offer:
            coupons = [
                {
                    "coupon_code": offer[0]['coupon_code'],
                    "coupon_type": offer[0]['coupon_type']
                }
            ]

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
            'stock_qty': stock_qty,
            'is_discounted': is_discounted,
            'discounted_product_exists': discounted_product_exists,
            'discounted_product_available': discounted_product_available,
            'discounted_price': discounted_price,
            'discounted_stock': discounted_stock,
            'offer_price': product.offer_price,
            'offer_start_date': product.offer_start_date,
            'offer_end_date': product.offer_end_date,
            'combo_available': True if coupons else False,
            'coupons': coupons
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
                RewardCls.order_direct_referrer_points(amount, parent_referrer, tid, t_type_i,
                                                       referral_obj.user_count_considered,
                                                       changed_by)

                # indirect reward to ancestor referrers
                RewardCls.order_indirect_referrer_points(amount, parent_referrer, tid, t_type_i,
                                                         referral_obj.user_count_considered, changed_by)
                referral_obj.user_count_considered = True
                referral_obj.save()
            return points_credit
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        error_logger.error(
            "Rewards not processed for order {} exception {} Line No {}".format(tid, e, exc_tb.tb_lineno))


@task()
def mail_to_vendor_on_po_creation(cart_id):
    instance = PosCart.objects.get(id=cart_id)
    try:
        recipient_list = [instance.vendor.email]
        vendor_name = instance.vendor.vendor_name
        po_no = instance.po_no
        subject = "Purchase Order {} | {}".format(po_no, instance.retailer_shop.shop_name)
        body = 'Dear {}, \n \n Find attached PO from {}, PepperTap POS. \n \n Note: Take Prior appointment before delivery ' \
               'and bring PO copy along with Original Invoice. \n \n Thanks, \n {}'.format(
            vendor_name, instance.retailer_shop.shop_name, instance.retailer_shop.shop_name)

        filename = 'PO_PDF_{}_{}_{}.pdf'.format(po_no, datetime.datetime.today().date(), vendor_name)
        template_name = 'admin/purchase_order/retailer_purchase_order.html'
        cmd_option = {
            'encoding': 'utf8',
            'margin-top': 3
        }
        data = generate_pdf_data(instance)
        response = PDFTemplateResponse(
            request=None, template=template_name,
            filename=filename, context=data,
            show_content_in_browser=False, cmd_options=cmd_option
        )
        email = EmailMessage()
        email.subject = subject
        email.body = body
        sender = GlobalConfig.objects.get(key='sender')
        email.from_email = sender.value
        email.to = recipient_list
        email.attach(filename, response.rendered_content, 'application/pdf')
        email.send()

        # send sms
        body = 'Dear {}, \n \n PO number {} has been generated from {}, PepperTap POS and sent to you over mail. \n \n N' \
               'ote: Take Prior appointment before delivery and bring PO copy along with Original Invoice. \n \n T' \
               'hanks, \n {}'.format(vendor_name, instance.po_no, instance.retailer_shop.shop_name,
                                     instance.retailer_shop.shop_name)

        message = SendSms(phone=instance.vendor.phone_number,
                          body=body)
        message.send()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        error_logger.error("Retailer PO mail, sms not sent - Po number {}, {}, line no {}".format(instance.po_no, e,
                                                                                                  exc_tb.tb_lineno))


def generate_pdf_data(instance):
    products = instance.po_products.all()
    order = instance.pos_po_order
    order_id = order.order_no
    sum_amount, sum_qty = 0, 0
    billing = instance.retailer_shop.shop_name_address_mapping.filter(address_type='billing').last()
    shipping = instance.retailer_shop.shop_name_address_mapping.filter(address_type='billing').last()
    for m in products:
        sum_qty = sum_qty + m.qty
        sum_amount = sum_amount + m.total_price()

    amt = [num2words(i) for i in str(sum_amount).split('.')]
    amt_in_words = amt[0]
    data = {
        "object": instance,
        "products": products,
        "po_instance": instance,
        "billing": billing,
        "shipping": shipping,
        "sum_qty": sum_qty,
        "total_amount": sum_amount,
        "amt_in_words": amt_in_words,
        "order_id": order_id,
        "url": get_config('SITE_URL'),
        "scheme": get_config('CONNECTION'),
    }
    return data
