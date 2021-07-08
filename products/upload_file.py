import io
import logging
import boto3
from botocore.exceptions import ClientError
from decouple import config


logger = logging.getLogger(__name__)

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


def upload_file_to_s3(csv_file, csv_filename):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :return: s3_file_upload_link if file was uploaded, else False
    """

    try:
        s3 = boto3.client('s3', aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                          aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'))
        info_logger.info(f"[products/api/v2/BulkDownloadProductAttributes] - Successfully connected with s3")
    except ClientError as err:
        error_logger.error(f"[products/api/v2/BulkDownloadProductAttributes] Failed to connect with s3 - {err}")
        raise err

    # Upload the file
    try:
        file = io.BytesIO(csv_file.getvalue().encode())
        s3.upload_fileobj(file, config('AWS_STORAGE_BUCKET_NAME'), f"files/{csv_filename}.csv")
        bucket_location = s3.get_bucket_location(Bucket=config('AWS_STORAGE_BUCKET_NAME'))
        object_url = "https://s3-{0}.amazonaws.com/{1}/{2}".format(
            bucket_location['LocationConstraint'], config('AWS_STORAGE_BUCKET_NAME'), f"files/{csv_filename}.csv")
        info_logger.info(f"[products/api/v2/BulkDownloadProductAttributes] Successfully get the response from s3")
    except ClientError as e:
        logging.error(e)
        return False
    return object_url