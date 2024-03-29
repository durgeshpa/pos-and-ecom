VALIDATION_ERROR_MESSAGES = {
    'INVALID_MOBILE_NUMBER': 'Mobile Number is not valid',
    'INVALID_NAME': 'Invalid name. Only alphabets are allowed',
    'OTP_ATTEMPTS_EXCEEDED': "You have exceeded limit for OTP attempts or resends. Please try in {} minutes",
    'OTP_EXPIRED': 'OTP expired! Please request a new OTP.',
    'OTP_NOT_MATCHED': 'Incorrect OTP',
    'INVALID_DATA': 'Invalid data',
    'INVALID_UNIT_NAME': 'Invalid unit name (eg: kg, litres)',
    'INVALID_VALUE': 'Invalid value. Only numbers are allowed',
    'INVALID_PRODUCT_NAME': 'Invalid product name. Special characters allowed are _ , @ . / # & + -',
    'INVALID_ADDRESS': 'Invalid address. Special characters allowed are # - , / . ( ) &',
    'INVALID_EAN_CODE': 'Invalid EAN code. Exactly 13 numbers required',
    'INVALID_SLUG': 'Invalid slug. Only lower case alphabets and (-) is allowed as special character.',
    'INVALID_STATUS': 'Invalid status value. It should be either 0 or 1',
    'INVALID_ID': 'Invalid ID. It should be numeric',
    'INVALID_SKU': 'Invalid SKU.(eg: 12BBPRG00000121)',
    'INVALID_PARENT_ID': 'Invalid Parent ID.(eg: PABCDEF0023)',
    'INVALID_PERCENTAGE': 'Invalid percentage. Only positive value is accepted without %(eg: 10,10.5).',
    'INVALID_DATETIME': 'Invalid datetime. It should be of format YYYY-MM-DD HH:MM:SS(eg: 2018-10-11 13:06:56)',
    'INVALID_PRICE': 'Invalid price.(eg: 1000, 200.50)',
    'INVALID_PINCODE': 'Invalid Pincode',
    'INVALID_PRODUCT_ID':'Invalid Product Id',
    'INVALID_PRODUCT_SKU':'Invalid Product SKU',
    'EMPTY':"%s can't be empty",
    'EMPTY_OR_NOT_VALID':"%s can't be empty or not valid (eg: 0)",
    'NOT_VALID':'%s is not valid.',
    'VENDOR_NOT_MAPPED':'%s is not mapped.',
    'DEACTIVATE':'%s is deactivated.',
    'EMPTY_OR_NOT_VALID_STRING': '%s cant be empty or only be a "Per Pack" or "Per Piece"',
    'INVALID_GSTIN_Number': 'Invalid Gstin number',
    'INVALID_MARGIN': '%s has not valid format( eg: 0, 201, 17.11)',
    'ALREADY_ADDED_SHOP':'Already added Sales Executive with this shop',
    'INVALID_INTEGER_VALUE':'Only Positive Integers Accepted',
    'OTP_EXPIRED_GENERATE_AGAIN':'Entered OTP expired! Please enter the new OTP',
    'Referral_code':'Please provide a valid referral code',
    'User_Already_Exist':'User Already Registered Please Login',
    'Enter_OTP':'Please Enter otp',
    'Phone_Number':'Please Enter Phone Number,',
    'User_not_register': 'You are not registered User, Please Sign Up.'
}

SUCCESS_MESSAGES = {
    'USER_IMPORT_SUCCESSFULLY': 'User Import Successfully.',
    'MOBILE_NUMBER_VERIFIED': 'Verified Successfully',
    'USER_ALREADY_EXISTS': 'User already exists! Please login',
    'USER_SHOP_ADDED': 'Shop added successfully',
    'CHANGED_STATUS': 'Po_Status changed to %s',
    'CSV_UPLOADED': 'CSV file has been successfully uploaded.',
    'CSV_UPLOADED_EXCEPT': 'CSV file has been successfully uploaded, except these ids:-%s',
    'AUDIT_ENDED_SKU': 'Audit completed for SKU {}',
    'AUDIT_ENDED_BIN': 'Audit completed for BIN {}',
    'SCHEME_SLAB_ADD_MORE':'Buy worth ₹{} more to earn ₹{} incentive at {}%',''
    'SCHEME_SLAB_HIGHEST':'You are already in the highest incentive slab earning margin at 2%. Buy more to earn more incentive',
    'SCHEME_BUY_MORE': 'Buy more to earn more incentive.',
    'ARS_MAIL_PO_APPROVAL_SUBJECT':'Summary of Auto PO’s generated on {}',
    'ARS_MAIL_PO_APPROVAL_BODY':'PFA the list of Auto PO’s generated on {}. '
                                'Please note that these PO’s will not be placed until approved '
                                'by concerned category managers by going to Seller Panel.',
    'ARS_MAIL_VENDOR_SUBJECT': 'PO_{}_{}_{}',
    'ARS_MAIL_VENDOR_BODY': 'Dear Partners, \n \n Find attached PO from Pepper Tap/Gram Factory. \n \n'
                            'Note: Take Prior appointment before delivery and bring PO copy along with Original Invoice. \n \n '
                            'Thanks, \n Gram Factory',
    'ARS_MAIL_WAREHOUSE_SUBJECT': 'Summary of Auto PO’s approved and placed on {}',
    'ARS_MAIL_WAREHOUSE_BODY': 'PFA the list of Auto PO’s approved on {}. '
                               'Please note the delivery dates of the respective POs in the CSV attached. '
                               'The same details can also be checked by going to Home -> Gram_To_Brand -> PO Generation',
    "2001": "Ok",
    "2002": "Executive Feedback saved successfully.",
}

