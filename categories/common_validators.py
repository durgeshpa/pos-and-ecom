import json
import logging

import sys
import requests
from io import BytesIO
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import URLValidator

from categories.models import Category

# Get an instance of a logger
logger = logging.getLogger(__name__)


def validate_data_format(request):
    # Validate category data
    try:
        data = json.loads(request.data["data"])
    except:
        return {'error': "Invalid Data Format", }

    if 'category_image' in data and data['category_image']:
        try:
            validate = URLValidator()
            validate(data['category_image'])
        except ValidationError:
            return {"error": "Invalid Image Url / Urls"}

        try:
            response = requests.get(data['category_image'])
            image = BytesIO(response.content)
            image = InMemoryUploadedFile(image, 'ImageField', data['category_image'].split('/')[-1], 'image/jpeg',
                                         sys.getsizeof(image),
                                         None)
            data['category_image'] = image
        except:
            pass

    if request.FILES.getlist('category_image'):
        data['category_image'] = request.FILES['category_image']

    return data


def get_validate_category(category_id):
    """ validate ids that belong to a Category model  """

    try:
        category = Category.objects.get(id=category_id)
    except Exception as e:
        logger.error(e)
        return {'error': '{} category not found'.format(category_id)}
    return {'category': category}


def validate_category_name(category_name, brand_id):
    """ validate category_name already exist in Category Model  """

    if Category.objects.filter(category_name__iexact=category_name, status=True).exclude(id=brand_id).exists():
        return {'error': 'category with this category name already exists'}


def validate_category_sku_part(category_sku_part, brand_id):
    """ validate category_sku_part already exist in Category Model  """

    if Category.objects.filter(category_sku_part__iexact=category_sku_part, status=True).exclude(id=brand_id).exists():
        return {'error': 'category with this category sku part already exists'}


def validate_category_slug(category_slug, brand_id):
    """ validate category_slug already exist in Category Model  """

    if Category.objects.filter(category_slug__iexact=category_slug, status=True).exclude(id=brand_id).exists():
        return {'error': 'category with this category slug already exists'}
