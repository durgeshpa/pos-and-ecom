from datetime import datetime

from rest_framework.pagination import LimitOffsetPagination


class SmallOffsetPagination(LimitOffsetPagination):
    """
    Custom LimitOffset
    """
    default_limit = 10
    max_limit = 50


class OffsetPaginationDefault50(LimitOffsetPagination):
    """
    Custom LimitOffset
    """
    default_limit = 50
    max_limit = 100


class FiftyOffsetPaginationDefault(LimitOffsetPagination):
    """
    Custom LimitOffset
    """
    default_limit = 200
    max_limit = 250


def time_diff_days_hours_mins_secs(dt2, dt1):
    """
    Returns the time difference between two given dates
    params :
        dt2 : later date instance
        dt1 : earlier date instance
    returns :
        time_string : String ( x days n hrs m mins y secs)
    """
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
    """
    Returns the time difference in seconds between two given dates
    params :
        dt2 : later date instance
        dt1 : earlier date instance
    """
    timedelta = dt2 - dt1
    return timedelta.days * 24 * 3600 + timedelta.seconds


def dhms_from_seconds(seconds):
    """
    Returns the time difference tuple including (days, hours, minutes, seconds) between two given dates
    params :
        dt2 : later date instance
        dt1 : earlier date instance
    """
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return (days, hours, minutes, seconds)


def isDateValid(date, pattern="%Y-%m-%d"):
    """
    Validates if given string is of date format provided
    """
    try:
        return datetime.strptime(date, pattern)
    except ValueError:
        return False


def getStrToDate(date, pattern="%Y-%m-%d"):
    """
    Converts string to date instance in the format provided
    Returns false if string is not a valid date
    """
    try:
        return datetime.strptime(date, pattern).date()
    except ValueError:
        return False


def isDateYearValid(date, pattern="%y-%m-%d"):
    """
    Validates if given string is of date format provided
    """
    try:
        return datetime.strptime(date, pattern)
    except ValueError:
        return False


def getStrToYearDate(date, pattern="%y-%m-%d"):
    """
    Converts string to date instance in the format provided
    Returns false if string is not a valid date
    """
    try:
        return datetime.strptime(date, pattern).date()
    except ValueError:
        return False


def isBlankRow(row, row_length):
    """
    Validates if a given CSV row of given length is blank
    """
    column_no = 0
    while column_no < row_length:
        if row[column_no].strip() != '':
            return False
        column_no = column_no+1
    return True
