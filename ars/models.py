from django.db import models

# Create your models here.
from model_utils import Choices

from brand.models import Brand, Vendor
from gram_to_brand.models import Cart
from products.models import ParentProduct, Product
from shops.models import Shop


class BaseTimestampModel(models.Model):
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)

    class Meta:
        abstract = True

class ProductDemand(BaseTimestampModel):
    warehouse = models.ForeignKey(Shop, related_name='warehouse_demands', on_delete=models.DO_NOTHING)
    parent_product = models.ForeignKey(ParentProduct, related_name='product_demands', on_delete=models.DO_NOTHING)
    active_child_product = models.ForeignKey(Product, related_name='child_product_demands', on_delete=models.DO_NOTHING)
    average_daily_sales = models.FloatField(default=0)
    current_inventory = models.PositiveIntegerField(default=0)
    demand = models.PositiveIntegerField(default=0)

    def __str__(self):
        return "%s - %s - %s"%(self.warehouse, self.parent_product, self.demand)


class VendorDemand(BaseTimestampModel):
    STATUS_CHOICE = Choices((1, 'DEMAND_CREATED', 'Demand Created'),
                            (2, 'PO_CREATED', 'PO Created'),
                            (3, 'FAILED', 'Failed'), (4, 'MAIL_SENT_FOR_APPROVAL', 'Mail sent for approval'),
                            )
    warehouse = models.ForeignKey(Shop, related_name='ars_shop_demands', on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, related_name='ars_brand_demands', on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, related_name='ars_vendor_demands', on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICE, null=True)
    po = models.ForeignKey(Cart, related_name='ars_po_demands', null=True, on_delete=models.DO_NOTHING)
    comment = models.TextField(null=True)


class VendorDemandProducts(BaseTimestampModel):
    po = models.ForeignKey(VendorDemand, related_name='ars_po_demands', on_delete=models.CASCADE)
    demand = models.ForeignKey(VendorDemand, related_name='ars_demand_products', on_delete=models.CASCADE)
    product = models.ForeignKey(ParentProduct, related_name='ars_product_demands', on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField()