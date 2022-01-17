from functools import wraps

from pos.common_functions import api_response

def resolve_headers(view_func):
    
    @wraps(view_func)
    def _wrapper(self, *args, **kwargs):
        kwargs = {}
        if self.request.META.get('HTTP_REPORT_TYPE'):
            kwargs['report_type'] = self.request.META.get('HTTP_REPORT_TYPE')
        else:
            return api_response("Please provide report type | BO | BP |")
        if self.request.META.get('HTTP_REPORT_SOURCE'):
            kwargs['report_source'] = self.request.META.get('HTTP_REPORT_SOURCE')
        else:
            return api_response("Please provide report source | redash | host |")
        return view_func(self, *args, **kwargs)
    return _wrapper