# -*- coding: utf-8 -*-
import random

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

def return_report_operators(key):

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
