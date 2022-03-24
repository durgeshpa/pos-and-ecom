import logging

from django.core.exceptions import ValidationError

from addresses.models import Route, City
from shops.models import Shop

logger = logging.getLogger(__name__)


def validate_data_dict_format(request):
    """ Validate dict data format """
    try:
        # data = json.loads(request.data["data"])
        data = request.data["data"]
        if not isinstance(data, dict):
            return {'error': 'Format of data is expected to be a dict.'}
    except Exception as e:
        return {'error': "Invalid Data Format", }

    return data


def validate_data_list_format(request):
    """ Validate list data format """
    try:
        data = request.data["data"]
        if not isinstance(data, list):
            return {'error': 'Format of data is expected to be a list.'}
    except:
        return {'error': "Invalid Data Format"}
    return {'data': data}


def validate_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id)}


def get_validate_routes(city_routes):
    """
    validate city routes that belong to a Route model also
    checking route shouldn't repeat else through error
    """
    # Validate mandatory fields
    if 'city_id' not in city_routes or not city_routes['city_id']:
        return {'error': "'city_id': This is mandatory."}
    if 'routes' not in city_routes or not city_routes['routes']:
        return {'error': "'routes': This is mandatory."}

    city = City.objects.filter(id=city_routes['city_id']).last()
    if not city:
        return {'error': f"'city_id' | Invalid city {city_routes['city_id']}"}

    if not isinstance(city_routes['routes'], list):
        return {"error": "Key 'routes' can be of list type only."}

    route_update_ids = []

    route_names_list = []
    routes_obj = []
    for route in city_routes['routes']:
        if not isinstance(route, dict):
            return {"error": "Key 'routes' can be of list of object type only."}

        if 'name' not in route or not route['name']:
            return {'error': "'name': This is mandatory for every route."}

        if 'id' in route and route['id']:
            try:
                route_instance = Route.objects.get(id=int(route['id']))
                if route_instance.city != city:
                    return {'error': f"'id' | Invalid route {route_instance.name} for {city}."}
                route_update_ids.append(route_instance.id)
            except:
                return {'error': f"'id' | Invalid route id {route['id']}"}
        else:
            if Route.objects.filter(city=city, name=route['name']).exists():
                return {'error': f"'name' | Route {route['name']} already mapped with {city}."}
            route['id'] = None

        route['city'] = city_routes['city_id']

        routes_obj.append(route)
        if route['name'] in route_names_list:
            return {'error': f"{route['name']} do not repeat same route for one City."}
        route_names_list.append(route['name'])
    return {'data': {"routes": routes_obj, "route_update_ids": route_update_ids}}


def get_validate_city_routes(city_routes, city):
    """
    validate city routes that belong to a Route model also
    checking route shouldn't repeat else through error
    """
    if not isinstance(city_routes, list):
        return {"error": "Key 'routes' can be of list type only."}

    route_update_ids = []

    route_names_list = []
    routes_obj = []
    for route in city_routes:
        if not isinstance(route, dict):
            return {"error": "Key 'routes' can be of list of object type only."}

        if 'name' not in route or not route['name']:
            return {'error': "'name': This is mandatory for every route."}

        if 'id' in route and route['id']:
            try:
                route_instance = Route.objects.get(id=int(route['id']))
                if route_instance.city != city:
                    return {'error': f"'id' | Invalid route {route_instance.name} for {city}."}
                route_update_ids.append(route_instance.id)
            except:
                return {'error': f"'id' | Invalid route id {route['id']}"}
        else:
            if Route.objects.filter(city=city, name=route['name']).exists():
                return {'error': f"'name' | Route {route['name']} already mapped with {city}."}
            route['id'] = None

        routes_obj.append(route)
        if route['name'] in route_names_list:
            return {'error': f"{route['name']} do not repeat same route for one City."}
        route_names_list.append(route['name'])
    return {'data': {"routes": routes_obj, "route_update_ids": route_update_ids}}


def get_validate_routes_mandatory_fields(routes):
    """
    validate city routes that belong to a Route model also
    checking route shouldn't repeat else through error
    """
    if not isinstance(routes, list):
        return {"error": "Key 'routes' can be of list type only."}

    route_names_list = []
    routes_obj = []
    for route in routes:
        if not isinstance(route, dict):
            return {"error": "Key 'routes' can be of list of object type only."}

        if 'name' not in route or not route['name']:
            return {'error': "'name': This is mandatory for every route."}

        routes_obj.append(route)
        if route['name'] in route_names_list:
            return {'error': f"{route['name']} do not repeat same route for one City."}
        route_names_list.append(route['name'])
    return {'data': {"routes": routes_obj}}


def check_headers(csv_file_headers, required_header_list):
    for head in csv_file_headers:
        if not head in required_header_list:
            raise ValidationError((f"Invalid Header | {head} | Allowable headers for the upload "
                                   f"are: {required_header_list}"))


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


def check_shop_route_mandatory_columns(uploaded_data_list, header_list):
    """
        This method will check that Data uploaded by user is not empty for mandatory fields.
    """
    row_num = 1
    mandatory_columns = ["shop_id", "city_id", "route_id"]
    for ele in mandatory_columns:
        if ele not in header_list:
            raise ValidationError(
                f"{mandatory_columns} are mandatory columns for 'Create Shop Route'")
    for row in uploaded_data_list:
        row_num += 1
        if 'shop_id' not in row.keys() or str(row['shop_id']).strip() == '':
            raise ValidationError(
                f"Row {row_num} | 'shop_id can't be empty")
        if not Shop.objects.filter(id=int(str(row['shop_id']).strip())).exists():
            raise ValidationError(f"Row {row_num} | Shop does not exist.")

        if 'city_id' not in row.keys() or str(row['city_id']).strip() == '':
            raise ValidationError(f"Row {row_num} | 'city_id' can't be empty")
        if not City.objects.filter(id=int(str(row['city_id']).strip())).exists():
            raise ValidationError(f"Row {row_num} | {row['city_id']} | City does not exist.")

        if 'route_id' not in row.keys() or str(row['route_id']).strip() == '':
            raise ValidationError(f"Row {row_num} | 'route_id' can't be empty")
        if not Route.objects.filter(id=str(row['route_id'].strip()), city_id=int(str(row['city_id']).strip())).exists():
            raise ValidationError(f"Row {row_num} | {row['route_id']} | Route does not exist.")


def read_shop_route_file(csv_file):
    """
        Template Validation (Checking, whether the csv file uploaded by user is correct or not!)
    """
    csv_file_header_list = next(csv_file)  # headers of the uploaded csv file
    # Converting headers into lowercase
    csv_file_headers = [str(ele).split(' ')[0].strip().lower() for ele in csv_file_header_list]
    required_header_list = ["shop_id", "shop_name", "city_id", "city_name", "route_id", "route"]

    check_headers(csv_file_headers, required_header_list)
    uploaded_data_by_user_list = get_csv_file_data(csv_file, csv_file_headers)
    # Checking, whether the user uploaded the data below the headings or not!
    if uploaded_data_by_user_list:
        check_shop_route_mandatory_columns(uploaded_data_by_user_list, csv_file_headers)
    else:
        raise ValidationError(
            "Please add some data below the headers to upload it!")
