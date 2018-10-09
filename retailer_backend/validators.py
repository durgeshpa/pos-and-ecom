from django.core.validators import RegexValidator
from .messages import VALIDATION_ERROR_MESSAGES

MobileNumberValidator = RegexValidator(
    regex='^[6-9]\d{9}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_MOBILE_NUMBER'],
    code='INVALID_MOBILE_NUMBER'
)
#for only alphabets
NameValidator = RegexValidator(
    regex='^[a-zA-Z\s]{2,255}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_NAME'],
    code='INVALID_NAME'
)
#for only numeric values
ValueValidator = RegexValidator(
    regex='^[0-9 ]+$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_VALUE'],
    code='INVALID_VALUE'
)
#for numeric + alphabets
UnitNameValidator = RegexValidator(
    regex='^\d+(\S|\s)[a-zA-Z]+$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_UNIT_NAME'],
    code='INVALID_UNIT_NAME'
)
#for alphabets + numeric + special characters (-, ., $, "",)
ProductNameValidator = RegexValidator(
    regex='^[ \w\$_,@./#&+-]*$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_PRODUCT_NAME'],
    code='INVALID_PRODUCT_NAME'
)
#
AddressNameValidator = RegexValidator(
    regex='^[\w*\s*\#\-\,\/\.\(\)\&]*$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_ADDRESS'],
    code='INVALID_NAME'
)
#13 digit numeric code
EanCodeValidator = RegexValidator(
    regex='^\d{13}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_EAN_CODE'],
    code='INVALID_EAN_CODE'
)

PhoneNumberValidator = RegexValidator(
    regex='^[6-9]\d{9}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_MOBILE_NUMBER'],
    code='INVALID_MOBILE_NUMBER'
)
