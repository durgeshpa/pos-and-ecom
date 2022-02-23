# -*- coding: utf-8 -*-
from categories.models import (Category, B2cCategory, 
                               B2cCategoryData, CategoryData)
from celery.task import task

@task
def copy_category_tree_data(model=Category):
    cat_map = {}
    categories = model.objects.filter(b2c_status=True)
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