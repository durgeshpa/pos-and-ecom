# -*- coding: utf-8 -*-
import random

from ecom.utils import generate_ecom_order_csv_report
from global_config.models import GlobalConfig
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

def return_host_report_operators(key):

    operators = {
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
    }

    return operators.get(key)

def return_redash_query_no_and_key(key):

    query_no_operator = GlobalConfig.objects.filter(key='redash_report_query_no_cred_map').last()
    api_key_operator = GlobalConfig.objects.filter(key='redash_report_api_key_cred_map').last()
    if not query_no_operator or not query_no_operator.value or not query_no_operator.value.get(key):
       raise KeyError("Please add a query_number map with key ::: redash_report_query_no_cred_map :::")
    if not api_key_operator or not api_key_operator.value or not api_key_operator.get(key):
       raise KeyError("Please add a query_number map with key ::: redash_report_api_key_cred_map :::")
    return query_no_operator.get(key), api_key_operator.get(key)
