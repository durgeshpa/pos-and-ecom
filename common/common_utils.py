import datetime
import hmac
import hashlib
from functools import reduce
import os
import shutil
import barcode
from barcode.writer import ImageWriter
import PIL
from PIL import Image
from pyzbar.pyzbar import decode
from io import BytesIO
import base64
import io


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


def barcode_gen(value):
	ean = barcode.get_barcode_class('code128')
	ean = ean(value, writer=ImageWriter())
	image = ean.render()
	output_stream = BytesIO()
	image_resize = image.resize((900, 300))
	image_resize.save(output_stream, format='JPEG', quality=150)
	output_stream.seek(0)
	return output_stream


def barcode_decoder(value):
	image = Image.open(value)
	image = image.convert('L')
	data = decode(image)
	return str(data[0][0])
