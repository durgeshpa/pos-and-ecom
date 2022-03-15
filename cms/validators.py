
def validate_data_format(request):
    """ Validate shop data  """
    try:
        data = request.data["data"]
    except Exception as e:
        return {'error': "Invalid Data Format", }

    return data


def validate_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id)}
