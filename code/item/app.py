"""
SFU CMPT 756
"""

# Standard library modules
import logging
import sys

# Installed packages
from flask import Blueprint
from flask import Flask
from flask import request
from flask import Response

from prometheus_flask_exporter import PrometheusMetrics

import requests

import simplejson as json

# The application

app = Flask(__name__)

metrics = PrometheusMetrics(app)
metrics.info('app_info', 'item process')

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
bp = Blueprint('app', __name__)


@bp.route('/health')
@metrics.do_not_track()
def health():
    return Response("", status=200, mimetype="application/json")


@bp.route('/readiness')
@metrics.do_not_track()
def readiness():
    return Response("", status=200, mimetype="application/json")


# @bp.route('/', methods=['GET'])
# def list_all():
#     headers = request.headers
#     # check header here
#     if 'Authorization' not in headers:
#         return Response(json.dumps({"error": "missing auth"}),
#                         status=401,
#                         mimetype='application/json')
#     # list all songs here
#     return {}


@bp.route('/<item_id>', methods=['GET'])
def get_item(item_id):
    headers = request.headers
    # check header here
    # if 'Authorization' not in headers:
    #     return Response(json.dumps({"error": "missing auth"}),
    #                     status=401,
    #                     mimetype='application/json')
    payload = {"objtype": "item", "objkey": item_id}
    url = db['name'] + '/' + db['endpoint'][0]
    response = requests.get(
        url,
        params=payload)
        # headers={'Authorization': headers['Authorization']})
    return (response.json())


@bp.route('/', methods=['POST'])
def create_item():
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}),
                        status=401,
                        mimetype='application/json')
    try:
        content = request.get_json()
        item_name = content['item_name']
        item_price = content['item_price']
        item_description = content['item_description']
        item_status = content['item_status']
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][1]
    response = requests.post(
        url,
        json={"objtype": "item", "item_name": item_name, "item_price": item_price, "item_description": item_description, "item_status": item_status},
        headers={'Authorization': headers['Authorization']})
    return (response.json())


@bp.route('/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}),
                        status=401,
                        mimetype='application/json')
    url = db['name'] + '/' + db['endpoint'][2]
    response = requests.delete(
        url,
        params={"objtype": "item", "objkey": item_id},
        headers={'Authorization': headers['Authorization']})
    return (response.json())

@bp.route('/<item_id>', methods=['PUT'])
def update_item(item_id):
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}), status=401,
                        mimetype='application/json')
    try:
        content = request.get_json()
        item_name = content['item_name']
        item_price = content['item_price']
        item_description = content['item_description']
        item_status = content['item_status']
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][3]
    response = requests.put(
        url,
        params={"objtype": "item", "objkey": item_id},
        json={"item_name": item_name, "item_price": item_price, "item_description": item_description, "item_status": item_status})
    return (response.json())


# All database calls will have this prefix.  Prometheus metric
# calls will not---they will have route '/metrics'.  This is
# the conventional organization.
app.register_blueprint(bp, url_prefix='/api/v1/item/')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error("missing port arg 1")
        sys.exit(-1)

    p = int(sys.argv[1])
    # Do not set debug=True---that will disable the Prometheus metrics
    app.run(host='0.0.0.0', port=p, threaded=True)
