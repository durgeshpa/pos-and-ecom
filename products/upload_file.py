import io
import logging
import boto3
from botocore.exceptions import ClientError
from decouple import config
import csv
from django.db import transaction
from django.http import HttpResponse

logger = logging.getLogger(__name__)

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


def s3_bucket():
    try:
        s3 = boto3.resource('s3', aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                            aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'))
        info_logger.info(f"[products/api/v2/BulkDownloadProductAttributes] - Successfully connected with s3")
    except ClientError as err:
        error_logger.error(f"[products/api/v2/BulkDownloadProductAttributes] Failed to connect with s3 - {err}")
        raise err
    return s3


@transaction.atomic
def upload_file_to_s3(csv_file, csv_filename):
    """Upload a file to an S3 bucket
    :param csv_file: File to upload
    :param csv_filename: File name
    :return: s3_file_upload_link if file was uploaded, else False
    """
    # upload the csv file in s3
    try:
        file = io.BytesIO(csv_file.getvalue().encode())
        s3 = s3_bucket()
        s3.meta.client.upload_fileobj(file, config('AWS_STORAGE_BUCKET_NAME'), f"files/{csv_filename}.csv")
        # bucket_location = s3.get_bucket_location(Bucket=config('AWS_STORAGE_BUCKET_NAME'))
        # object_url = "https://s3-{0}.amazonaws.com/{1}/{2}".format(
        #     bucket_location['LocationConstraint'], config('AWS_STORAGE_BUCKET_NAME'), f"files/{csv_filename}.csv")
        res_obj = download_file_from_s3(csv_filename)
        info_logger.info(f"[products/api/v2/BulkDownloadProductAttributes] Successfully get the response from s3")
    except ClientError as e:
        logging.error(e)
        return False
    return res_obj


def download_file_from_s3(csv_file_name):
    # download the csv file in s3
    s3 = s3_bucket()
    obj = s3.Bucket(config('AWS_STORAGE_BUCKET_NAME')).Object(key=f'files/{csv_file_name}.csv')  # file path in S3
    try:
        res = obj.get()
        info_logger.info(f"[products/api/v2/BulkDownloadProductAttributes] Successfully get the response from s3")
    except ClientError as err:
        error_logger.error(f"[products/api/v2/BulkDownloadProductAttributes] Failed to get the response from s3 - {err}")
        raise err

    csv_data = res['Body'].read().decode('utf-8').split('\n')
    reader = csv.reader(csv_data)
    header = csv_data[0].split(',')
    headers = []
    for ele in header:
        headers.append(ele.replace('"', ''))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(csv_file_name)
    writer = csv.writer(response)
    index = 0
    for row in reader:
        if len(row) > 0:
            if row == headers:
                writer.writerow(row)
            else:
                writer.writerow(row)
                index = index + 1
    info_logger.info(f"[products/api/v2/BulkDownloadProductAttributes] - CSV has been "
                     f"successfully downloaded with response [{response}]")
    return response
