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
def findTax(r, per, product_cess_amount, qty, *args, **kwargs):
    # you would need to do any localization of the result here
    special_cess= float(product_cess_amount)
    return round((((float((r-special_cess)*100)/(100+per)*per)/100) + special_cess)*qty)

@register.simple_tag(name='findReturnTax')
def findReturnTax(r, per, product_cess_amount, returned_qty, damaged_qty, *args, **kwargs):
    # you would need to do any localization of the result here
    qty = returned_qty + damaged_qty
    special_cess= float(product_cess_amount)
    return round((((float((float(r)-special_cess)*100)/(100+per)*per)/100) + special_cess)*qty)


@register.simple_tag(name='addition')
def addition(qty, unit_price, *args, **kwargs):
    # you would need to do any localization of the result here
    return qty + unit_price


@register.simple_tag(name='addMultiplication')
def addMultiplication(qty, unit_price, newqty, *args, **kwargs):
    #special_cess = float(product_cess_amount) * (int(shipped_qty))
    return round(float(qty) * int(unit_price + newqty), 2)


@register.simple_tag(name='multiply_price_with_qty')
def multiply_price_with_qty(unit_price, qty, *args, **kwargs):
    #special_cess = float(product_cess_amount) * (int(shipped_qty))
    return round(float(unit_price) * int(qty), 2)


@register.simple_tag(name='addMultiplicationcreditNote')
def addMultiplicationcreditNote(unit_price, discounted_price, qty,  *args, **kwargs):
    return round((float(unit_price) - float(discounted_price)) * int(qty),2)


@register.simple_tag(name='discount')
def findDiscount(effective, discounted, *args, **kwargs):return round((effective - discounted), 2)
