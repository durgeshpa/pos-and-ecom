from operator import itemgetter
from datetime import datetime
from elasticsearch import Elasticsearch

from retailer_to_sp.models import Cart
from pos.models import RetailerProduct
from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix

es = Elasticsearch(["https://search-gramsearch-7ks3w6z6mf2uc32p3qc4ihrpwu.ap-south-1.es.amazonaws.com"])


class BasicCartOffers(object):

    @classmethod
    def refresh_offers_cart(cls, cart):
        """
            Refresh Combo On all products
            Get nearest cart offer
        """
        cart_products = cart.rt_cart_list.all()
        cart_value = 0
        offer = ''
        if cart_products:
            # Add/Remove/Update combo offers on all products
            offers_list = BasicCartOffers.refresh_combo(cart, cart_products)
            Cart.objects.filter(pk=cart.id).update(offers=offers_list)
            # Get nearest cart offer over cart value
            offer = BasicCartOffers.get_cart_nearest_offer(cart, cart_products)
        return offer

    @classmethod
    def refresh_offers_checkout(cls, cart, auto_apply=False, coupon_id=None):
        """
            Refresh All Cart Offers
            Combo On all products
            Cart level offers
        """
        cart_products = cart.rt_cart_list.all()
        cart_value = 0
        offers_list = []
        if cart_products:
            for product_mapping in cart_products:
                cart_value += product_mapping.selling_price * product_mapping.qty
            offers_list = cart.offers
            # Check already applied cart offer
            offers_list = BasicCartOffers.refresh_basic_cart_offers(cart, float(cart_value),
                                                                    offers_list, auto_apply, coupon_id)
            Cart.objects.filter(pk=cart.id).update(offers=offers_list['offers_list'])
        return offers_list

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
                                                               (len(products_id)))
        # Offers corresponding to product
        offers_mapping = {}
        for offer in combo_offers:
            offers_mapping[offer['purchased_product']] = offer

        offers_list = cart.offers
        for product_map in cart_products:
            # Refresh combo for all added products
            if product_map.product_type == 1:
                coupon = offers_mapping[
                    product_map.retailer_product.id] if product_map.retailer_product.id in offers_mapping else {}
                # Add/remove/update combo on a product
                offers_list = BasicCartOffers.basic_combo_offers(int(product_map.qty), float(product_map.selling_price),
                                                                 product_map.retailer_product.id, coupon, offers_list)
        return offers_list

    @classmethod
    def get_cart_nearest_offer(cls, cart, cart_products):
        """
            Get nearest offer applicable over order value
        """
        cart_value = 0
        for product_mapping in cart_products:
            cart_value += product_mapping.selling_price * product_mapping.qty
        offer = ''
        coupons = BasicCartOffers.get_cart_nearest_coupon(cart.seller_shop.id, float(cart_value))
        if coupons:
            offer = 'Shop for ₹' + str(coupons[0]['cart_minimum_value']).rstrip('0').rstrip('.') + ' and get additional '
            if coupons[0]['is_percentage']:
                offer += str(coupons[0]['discount']).rstrip('0').rstrip('.') + '% Off.'
            else:
                offer += '₹' + str(coupons[0]['discount']).rstrip('0').rstrip('.') + ' Off.'
        return offer

    @classmethod
    def get_basic_combo_coupons(cls, purchased_product_ids, shop_id, size=1, source=None):
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
                      }
        }
        if source:
            body["_source"] = {"includes": source}
        c_list = []
        try:
            coupons_list = es.search(index=create_es_index("rc-{}".format(shop_id)), body=body)
            for c in coupons_list['hits']['hits']:
                c_list.append(c["_source"])
        except:
            pass
        return c_list

    @classmethod
    def basic_combo_offers(cls, qty, sp, product_id, coupon, offers_list):
        """
            Combo Offers on a product in basic cart
        """
        offers_list = [] if not offers_list else offers_list
        # Product price total
        product_total = qty * sp
        # Check if coupon is there
        if not coupon:
            offer = BasicCartOffers.get_offer_no_coupon(product_id, product_total)
            return BasicCartOffers.update_combo(product_id, offers_list, offer)
        # Check free product
        free_product = RetailerProduct.objects.filter(id=coupon['free_product']).last()
        if not free_product:
            offer = BasicCartOffers.get_offer_no_coupon(product_id, product_total)
            return BasicCartOffers.update_combo(product_id, offers_list, offer)
        # Check and apply coupon
        # Quantity in cart should be greater than purchased product quantity given for combo
        if int(qty) >= int(coupon['purchased_product_qty']):
            offer = BasicCartOffers.get_offer_combo_coupon(coupon, product_total)
            # Units of purchased product quantity
            purchased_product_multiple = int(int(qty) / int(coupon['purchased_product_qty']))
            # No of free items to be given on qty left
            free_item_qty = int(purchased_product_multiple * int(coupon['free_product_qty']))
            offer['free_item_name'] = free_product.name
            offer['free_item_mrp'] = float(free_product.mrp)
            offer['free_item_qty_added'] = free_item_qty
            offer['display_text'] = str(free_item_qty) + ' ' + free_product.name + ' worth ₹' + str(
                round(float(free_product.mrp) * float(free_item_qty), 2)).rstrip('0').rstrip('.') + ' Free'
        else:
            # Next applicable combo offer on product
            offer = BasicCartOffers.get_offer_next(coupon, product_total, qty)
        # Update offers, remove previous not applicable combos on product
        return BasicCartOffers.update_combo(product_id, offers_list, offer)

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
            'discounted_product_subtotal': product_total
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
            'coupon_description': coupon['coupon_code'],
            'coupon_name': coupon['coupon_name'] if 'coupon_name' in coupon else '',
            'item_id': coupon['purchased_product'],
            'product_subtotal': product_total,
            'discounted_product_subtotal': product_total
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
            'free_item_qty': coupon['free_product_qty']
        })
        return ret

    @classmethod
    def update_combo(cls, product_id, offers_list, new_offer):
        """
            Return updated list of offers after adding/updating combo offer on product
        """
        cart_offers_new = []
        if offers_list:
            for offer in offers_list:
                if offer['coupon_type'] == 'catalog' and int(offer['item_id']) == int(product_id):
                    continue
                cart_offers_new.append(offer)
        if new_offer:
            cart_offers_new.append(new_offer)
        return cart_offers_new

    @classmethod
    def refresh_basic_cart_offers(cls, cart, cart_value, offers_list, auto_apply=False, coupon_id=None):
        """
            Refresh cart level discount
        """
        # Get coupons available on cart from es
        c_list = BasicCartOffers.get_basic_cart_coupons(cart.seller_shop.id, cart_value)
        # Check already applied coupon, Auto apply if required
        offers_list = BasicCartOffers.basic_cart_offers(c_list, cart_value, offers_list, auto_apply, coupon_id)
        return offers_list

    @classmethod
    def get_basic_cart_coupons(cls, shop_id, cart_value):
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
                                          {"range": {"end_date": {"gte": date}}},
                                          {"range": {"cart_minimum_value": {"lte": cart_value}}}]
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
    def get_cart_nearest_coupon(cls, shop_id, cart_value):
        """
            Get nearest coupon available over cart value
        """
        date = datetime.now()
        body = {
            "from": 0,
            "size": 1,
            "query": {"bool": {"filter": [{"term": {"active": True}},
                                          {"term": {"coupon_type": 'cart'}},
                                          {"range": {"start_date": {"lte": date}}},
                                          {"range": {"end_date": {"gte": date}}},
                                          {"range": {"cart_minimum_value": {"gt": cart_value}}}]
                               }
                      },
            "sort": [
                {"cart_minimum_value": "asc"},
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
    def basic_cart_offers(cls, c_list, cart_value, offers_list, auto_apply=False, coupon_id=None):
        """
            Check if cart applicable offers can be applied
            Remove already applied offer if not valid
            Auto apply max discount offer if required
        """
        # Intended coupon is applied or not
        applied = False
        # All available and applicable coupons on cart
        applicable_offers = []
        # All available and currently not applicable coupons on cart
        other_offers = []
        # Check if any coupon is already applied on cart
        applied_offer = {}
        if offers_list:
            for offer in offers_list:
                if offer['coupon_type'] == 'cart' and offer['type'] == 'discount':
                    applied_offer = offer
        # Final coupon - 1. Either no auto_apply and refresh coupon already applied OR 2. Auto apply max discount coupon
        final_offer_coupon_id = {}
        final_offer_applied = {}
        final_offer = {}
        spot_discount_offer = {}
        # Check all available coupons for cart minimum value
        for coupon in c_list:
            offer = BasicCartOffers.get_offer_cart_coupon(coupon)
            # When cart qualifies for coupon
            if cart_value >= coupon['cart_minimum_value']:
                discount = BasicCartOffers.discount_value(offer, cart_value)
                offer['discount_value'] = discount
                offer['applicable'] = 1
                if coupon_id and int(coupon_id) == int(coupon['id']):
                    applied = True
                    final_offer_coupon_id = offer
                    continue
                # If already applied coupon_id is still applicable, refresh the discount amount/offer
                if applied_offer and 'coupon_id' in applied_offer and int(applied_offer['coupon_id']) == int(
                        coupon['id']) and not auto_apply:
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
            elif final_offer_applied:
                final_offer_applied['applied'] = 1
                applicable_offers.append(final_offer_applied)
                final_offer = final_offer_applied
        elif final_offer_applied:
            final_offer_applied['applied'] = 1
            applicable_offers.append(final_offer_applied)
            applied = True
            final_offer = final_offer_applied
        elif applied_offer and 'sub_type' in applied_offer and applied_offer['sub_type'] == 'spot_discount' \
                and not auto_apply:
            applied = True
            final_offer = applied_offer
            spot_discount_offer = final_offer

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
        return {'offers_list': offers_list, 'total_offers': applicable_offers + other_offers, 'applied': applied,
                'spot_discount': spot_discount_offer}

    @classmethod
    def get_offer_cart_coupon(cls, coupon):
        """
            Cart available offer
        """
        return {
            'coupon_type': 'cart',
            'type': 'discount',
            'sub_type': 'set_discount',
            'coupon_id': coupon['id'],
            'coupon_description': coupon['coupon_code'],
            'coupon_name': coupon['coupon_name'] if 'coupon_name' in coupon else '',
            'cart_minimum_value': coupon['cart_minimum_value'],
            'is_percentage': coupon['is_percentage'],
            'discount': coupon['discount'],
            'max_discount': coupon['max_discount']
        }

    @classmethod
    def get_offer_spot_discount(cls, is_percentage, discount, discount_value):
        """
            Spot discount cart
        """
        return {
            'coupon_type': 'cart',
            'type': 'discount',
            'sub_type': 'spot_discount',
            'is_percentage': is_percentage,
            'discount': discount,
            'discount_value': discount_value,
            'applied': 1
        }

    @classmethod
    def update_cart_offer(cls, offers_list, cart_value, new_offer=None):
        """
            Return updated list of offers for cart discount after adding new offer
        """
        new_offers = []
        if offers_list:
            for offer in offers_list:
                if offer['coupon_type'] == 'cart' and offer['type'] == 'discount':
                    continue
                if offer['coupon_type'] == 'catalog':
                    discounted_price_subtotal = round(
                        ((float(offer['product_subtotal']) / float(cart_value)) * float(new_offer['discount_value'])),
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
    def basic_cart_offers_check(cls, cart, offers_list, shop_id):
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
                if offer['coupon_type'] == 'cart' and offer['type'] == 'free_product':
                    continue
                if offer['coupon_type'] == 'cart' and offer['type'] == 'discount' and offer[
                    'sub_type'] == 'set_discount':
                    if float(offer['cart_minimum_value']) > cart_total:
                        continue
                    cart_offer = offer
                new_offers_list.append(offer)
        new_offers_list = BasicCartOffers.update_cart_offer(new_offers_list, cart_total, cart_offer)
        # check for free product offer on cart
        free_product_coupons = BasicCartOffers.get_basic_cart_product_coupon(shop_id, cart_total)
        if free_product_coupons:
            free_product_coupon = free_product_coupons[0]
            free_product = RetailerProduct.objects.filter(id=free_product_coupon['free_product']).last()
            if free_product:
                new_offers_list.append(BasicCartOffers.get_free_product_cart_coupon(free_product_coupon, free_product))
        return new_offers_list

    @classmethod
    def apply_spot_discount(cls, cart, spot_discount, is_percentage):
        """
            Apply spot discount on cart
            Remove other offers
        """
        cart_products = cart.rt_cart_list.all()
        if cart_products:
            cart_value = 0
            if cart_products:
                for product_mapping in cart_products:
                    cart_value += product_mapping.selling_price * product_mapping.qty
            discount_value = round((float(spot_discount) / 100) * float(cart_value), 2) if is_percentage else float(
                spot_discount)
            if discount_value <= cart_value:
                offer = BasicCartOffers.get_offer_spot_discount(is_percentage, spot_discount, discount_value)
                offers = BasicCartOffers.update_cart_offer(cart.offers, cart_value, offer)
                Cart.objects.filter(pk=cart.id).update(offers=offers)
                return {'applied': True, 'offers_list': offers}
            else:
                return {'error': 'Please Provide Spot Discount Less Than Cart Value', 'code': 406}
        else:
            return {'error': 'No Products In Cart Yet!', 'code': 200}

    @classmethod
    def apply_spot_discount_returns(cls, spot_discount, is_percentage, current_amount, order_return,
                                    refund_amount_raw):
        """
            Check and apply provided spot discount on returns cart
        """
        discount_value = round((spot_discount / 100) * float(current_amount), 2) if is_percentage else spot_discount
        if float(current_amount) >= float(discount_value):
            offer = BasicCartOffers.get_offer_spot_discount(is_percentage, spot_discount, discount_value)
            order_return.refund_amount = float(refund_amount_raw) + float(spot_discount)
            order_return.offers = [offer]
            order_return.save()
            return {'applied': True}
        else:
            return {'error': "Please provide spot discount less than current amount", 'code': 406}

    @classmethod
    def refresh_returns_offers(cls, order, current_amount, order_return, refund_amount_raw, coupon_id=None):
        """
            Get applied and applicable offers on new cart value after returns
        """
        # Get coupons available on cart from es
        c_list = BasicCartOffers.get_basic_cart_coupons(order.seller_shop.id)
        # Check already applied coupon, Auto apply if required
        offers_list = BasicCartOffers.basic_cart_offers(c_list, current_amount, order_return.offers, False,
                                                        coupon_id)
        offers = offers_list['offers_list']
        if offers:
            for offer in offers:
                refund_amount = refund_amount_raw + offer['discount_value']
                order_return.offers = [offer]
                order_return.refund_amount = refund_amount
                order_return.save()
                break
        return offers_list

    @classmethod
    def discount_value(cls, offer, cart_value):
        if not offer['is_percentage']:
            discount = float(offer['discount'])
        else:
            if float(offer['max_discount']) == 0 or float(offer['max_discount']) > (
                    float(offer['discount']) / 100) * float(cart_value):
                discount = round((float(offer['discount']) / 100) * float(cart_value), 2)
            else:
                discount = float(offer['max_discount'])
        return discount

    @classmethod
    def get_basic_cart_product_coupon(cls, shop_id, cart_value):
        """
            Get Cart Free Product coupon from elasticsearch
        """
        date = datetime.now()
        body = {
            "from": 0,
            "size": 1,
            "query": {"bool": {"filter": [{"term": {"active": True}},
                                          {"term": {"coupon_type": 'cart_free_product'}},
                                          {"range": {"start_date": {"lte": date}}},
                                          {"range": {"end_date": {"gte": date}}},
                                          {"range": {"cart_minimum_value": {"lte": cart_value}}}]
                               }
                      },
            "sort": [
                {"cart_minimum_value": "desc"},
            ]
        }
        c_list = []
        try:
            coupons_list = es.search(index=create_es_index("rc-{}".format(shop_id)), body=body)
            for c in coupons_list['hits']['hits']:
                c_list.append(c["_source"])
        except Exception as e:
            pass
        return c_list

    @classmethod
    def get_free_product_cart_coupon(cls, coupon, free_product):
        """
            Cart available offer free product
        """
        return {
            'coupon_type': 'cart',
            'type': 'free_product',
            'sub_type': '',
            'coupon_id': coupon['id'],
            'coupon_description': coupon['coupon_code'],
            'coupon_name': coupon['coupon_name'] if 'coupon_name' in coupon else '',
            'cart_minimum_value': coupon['cart_minimum_value'],
            'free_item_id': coupon['free_product'],
            'free_item_qty': coupon['free_product_qty'],
            'free_item_name': free_product.name,
            'free_item_mrp': float(free_product.mrp)
        }


def create_es_index(index):
    """
        Return elastic search index specific to environment
    """
    return "{}-{}".format(es_prefix, index)
