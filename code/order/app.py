"""
SFU CMPT 756 team w project
Sample application---order service.
"""

# Standard library modules
import logging
import sys
import time

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
metrics.info('app_info', 'Order process')

bp = Blueprint('app', __name__)

db = {
    "name": "http://cmpt756pj-db:5003/api/v1/datastore",
    # "name": "http://host.docker.internal:5003/api/v1/datastore",
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


@bp.route('/<user_id>/<order_id>', methods=['PUT'])
def update_order(user_id, order_id):
    """
    Update an order
    """
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}), status=401,
                        mimetype='application/json')
    try:
        content = request.get_json()
        content['updated_time'] = time.strftime("%m/%d/%Y %H:%M:%S", time.localtime()) 
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][5]
    try:
        response = requests.put(
            url,
            params={"partition_key": "user_id", "partition_value": user_id, "table_name": "order",
                    "sort_key": "order_id", "sort_value": order_id},
            json=content
        )
    except Exception as e:
        return {
            "error": e,
            "content": content
        }
    return (response.json())



@bp.route('/<user_id>/<order_id>', methods=['POST'])
def create_order(user_id, order_id):
    """
    Create an order.
    """
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}), status=401,
                        mimetype='application/json')
    try:
        content = request.get_json()
        content['created_time'] = time.strftime("%m/%d/%Y %H:%M:%S", time.localtime())
        content['updated_time'] = time.strftime("%m/%d/%Y %H:%M:%S", time.localtime())
        content['partition_key'] = 'user_id'
        content['partition_value'] = user_id
        content['sort_key'] = "order_id"
        content['sort_value'] = order_id
        content['table_name'] = "order"
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][6]
    try:
        response = requests.post(
            url,
            # params={"partition_key": "user_id", "partition_value": user_id, "table_name": "order", 
            #         "sort_key": "order_id", "sort_value": order_id},
            json=content)
    except Exception as e:
        return {
            "error": e,
            "content": content
        }
    return (response.json())


@bp.route('/<user_id>/<order_id>', methods=['DELETE'])
def delete_order(user_id, order_id):
    """
    Delete an order
    """
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}),
                        status=401,
                        mimetype='application/json')
    url = db['name'] + '/' + db['endpoint'][7]
    response = requests.delete(url,
                               params={"partition_key": "user_id", "partition_value": user_id, 
                                           "sort_key": "order_id", "sort_value": order_id,
                                           "table_name": "order"})
    return (response.json())


@bp.route('/<user_id>/<order_id>', methods=['GET'])
def get_order_by_id(user_id, order_id):
    """
    Get an order by order_id
    """
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(
            json.dumps({"error": "missing auth"}),
            status=401,
            mimetype='application/json')
    # payload = {"objtype": "order", "objkey": order_id}
    payload = {"partition_key": "user_id", "partition_value": user_id, 
                "sort_key": "order_id", "sort_value": order_id,
                "table_name": "order"}
    url = db['name'] + '/' + db['endpoint'][4]
    response = requests.get(url, params=payload)
    return (response.json())


@bp.route('/<user_id>', methods=['GET'])
def get_order(user_id):
    """
    Lists all orders of a user
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
                "table_name": "order"}
    url = db['name'] + '/' + db['endpoint'][4]
    response = requests.get(url, params=payload)
    return (response.json())


# All database calls will have this prefix.  Prometheus metric
# calls will not---they will have route '/metrics'.  This is
# the conventional organization.
app.register_blueprint(bp, url_prefix='/api/v1/order/')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error("Usage: app.py <service-port>")
        sys.exit(-1)

    p = int(sys.argv[1])
    # Do not set debug=True---that will disable the Prometheus metrics
    app.run(host='0.0.0.0', port=p, threaded=True)
