import threading
from django.utils.timezone import now


class RequestMiddleware:

  def __init__(self, get_response, thread_local=threading.local()):
    self.get_response = get_response
    self.thread_local = thread_local
    # One-time configuration and initialization.

  def __call__(self, request):
    # Code to be executed for each request before
    # the view (and later middleware) are called.
    self.thread_local.current_request = request

    response = self.get_response(request)

    # Code to be executed for each request/response after
    # the view is called.

    return response

    def process_response(self, request, response):
        if request.user.is_authenticated():
            User.objects.filter(pk=request.user.pk).update(last_login=now())
        return response

def get_current_user():
    request = RequestMiddleware(get_response=None)
    request = request.thread_local.current_request
    return request.user





