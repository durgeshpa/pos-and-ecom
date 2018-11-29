#created by Raj Shekhar at 12:32 29/11/2018

from django import template
from datetime import date, timedelta

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
