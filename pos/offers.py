from operator import itemgetter
from datetime import datetime
from elasticsearch import Elasticsearch

from retailer_to_sp.models import CartProductMapping, Cart
from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix

es = Elasticsearch(["https://search-gramsearch-7ks3w6z6mf2uc32p3qc4ihrpwu.ap-south-1.es.amazonaws.com"])


class BasicCartOffers(object):

    @classmethod
    def refresh_offers(cls, cart, auto_apply=False, coupon_id=''):
        """
            Refresh All Cart Offers
            Combo On all products
            Cart level offers
        """
        cart_products = cart.rt_cart_list.all()
        cart_value = 0
        if cart_products:
            for product_mapping in cart_products:
                cart_value += product_mapping.selling_price * product_mapping.qty
            # Add/Remove/Update combo offers on all products
            offers_list = BasicCartOffers.refresh_combo(cart, cart_products)
            # Check already applied cart offer
            offers_list = BasicCartOffers.refresh_basic_cart_offers(Cart.objects.get(pk=cart.id), cart_value,
                                                                    offers_list, auto_apply, coupon_id)
            Cart.objects.filter(pk=cart.id).update(offers=offers_list['offers_list'])
            return offers_list
        else:
            return {'error': 'No Products In Cart Yet!'}

    @classmethod
    def refresh_combo(cls, cart, cart_products):
        """
            Refresh combo offers on cart products
            Check applied offers, new offers
        """
        # Collect ids for all products added in cart
        products_id = []
        for product_map in cart_products:
            if product_map.selling_price > 0:
                products_id += [product_map.retailer_product.id]
        # Get combo coupons applicable for all products from es
        combo_offers = BasicCartOffers.get_basic_combo_coupons(products_id, cart.seller_shop.id,
                                                               (len(products_id) * 10))
        # Offers corresponding to product
        offers_mapping = {}
        for offer in combo_offers:
            if offer['purchased_product'] in offers_mapping:
                previous_offers = offers_mapping[offer['purchased_product']]
                offers_mapping[offer['purchased_product']] = previous_offers + [offer]
            else:
                offers_mapping[offer['purchased_product']] = [offer]
        offers_list = cart.offers
        for product_map in cart_products:
            # Refresh combo for all added product
            if product_map.selling_price > 0:
                c_list = offers_mapping[
                    product_map.retailer_product.id] if product_map.retailer_product.id in offers_mapping else []
                # Add/remove/update combo on a product
                offers_list = BasicCartOffers.basic_combo_offers(product_map.qty, c_list, Cart.objects.get(pk=cart.id),
                                                                 product_map.retailer_product, offers_list,
                                                                 float(product_map.selling_price))
        return offers_list

    @classmethod
    def get_basic_combo_coupons(cls, purchased_product_ids, shop_id, size=10):
        """
            Get Product combo coupons from elasticsearch
        """
        date = datetime.now()
        body = {
            "from": 0,
            "size": size,
            "query": {"bool": {"filter": [{"term": {"active": True}},
                                          {"term": {"coupon_type": 'catalogue_combo'}},
                                          {"terms": {"purchased_product": purchased_product_ids}},
                                          {"range": {"start_date": {"lte": date}}},
                                          {"range": {"end_date": {"gte": date}}}]
                               }
                      },
            "sort": [
                {"purchased_product_qty": "desc"},
            ]
        }
        c_list = []
        try:
            coupons_list = es.search(index=create_es_index("rc-{}".format(shop_id)), body=body)
            for c in coupons_list['hits']['hits']:
                c_list.append(c["_source"])
        except:
            pass
        return c_list

    @classmethod
    def basic_combo_offers(cls, qty, c_list, cart, product, offers_list, sp):
        """
            Combo Offers on a product in basic cart
        """
        offers_list = [] if not offers_list else offers_list
        # Product price total
        product_total = qty * sp
        # To add details of product discount subtotal if no combo offers present
        general_offer = {}
        if not c_list:
            general_offer = BasicCartOffers.get_offer_no_coupon(product.id, product_total)
        # Applied combo offers on product
        applied_offers = []
        # Free item ids of applied combo offers on product
        free_item_ids = {}
        # Next applicable combo offer on product
        next_offer = {}
        added_qty = qty
        for coupon in c_list:
            # Quantity in cart should be greater than purchased product quantity given for combo
            if int(qty) >= int(coupon['purchased_product_qty']):
                offer = BasicCartOffers.get_offer_combo_coupon(coupon, product_total)
                # Units of purchased product quantity
                purchased_product_multiple = int(int(qty) / int(coupon['purchased_product_qty']))
                # No of free items to be given on qty left
                free_item_qty = int(purchased_product_multiple * int(coupon['free_product_qty']))
                # No of free items to be given on total qty in cart
                free_item_ids[offer['free_item_id']] = free_item_qty + free_item_ids[offer['free_item_id']] if free_item_ids and\
                    offer['free_item_id'] in free_item_ids else free_item_qty
                applied_offers.append(offer)
                # Remaining product qty to check other offers
                qty = qty - purchased_product_multiple * int(coupon['purchased_product_qty'])
            elif not applied_offers:
                # Next applicable combo offer on product
                next_offer = BasicCartOffers.get_offer_next(coupon, product_total, added_qty)

        # Update quantities of all free products in applied offers
        for offer in applied_offers:
            cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart,
                                                                       retailer_product_id=offer['free_item_id'],
                                                                       parent_retailer_product_id=offer['item_id'])
            cart_mapping.selling_price = 0
            cart_mapping.qty = free_item_ids[offer['free_item_id']]
            cart_mapping.no_of_pieces = free_item_ids[offer['free_item_id']]
            cart_mapping.save()

        # Add next_offer and general_offer to total offers list
        if next_offer:
            applied_offers.append(next_offer)
        if general_offer:
            applied_offers.append(general_offer)
        # Update offers, remove previous not applicable combos on product
        offers_list = BasicCartOffers.update_combo(cart, product, applied_offers, offers_list, free_item_ids)
        return offers_list

    @classmethod
    def get_offer_no_coupon(cls, product_id, product_total):
        """
            To add details of product discount subtotal if no combo offers present
        """
        return {
            "coupon_type": "catalog",
            "type": "none",
            "available_type": "none",
            'item_id': product_id,
            'product_subtotal': product_total,
            'discounted_product_subtotal': product_total,
            'discounted_product_subtotal_after_sku_discount': product_total,
        }

    @classmethod
    def get_default_combo_fields(cls, coupon, product_total, sub_type):
        """
            Combo Applicable Offer Details
        """
        return {
            'coupon_type': "catalog",
            'type': sub_type,
            'available_type': "combo",
            'coupon_id': coupon['id'],
            'coupon_code': coupon['coupon_code'],
            'item_id': coupon['purchased_product'],
            'product_subtotal': product_total,
            'discounted_product_subtotal': product_total,
            'discounted_product_subtotal_after_sku_discount': product_total
        }

    @classmethod
    def get_offer_next(cls, coupon, product_total, added_qty):
        """
            Combo Applicable Offer
        """
        ret = BasicCartOffers.get_default_combo_fields(coupon, product_total, 'none')
        ret.update({
            'display_text': "Add " + str(int(coupon['purchased_product_qty']) - int(added_qty)) + " more to get " \
                            + str(coupon['free_product_qty']) + " " + str(coupon['free_product_name']) + " Free"
        })
        return ret

    @classmethod
    def get_offer_combo_coupon(cls, coupon, product_total):
        """
            Combo Applied Offer
        """
        ret = BasicCartOffers.get_default_combo_fields(coupon, product_total, 'combo')
        ret.update({
            'free_item_id': coupon['free_product'],
            'item_qty': coupon['purchased_product_qty'],
            'free_item_qty': coupon['free_product_qty'],
            'display_text': 'Combo Offer Applied'
        })
        return ret

    @classmethod
    def update_combo(cls, cart, product, applied_offers, offers_list, free_item_ids):
        """
            Return updated list of offers after adding/updating combo offer on product
        """
        cart_offers_new = []
        if offers_list:
            for offer in offers_list:
                if offer['coupon_type'] == 'catalog' and int(offer['item_id']) == int(product.id):
                    if offer['type'] == 'combo' and int(offer['free_item_id']) not in free_item_ids:
                        CartProductMapping.objects.filter(cart=cart,
                                                          retailer_product_id=offer['free_item_id'],
                                                          parent_retailer_product_id=offer['item_id']).delete()
                    continue
                cart_offers_new.append(offer)
        cart_offers_new += applied_offers
        return cart_offers_new

    @classmethod
    def refresh_basic_cart_offers(cls, cart, cart_value, offers_list, auto_apply=False, coupon_id=''):
        """
            Refresh cart level discount
        """
        # Get coupons available on cart from es
        c_list = BasicCartOffers.get_basic_cart_coupons(cart.seller_shop.id)
        # Check already applied coupon, Auto apply if required
        offers_list = BasicCartOffers.basic_cart_offers(c_list, cart_value, cart, offers_list, auto_apply, coupon_id)
        return offers_list

    @classmethod
    def get_basic_cart_coupons(cls, shop_id):
        """
            Get coupons available on carts of shop
        """
        date = datetime.now()
        body = {
            "from": 0,
            "size": 50,
            "query": {"bool": {"filter": [{"term": {"active": True}},
                                          {"term": {"coupon_type": 'cart'}},
                                          {"range": {"start_date": {"lte": date}}},
                                          {"range": {"end_date": {"gte": date}}}]
                               }
                      }
        }
        c_list = []
        try:
            coupons_list = es.search(index=create_es_index("rc-{}".format(shop_id)), body=body)
            for c in coupons_list['hits']['hits']:
                c_list.append(c["_source"])
        except:
            pass
        return c_list

    @classmethod
    def basic_cart_offers(cls, c_list, cart_value, cart, offers_list, auto_apply=False, coupon_id=''):
        """
            Check if cart applicable offers can be applied
            Remove already applied offer if not valid
            Auto apply max discount offer if required
        """
        # Intended coupon is applied or not
        applied = False
        # To Remove any offer from cart if no coupons available
        if not c_list:
            offers_list = BasicCartOffers.update_cart_offer(offers_list, cart_value)
            return {'offers_list': offers_list, 'total_offers': []}
        # All available and applicable coupons on cart
        applicable_offers = []
        # All available and currently not applicable coupons on cart
        other_offers = []
        # Check if any coupon is already applied on cart
        cart_offers = cart.offers
        applied_offer = {}
        if cart_offers:
            for offer in cart_offers:
                if offer['coupon_type'] == 'cart':
                    applied_offer = offer
        # Final coupon - 1. Either no auto_apply and refresh coupon already applied OR 2. Auto apply max discount coupon
        final_offer_coupon_id = {}
        final_offer_applied = {}
        final_offer = {}
        # Check all available coupons for cart minimum value
        for coupon in c_list:
            offer = BasicCartOffers.get_offer_cart_coupon(coupon)
            # When cart qualifies for coupon
            if cart_value >= coupon['cart_minimum_value']:
                if not coupon['is_percentage']:
                    discount = coupon['discount']
                else:
                    if coupon['max_discount'] == 0 or coupon['max_discount'] > (coupon['discount'] / 100) * cart_value:
                        discount = round((coupon['discount'] / 100) * cart_value, 2)
                    else:
                        discount = coupon['max_discount']
                offer['discount_value'] = discount
                offer['applicable'] = 1
                if coupon_id == coupon['id']:
                    applied = True
                    final_offer_coupon_id = offer
                    continue
                # If already applied coupon_id is still applicable, refresh the discount amount/offer
                if applied_offer and applied_offer['coupon_id'] == coupon['id'] and not auto_apply:
                    final_offer_applied = offer
                    continue
                applicable_offers.append(offer)
            else:
                offer['applicable'] = 0
                offer['extra_amount'] = int(coupon['cart_minimum_value']) - int(cart_value)
                other_offers.append(offer)

        # Set Final coupon to be applied
        if coupon_id:
            if final_offer_coupon_id:
                applied = True
                final_offer_coupon_id['applied'] = 1
                applicable_offers.append(final_offer_coupon_id)
                final_offer = final_offer_coupon_id
            if final_offer_applied:
                applicable_offers.append(final_offer_applied)
        elif final_offer_applied:
            final_offer_applied['applied'] = 1
            applicable_offers.append(final_offer_applied)
            applied = True
            final_offer = final_offer_applied

        if applicable_offers:
            applicable_offers = sorted(applicable_offers, key=itemgetter('discount_value'), reverse=True)
            # Apply highest discount coupon if auto apply
            if auto_apply and not applied:
                applicable_offers[0]['applied'] = 1
                final_offer = applicable_offers[0]
                applied = True
        if other_offers:
            other_offers = sorted(other_offers, key=itemgetter('cart_minimum_value'), reverse=True)
        # Either highest discount available offer is auto applied OR existing offer if applicable is updated
        if final_offer:
            offers_list = BasicCartOffers.update_cart_offer(offers_list, cart_value, final_offer)
        else:
            # Cart does not qualify for any offer
            offers_list = BasicCartOffers.update_cart_offer(offers_list, cart_value)
        return {'offers_list': offers_list, 'total_offers': applicable_offers + other_offers, 'applied':applied}

    @classmethod
    def get_offer_cart_coupon(cls, coupon):
        """
            Cart available offer
        """
        return {
                'coupon_type': 'cart',
                'type': 'discount',
                'coupon_id': coupon['id'],
                'coupon_code': coupon['coupon_code'],
                'cart_minimum_value': coupon['cart_minimum_value'],
                'is_percentage': coupon['is_percentage'],
                'discount': coupon['discount'],
                'max_discount': coupon['max_discount']
            }

    @classmethod
    def update_cart_offer(cls, offers_list, cart_value, new_offer=None):
        """
            Return updated list of offers for cart discount after adding new offer
        """
        new_offers = []
        if offers_list:
            for offer in offers_list:
                if offer['coupon_type'] == 'cart':
                    continue
                if offer['coupon_type'] == 'catalog':
                    discounted_price_subtotal = round(
                        ((offer['product_subtotal'] / float(cart_value)) * float(new_offer['discount_value'])),
                        2) if new_offer else 0
                    offer.update({'cart_or_brand_level_discount': discounted_price_subtotal})
                    discounted_product_subtotal = round(
                        offer['product_subtotal'] - discounted_price_subtotal, 2)
                    offer.update({'discounted_product_subtotal': discounted_product_subtotal})
                new_offers.append(offer)
        if new_offer:
            new_offers.append(new_offer)
        return new_offers

    @classmethod
    def basic_cart_offers_check(cls, cart, offers_list):
        """
            Check Cart amount for applied discounts on updating quantity for any product
        """
        new_offers_list = []
        cart_total = 0
        cart_offer = None
        if offers_list:
            cart_products = cart.rt_cart_list.all()
            for product in cart_products:
                cart_total += product.selling_price * product.qty
            for offer in offers_list:
                if offer['coupon_type'] == 'cart':
                    if offer['cart_minimum_value'] > cart_total:
                        continue
                    cart_offer = offer
                new_offers_list.append(offer)
        new_offers_list = BasicCartOffers.update_cart_offer(new_offers_list, cart_total, cart_offer)
        return new_offers_list


def create_es_index(index):
    """
        Return elastic search index specific to environment
    """
    return "{}-{}".format(es_prefix, index)
