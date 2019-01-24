from django import template
from datetime import date, timedelta
import inflect

register = template.Library()
grn_returned_qty_list = []

@register.filter(name='returned_qty')
def returned_qty(value, *args, **kwargs):
    grn_returned_qty_list.append(value)

@register.filter(name='po_product_price')
def po_product_price(value, *args, **kwargs):
    result = value * grn_returned_qty_list[0]
    grn_returned_qty_list.clear()
    return result

@register.filter(name='amount')
def amount(value, *args, **kwargs):
    p = inflect.engine()
    q= p.number_to_words(value)
    return q
