#created by Raj Shekhar at 12:32 29/11/2018

from django import template
from datetime import date, timedelta
import inflect

register = template.Library()

qty_list = []

@register.filter(name='qty')
def qty(value, *args, **kwargs):
    qty_list.append(value)

@register.filter(name='price')
def price(value, *args, **kwargs):
    result = value*qty_list[0]
    qty_list.clear()
    return result

@register.filter(name='amount')
def amount(value, *args, **kwargs):
    p = inflect.engine()
    q= p.number_to_words(value)
    return q
