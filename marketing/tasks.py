import requests
from celery.task import task


@task
def send_gupshup_request(url, parameters):
    req = requests.get(url, params=parameters)
    return req.status_code, req.text
