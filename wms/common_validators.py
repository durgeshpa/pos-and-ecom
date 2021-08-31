import logging
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from shops.models import Shop
from products.models import ParentProduct
from wms.models import Zone, WarehouseAssortment
logger = logging.getLogger(__name__)

User = get_user_model()


def validate_ledger_request(request):
    sku = request.GET.get('sku')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not sku:
        return {"error": "please select sku"}

    if not start_date:
        return {"error": "please select start_date"}

    if not end_date:
        return {"error": "please select end_date"}
    return {"data": {"sku": sku, "start_date": start_date, "end_date": end_date}}


def validate_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id)}


def validate_id_and_warehouse(queryset, id, warehouse):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id, warehouse=warehouse).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id, warehouse=warehouse)}


def validate_data_format(request):
    """ Validate shop data  """
    try:
        # data = json.loads(request.data["data"])
        data = request.data["data"]
    except Exception as e:
        return {'error': "Invalid Data Format", }

    return data


def get_validate_putaway_users(putaway_users):
    """
    validate ids that belong to a User model also
    checking putaway_user shouldn't repeat else through error
    """
    putaway_users_list = []
    putaway_users_obj = []
    for putaway_users_data in putaway_users:
        try:
            putaway_user = get_user_model().objects.get(
                id=int(putaway_users_data['id']))
            if not putaway_user.groups.filter(name='Putaway').exists():
                return {'error': '{} putaway_user does not have required permission.'.format(putaway_users_data['id'])}
        except Exception as e:
            logger.error(e)
            return {'error': '{} putaway_user not found'.format(putaway_users_data['id'])}
        putaway_users_obj.append(putaway_user)
        if putaway_user in putaway_users_list:
            return {'error': '{} do not repeat same putaway_user for one Zone'.format(putaway_user)}
        putaway_users_list.append(putaway_user)
    return {'putaway_users': putaway_users_obj}


def get_csv_file_data(csv_file, csv_file_headers):
    uploaded_data_by_user_list = []
    csv_dict = {}
    count = 0
    for row in csv_file:
        for ele in row:
            csv_dict[csv_file_headers[count]] = ele
            count += 1
        uploaded_data_by_user_list.append(csv_dict)
        csv_dict = {}
        count = 0
    return uploaded_data_by_user_list


def check_headers(csv_file_headers, required_header_list):
    for head in csv_file_headers:
        if not head in required_header_list:
            raise ValidationError((f"Invalid Header | {head} | Allowable headers for the upload "
                                   f"are: {required_header_list}"))


def get_validate_warehouse(warehouse_id):
    try:
        warehouse = Shop.objects.get(id=warehouse_id, shop_type__shop_type='sp')
    except Exception as e:
        return {'error': '{} warehouse not found'.format(warehouse_id)}
    return {'data': warehouse}


def check_warehouse_assortment_mandatory_columns(warehouse, uploaded_data_list, header_list, upload_type):
    """
        This method will check that Data uploaded by user is not empty for mandatory fields.
    """
    row_num = 1
    if upload_type == "warehouse_assortment":
        mandatory_columns = ['warehouse_id', 'product_id', 'zone_id']
        for ele in mandatory_columns:
            if ele not in header_list:
                raise ValidationError(
                    f"{mandatory_columns} are mandatory columns for 'Create Warehouse Assortment'")
        for row in uploaded_data_list:
            row_num += 1
            if 'warehouse_id' not in row.keys() or str(row['warehouse_id']).strip() == '':
                raise ValidationError(
                    f"Row {row_num} | 'warehouse_id can't be empty")
            if int(str(row['warehouse_id']).strip()) != warehouse.id:
                raise ValidationError(f"Row {row_num} | Please upload assortment for the selected warehouse.")

            if 'product_id' not in row.keys() or str(row['product_id']).strip() == '':
                raise ValidationError(
                    f"Row {row_num} | 'product_id' can't be empty")
            if not ParentProduct.objects.filter(id=int(str(row['product_id']).strip())).exists():
                raise ValidationError(f"Row {row_num} | {row['product_id']} | Product does not exist.")

            if 'zone_id' not in row.keys() or str(row['zone_id']).strip() == '':
                raise ValidationError(f"Row {row_num} | 'zone_id' can't be empty")
            if not Zone.objects.filter(id=int(str(row['zone_id']).strip()), warehouse=warehouse).exists():
                raise ValidationError(
                    f"Row {row_num} | {row['zone_id']} | Zone does not exist / not mapped to selected warehouse.")

            if WarehouseAssortment.objects.filter(warehouse=warehouse, product_id=int(str(row['product_id']).strip())) \
                    .exists():
                raise ValidationError(
                    f"Row {row_num} | Warehouse assortment already exist for selected 'warehouse', 'product'.")


def read_warehouse_assortment_file(warehouse, csv_file, upload_type):
    """
        Template Validation (Checking, whether the csv file uploaded by user is correct or not!)
    """
    csv_file_header_list = next(csv_file)  # headers of the uploaded csv file
    # Converting headers into lowercase
    csv_file_headers = [str(ele).split(' ')[0].strip().lower() for ele in csv_file_header_list]
    if upload_type == "warehouse_assortment":
        required_header_list = ['warehouse_id', 'warehouse', 'product_id', 'product', 'zone_id', 'zone_supervisor',
                                'zone_coordinator']

    check_headers(csv_file_headers, required_header_list)
    uploaded_data_by_user_list = get_csv_file_data(csv_file, csv_file_headers)
    # Checking, whether the user uploaded the data below the headings or not!
    if uploaded_data_by_user_list:
        check_warehouse_assortment_mandatory_columns(
            warehouse, uploaded_data_by_user_list, csv_file_headers, upload_type)
    else:
        raise ValidationError(
            "Please add some data below the headers to upload it!")

