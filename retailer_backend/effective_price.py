from retailer_to_sp.models import *

end_date = datetime.datetime.today()
start_date = end_date - datetime.timedelta(days=88)

orders = CartProductMapping.objects.filter(created_at__gte = start_date, created_at__lte = end_date, cart__cart_status = 'ordered', cart__order_id__startswith = 'GOR')
for m in orders:
    m.effective_price = m.item_effective_prices
    m.save()
