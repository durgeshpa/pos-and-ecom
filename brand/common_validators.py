import json
import logging

import sys
import requests
from io import BytesIO
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import URLValidator

# Get an instance of a logger
logger = logging.getLogger(__name__)


def validate_data_format(request):
    # Validate brand data
    try:
        data = json.loads(request.data["data"])
    except:
        return {'error': "Invalid Data Format", }

    if 'brand_logo' in data:
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
