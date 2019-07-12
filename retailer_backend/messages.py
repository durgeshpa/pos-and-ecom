VALIDATION_ERROR_MESSAGES = {
    'INVALID_MOBILE_NUMBER': 'Mobile Number is not valid',
    'INVALID_NAME': 'Invalid name. Only alphabets are allowed',
    'OTP_ATTEMPTS_EXCEEDED': 'Exceeded maximum attempts! Please enter the new OTP',
    'OTP_EXPIRED': 'OTP expired! Please enter the new OTP',
    'OTP_NOT_MATCHED': 'OTP does not match',
    'USER_NOT_EXIST': 'Invalid data',
    'INVALID_UNIT_NAME': 'Invalid unit name (eg: kg, litres)',
    'INVALID_VALUE': 'Invalid value. Only numbers are allowed',
    'INVALID_PRODUCT_NAME': 'Invalid product name. Special characters allowed are _ , @ . / # & + -',
    'INVALID_ADDRESS': 'Invalid address. Special characters allowed are # - , / . ( ) &',
    'INVALID_EAN_CODE': 'Invalid EAN code. Exactly 13 numbers required',
    'INVALID_SLUG': 'Invalid slug. Only lower case alphabets and (-) is allowed as special character.',
    'INVALID_STATUS': 'Invalid status value. It should be either 0 or 1',
    'INVALID_ID': 'Invalid ID. It should be numeric',
    'INVALID_SKU': 'Invalid SKU.(eg: 12BBPRG00000121)',
    'INVALID_PERCENTAGE': 'Invalid percentage. Only positive value is accepted without %(eg: 10,10.5).',
    'INVALID_DATETIME': 'Invalid datetime. It should be of format YYYY-MM-DD HH:MM:SS(eg: 2018-10-11 13:06:56)',
    'INVALID_PRICE': 'Invalid price.(eg: 1000, 200.50)',
    'INVALID_PINCODE': 'Invalid Pincode',
    'INVALID_PRODUCT_ID':'Invalid Product Id',
    'EMPTY':'%s cant be empty',
    'EMPTY_OR_NOT_VALID':'%s cant be empty or not valid( eg: 11.11)',
    'INVALID_GSTIN_Number': 'Invalid Gstin number',
    'INVALID_MARGIN': '%s has not valid format( eg: 0, 201, 17.11)',

}

SUCCESS_MESSAGES = {
    'USER_IMPORT_SUCCESSFULLY': 'User Import Successfully.',
    'MOBILE_NUMBER_VERIFIED': 'Your mobile number verified successfully',
    'USER_ALREADY_EXISTS': 'User already exists! Please login',
    'USER_SHOP_ADDED': 'Shop added successfully',
    'CHANGED_STATUS': 'Po_Status changed to %s'
}

ERROR_MESSAGES = {
    'AVAILABLE_PRODUCT': 'Available No of Pieces : {0}',
    'INVALID_PRICE_UPLOAD': 'You cant upload Retailer Price greater than MRP',
}
