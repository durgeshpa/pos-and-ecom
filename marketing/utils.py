from shops.models import Shop


def has_gf_employee_permission(user):
    if user.has_perm("marketing.has_gf_employee_permission"):
        return True
    return False


def shop_obj_related_owner(user):
    return Shop.objects.filter(shop_owner=user, shop_type__shop_sub_type__retailer_type_name__in=['fofo', 'foco'])