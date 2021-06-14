import json


def validate_data_format(request):
    # Validate category data
    try:
        data = json.loads(request.data["data"])
    except:
        return {'error': "Invalid Data Format", }

    if request.FILES['category_image']:
        data['category_image'] = request.FILES['category_image']

    return data
