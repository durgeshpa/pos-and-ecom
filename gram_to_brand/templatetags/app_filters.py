#created by Raj Shekhar at 12:32 29/11/2018

from django import template
from datetime import date, timedelta
import inflect

register = template.Library()

qty_list = []
# qty_list1 =[]

# @register.filter(name='case_size')
# def case_size(value, *args, **kwargs):
#     qty_list.append(value)
#
# @register.filter(name='number_of_cases')
# def number_of_cases(value, *args, **kwargs):
#
#     qty_list1.append(value)
#
# @register.filter(name='total_quantity')
# def total_quantity(value, *args, **kwargs):
#     result1 = value*qty_list[0]
#     qty_list.clear()
#     return result1
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
