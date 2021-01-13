from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from rest_framework.pagination import LimitOffsetPagination

from products.models import Product

class SmallOffsetPagination(LimitOffsetPagination):
    """
    Custom LimitOffset
    """
    default_limit = 10
    max_limit = 50

def time_diff_days_hours_mins_secs(dt2, dt1):
    diff_in_seconds = date_diff_in_seconds(dt2, dt1)
    days, hours, minutes, seconds = dhms_from_seconds(diff_in_seconds)
    time_string = ''
    if days > 0:
        time_string += '%d days' % days
    if hours > 0:
        time_string += ' %d hrs' % hours
    if minutes > 0:
        time_string += ' %d mins' % minutes
    if seconds > 0:
        time_string += ' %d secs' % seconds
    return time_string


def date_diff_in_seconds(dt2, dt1):
    timedelta = dt2 - dt1
    return timedelta.days * 24 * 3600 + timedelta.seconds


def dhms_from_seconds(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return (days, hours, minutes, seconds)

