import json
import logging

import sys
import requests
from io import BytesIO
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import URLValidator

from brand.models import Brand

# Get an instance of a logger
logger = logging.getLogger(__name__)


def validate_data_format(request):
    # Validate brand data
    try:
        data = json.loads(request.data["data"])
    except:
        return {'error': "Invalid Data Format", }

    if 'brand_logo' in data and data['brand_logo']:
        try:
            validate = URLValidator()
            validate(data['brand_logo'])
        except ValidationError:
            return {"error": "Invalid Image Url / Urls"}

        try:
            response = requests.get(data['brand_logo'])
            image = BytesIO(response.content)
            image = InMemoryUploadedFile(image, 'ImageField', data['brand_logo'].split('/')[-1], 'image/jpeg',
                                         sys.getsizeof(image),
                                         None)
            data['brand_logo'] = image
        except:
            pass

    if request.FILES.getlist('brand_logo'):
        data['brand_logo'] = request.FILES['brand_logo']

    return data


def validate_brand_name(brand_name, brand_id):
    """ validate brand_name already exist in Brand Model  """
    if Brand.objects.filter(brand_name__iexact=brand_name, status=True).exclude(id=brand_id).exists():
        return {'error': 'brand with this brand name already exists'}


def validate_brand_code(brand_code, brand_id):
    """ validate brand_code already exist in Brand Model  """
    if Brand.objects.filter(brand_code__iexact=brand_code, status=True).exclude(id=brand_id).exists():
        return {'error': 'brand with this brand code already exists'}


def validate_brand_slug(brand_slug, brand_id):
    """ validate brand_slug already exist in Brand Model  """

    if Brand.objects.filter(brand_slug__iexact=brand_slug, status=True).exclude(id=brand_id).exists():
        return {'error': 'brand with this brand slug already exists'}