ERROR_MESSAGES = {
    'EMPTY': '%s can\'t be empty',
    'REQUIRED_BATCH_SKU': 'Missing sku/batch_id',
    'INVALID_AUDIT_STATE': "This audit is not in %s state.",
    'AUDIT_NOT_STARTED': "This audit is not in started state",
    "AUDIT_STARTED": "Audit already started.",
    'AUDIT_START_TIME_ERROR': "Audit Task can be initiated only after {} mins from Audit Creation time. Start Time: {}",
    'FAILED_STATE_CHANGE': "Audit state could not be changed",
    'AUDIT_END_FAILED': "Audit can be ended only when audit has been ended for all {}",
    'NO_RECORD': 'No %s record found',
    'SOME_ISSUE': 'There seems to be some issue.',
    'EXPIRED_NON_ZERO': 'For Future expiry date, the expired qty should be 0',
    'NORMAL_NON_ZERO': 'For Past expiry date, the normal and damaged qty should be 0',
    'BATCH_BIN_ISSUE': 'This batch {} is not found in this bin {}',
    'BIN_INACTIVE': 'This bin is inactive',
    'DIFF_BATCH_ONE_BIN': 'Quantity could not be updated as different expiry date product already present in this bin',
    'AUDIT_SKU_NOT_IN_SCOPE': "This sku is out of scope for this audit",
    'AUDIT_BIN_NOT_IN_SCOPE': "This bin is out of scope for this audit",
    'AVAILABLE_QUANTITY': 'Available Qty : {0}',
    'AVAILABLE_PRODUCT': 'Available No of Pieces : {0}',
    'INVALID_PRICE_UPLOAD': "You cannot upload Selling Price greater than MRP",
    'INVALID_SP_PRICE': "You cannot upload Service Partner Price greater than Super Retailer",
    'INVALID_SR_PRICE': "You cannot upload Super Retailer Price greater than Retailer",
    'INVALID_MAPPING': "Shop id- %s and employee no- %s , has duplicate entry",
    'PRODUCT_REMOVED': "Some products in cart aren’t available anymore, please update cart",
    'PICKUP_NOT_FOUND': "No Pickup found for this order",
    'PICKER_DASHBOARD_ENTRY_MISSING': "No Pickup Dashboard entry found",
    'PICK_BIN_DETAILS_NOT_FOUND': "No Pickup Details found for given input",
    'ORDER_CANCELLED': "Order no. {} is cancelled, kindly submit the picked item to QC head",
    "4001": "Selected records are exceeding system capacity, please keep max records at 50.",
    "4002": "Selected file status is QC pending, you can't download this file.",
    "4003": "Oops! Something went wrong, Please check the data of csv file.",
    "4004": "row number- %s data is already exists in the sheet.",
    "4005": "API request is not Authorized.",
    "4006": "%s value has an invalid date format. It must be in YYYY-MM-DD format.",
    "4007": "This User is not Authorized.",
    "4008": "beat_plan_date key is missing in param.",
    "4009": "Issue in Feedback value.",
    "4010": "Issue in DateField.",
    "4011": "Executive has already submitted the feedback for same date.",
    "4012": "Report param is missing.",
    "4013": "No Reports available for selected options.",
    "4014": "No Beat Plan available for selected date.",
    "4015": "No Shop associated with Sales Manager.",
    "4016": "No Executive associated with Sales Manager.",
    "4017": "Feedback Submission is allowed only for the Current Date.",
    "4018": "Request Param value is not correct, Please re-verify at your end.",
    "4019": "{} is not available for order at the moment, please try after some time.",
    "4020": "executive_id key is missing in params",
    "1001": "Selected records are exceeding system capacity, please keep max records at 50.",
    "1002": "Selected file status is QC pending, you can't download this file.",
    "1003": "More than 1 GRN selected. 1 GRN is allowed at a time to download Barcode"
}

NOTIFICATIONS = {
    "TRIP_START_MSG" : "Hi {}, Your order is out for delivery with {}({}). Total invoice value is {}.  Thanks, Team GramFactory"
}