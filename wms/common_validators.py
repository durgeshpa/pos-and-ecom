import logging
from datetime import datetime

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Subquery, OuterRef, Case, When, Q
from django.db.models.functions import Cast

from shops.models import Shop
from products.models import ParentProduct
from wms.models import Zone, WarehouseAssortment, Putaway, In, Crate, Pickup, QCArea

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


def get_validate_putaway_users(putaway_users, warehouse_id):
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
                return {'error': '{} putaway_user does not have required permission.'.format(str(putaway_user.id))}
            if putaway_user.shop_employee.last().shop_id != warehouse_id:
                return {'error': '{} putaway_user does not mapped to selected warehouse.'.format(str(putaway_user.id))}
        except Exception as e:
            logger.error(e)
            return {'error': '{} putaway_user not found'.format(putaway_users_data['id'])}
        putaway_users_obj.append(putaway_user)
        if putaway_user in putaway_users_list:
            return {'error': '{} do not repeat same putaway_user for one Zone'.format(putaway_user)}
        putaway_users_list.append(putaway_user)
    return {'putaway_users': putaway_users_obj}

def get_validate_picker_users(picker_users):
    """
    validate ids that belong to a User model also
    checking picker_user shouldn't repeat else through error
    """
    picker_users_list = []
    picker_users_obj = []
    for picker_users_data in picker_users:
        try:
            picker_user = get_user_model().objects.get(
                id=int(picker_users_data['id']))
            if not picker_user.groups.filter(name='Picker Boy').exists():
                return {'error': '{} picker_user does not have required permission.'.format(picker_users_data['id'])}
        except Exception as e:
            logger.error(e)
            return {'error': '{} picker_user not found'.format(picker_users_data['id'])}
        picker_users_obj.append(picker_user)
        if picker_user in picker_users_list:
            return {'error': '{} do not repeat same picker_user for one Zone'.format(picker_user)}
        picker_users_list.append(picker_user)
    return {'picker_users': picker_users_obj}


def get_validate_picker_users(picker_users, warehouse_id):
    """
    validate ids that belong to a User model also
    checking picker_user shouldn't repeat else through error
    """
    picker_users_list = []
    picker_users_obj = []
    for picker_users_data in picker_users:
        try:
            picker_user = get_user_model().objects.get(
                id=int(picker_users_data['id']))
            if not picker_user.groups.filter(name='Picker Boy').exists():
                return {'error': '{} picker_user does not have required permission.'.format(picker_users_data['id'])}
            if picker_user.shop_employee.last().shop_id != warehouse_id:
                return {'error': '{} picker_user does not mapped to selected warehouse.'.format(str(picker_user.id))}
        except Exception as e:
            logger.error(e)
            return {'error': '{} picker_user not found'.format(picker_users_data['id'])}
        picker_users_obj.append(picker_user)
        if picker_user in picker_users_list:
            return {'error': '{} do not repeat same picker_user for one Zone'.format(picker_user)}
        picker_users_list.append(picker_user)
    return {'picker_users': picker_users_obj}


def get_validate_qc_areas(qc_areas, warehouse_id):
    """
    validate ids that belong to a QCAres model also
    checking qc_area shouldn't repeat else through error
    """
    qc_areas_list = []
    qc_areas_obj = []
    for qc_areas_data in qc_areas:
        try:
            qc_area = QCArea.objects.get(id=int(qc_areas_data['id']))
            if qc_area.warehouse.id != warehouse_id:
                return {'error': '{} qc_area does not mapped to selected warehouse.'.format(str(qc_area.id))}
        except Exception as e:
            logger.error(e)
            return {'error': '{} qc_area not found'.format(qc_areas_data['id'])}
        qc_areas_obj.append(qc_area)
        if qc_area in qc_areas_list:
            return {'error': '{} do not repeat same qc_area for one QC Desk'.format(qc_area)}
        qc_areas_list.append(qc_area)
    return {'qc_areas': qc_areas_obj}


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
            if not ParentProduct.objects.filter(parent_id=str(row['product_id']).strip()).exists():
                raise ValidationError(f"Row {row_num} | {row['product_id']} | Product does not exist.")

            if 'zone_id' not in row.keys() or str(row['zone_id']).strip() == '':
                raise ValidationError(f"Row {row_num} | 'zone_id' can't be empty")
            if not Zone.objects.filter(id=int(str(row['zone_id']).strip()), warehouse=warehouse).exists():
                raise ValidationError(
                    f"Row {row_num} | {row['zone_id']} | Zone does not exist / not mapped to selected warehouse.")

            if WarehouseAssortment.objects.filter(
                    warehouse=warehouse, product=ParentProduct.objects.filter(
                        parent_id=str(row['product_id']).strip()).last()).exists():
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


def validate_putaways_by_token_id_and_zone(token_id, zone_id):
    """validation warehouse assortment for the selected warehouse and product"""
    putaways = Putaway.objects.filter(
        putaway_type__in=['GRN', 'RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING', 'picking_cancelled']). \
        annotate(token_id=Case(
                    When(putaway_type='GRN',
                         then=Cast(Subquery(In.objects.filter(
                             id=Cast(OuterRef('putaway_type_id'), models.IntegerField())).
                                            order_by('-in_type_id').values('in_type_id')[:1]), models.CharField())),
                    When(putaway_type='picking_cancelled',
                         then=Cast(Subquery(Pickup.objects.filter(
                             id=Cast(OuterRef('putaway_type_id'), models.IntegerField())).
                                            order_by('-pickup_type_id').
                                            values('pickup_type_id')[:1]), models.CharField())),
                    When(putaway_type__in=['RETURNED', 'CANCELLED', 'PAR_SHIPMENT', 'REPACKAGING'],
                         then=Cast('putaway_type_id', models.CharField())),
                    output_field=models.CharField(),
                )
                ). \
        filter(zone_id=zone_id, token_id=token_id, status__in=[Putaway.NEW, Putaway.ASSIGNED])
    if not putaways.exists():
        return {'error': 'please provide a valid Token Id / Zone Id.'}
    return {'data': putaways.all()}


