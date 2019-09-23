from django.db.models import Q

from celery.task import task
from celery.contrib import rdb

from .models import ProductPrice


@task
def approve_product_price(product_price_id):
    price_data = ProductPrice.objects.values(
        'product_id', 'seller_shop_id', 'buyer_shop_id', 'city_id',
        'pincode_id').get(id=product_price_id)
    product_prices = ProductPrice.objects.filter(
        ~Q(id=product_price_id),
        product=price_data.get('product_id'),
        seller_shop=price_data.get('seller_shop_id'),
        buyer_shop=price_data.get('buyer_shop_id'),
        city=price_data.get('city_id'),
        pincode=price_data.get('pincode_id'),
        approval_status=ProductPrice.APPROVED
    )
    product_prices.update(approval_status=ProductPrice.DEACTIVATED)
