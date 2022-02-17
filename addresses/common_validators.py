import logging

from addresses.models import Route, City

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
