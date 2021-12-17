import codecs
import csv
import decimal
import re

from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from products.models import Product


def check_mandatory_data(row, key_string, row_num):
    """
        Check Mandatory Fields from uploaded CSV for creating or updating Retailer Products
    """
    if key_string not in row.keys():
        raise ValidationError(_(f"Row {row_num} | Please provide {key_string}"))

    if key_string in row.keys():
        if row[key_string] == '':
            raise ValidationError(_(f"Row {row_num} | Please provide {key_string}"))


def read_file_to_convert_into_list(headers, reader):
    """
        Reading & validating File Uploaded by user
    """
    uploaded_data_by_user_list = []
    csv_dict = {}
    count = 0
    for id, row in enumerate(reader):
        for ele in row:
            csv_dict[headers[count]] = ele
            count += 1
        uploaded_data_by_user_list.append(csv_dict)
        csv_dict = {}
        count = 0
    return uploaded_data_by_user_list


def check_mandatory_data(row, key_string, row_num):
    """
            Check Mandatory Fields from uploaded CSV for creating or updating Retailer Products
        """
    if key_string not in row.keys():
        return {'status': False, 'msg': f"Row {row_num} | Please provide {key_string}"}

    if key_string in row.keys():
        if row[key_string] == '':
            return {'status': False, 'msg': f"Row {row_num} | Please provide {key_string}"}
    return {'status': True, 'msg': 'SUCCESS'}


