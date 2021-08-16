from django.db.models import Q


# search using name based on criteria that matches
def offer_page_search(queryset, search_text):
    queryset = queryset.filter(name__icontains=search_text)

    return queryset
