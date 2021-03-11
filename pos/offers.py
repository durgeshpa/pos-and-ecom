from elasticsearch import Elasticsearch

from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix
es = Elasticsearch(["https://search-gramsearch-7ks3w6z6mf2uc32p3qc4ihrpwu.ap-south-1.es.amazonaws.com"])

class BasicCartOffers(object):

    @classmethod
    def get_basic_product_offers(cls, purchased_product, qty, price, c_list):
        """
            Offers on a product in basic cart
            Currently combo only
        """
        offers = []
        for coupon in c_list:
            # Quantity in cart should be greater than purchased product quantity given for combo
            if qty > coupon['purchased_product_qty']:
                # Units of purchased product quantity
                purchased_product_multiple = int(qty / coupon['purchased_product_qty'])
                # No of free items to be given on total product added in cart
                free_item_qty = purchased_product_multiple * coupon['free_product_qty']
                offers.append({
                    'coupon_type': 'catalog',
                    'type': 'combo',
                    'coupon_id': coupon['id'],
                    'coupon_code': coupon['coupon_code'],
                    'discount': 0,
                    'item': purchased_product.name,
                    'item_id': purchased_product.id,
                    'free_item_id': coupon['free_product'],
                    'free_item_name': coupon['free_product_name'],
                    'free_item_quantity': free_item_qty,
                    'discounted_product_subtotal': price * qty
                })
        return offers

    @classmethod
    def get_basic_cart_offers(cls, c_list, cart_value):
        offers = []
        for coupon in c_list:
            if cart_value >= coupon['cart_minimum_value']:
                if not coupon['is_percentage']:
                    discount_value_cart = coupon['discount']
                else:
                    if coupon['max_discount'] == 0 or coupon['max_discount'] > (coupon['discount'] / 100) * cart_value:
                        discount_value_cart = round((coupon['discount'] / 100) * cart_value, 2)
                    else:
                        discount_value_cart = coupon['max_discount']
                offers.append({
                    'coupon_type': 'cart',
                    'type': 'discount',
                    'coupon_id': coupon['id'],
                    'coupon_code': coupon['coupon_code'],
                    'discount': discount_value_cart
                })
        return offers

    @classmethod
    def get_basic_combo_coupons(cls, purchased_product_id, shop_id, date):
        """
            Get Product combo coupons from elasticsearch
        """
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
                                "coupon_type" : 'catalogue_combo'
                            }
                        },
                        {
                            "term": {
                                "purchased_product": purchased_product_id
                            }
                        },
                        {
                            "range": {
                                "lte": {
                                    "start_date": date
                                }
                            }
                        },
                        {
                            "range": {
                                "gte": {
                                    "end_date": date
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
    def get_basic_cart_coupons(cls, shop_id, date):
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
                                "lte": {
                                    "start_date": date
                                }
                            }
                        },
                        {
                            "range": {
                                "gte": {
                                    "end_date": date
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

def create_es_index(index):
	return "{}-{}".format(es_prefix, index)