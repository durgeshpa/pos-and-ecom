import datetime
import hmac
import hashlib
from functools import reduce


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