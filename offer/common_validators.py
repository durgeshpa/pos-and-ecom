import logging

from offer.models import OfferPage


# Get an instance of a logger
logger = logging.getLogger(__name__)


def get_validate_page(page):
    """ validate id that belong to a OfferPage model if not through error """
    try:
        off_page_obj = OfferPage.objects.get(id=page)
    except Exception as e:
        logger.error(e)
        return {'error': 'please provide a valid offer page id'}
    return {'page': off_page_obj}