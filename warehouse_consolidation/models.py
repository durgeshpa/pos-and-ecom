from datetime import timezone

from django.db import models

# Create your models here.
from django.db.models import query, manager
from model_utils import Choices

from brand.models import Vendor
from gram_to_brand.models import GRNOrder
from retailer_to_sp.models import Cart, Order
from shops.models import Shop


class BaseQuerySet(query.QuerySet):

    def update(self, **kwargs):
        kwargs['modified_at'] = timezone.now()
        super().update(**kwargs)

class Manager(manager.BaseManager.from_queryset(BaseQuerySet)):
    pass

class BaseTimestampModel(models.Model):
    objects = Manager()
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)

    class Meta:
        abstract = True

class SourceDestinationMapping(BaseTimestampModel):
    source_wh = models.ForeignKey(Shop, related_name='+', on_delete=models.CASCADE, unique=True)
    dest_wh = models.ForeignKey(Shop, related_name='+', on_delete=models.CASCADE, unique=True)
    retailer_shop = models.ForeignKey(Shop, related_name='+', on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, related_name='+',on_delete=models.CASCADE)


class AutoOrderProcessing(BaseTimestampModel):
    ORDER_PROCESSING_STATUS = Choices((0, 'GRN', 'GRN Done'),
                                      (1, 'PUTAWAY', 'Putaway Done'),
                                      (2, 'ORDERED', 'Order Placed'),
                                      (3, 'PICKUP_CREATED', 'Pickup Created'),
                                      (4, 'PICKUP_COMPLETED', 'Pickup Completed'),
                                      (5, 'SHIPMENT', 'Shipment Created'),
                                      (6, 'QC', 'QC Done'),
                                      (7, 'TRIP', 'Trip Created'),
                                      (8, 'TRIP_STARTED', 'Trip Started'),
                                      (9, 'DELIVERED', 'Delivered'),)
    grn = models.OneToOneField(GRNOrder, related_name='auto_order', on_delete=models.CASCADE)
    grn_warehouse = models.ForeignKey(Shop, related_name='shop_grns_for_auto_processing', on_delete=models.CASCADE)
    state = models.CharField(max_length=255, choices=ORDER_PROCESSING_STATUS, default=ORDER_PROCESSING_STATUS.GRN)
    retailer_shop = models.ForeignKey(Shop, related_name='auto_processing_shop_entries', on_delete=models.CASCADE)
    cart = models.OneToOneField(Cart, related_name='auto_processing_carts', on_delete=models.CASCADE)
    order = models.OneToOneField(Order, related_name='auto_processing_orders', on_delete=models.CASCADE)
