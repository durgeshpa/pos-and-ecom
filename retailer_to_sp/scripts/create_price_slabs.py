
from products.models import ProductPrice, PriceSlab

products_with_case_size = []

def run():
    product_prices = ProductPrice.objects.filter(price_slabs__isnull=True, product__parent_product__inner_case_size=1)
    print("Total Prices - {}".format(product_prices.count()))
    counter = 0
    for price in product_prices:
        if price.selling_price and price.price_slabs.all().count() == 0:
            PriceSlab.objects.create(product_price=price, start_value=1, end_value=0, selling_price=price.selling_price)
            counter=counter+1
    print("Total Slabs Created - {}".format(counter))