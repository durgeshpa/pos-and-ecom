from distutils.log import error
from sqlite3 import paramstyle


def validate_host_input_params(key, params, errors, report_type):
    if not params:
         errors['input_params'] = "input_params is required for report generation"
         return errors
    if key == 'EO':
       if not params.get('shop'):
          errors['shop'] = 'Shop Id is required for report generation'
    if key == 'BO':
       if not params.get('shop'):
          errors['shop'] = 'Shop Id is required for report generation'
    if key == 'BP':
       if not params.get('shop'):
          errors['shop'] = 'Shop Id is required for report generation'
       if not params.get('payment_type'):
          errors['payment_type'] = 'Payment Type is required for report generation'
    if report_type == 'AD':
      if not params.get('date_start'):
         errors['date_start'] = 'Start date is mandatory for report generation'
    return errors
    
def validate_redash_input_params(key, params, errors, report_type):
    if not params:
         errors['input_params'] = "input_params is required for report generation"
         return errors
    if key == 'EO':
       if not params.get('shop'):
          errors['shop'] = 'Shop Id is required for report generation'
    if key == 'BO':
       if not params.get('shop'):
          errors['shop'] = 'Shop Id is required for report generation'
    if key == 'BP':
       if not params.get('shop'):
          errors['shop'] = 'Shop Id is required for report generation'
    if report_type == 'AD':
      if not params.get('date_start'):
         errors['date_start'] = 'Start date is mandatory for report generation'
      if not params.get('date_end'):
         errors['date_end'] = 'End Date is mandatory for report generation'
    return errors