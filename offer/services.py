from django.db.models import Q


# search using name based on criteria that matches
def offer_banner_offer_page_slot_search(queryset, search_text):
    queryset = queryset.filter(name__icontains=search_text)

    return queryset


def offer_banner_position_search(queryset, search_text):
    queryset = queryset.filter(Q(page__name__icontains=search_text) | Q(shop__shop_name__icontains=search_text))

    return queryset


def top_sku_search(queryset, search_text):
    queryset = queryset.filter(Q(product__product_name__icontains=search_text) | Q(shop__shop_name__icontains=search_text))

    return queryset