from products.models import PriceSlab, ProductPrice
from shops.models import Shop

old_warehouse = Shop.objects.filter(id=600).last()
new_warehouse = Shop.objects.filter(id=50484).last()


def run():
    print('create_produsct_price_and_slab_for_existing_data | STARTED')

    product_price_instances = ProductPrice.objects.filter(seller_shop=old_warehouse).\
        values('id', 'product_id', 'mrp', 'selling_price', 'buyer_shop_id', 'city_id', 'pincode_id',
               'price_to_retailer', 'start_date', 'end_date', 'approval_status', 'status')
    total_price = product_price_instances.count()
    for cnt, product_price in enumerate(product_price_instances):
        ins_id = product_price.pop('id')
        buyer_shop_id = product_price.pop('buyer_shop_id')
        product_id = product_price.pop('product_id')
        print(f"ProductPrice id {ins_id}, seller_shop {new_warehouse}, buyer_shop_id {buyer_shop_id},"
              f" product_id {product_id}, object {product_price}")
        new_product_price, created = ProductPrice.objects.update_or_create(
            seller_shop=new_warehouse, buyer_shop_id=buyer_shop_id, product_id=product_id, defaults=product_price)
        print(f"ProductPrice created: {created} entry {new_product_price.pk} --> {new_product_price}")

        if created:
            price_slab_instances = PriceSlab.objects.filter(product_price_id=ins_id).\
                values('product_price', 'start_value', 'end_value', 'selling_price', 'offer_price',
                       'offer_price_start_date', 'offer_price_end_date')
            for price_slab in price_slab_instances:
                price_slab['product_price'] = new_product_price
                new_price_slab = PriceSlab.objects.create(**price_slab)
                print(f"PriceSlab entry {new_price_slab.pk} --> {new_price_slab}")

        print(f"{cnt + 1}/{total_price} | ProductPrice Completed.")

