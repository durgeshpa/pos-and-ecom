from operator import itemgetter
from datetime import datetime
from elasticsearch import Elasticsearch

from retailer_to_sp.models import CartProductMapping, Cart
from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix

es = Elasticsearch(["https://search-gramsearch-7ks3w6z6mf2uc32p3qc4ihrpwu.ap-south-1.es.amazonaws.com"])


class BasicCartOffers(object):

    @classmethod
    def refresh_offers(cls, cart, auto_apply=False):
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
                                                                    offers_list, auto_apply)
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
        products_id = []
        for product_map in cart_products:
            products_id += [product_map.retailer_product.id]
        # Get combo coupons applicable for all products from es
        combo_offers = BasicCartOffers.get_basic_combo_coupons(products_id, cart.seller_shop.id, len(products_id))
        # Offers corresponding to product
        offers_mapping = {}
        for offer in combo_offers:
            offers_mapping[offer['purchased_product']] = offer
        offers_list = cart.offers
        for product_map in cart_products:
            if product_map.selling_price > 0:
                c_list = [offers_mapping[
                              product_map.retailer_product.id]] if product_map.retailer_product.id in offers_mapping else []
                # Add/remove/update combo on a product
                offers_list = BasicCartOffers.basic_combo_offers(product_map.qty, c_list, Cart.objects.get(pk=cart.id),
                                                                 product_map.retailer_product, offers_list)
        return offers_list

    @classmethod
    def refresh_basic_cart_offers(cls, cart, cart_value, offers_list, auto_apply=False):
        """
            Refresh cart level discount
        """
        # Get coupons available on cart from es
        c_list = BasicCartOffers.get_basic_cart_coupons(cart.seller_shop.id)
        # Check already applied coupon, Auto apply if required
        offers_list = BasicCartOffers.basic_cart_offers(c_list, cart_value, cart, offers_list, auto_apply)
        return offers_list

    @classmethod
    def checkout_apply_offer(cls, cart, coupon_id):
        """
            Apply discount coupon on checkout
        """
        cart_products = cart.rt_cart_list.all()
        cart_value = 0
        if cart_products:
            for product_mapping in cart_products:
                cart_value += product_mapping.selling_price * product_mapping.qty
            # Get coupons available on cart from es
            c_list = BasicCartOffers.get_basic_cart_coupons(cart.seller_shop.id)
            # Check and apply coupon
            offers = BasicCartOffers.apply_cart_offer(c_list, cart, coupon_id, cart_value)
            Cart.objects.filter(pk=cart.id).update(offers=offers['offers'])
            return offers
        else:
            return {'error': 'No Products In Cart Yet!'}

    @classmethod
    def basic_combo_offers(cls, qty, c_list, cart, product, offers_list):
        """
            Combo Offers on a product in basic cart
        """
        # Remove combo from cart if present and any offer is not found on product
        if not c_list:
            offers_list = BasicCartOffers.remove_combo(cart, product, offers_list)
            return offers_list

        for coupon in c_list:
            offer = {
                'coupon_type': 'catalog',
                'type': 'combo',
                'coupon_id': coupon['id'],
                'coupon_code': coupon['coupon_code'],
                'item_id': coupon['purchased_product'],
                'free_item_id': coupon['free_product'],
                'item_qty': coupon['purchased_product_qty'],
                'free_item_qty': coupon['free_product_qty']
            }
            # Quantity in cart should be greater than purchased product quantity given for combo
            if int(qty) >= int(coupon['purchased_product_qty']):
                # Units of purchased product quantity
                purchased_product_multiple = int(int(qty) / int(coupon['purchased_product_qty']))
                # No of free items to be given on total product added in cart
                free_item_qty = int(purchased_product_multiple * int(coupon['free_product_qty']))
                # Add Free product as Cart Item
                cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart,
                                                                           retailer_product_id=coupon['free_product'])
                cart_mapping.selling_price = 0
                cart_mapping.qty = free_item_qty
                cart_mapping.no_of_pieces = free_item_qty
                cart_mapping.save()
                # To Update offer in cart
                offer['applied'] = True
                combo_text = 'Combo Offer Applied'
                offer['combo_text'] = combo_text
                offers_list = BasicCartOffers.update_combo(cart, product, offer, offers_list)
                return offers_list
            # If Quantity of purchased product does not qualify for combo, notify user to add more quantity
            # Also To Remove applied combo
            else:
                combo_text = "Add " + str(int(coupon['purchased_product_qty']) - int(qty)) + " more to get " \
                             + str(coupon['free_product_qty']) + " " + str(coupon['free_product_name']) + " Free"
                offer['applied'] = False
                offer['combo_text'] = combo_text
                CartProductMapping.objects.filter(cart=cart, retailer_product_id=offer['free_item_id'],
                                                  selling_price=0).delete()
                offers_list = BasicCartOffers.update_combo(cart, product, offer, offers_list)
                return offers_list

    @classmethod
    def basic_cart_offers(cls, c_list, cart_value, cart, offers_list, auto_apply=False):
        """
            Check if cart applicable offers can be applied
            Remove already applied offer if not valid
            Auto apply max discount offer if required
        """
        # To Remove any offer from cart if no coupons available
        if not c_list:
            offers_list = BasicCartOffers.remove_cart_offer(offers_list)
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
        final_offer = {}
        # Check all available coupons for cart minimum value
        for coupon in c_list:
            offer = {
                'coupon_type': 'cart',
                'type': 'discount',
                'coupon_id': coupon['id'],
                'coupon_code': coupon['coupon_code'],
                'cart_minimum_value': coupon['cart_minimum_value'],
                'is_percentage': coupon['is_percentage'],
                'discount': coupon['discount']
            }
            # When cart qualifies for couupon
            if cart_value >= coupon['cart_minimum_value']:
                # If already applied coupon_id is still applicable, refresh the discount amount/offer
                if applied_offer and applied_offer['coupon_id'] == coupon['id'] and not auto_apply:
                    final_offer = offer
                    offer['applied'] = 1
                offer['applicable'] = 1
                applicable_offers.append(offer)
            else:
                offer['applicable'] = 0
                offer['extra_amount'] = int(coupon['cart_minimum_value']) - int(cart_value)
                other_offers.append(offer)
        if applicable_offers:
            applicable_offers = sorted(applicable_offers, key=itemgetter('discount_value_cart'), reverse=True)
            # Apply highest discount coupon if auto apply
            if auto_apply:
                final_offer = applicable_offers[0]
                applicable_offers[0]['applied'] = 1
        if other_offers:
            other_offers = sorted(other_offers, key=itemgetter('cart_minimum_value'), reverse=True)
        # Either highest discount available offer is auto applied OR existing offer if applicable is updated
        if final_offer:
            offers_list = BasicCartOffers.update_cart_offer(final_offer, offers_list)
        else:
            # Cart does not qualify for any offer
            offers_list = BasicCartOffers.remove_cart_offer(offers_list)
        return {'offers_list': offers_list, 'total_offers': applicable_offers + other_offers}

    @classmethod
    def apply_cart_offer(cls, c_list, cart, coupon_id, cart_value):
        """
            Apply coupon on cart checkout
        """
        applied = False
        offers = cart.offers
        # To remove if any coupon not available
        if not c_list:
            offers = BasicCartOffers.remove_cart_offer(cart.offers)
            return {'applied': False, 'offers': offers}
        for coupon in c_list:
            # Validate coupon to be applied
            if int(coupon['id']) == int(coupon_id) and int(cart_value) >= int(coupon['cart_minimum_value']):
                offer = {
                    'coupon_type': 'cart',
                    'type': 'discount',
                    'coupon_id': coupon['id'],
                    'coupon_code': coupon['coupon_code'],
                    'cart_minimum_value': coupon['cart_minimum_value'],
                    'is_percentage': coupon['is_percentage'],
                    'discount': coupon['discount']
                }
                offers = BasicCartOffers.update_cart_offer(offer, cart.offers)
                applied = True
        return {'applied': applied, 'offers': offers}

    @classmethod
    def update_cart_offer(cls, new_offer, offers_list):
        """
            Return updated list of offers for cart discount after adding new offer
        """
        new_offers = []
        if offers_list:
            for offer in offers_list:
                if offer['coupon_type'] == 'cart':
                    continue
                new_offers.append(offer)
        new_offers.append(new_offer)
        return new_offers

    @classmethod
    def remove_cart_offer(cls, offers_list):
        """
            Return updated list of cart offers after removing cart offer
        """
        new_offers = []
        if offers_list:
            for offer in offers_list:
                if offer['coupon_type'] == 'cart':
                    continue
                new_offers.append(offer)
        return new_offers

    @classmethod
    def get_basic_combo_coupons(cls, purchased_product_ids, shop_id, size=1):
        """
            Get Product combo coupons from elasticsearch
        """
        date = datetime.now()
        body = {
            "from": 0,
            "size": size,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "term": {
                                "active": True
                            }
                        },
                        {
                            "term": {
                                "coupon_type": 'catalogue_combo'
                            }
                        },
                        {
                            "terms": {
                                "purchased_product": purchased_product_ids
                            }
                        },
                        {
                            "range": {
                                "start_date": {
                                    "lte": date
                                }
                            }
                        },
                        {
                            "range": {
                                "end_date": {
                                    "gte": date
                                }
                            }
                        },
                    ]
                }
            }
        }
        coupons_list = es.search(index=create_es_index("rc-{}".format(shop_id)), body=body)
        c_list = []
        for c in coupons_list['hits']['hits']:
            c_list.append(c["_source"])
        return c_list

    @classmethod
    def get_basic_cart_coupons(cls, shop_id):
        """
            Get coupons available on carts of shop
        """
        date = datetime.now()
        body = {
            "from": 0,
            "size": 50,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "term": {
                                "active": True
                            }
                        },
                        {
                            "term": {
                                "coupon_type": 'cart'
                            }
                        },
                        {
                            "range": {
                                "start_date": {
                                    "lte": date
                                }
                            }
                        },
                        {
                            "range": {
                                "end_date": {
                                    "gte": date
                                }
                            }
                        },
                    ]
                }
            },
            "sort": [
                {"cart_minimum_value": "asc"},
            ]
        }
        coupons_list = es.search(index=create_es_index("rc-{}".format(shop_id)), body=body)
        c_list = []
        for c in coupons_list['hits']['hits']:
            c_list.append(c["_source"])
        return c_list

    @classmethod
    def update_combo(cls, cart, product, new_offer, offers_list):
        """
            Return updated list of offers after adding combo offer on product
        """
        cart_offers_new = []
        if offers_list:
            for offer in offers_list:
                if offer['type'] == 'combo' and int(offer['item_id']) == int(product.id):
                    if int(offer['free_item_id']) != new_offer['free_item_id']:
                        CartProductMapping.objects.filter(cart=cart, retailer_product_id=offer['free_item_id'],
                                                          selling_price=0).delete()
                    continue
                cart_offers_new.append(offer)
        cart_offers_new.append(new_offer)
        return cart_offers_new

    @classmethod
    def remove_combo(cls, cart, product, offers_list):
        """
            Return updated list of offers after removing combo offer on product
        """
        cart_offers_new = []
        if offers_list:
            for offer in offers_list:
                if offer['type'] == 'combo' and int(offer['item_id']) == int(product.id):
                    CartProductMapping.objects.filter(cart=cart, retailer_product_id=offer['free_item_id'],
                                                      selling_price=0).delete()
                    continue
                cart_offers_new.append(offer)
        return cart_offers_new

    @classmethod
    def basic_cart_offers_check(cls, cart, offers_list):
        """
            Check Cart amount for applied discounts on updating quantity for any product
        """
        new_offers_list = []
        if offers_list:
            cart_total = 0
            cart_products = cart.rt_cart_list.all()
            for product in cart_products:
                cart_total += product.selling_price
            for offer in offers_list:
                if offer['coupon_type'] == 'cart' and offer['cart_minimum_value'] > cart_total:
                    continue
                new_offers_list.append(offer)
        return new_offers_list


def create_es_index(index):
    return "{}-{}".format(es_prefix, index)
