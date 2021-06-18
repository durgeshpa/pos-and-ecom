
from django import template
register = template.Library()

@register.simple_tag
def percentof(part, whole):
    try:
        return "%.0f%%" % (float(part) / whole * 100)
    except:
        return 0