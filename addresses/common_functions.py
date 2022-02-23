

def serializer_error_batch(serializer):
    """
        Serializer Error Method
    """
    errors = []
    for error_s in serializer.errors:
        for field in error_s:
            for error in error_s[field]:
                if 'non_field_errors' in field:
                    result = error
                else:
                    result = ''.join('{} : {}'.format(field, error))
                errors.append(result)
    return errors


def serializer_error(serializer):
    """
        Serializer Error Method
    """
    errors = []
    for field in serializer.errors:
        for error in serializer.errors[field]:
            if 'non_field_errors' in field:
                result = error
            else:
                result = ''.join('{} : {}'.format(field, error))
            errors.append(result)
    return errors[0]