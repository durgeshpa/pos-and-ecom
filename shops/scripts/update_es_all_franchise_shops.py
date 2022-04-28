from shops.models import Shop
from pos.models import RetailerProduct
from pos.tasks import update_es
import logging
import traceback


info_logger = logging.getLogger('elastic_log')

def run():
    """
        Refresh retailer Products Es for all Franchise shops
    """
    refreshEsRetailerAllFranchiseShops()

def refreshEsRetailerAllFranchiseShops():
    try:
        info_logger.info("-------------Refresh ES started for all Franchise stores--------------")
        shops = Shop.objects.filter(shop_type__shop_type='f', status=True, approval_status=2, pos_enabled=True)
        info_logger.info("Shops Total :: {}", shops.count())
        print("Shops :: ", shops)
        for shop in shops:
            info_logger.info("ES refersh started for Shop :: {}, id :: {}".format(shop.shop_name, shop.id))
            print("ES refersh started for Shop :: {}, id :: {}".format(shop.shop_name, shop.id))
            shop_id = shop.id
            all_products = RetailerProduct.objects.filter(shop=shop)
            print("Number of products ::", all_products.count())
            info_logger.info("Number of products :: {}".format(all_products.count()))
            update_es(all_products, shop_id)
            print("ES updated for shop :: {}, id :: {}".format(shop.shop_name, shop.id))
            info_logger.info("ES updated for shop :: {}, id :: {}".format(shop.shop_name, shop.id))
        info_logger.info("All franchise shops updated!!")
    except Exception as e:
        traceback.print_exc()