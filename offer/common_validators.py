import json
import logging

import sys
import requests
from io import BytesIO
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import URLValidator


from offer.models import OfferPage, OfferBannerSlot, OfferBanner

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


def get_validate_offerbannerslot(page):
    """ validate id that belong to a OfferBannerSlot model if not through error """
    try:
        off_banner_slot_obj = OfferBannerSlot.objects.get(id=page)
    except Exception as e:
        logger.error(e)
        return {'error': 'please provide a valid offer banner slot id'}
    return {'off_banner_slot': off_banner_slot_obj}


def get_validated_offer_ban_data(offer_ban_data):
    for val in offer_ban_data:
        if 'offer_banner_data' not in val:
            return {'error': "'offer_banner_data' is required"}
        if not OfferBanner.objects.filter(id=val['offer_banner_data']).exists():
            return {'error': f"'offer_banner_data'{val['offer_banner_data']} is invalid"}
        # if 'offer_banner_data_order' not in val:
        #     return {'error': "'offer_banner_data_order' is required"}
        # if not val['offer_banner_data_order'] or not re.match("^[\d\,]*$", str(val['offer_banner_data_order'])):
        #     return {'error': f"'offer_banner_data_order'{val['offer_banner_data_order']} is invalid"}

    return {'data': offer_ban_data}


def validate_data_format(request):
    # validate offer banner data
    try:
        data = json.loads(request.data["data"])
    except Exception as e:
        return {'error': "Invalid Data Format", }

    if 'image' in data and data['image']:
        try:
            validate = URLValidator()
            validate(data['image'])
        except ValidationError:
            return {"error": "Invalid Image Url / Urls"}

        try:
            response = requests.get(data['image'])
            image = BytesIO(response.content)
            image = InMemoryUploadedFile(image, 'ImageField', data['image'].split('/')[-1], 'image/jpeg',
                                         sys.getsizeof(image),
                                         None)
            data['image'] = image
        except:
            pass

    if request.FILES.getlist('image'):
        data['image'] = request.FILES['image']

    return data
