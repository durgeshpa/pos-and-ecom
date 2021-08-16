from rest_framework.exceptions import APIException

class NotAllowed(APIException):
    status_code = 401
    default_detail = 'You don\'t have permission to do that.'
    default_code = 'no_permission'