def bulk_product_validation(products_csv, shop_id):
    RetailerProduct = apps.get_model('pos.RetailerProduct')
    MeasurementCategory = apps.get_model('pos.MeasurementCategory')
    MeasurementUnit = apps.get_model('pos.MeasurementUnit')

    validated_rows = []
    error_dict = {}
    reader = csv.reader(codecs.iterdecode(products_csv, 'utf-8', errors='ignore'))
    headers = next(reader, None)
    data_list = read_file_to_convert_into_list(headers, reader)
    for row_num, row in enumerate(data_list):
        row_num += 2
        error_msg = []
        resp_shop_id = check_mandatory_data(row, 'shop_id', row_num)
        if not resp_shop_id['status']:
            raise ValidationError(str(resp_shop_id['msg']))
        resp_product_name = check_mandatory_data(row, 'product_name', row_num)
        if not resp_product_name['status']:
            raise ValidationError(str(resp_product_name['msg']))
        resp_mrp = check_mandatory_data(row, 'mrp', row_num)
        if not resp_mrp['status']:
            raise ValidationError(str(resp_mrp['msg']))
        resp_selling_price = check_mandatory_data(row, 'selling_price', row_num)
        if not resp_selling_price['status']:
            raise ValidationError(str(resp_selling_price['msg']))
        resp_product_pack_type = check_mandatory_data(row, 'product_pack_type', row_num)
        if not resp_product_pack_type['status']:
            raise ValidationError(str(resp_product_pack_type['msg']))
        resp_available_for_online_orders = check_mandatory_data(row, 'available_for_online_orders', row_num)
        if not resp_available_for_online_orders['status']:
            raise ValidationError(str(resp_available_for_online_orders['msg']))
        resp_is_visible = check_mandatory_data(row, 'is_visible', row_num)
        if not resp_is_visible['status']:
            raise ValidationError(str(resp_is_visible['msg']))
        resp_initial_purchase_value = check_mandatory_data(row, 'initial_purchase_value', row_num)
        if not resp_initial_purchase_value['status']:
            raise ValidationError(str(resp_initial_purchase_value['msg']))

        if int(row["shop_id"]) != shop_id:
            error_msg.append(f"wrong shop_id {row['shop_id']}")

        if row["product_id"] != '':
            if not RetailerProduct.objects.filter(id=row["product_id"]).exists():
                error_msg.append(f"product_id {row['product_id']} does not exist")

        if not re.match("^\d+[.]?[\d]{0,2}$", str(row['mrp'])):
            error_msg.append(str("mrp can only be a numeric value."))

        if not re.match("^\d+[.]?[\d]{0,2}$", str(row['selling_price'])):
            error_msg.append(str("selling_price can only be a numeric value."))

        if decimal.Decimal(row['selling_price']) > decimal.Decimal(row['mrp']):
            error_msg.append(str(f"selling_price cannot be greater than mrp"))

        if 'linked_product_sku' in row.keys():
            if row['linked_product_sku'] != '':
                if not Product.objects.filter(product_sku=row['linked_product_sku']).exists():
                    error_msg.append(str(f"linked_product_sku {row['linked_product_sku']} does not exist"))

        # Check for discounted product
        if row.get('product_id') == '' and 'discounted_price' in row.keys() and not row.get('discounted_price') == '':
            error_msg.append(str(f"'Discounted Product cannot be created for new product Provide product Id"))

        if row.get('product_id') != '' and 'discounted_price' in row.keys() and row.get('discounted_price'):
            product = RetailerProduct.objects.filter(id=row["product_id"]).last()
            if product.sku_type == 4:
                error_msg.append("This product is already discounted")
            elif 'discounted_stock' not in row.keys() or not row['discounted_stock']:
                error_msg.append("Discounted stock is required to create discounted product")
            elif decimal.Decimal(row['discounted_price']) <= 0:
                error_msg.append("Discounted Price should be greater than 0")
            elif decimal.Decimal(row['discounted_price']) >= decimal.Decimal(row['selling_price']):
                error_msg.append("Discounted Price should be less than selling price")
            elif int(row['discounted_stock']) < 0:
                error_msg.append("Invalid discounted stock")

        if 'available_for_online_orders' in row.keys() and str(row['available_for_online_orders']).lower() not in \
                ['yes', 'no']:
            error_msg.append("Available for Online Orders should be Yes OR No")
        if 'available_for_online_orders' and str(row['available_for_online_orders']).lower() == 'yes':
            row['online_enabled'] = True
        else:
            row['online_enabled'] = False

        if 'is_visible' in row.keys() and str(row['is_visible']).lower() == 'yes':
            row['is_deleted'] = False
        else:
            row['is_deleted'] = True

        if 'online_order_price' in row.keys() and row['online_order_price'] and \
                decimal.Decimal(row['online_order_price']) > decimal.Decimal(row['mrp']):
            error_msg.append("Online Order Price should be equal to OR less than MRP")

        # if 'initial_purchase_value' in row.keys() and row['initial_purchase_value'] and \
        #         decimal.Decimal(row['initial_purchase_value']) > decimal.Decimal(row['selling_price']):
        #     error_msg.append("Initial Purchase Value should be equal to OR less than Selling Price")

        # Validate packaging type and measurement category
        if row['product_pack_type'].lower() not in ['loose', 'packet']:
            error_msg.append(str(f"Invalid product_pack_type. Options are 'packet' or 'loose'"))
        if row['product_pack_type'].lower() == 'loose':
            check_mandatory_data(row, 'measurement_category', row_num)
            try:
                measure_cat = MeasurementCategory.objects.get(category=row['measurement_category'])
                MeasurementUnit.objects.get(id=measure_cat.id)
            except:
                error_msg.append(str(f"Invalid measurement_category."))
            row['purchase_pack_size'] = 1

        if not str(row['purchase_pack_size']).isdigit():
            error_msg.append(str(f"Invalid purchase_pack_size."))

        # check for offer price
        if 'offer_price' in row.keys() and row['offer_price']:
            if decimal.Decimal(row['offer_price']) > decimal.Decimal(row['mrp']):
                error_msg.append("Offer Price should be equal to OR less than MRP")
            if not 'offer_start_date' in row.keys() or not row['offer_start_date']:
                error_msg.append("Offer Start Date is missing")
            if not 'offer_end_date' in row.keys() or not row['offer_end_date']:
                error_msg.append("Offer End Date is missing")
            if row['offer_start_date'] > row['offer_end_date']:
                error_msg.append("Offer start date should be less than offer end date")

        # Check if product with this ean code and mrp already exists
        if row.get('product_id') == '' and RetailerProduct.objects.filter(shop_id=row.get('shop_id'),
                                                                          product_ean_code=row.get('product_ean_code'),
                                                                          mrp=row.get('mrp'),
                                                                          is_deleted=False).exists():
            error_msg.append(str(f"product with ean code {row.get('product_ean_code')} "
                                 f"and mrp {row.get('mrp')} already exists"))

        if error_msg:
            msg = ", "
            msg = msg.join(map(str, error_msg))
            error_dict[str(row_num)] = msg
        else:
            validated_rows.append(row)

    return error_dict, validated_rows
