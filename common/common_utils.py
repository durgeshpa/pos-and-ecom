# python imports
import io
import os
import datetime
import hmac
import hashlib
import requests
import logging
import zipfile
from functools import reduce
from pathlib import Path

# django imports
from django.http import HttpResponse

# app imports
from common.constants import ZIP_FILE_NAME

logger = logging.getLogger(__name__)

def convert_date_format_ddmmmyyyy(scheduled_date):
    #This function converts %Y-%m-%d datetime format to a DD/MMM/YYYY 

    #logging.info("converting date format from %d/%m/%Y to %Y-%m-%d")
    return datetime.datetime.strptime(scheduled_date,'%Y-%m-%d').strftime("%d/%b/%Y").__str__()


def concatenate_values(x1, x2): 

	return str(x1) + "|" + str(x2)


def generate_message(values):

	reduce(concatenate_values, values)


def convert_hash_using_hmac_sha256(payload):

	# generate message by concatenating the value of all request parameters 
	# in ascending
	# order with separator as |

	message = sorted(payload.iteritems(), key = lambda x : x[1])
	message = generate_message(message.values()) #'|'.join(message.values())
	signature = hmac.new(bytes(API_SECRET , 'latin-1'), msg = bytes(message , 'latin-1'), digestmod = hashlib.sha256).hexdigest().upper()
	print(signature)
	return signature


def create_temp_file(shipment, tmp_dir, filename, file_name):
	"""

	:param shipment: shipment object
	:param tmp_dir: path of temp directory
	:param filename: filename of individual pdf
	:param file_name: list objects
	:return: list of file name
	"""

	try:
		# request initiate to get the pdf
		r = requests.get(shipment.invoice.invoice_pdf.url)
		filename = tmp_dir + '/' + filename
		file_h = Path(filename)
		# write the pdf file
		file_h.write_bytes(r.content)
		# append all files in a list
		file_name.append(filename)
	except Exception as e:
		logger.exception(e)
	return file_name


def create_zip(file_name, tmp_dir):
	"""

	:param file_name: name of individual file
	:param tmp_dir: path of temp directory
	:return: zip folder
	"""
	try:
		# initiate the zip folder name
		zip_filename = ZIP_FILE_NAME
		zip_buffer = io.BytesIO()
		with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
			for file in file_name:
				# append pdf file in zip folder
				zip_file.write(file)
				# remove temp file
				os.remove(file)
		zip_buffer.seek(0)
		# create response for download the zip
		response = HttpResponse(zip_buffer, content_type='application/zip')
		response['Content-Disposition'] = 'attachment; filename = %s' % zip_filename
		# remove temp dir
		os.rmdir(tmp_dir)
		return response
	except Exception as e:
		logger.exception(e)


def create_file_name(unique_id):
	"""

	:param unique_id: unique id
	:return: unique file name
	"""
	return 'invoice' + '_' + str(unique_id) + '.pdf'
