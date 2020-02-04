from elasticsearch_dsl.connections import connections
# Create a connection to ElasticSearch
connections.create_connection()

from django_elasticsearch_dsl import DocType, Index
from products.models import Product

product = Index('Products')

# reference elasticsearch doc for default settings here
product.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@product.doc_type
class ProductDocument(DocType):

    class Meta:
        model = Product
        fields = ['product_name', 'product_sku', 'product_brand']
