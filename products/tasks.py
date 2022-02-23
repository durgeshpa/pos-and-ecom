from django.db.models import Q

from celery.task import task
from celery.contrib import rdb

from .models import ProductPrice, ParentProduct, Product, ProductB2cCategory, ProductCategory, ParentProductB2cCategory


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


@task
def load_b2c_parent_category_data(cat_map=None):
    if not cat_map:
        return 0
    b2c_products = ParentProduct.objects.filter(product_type__in=['b2c', 'both'])
    for product in b2c_products:
        p_categories = product.parent_product_pro_category.all()
        for p_category in p_categories:
            cat_id = p_category.category.id
            parent_id = p_category.category.category_parent.id if p_category.category.category_parent else None
            ParentProductB2cCategory.objects.create(parent_product=product, 
                                                    category=cat_map.get((cat_id, parent_id)))
        