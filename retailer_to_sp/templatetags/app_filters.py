
from django import template
register = template.Library()

@register.simple_tag
def percentof(part, whole):
    try:
        return "%.0f%%" % (float(part) / whole * 100)
    except:
        return 0


@register.simple_tag
def subtract(num1, num2):
    try:
        result = num1 - num2
        return result if result>0 else 0
    except:
        return 0