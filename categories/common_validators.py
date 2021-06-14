import json
import logging

from categories.models import Category

# Get an instance of a logger
logger = logging.getLogger(__name__)


def get_validate_category(category_id):
    """ validate ids that belong to a Category model  """

    try:
        category = Category.objects.get(id=category_id)
    except Exception as e:
        logger.error(e)
        return {'error': '{} category not found'.format(category_id)}
    return {'category': category}


def validate_data_format(request):
    # Validate category data
    try:
        data = json.loads(request.data["data"])
    except:
        return {'error': "Invalid Data Format", }

    if request.FILES['category_image']:
        data['category_image'] = request.FILES['category_image']

    return data
