from django.db import models

from django.db.models import query, manager
from django.utils import timezone
from model_utils import Choices

from brand.models import Vendor
from gram_to_brand.models import GRNOrder
from retailer_to_sp.models import Cart, Order
from shops.models import Shop
from gram_to_brand.models import Cart as POCart

class BaseQuerySet(query.QuerySet):

    def update(self, **kwargs):
        kwargs['updated_at'] = timezone.now()
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
                                      (2, 'CART_CREATED', 'Cart Created'),
                                      (3, 'RESERVED', 'Cart Reserved'),
                                      (4, 'ORDERED', 'Order Placed'),
                                      (5, 'PICKUP_CREATED', 'Pickup Created'),
                                      (6, 'PICKING_ASSIGNED', 'Picking Assigned'),
                                      (7, 'PICKUP_COMPLETED', 'Pickup Completed'),
                                      (8, 'SHIPMENT_CREATED', 'Shipment Created'),
                                      (9, 'QC_DONE', 'QC Done'),
                                      (10, 'TRIP_CREATED', 'Trip Created'),
                                      (11, 'TRIP_STARTED', 'Trip Started'),
                                      (12, 'DELIVERED', 'Delivered'),
                                      (13, 'PO_CREATED', 'PO Created'),
                                      (14, 'AUTO_GRN_DONE', 'AUTO GRN Done'))
    source_po = models.ForeignKey(POCart, related_name='auto_process_entries_for_po', on_delete=models.CASCADE)
    grn = models.OneToOneField(GRNOrder, related_name='auto_order', on_delete=models.CASCADE)
    grn_warehouse = models.ForeignKey(Shop, related_name='shop_grns_for_auto_processing', on_delete=models.CASCADE)
    state = models.PositiveSmallIntegerField(choices=ORDER_PROCESSING_STATUS, default=ORDER_PROCESSING_STATUS.PUTAWAY)
    retailer_shop = models.ForeignKey(Shop, related_name='auto_processing_shop_entries', on_delete=models.CASCADE, null=True)
    cart = models.OneToOneField(Cart, related_name='auto_processing_carts', on_delete=models.CASCADE, null=True)
    order = models.OneToOneField(Order, related_name='auto_processing_orders', on_delete=models.CASCADE, null=True)
    auto_po = models.ForeignKey(POCart, related_name='grn_for_po', on_delete=models.CASCADE, null=True)
    auto_grn = models.OneToOneField(GRNOrder, related_name='auto_processing_by_grn', on_delete=models.CASCADE, null=True)
