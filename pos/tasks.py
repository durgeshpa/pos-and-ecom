from celery.task import task
from elasticsearch import Elasticsearch

from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix
from pos.models import RetailerProduct

es = Elasticsearch(["https://search-gramsearch-7ks3w6z6mf2uc32p3qc4ihrpwu.ap-south-1.es.amazonaws.com"])


def create_es_index(index):
    return "{}-{}".format(es_prefix, index)


@task
def update_shop_retailer_product_es(shop_id, product_id, **kwargs):
    try:
        if shop_id:
            if product_id and RetailerProduct.objects.filter(id=product_id).exists():
                products = RetailerProduct.objects.filter(id=product_id)
            else:
                products = RetailerProduct.objects.filter(id=product_id, shop_id=shop_id)
            for product in products:
                margin = ((product.mrp - product.selling_price) / product.mrp) * 100
                product_img = product.retailer_product_image.all()
                product_images = [
                    {
                        "image_name": p_i.image_name,
                        "image_alt": p_i.image_alt_text,
                        "image_url": p_i.image.url
                    }
                    for p_i in product_img
                ]
                params = {
                    'id' : product.id,
                    'name' : product.name,
                    'mrp' : product.mrp,
                    'selling_price' : product.selling_price,
                    'margin' : margin,
                    'images' : product_images
                }
                es.index(index=create_es_index('rp-{}'.format(shop_id)), id=params['id'], body=params)
    except Exception as e:
        pass