import logging
from products.common_function import get_b2c_product_details
from products.models import Product
from retailer_backend.settings import es
from sp_to_gram.tasks import create_es_index

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')


def run():
    es_index = 'all_b2c_product'
    products = Product.objects.filter(status='active', product_mrp__isnull=False)
    print("Total Products - {}".format(products.count()))
    count = 0
    for product in products:
        count +=1
        product = get_b2c_product_details(product)
        info_logger.info(product)
        try:
            es.index(index=create_es_index(es_index), doc_type='product', id=product['id'], body=product)
            info_logger.info(
                "Inside update_product_b2c_elasticsearch, product id: " + str(product['id']) + ", product: " + str(
                    product))
            print("Product - {}".format(product['id']))
            print(count)
        except Exception as e:
            info_logger.info("error in upload_shop_stock index creation")
            info_logger.info(e)
