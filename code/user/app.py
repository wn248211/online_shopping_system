
# Standard library modules
import logging
import sys
import time
import random

# Installed packages
from flask import Blueprint
from flask import Flask
from flask import request
from flask import Response

import jwt

from prometheus_flask_exporter import PrometheusMetrics

import requests

import simplejson as json

# The application

app = Flask(__name__)

metrics = PrometheusMetrics(app)
metrics.info('app_info', 'User process')

bp = Blueprint('app', __name__)

db = {
    "name": "http://cmpt756pj-db:5003/api/v1/datastore",
    "endpoint": [
        "read",
        "write",
        "delete",
        "update",
        "read_by_composite_key",
        "update_by_composite_key",
        "write_by_composite_key",
        "delete_by_composite_key"
    ]
}

item_svc = {
    "name": "http://cmpt756pj-item:5001/api/v1/item"
}

order_svc = {
    "name": "http://cmpt756pj-order:5002/api/v1/order"
}


@bp.route('/', methods=['GET'])
@metrics.do_not_track()
def hello_world():
    return ("If you are reading this in a browser, your service is "
            "operational. Switch to curl/Postman/etc to interact using the "
            "other HTTP verbs.")


@bp.route('/health')
@metrics.do_not_track()
def health():
    return Response("", status=200, mimetype="application/json")


@bp.route('/readiness')
@metrics.do_not_track()
def readiness():
    return Response("", status=200, mimetype="application/json")


@bp.route('/<user_id>', methods=['PUT'])
def update_user(user_id):
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}), status=401,
                        mimetype='application/json')
    try:
        content = request.get_json()
        email = content['email']
        address = content['address']
        username = content['username']
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][3]
    response = requests.put(
        url,
        params={"objtype": "user", "objkey": user_id},
        json={"email": email, "address": address, "username": username})
    return (response.json())


@bp.route('/', methods=['POST'])
def create_user():
    """
    Create a user.
    If a record already exists with the same address, username, and email,
    the old UUID is replaced with a new one.
    """
    try:
        content = request.get_json()
        email = content['email']
        address = content['address']
        username = content['username']
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][1]
    response = requests.post(
        url,
        json={"objtype": "user",
              "email": email,
              "address": address,
              "username": username})
    return (response.json())


@bp.route('/<user_id>', methods=['GET'])
def get_user(user_id):
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(
            json.dumps({"error": "missing auth"}),
            status=401,
            mimetype='application/json')
    payload = {"objtype": "user", "objkey": user_id}
    url = db['name'] + '/' + db['endpoint'][0]
    response = requests.get(url, params=payload)
    return (response.json())


@bp.route('/login', methods=['PUT'])
def login():
    try:
        content = request.get_json()
        uid = content['uid']
    except Exception:
        return json.dumps({"message": "error reading parameters"})
    url = db['name'] + '/' + db['endpoint'][0]
    response = requests.get(url, params={"objtype": "user", "objkey": uid})
    data = response.json()
    if len(data['Items']) > 0:
        encoded = jwt.encode({'user_id': uid, 'time': time.time()},
                             'secret',
                             algorithm='HS256')
    return encoded


@bp.route('/logoff', methods=['PUT'])
def logoff():
    try:
        content = request.get_json()
        _ = content['jwt']
    except Exception:
        return json.dumps({"message": "error reading parameters"})
    return {}


@bp.route('/<user_id>/cart', methods=['GET'])
def get_items_in_user_cart(user_id):
    """
    Lists all items of in the user's shorping cart
    """
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(
            json.dumps({"error": "missing auth"}),
            status=401,
            mimetype='application/json')
    # payload = {"objtype": "order", "objkey": user_id}
    payload = {"partition_key": "user_id", "partition_value": user_id,
               "table_name": "shopping-Cart"}
    url = db['name'] + '/' + db['endpoint'][4]
    response = requests.get(url, params=payload)
    return (response.json())


@bp.route('/<user_id>/cart/item/<item_id>', methods=['DELETE'])
def delete_item_from_user_cart(user_id, item_id):
    """
    Delete item from the user's shorping cart
    """
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(
            json.dumps({"error": "missing auth"}),
            status=401,
            mimetype='application/json')
    # payload = {"objtype": "order", "objkey": user_id}
    payload = {"partition_key": "user_id", "partition_value": user_id,
               "sort_key": "item_id", "sort_value": item_id, "table_name": "shopping-Cart"}
    url = db['name'] + '/' + db['endpoint'][7]
    response = requests.delete(url, params=payload)
    return (response.json())


@bp.route('/<user_id>/cart/item', methods=['POST'])
def insert_item_to_user_cart(user_id):
    """
    add one item to user cart.
    """
    try:
        content = request.get_json()
        item_id = content['item_id']
        quantity = content['quantity']
    except Exception:
        return json.dumps({"message": "error reading arguments"})

    url = db['name'] + '/' + db['endpoint'][6]
    response = requests.post(
        url,
        json={"table_name": "shopping-Cart",
              "partition_key": "user_id",
              "partition_value": user_id,
              "sort_key": "item_id",
              "sort_value": item_id,
              "quantity": quantity})
    return (response.json())


@bp.route('/<user_id>/cart/checkout', methods=['POST'])
def checkout_user_cart(user_id):
    """
    checkout user cart and create an order
    """
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}), status=401,
                        mimetype='application/json')

    items = get_items_in_user_cart(user_id).get("Items")
    if not items:
        return Response(json.dumps({"error": "checkout empty shopping cart"}),
                        status=400,
                        mimetype='application/json')
    price = 0
    for item in items:
        item_id = item["item_id"]
        get_item_url = item_svc['name']+'/' + item_id
        get_item_response = requests.get(get_item_url)
        item_price = get_item_response.json().get('Items')[0]['item_price']
        price += item_price

        payload = {"partition_key": "user_id", "partition_value": user_id,
                   "sort_key": "item_id", "sort_value": item_id, "table_name": "shopping-Cart"}
        url = db['name'] + '/' + db['endpoint'][7]
        response = requests.delete(url, params=payload)

    order_id = random.randint(1, sys.maxsize)
    create_order_url = order_svc['name'] + '/' + user_id + '/' + str(order_id)
    order_body = {"price": price, "items": items}
    order_response = requests.post(create_order_url, json=order_body, headers={
                                   'Authorization': headers['Authorization']})
    resp = order_response.json()
    resp["order_id"] = order_id
    return (resp)


# All database calls will have this prefix.  Prometheus metric
# calls will not---they will have route '/metrics'.  This is
# the conventional organization.
app.register_blueprint(bp, url_prefix='/api/v1/user/')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error("Usage: app.py <service-port>")
        sys.exit(-1)

    p = int(sys.argv[1])
    # Do not set debug=True---that will disable the Prometheus metrics
    app.run(host='0.0.0.0', port=p, threaded=True)
