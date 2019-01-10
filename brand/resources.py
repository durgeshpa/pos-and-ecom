from import_export import resources
from .models import Brand

class BrandResource(resources.ModelResource):
    class Meta:
        model = Brand
        exclude = ('brand_logo','created_at','updated_at')
