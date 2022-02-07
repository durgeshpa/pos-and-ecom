# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from ecom.utils import generate_ecom_order_csv_report
from pos.utils import (
    create_order_data_excel,
    create_order_return_excel,
    generate_prn_csv_report,
    generate_csv_payment_report,
    download_grn_cvs
)
from pos.views import (
    posinventorychange_data_excel,
)
from global_config.models import GlobalConfig
from retailer_to_sp.models import (
       Order
)
from pos.models import (
    RetailerOrderReturn,
    RetailerOrderedProduct,
    Payment,
    PosReturnGRNOrder,
    InventoryChangePos,
    PosGRNOrder
)

"""
         'EO': (generate_ecom_order_csv_report,
               Order),
        'BO': (create_order_data_excel,
               RetailerOrderedProduct),
        'SGR': (generate_prn_csv_report,
                PosReturnGRNOrder),
        'BR': (create_order_return_excel,
               RetailerOrderReturn),
        'BP': (generate_csv_payment_report,
               Payment),
        'IC': (posinventorychange_data_excel,
               InventoryChangePos),
        'SG': (download_grn_cvs,
               PosGRNOrder)
"""
def return_model_ref(key):
   models = {
      'EO': Order,
      'BO': RetailerOrderedProduct,
      'SGR': PosReturnGRNOrder,
      'BR': RetailerOrderReturn,
      'BP': Payment,
      'IC': InventoryChangePos,
      'SG': PosGRNOrder
   }
   return models.get(key)

def return_host_generator_function(key):

    operators = {
        'generate_ecom_order_csv_report': generate_ecom_order_csv_report,
        'create_order_data_excel': create_order_data_excel,
        'generate_prn_csv_report': generate_prn_csv_report,
        'create_order_return_excel': create_order_return_excel,
        'generate_csv_payment_report': generate_csv_payment_report,
        'posinventorychange_data_excel': posinventorychange_data_excel,
        'download_grn_cvs': download_grn_cvs
    }

    return operators.get(key)   
              
# def return_redash_query_no_and_key(key):

#     query_no_operator = GlobalConfig.objects.filter(key='redash_report_query_no_cred_map').last()
#     api_key_operator = GlobalConfig.objects.filter(key='redash_report_api_key_cred_map').last()
#     if not query_no_operator or not query_no_operator.value or not query_no_operator.value.get(key):
#        raise KeyError("Please add a query_number map with key ::: redash_report_query_no_cred_map :::")
#     if not api_key_operator or not api_key_operator.value or not api_key_operator.get(key):
#        raise KeyError("Please add a query_number map with key ::: redash_report_api_key_cred_map :::")
#     return query_no_operator.get(key), api_key_operator.get(key)


# def set_host_input_params(key, input_params, report_type, frequency=None, user=None):
#     params = {}
#     if key == 'EO':
#        params['ordered_cart__cart_type'] = 'ECOM'
#        params['seller_shop_id'] = input_params.get('shop')
#        # if not user.is_superuser:
#        #    params['seller_shop__pos_shop__user'] = user
#     if key == 'BO':
#        params['order__ordered_cart__cart_type'] = 'BASIC'
#        #params['order__seller_shop__pos_shop__status'] = True
#        params['order__seller_shop_id'] = input_params.get('shop')
#        # if not user.is_superuser:
#        #    params['order__seller_shop__pos_shop__user'] = user
#        if input_params.get('shop_type'):
#           params['order__seller_shop__shop_type__shop_sub_type__retailer_type_name'] = input_params.get('shop_type')
#     if key == 'BP':
#        params['order__seller_shop_id'] = input_params.get('shop')
#        if input_params.get('payment_type'):
#           params['payment_type__type'] = input_params.get('payment_type')
#     if report_type == 'AD':
#        params['created_at__date__gte'] = input_params.get('date_start')
#        if input_params.get('date_end'):
#           params['created_at__date__lte'] = input_params.get('date_end')
#     else:
#        if frequency == "Daily":
#           start = datetime.now() - timedelta(days=1)
#        elif frequency in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
#           start = datetime.now() - timedelta(days=7)
#        else:
#           start = datetime.now() - timedelta(days=30) 
#        params['created_at__date__gte'] = start.strftime("%Y-%m-%d")
#     return params

# def set_redash_input_params(key, input_params, user=None):
#     pass

def flat_to_nested_dict(dict, marker='.'):
    result = {}
    for key, val in dict.items():
        t = result
        prev = None
        for part in key.split(marker): # 1.2.3 | prev = 1, | t = {'1': {} } ;; prev = 2
            if prev is not None:
                t = t.setdefault(prev, {})
                #print('here', t, prev, result)
            prev = part
        else:
            t.setdefault(prev, val)
            #print(t)
    #print('last', t, result)
    return result