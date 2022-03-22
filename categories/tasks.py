# -*- coding: utf-8 -*-
from categories.models import (Category, B2cCategory, 
                               B2cCategoryData, CategoryData)
from celery.task import task
from products.tasks import load_b2c_parent_category_data

@task
def copy_category_tree_data():
    cat_map = {}
    categories = Category.objects.filter(b2c_status=True)
    non_b2c_parent_cat = categories.filter(category_parent__b2c_status=False).values_list('category_parent_id', flat=True)
    categories |= Category.objects.filter(id__in=non_b2c_parent_cat)
    for category in categories:
        b2c_parent_cat = B2cCategory.objects.create(category_name=category.category_name, 
                                                    category_slug=category.category_slug,
                                                    category_desc=category.category_desc,
                                                    category_parent=None,
                                                    category_sku_part=category.category_sku_part,
                                                    category_image=category.category_image,
                                                    updated_by=category.updated_by,
                                                    status=category.status)
        cat_map[(category.id, category.category_parent.id if category.category_parent else None)] = b2c_parent_cat
    for key, value in cat_map.items():
        cat_parent_id = key[-1]
        if cat_parent_id:
            category = categories.get(id=cat_parent_id)
            cat_parent = cat_map.get((cat_parent_id, category.category_parent.id if category.category_parent else None))
            value.category_parent = cat_parent
            value.save()
    positiondatas = CategoryData.objects.filter(category_data__in=categories)
    for positiondata in positiondatas:
        b2c_category = cat_map.get((positiondata.category_data.id,\
                                           positiondata.category_data.category_parent.id if \
                                               positiondata.category_data.category_parent else None))
        B2cCategoryData.objects.create(category_pos=positiondata.category_pos, 
                                       category_data=b2c_category,
                                       category_data_order=positiondata.category_data_order)
    load_b2c_parent_category_data(cat_map)

@task
def copy_b2c_category_data():
    cat_map = {}
    missing_cats = []
    b2c_categories = B2cCategory.objects.all()
    print(b2c_categories.count())
    for b2c_category in b2c_categories:
        if not Category.objects.filter(category_name=b2c_category.category_name).exists():
            print("Missing or new Category found :: " , b2c_category.category_name)
            print("Found category parent :: ", b2c_category.category_parent.category_name if b2c_category.category_parent else None)
            category = Category.objects.create(
                category_name=b2c_category.category_name, 
                category_slug=b2c_category.category_slug,
                category_desc=b2c_category.category_desc,
                category_parent=None,
                category_sku_part=b2c_category.category_sku_part,
                category_image=b2c_category.category_image,
                updated_by=b2c_category.updated_by,
                status=b2c_category.status
            )
            missing_cats.append(b2c_category.id)
        else:
            category = Category.objects.get(category_name=b2c_category.category_name)
            print("Found category :: ", category)
        cat_map[(b2c_category.id, b2c_category.category_parent.id if b2c_category.category_parent else None)] = category
    for key, value in cat_map.items():
        cat_parent_id = key[-1]
        if cat_parent_id and key[0] in missing_cats:
            print("Mapping Parent for :: category :: ", value)
            b2c_category = b2c_categories.get(id=cat_parent_id)
            category_parent = cat_map.get((cat_parent_id, b2c_category.category_parent.id if b2c_category.category_parent else None))
            print("Parent Found :: ", category_parent)
            value.category_parent = category_parent
            value.save()