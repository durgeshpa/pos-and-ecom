#created by Raj Shekhar at 12:32 29/11/2018

from django import template
register = template.Library()

@register.simple_tag
def percentof(part, whole):
    try:
        return "%d%%" % (float(part) / whole * 100)
    except:
        return 0