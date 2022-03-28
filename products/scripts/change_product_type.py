from products.models import ParentProduct

def run():
    products = ParentProduct.objects.filter(status=True)
    print(products.count, " :: Products set to both category", products)
    products.update(product_type='both')