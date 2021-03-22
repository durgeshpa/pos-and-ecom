from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from global_config.models import GlobalConfig


def pagination(request, serializer):
    """
         Common Pagination Function for Paginate Queryset
    """
    records_per_page = 10

    per_page_orders = request.GET.get('records_per_page') if request.GET.get('records_per_page') else records_per_page
    paginator = Paginator(serializer.data, int(per_page_orders))
    page_number = request.GET.get('page_number')
    try:
        offers_orders = paginator.page(page_number)
    except PageNotAnInteger:
        offers_orders = paginator.page(1)
    except EmptyPage:
        offers_orders = paginator.page(paginator.num_pages)
    serializer_paginate_data = {
        'previous_page': offers_orders.has_previous() and offers_orders.previous_page_number() or None,
        'next_page': offers_orders.has_next() and offers_orders.next_page_number() or None,
        'data': list(offers_orders)
    }
    return serializer_paginate_data
