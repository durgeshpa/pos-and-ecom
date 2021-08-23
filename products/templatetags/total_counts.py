from django import template
from products.models import ParentProduct, Product

register = template.Library()


@register.simple_tag
def get_parent_products_count():
    return ParentProduct.objects.count()


@register.simple_tag
def get_active_parent_products_count():
    return ParentProduct.objects.filter(status=True).count()


@register.simple_tag
def get_products_count():
    return Product.objects.count()


@register.simple_tag
def get_active_products_count():
    return Product.objects.filter(status='active').count()
