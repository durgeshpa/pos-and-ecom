import requests
from rest_framework.response import Response

'''
It is data wrapper method.
params:
    data=data which you want to send
    status_code=staus_code of request
'''
def data_wrapper_response(data=None, status_code=None):
    if status_code in [200,201,204]:
        status = True
    else:
        status = False


    data = {
        'is_success':status,
        'message': [''],
        'response_data':data
    }
    
    return Response(data, status=status_code)


def format_data(result):
    '''
    Method use for formatting data in django generic and viewset apis
    '''
    if result.status_code in [200,201]:
        status = True
    else:
        status = False

    data = {
        'is_success':status,
        'message':[''],
        'response_data':result.data
    }
    result.data = data

    return result