from import_export import resources
from .models import Category, B2cCategory


class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        exclude = ('category_image', 'is_created', 'updated_at')

class B2cCategoryResource(resources.ModelResource):
    class Meta:
        model = B2cCategory
        execlude = ('category_image', 'is_created', 'updated_at')