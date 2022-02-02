from django.db.models import F, Subquery, OuterRef

from retailer_to_sp.models import Order, OrderedProduct


def run():
    print('populate_current_shop_for_existing_data | STARTED')

    shipments = OrderedProduct.objects.filter(current_shop__isnull=True)
    shipments.update(current_shop_id=Subquery(Order.objects.filter(
        id=OuterRef('order_id')).values('seller_shop_id')[:1]))
    print("Current shop updation completed")

    print("Task completed")

