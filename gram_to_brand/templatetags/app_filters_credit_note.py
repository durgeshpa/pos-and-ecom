#created by Raj Shekhar at 12:32 29/11/2018

from django import template
from datetime import date, timedelta
import inflect

register = template.Library()

returned_qty_list= []
returned_qty_list_amount=[]

@register.filter(name='total_returned_qty')
def total_returned_qty(value, *args, **kwargs):
    returned_qty_list.append(value)

@register.filter(name='inner_case_size')
def inner_case_size(value, *args, **kwargs):
    result = int(value)*returned_qty_list[0]
    returned_qty_list_amount.append(result)
    returned_qty_list.clear()
    return result

@register.filter(name='price_to_retailer')
def price_to_retailer(value, *args, **kwargs):
    result = value*returned_qty_list_amount[0]
    returned_qty_list_amount.clear()
    return result

@register.filter(name='amount')
def amount(value, *args, **kwargs):
    p = inflect.engine()
    q= p.number_to_words(value)
    return q

@register.simple_tag(name='findTax')
def findTax(r, per, *args, **kwargs):
    # you would need to do any localization of the result here
    return round(((float(r*100)/(100+per)*per)/100),2)


@register.simple_tag(name='addition')
def addition(qty, unit_price, *args, **kwargs):
    # you would need to do any localization of the result here
    return (qty  + unit_price)

@register.simple_tag(name='addMultiplication')
def addMultiplication(qty, unit_price, newqty, *args, **kwargs):
    return round(float(qty) * int(unit_price + newqty),2)

@register.simple_tag(name='addMultiplicationcreditNote')
def addMultiplicationcreditNote(qty, unit_price, discounted_price, *args, **kwargs):
    return round(float(qty - unit_price) * int(discounted_price),2)

@register.simple_tag(name='discount')
def findDiscount(effective, discounted, *args, **kwargs):return round((effective - discounted), 2)
