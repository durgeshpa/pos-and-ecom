from import_export import resources
from .models import Order

class OrderResource(resources.ModelResource):
    class Meta:
        model = Order
        exclude = ('created_at','modified_at')
