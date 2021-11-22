from retailer_backend.common_function import get_last_no_to_increment
from django.core.cache import cache

from retailer_to_sp.models import Cart

starts_with = 'AOR200903'
def refresh_counter():
    last_number = cache.incr(starts_with)
    print(last_number)
    last_number = get_last_no_to_increment(Cart, 'order_id', '', starts_with)
    last_number += 1
    print(last_number)
    cache.set(starts_with, last_number)
    cache.persist(starts_with)


def run():
    refresh_counter()