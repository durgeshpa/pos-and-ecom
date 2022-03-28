from products.models import ParentProduct, ParentProductB2cCategory, ParentProductCategory
from categories.models import B2cCategory, Category

def run():
    products = ParentProduct.objects.filter(status=True)
    for product in products:
        if not product.parent_product_pro_category.exists() or \
            not product.parent_product_pro_b2c_category.exists():
                categories = product.parent_product_pro_category.all()
                b2c_categories = product.parent_product_pro_b2c_category.all()
                if product.parent_product_pro_category.exists():
                    for cat in categories:
                        if B2cCategory.objects.filter(category_name=cat.category.category_name).exists():
                            b2c_ct = B2cCategory.objects.get(category_name=cat.category.category_name)
                            ParentProductB2cCategory.objects.create(
                                parent_product = product,
                                category = b2c_ct,
                                status = cat.status
                            )
                        else:
                            print(cat.category.category_name, cat.category.id)
                elif product.parent_product_pro_b2c_category.exists():
                    for b2c_cat in b2c_categories:
                        ct = Category.objects.get(category_name=b2c_cat.category.category_name)
                        ParentProductCategory.objects.create(
                            parent_product = product,
                            category = ct,
                            status = b2c_cat.status
                        )