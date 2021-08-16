from import_export import resources
from .models import Category


class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        exclude = ('category_image', 'is_created', 'updated_at')
