from import_export import resources
from .models import RuleSetProductMapping

class RuleSetProductMappingResource(resources.ModelResource):
    class Meta:
        model = RuleSetProductMapping
        exclude = ( 'created_at', )
