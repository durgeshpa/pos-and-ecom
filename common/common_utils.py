# python imports
import datetime
import hmac
import hashlib
import requests
import logging
import ast
from functools import reduce
from decouple import config
# django imports
from django.shortcuts import redirect

# app imports
from common.constants import Version, STREAM_API_NAME, STATUS_API_NAME

logger = logging.getLogger(__name__)


def convert_date_format_ddmmmyyyy(scheduled_date):
    # This function converts %Y-%m-%d datetime format to a DD/MMM/YYYY

    # logging.info("converting date format from %d/%m/%Y to %Y-%m-%d")
    return datetime.datetime.strptime(scheduled_date, '%Y-%m-%d').strftime("%d/%b/%Y").__str__()


def concatenate_values(x1, x2):
    return str(x1) + "|" + str(x2)


def generate_message(values):
    reduce(concatenate_values, values)


def convert_hash_using_hmac_sha256(payload):
    # generate message by concatenating the value of all request parameters
    # in ascending
    # order with separator as |

    message = sorted(payload.iteritems(), key=lambda x: x[1])
    message = generate_message(message.values())
    signature = hmac.new(bytes(API_SECRET, 'latin-1'), msg=bytes(message, 'latin-1'),
                         digestmod=hashlib.sha256).hexdigest().upper()
    return signature


def create_file_path(file_path_list, bucket_location, file_name):
    """
    :param file_path_list: list of file path
    :param bucket_location: location of S3 bucket
    :param file_name: name of pdf file
    :return: list of pdf files path
    """

    try:
        bucket_name = config('AWS_STORAGE_BUCKET_NAME')
        file_path = bucket_name + '/' + bucket_location + '/' + file_name
        file_path_list.append(file_path)
    except Exception as e:
        logger.exception(e)
    return file_path_list


def create_zip_url(file_path_list):
    """

    :param file_path_list: collection of pdf files
    :return: :- response of zip status api
    """
    try:
        # S3zip Server URL
        api_url = config('S3_ZIP_API')
        # crete API end point for S3zip stream API
        stream_api_end_point = api_url + '/' + Version + '/' + STREAM_API_NAME
        bearer = 'Bearer {}'.format(config('AUTHORIZATION_KEY'))
        headers = {"Authorization": bearer}
        # create payload and configure AWS Key, Secret, Bucket Name, Region and collection of files
        payload = {'awsKey': config('AWS_ACCESS_KEY_ID'), 'awsSecret': config('AWS_SECRET_ACCESS_KEY'),
                   'awsBucket': config('AWS_STORAGE_BUCKET_NAME'), 'awsRegion': config('AWS_REGION'),
                   'filePaths': file_path_list}
        # call S3zip stream API
        stream_api_response = requests.request("POST", stream_api_end_point, data=payload, headers=headers)
        # call zip status api and send the parameter as a response of stream api and api url
        response = s3_zip_status_api(stream_api_response, api_url)
        return response
    except Exception as e:
        logger.exception(e)


def s3_zip_status_api(stream_api_response, api_url):
    """
    :param stream_api_response: response of S3ZIP stream API
    :param api_url: api url
    :return: redirect the response url
    """
    try:
        # crete API end point for S3zip status API
        status_api_end_point = api_url + '/' + Version + '/' + STATUS_API_NAME
        bearer = 'Bearer {}'.format(config('AUTHORIZATION_KEY'))
        headers = {'Content-Type': 'application/json; charset=UTF-8', "Authorization": bearer}
        # send payload which is S3 stream API response
        payload = stream_api_response
        # call S3zip status API
        response = requests.request("POST", status_api_end_point, data=payload, headers=headers)
        # convert string dict to string and get the Zip url
        response = ast.literal_eval(str(response.text))['result']
        return redirect(response)
    except Exception as e:
        logger.exception(e)


def create_file_name(file_prefix, unique_id):
    """

    :param file_prefix: append the prefix according to object
    :param unique_id: unique id
    :return: file name
    """
    # return unique name of pdf file
    return file_prefix + str(unique_id) + '.pdf'
