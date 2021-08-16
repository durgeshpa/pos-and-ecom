from django.db.models import Q


# search using user name & phone number based on criteria that matches
def group_search(queryset, search_text):
    queryset = queryset.filter(Q(name__icontains=search_text))
    return queryset