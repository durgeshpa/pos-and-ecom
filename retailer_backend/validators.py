from django.core.validators import RegexValidator
from .messages import VALIDATION_ERROR_MESSAGES

MobileNumberValidator = RegexValidator(
    regex='^\d{10}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_MOBILE_NUMBER'],
    code='INVALID_MOBILE_NUMBER'
)

NameValidator = RegexValidator(
    regex='^[a-zA-Z\s]{2,255}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_NAME'],
    code='INVALID_NAME'
)
ValueValidator = RegexValidator(
    regex='^[0-9 ]+$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_NAME'],
    code='INVALID_NAME'
)

UnitNameValidator = RegexValidator(
    regex='^[a-zA-Z\s]{2,255}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_NAME'],
    code='INVALID_NAME'
)

ProductNameValidator = RegexValidator(
    regex='^[a-zA-Z\s]{2,255}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_NAME'],
    code='INVALID_NAME'
)

AddressNameValidator = RegexValidator(
    regex='^[a-zA-Z\s]{2,255}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_NAME'],
    code='INVALID_NAME'
)
EanCodeValidator = RegexValidator(
    regex='^[a-zA-Z\s]{2,255}$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_NAME'],
    code='INVALID_NAME'
)

PhoneNumberValidator = RegexValidator(
    regex='^[0-9 ]+$',
    message=VALIDATION_ERROR_MESSAGES['INVALID_NAME'],
    code='INVALID_NAME'
)
