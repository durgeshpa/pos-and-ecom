#created by Raj Shekhar at 12:32 29/11/2018

from django import template
from datetime import date, timedelta
import inflect

register = template.Library()

qty_list = []
shipped_qty_list= []
shipped_qty_list_amount=[]

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

@register.filter(name='shipped_qty')
def shipped_qty(value, *args, **kwargs):
    shipped_qty_list.append(value)

@register.filter(name='inner_case_size')
def inner_case_size(value, *args, **kwargs):
    result = int(value)*shipped_qty_list[0]
    shipped_qty_list_amount.append(result)
    shipped_qty_list.clear()
    return result

@register.filter(name='price_to_retailer')
def price_to_retailer(value, *args, **kwargs):
    result = value*shipped_qty_list_amount[0]
    shipped_qty_list_amount.clear()
    return result

@register.filter(name='amount')
def amount(value, *args, **kwargs):
    p = inflect.engine()
    q= p.number_to_words(value)
    return q
