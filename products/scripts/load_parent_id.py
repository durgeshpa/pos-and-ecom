from django.db.models import Q
from products.models import ParentProduct, ParentProductB2cCategory, ParentProductCategory
from categories.models import B2cCategory, Category

def run():
    null_parent_id_products = ParentProduct.objects.filter(parent_id='')
    print(null_parent_id_products.values_list('id', flat=True))
    for product in null_parent_id_products:
        print(product.name)
        if product.product_type == 'b2c':
            cats = product.parent_product_pro_category.all()
            print(cats)
            if cats:
                categories = cats.values_list('category_id', flat=True)
                cat_map = {}
                parent_categories = Category.objects.filter(id__in=categories).values_list('category_parent_id', flat=True)
                
                categories = Category.objects.filter(Q(id__in=categories))
                for category in categories:
                    print(category.category_name)
                    try:
                        b2c_parent_cat = B2cCategory.objects.get(category_name=category.category_name)
                        ParentProductB2cCategory.objects.create(parent_product=product, 
                                                                category=b2c_parent_cat,
                                                                status=True)
                    except B2cCategory.DoesNotExist:
                        b2c_parent_cat = B2cCategory.objects.create(category_name=category.category_name, 
                                                            category_slug=category.category_slug,
                                                            category_desc=category.category_desc,
                                                            category_parent=None,
                                                            category_sku_part=category.category_sku_part,
                                                            category_image=category.category_image,
                                                            updated_by=category.updated_by,
                                                            status=category.status)
                        ParentProductB2cCategory.objects.create(parent_product=product, 
                                                                category=b2c_parent_cat,
                                                                status=True)
                        cat_map[(category.id, category.category_parent.id if category.category_parent else None)] = b2c_parent_cat
                print(cat_map)
                for key, value in cat_map.items():
                    cat_parent_id = key[-1]
                    if cat_parent_id:
                        category = categories.get(id=cat_parent_id)
                        cat_parent = cat_map.get((cat_parent_id, category.category_parent.id if category.category_parent else None))
                        value.category_parent = cat_parent
                        value.save()
            else:
                cat = product.parent_product_pro_b2c_category.first()
                if cat:
                    cat.save()
        else:
            cat = product.parent_product_pro_category.first()
            if cat:
                cat.save()
    null_parent_id_products2 = ParentProduct.objects.filter(parent_id='')
    for product in null_parent_id_products2:
        if product.product_type == 'b2c':
            cat = product.parent_product_pro_b2c_category.first()
            if cat:
                cat.save()
        else:
            cat = product.parent_product_pro_category.first()
            if cat:
                cat.save()
    
    
            