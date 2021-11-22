from django.core.validators import RegexValidator
from .messages import VALIDATION_ERROR_MESSAGES


PinCodeValidator = RegexValidator(
    regex='^[1-9][0-9]{5}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_PINCODE'],
    code='INVALID_PINCODE'
)

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
#alphabets + numbers + only -
SlugValidator = RegexValidator(
    regex='^[a-z0-9]+(?:-[a-z0-9]+)*$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_SLUG'],
    code='INVALID_SLUG'
)

#PABCDEF0023
ParentIDValidator = RegexValidator(
    regex='^[P][A-Z]{3}[A-Z]{3}[\d]{4}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_PARENT_ID'],
    code='INVALID_PARENT_ID'
)

#12BBPRG00000121
SKUValidator = RegexValidator(
    regex='^[\d]{2}[A-Z]{5}[\d]{8}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_SKU'],
    code='INVALID_SKU'
)

CapitalAlphabets = RegexValidator(r'^[A-Z]{3}$', 'Only three capital alphates allowed')

#status validator either 0 or 1
StatusValidator = RegexValidator(
    regex='^(1|0)$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_STATUS'],
    code='INVALID_STATUS'
)

#only numeric digits allowed
IDValidator = RegexValidator(
    regex='^[\d]*$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_ID'],
    code='INVALID_ID'
)

#YYYY-MM-DD HH:MM:SS (24time)
DateTimeValidator = RegexValidator(
    regex='^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_DATETIME'],
    code='INVALID_DATETIME'
)

#positive float numbers without %
PercentageValidator = RegexValidator(
    regex='^(?=.+)(?:[1-9]\d*|0)?(?:\.\d+)?$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_PERCENTAGE'],
    code='INVALID_PERCENTAGE'
)

#for only numeric values
ValueValidator = RegexValidator(
    regex='^[0-9 ]+$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_VALUE'],
    code='INVALID_VALUE'
)
#for numeric + alphabets
UnitNameValidator = RegexValidator(
    regex='^[a-zA-Z]+$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_UNIT_NAME'],
    code='INVALID_UNIT_NAME'
)
#for alphabets + numeric + special characters (-, ., $, "",)
ProductNameValidator = RegexValidator(
    regex='^[ \w\$\_\,\%\@\.\/\#\&\+\-\(\)]*$',
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

PriceValidator = RegexValidator(
    regex='^\d{0,8}(\.\d{1,4})?$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_PRICE'],
    code='INVALID_PRICE'
)

GSTINValidator = RegexValidator(
    regex='^[a-zA-Z0-9]*$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_GSTIN_Number'],
    code='INVALID_GSTIN_Number'
)
PriceValidator2 = RegexValidator(
    regex='^[0-9]{0,}(\.\d{0,2})?$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_PRICE'],
    code='INVALID_PRICE'
)
PositiveIntegerValidator = RegexValidator(
    regex='^[1-9]\d*$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_INTEGER_VALUE'],
    code='INVALID_INTEGER_VALUE'
)