def validate_grouped_request(request):
    data_days = request.GET.get('data_days')
    created_at = request.GET.get('created_at')

    if data_days and int(data_days) > 30:
        return {"error": "'data_days' can't be more than 30 days."}

    if created_at:
        try:
            if data_days:
                created_at = datetime.strptime(created_at, "%Y-%m-%d")
        except Exception as e:
            return {"error": "Invalid format | 'created_at' format should be YYYY-MM-DD."}

    return {"data": request}


def validate_putaway_user_by_zone(zone, putaway_user_id):
    zone_objs = Zone.objects.filter(id=zone, putaway_users__id=putaway_user_id)
    if zone_objs.exists():
        return {'data': User.objects.get(id=putaway_user_id)}
    return {'error': 'Invalid putaway user!'}


def validate_zone(zone):
    if Zone.objects.filter(id=zone).exists():
        return {'data': Zone.objects.filter(id=zone).last()}
    return {'error': 'Invalid zone!'}


def validate_putaway_user_against_putaway(putaway_id, user_id):
    """validating user against the putaway"""
    putaway = Putaway.objects.filter(id=putaway_id, putaway_user=user_id).last()
    if not putaway:
        return {'error': 'Putaway is not assigned to the logged in user.'}
    return {'data': putaway}


def validate_pickup_crates_list(crates_dict, pickup_quantity, warehouse_id, zone, order_no):
    if 'is_crate_applicable' not in crates_dict:
        return {"error": "Missing 'is_crate_applicable' in pickup_crates."}
    if crates_dict['is_crate_applicable'] is True:
        if 'crates' not in crates_dict or not crates_dict['crates']:
            return {"error": "Missing 'crates' in pickup_crates for 'is_crate_applicable' is True."}
        if not isinstance(crates_dict['crates'], list):
            return {"error": "Key 'crates' can be of list type only."}
        total_crate_qty = 0
        for crate_obj in crates_dict['crates']:
            if not isinstance(crate_obj, dict):
                return {"error": "Key 'crates' can be of list of object type only."}
            if 'crate_id' not in crate_obj or not crate_obj['crate_id']:
                return {"error": "Missing 'crate_id' in pickup_crates for 'is_crate_applicable' is True."}
            if 'quantity' not in crate_obj or not crate_obj['quantity']:
                return {"error": "Missing 'quantity' in pickup_crates for 'is_crate_applicable' is True."}
            if not Crate.objects.filter(crate_id=crate_obj['crate_id'], warehouse__id=warehouse_id,
                                        crate_type=Crate.PICKING, zone=zone).exists():
                return {"error": "Invalid crates selected in pickup_crates."}
            crate = Crate.objects.filter(crate_id=crate_obj['crate_id'], warehouse__id=warehouse_id,
                                        crate_type=Crate.PICKING, zone=zone).last()
            if crate.crates_pickup.filter(~Q(pickup__pickup_type_id=order_no), is_in_use=True).exists():
                return {"error" : f"Crate {crate_obj['crate_id']} is already being used for some other pickup"}
            total_crate_qty += int(crate_obj['quantity'])
        if total_crate_qty != pickup_quantity:
            return {"error": "Crates quantity should be matched with pickup quantity."}
    return {"data": crates_dict}


def validate_pickup_request(request):
    data_days = request.GET.get('data_days')
    created_at = request.GET.get('date')
    pickuptype = request.GET.get('type')

    if data_days and int(data_days) > 30:
        return {"error": "'data_days' can't be more than 30 days."}

    if created_at:
        try:
            created_at = datetime.strptime(created_at, "%Y-%m-%d")
            if created_at.date() > datetime.today().date():
                return {"error": "Invalid date | Picking date can not be greater than today."}

        except Exception as e:
            return {"error": "Invalid format | 'created_at' format should be YYYY-MM-DD."}
    else:
        return {"error": "Date | This is required."}


    if pickuptype and int(pickuptype) not in [1, 2]:
        return {"error": "'type' | This is invalid."}

    return {"data": request}


def validate_data_days_date_request(request):
    data_days = request.GET.get('data_days')
    date = request.GET.get('date', None)

    if not date:
        return {"error": "'date' | This is mandatory."}
    else:
        try:
            date = datetime.strptime(date, "%Y-%m-%d")
        except Exception as e:
            return {"error": "Invalid format | 'date' format should be YYYY-MM-DD."}

    if data_days and int(data_days) > 30:
        return {"error": "'data_days' can't be more than 30 days."}

    return {"data": request}

def validate_shipment(queryset, shipment_id):
    shipment = queryset.filter(id=shipment_id).last()
    if not shipment:
        return {"error": "Invalid shipment id"}
    return {"data": shipment}

def validate_shipment_qc_desk(queryset, shipment_id, user):
    shipment = queryset.filter(id=shipment_id).last()
    if not shipment:
        return {"error" : "Invalid shipment id"}

    if shipment.qc_area.qc_desk_areas.filter(desk_enabled=True, qc_executive=user).exists():
        return {"data": shipment}
    return {"error": 'Logged in user is not allowed to start QC for this shipment'}
