import json


def validate_data_format(request):
    """
        Validating Entered data,
        Convert python data(request.data) in to a JSON string,
    """
    try:
        data = json.dumps(request.data)
    except Exception as e:
        msg = {'is_success': False,
               'message': "Invalid Data Format",
               'response_data': None}
        return msg
    return data


def validate_dev_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id)}