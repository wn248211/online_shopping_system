"""
SFU CMPT 756
Sample application---database service.
"""

# Standard library modules
import base64
import logging
import os
import sys
import urllib.parse
import uuid

# Installed packages

import boto3
from boto3.dynamodb.conditions import Key

from flask import Blueprint
from flask import Flask
from flask import request
from flask import Response

from prometheus_flask_exporter import PrometheusMetrics

import simplejson as json

# The application

app = Flask(__name__)

metrics = PrometheusMetrics(app)
metrics.info('app_info', 'Database process')

bp = Blueprint('app', __name__)

# default to us-east-1 if no region is specified
# (us-east-1 is the default/only supported region for a starter account)
region = os.getenv('AWS_REGION', 'us-east-1')

# these must be present; if they are missing, we should probably bail now
access_key = os.getenv('AWS_ACCESS_KEY_ID')
secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

# this is only needed for starter accounts
session_token = os.getenv('AWS_SESSION_TOKEN')

# Must be presented to authorize call to `/load`
loader_token = os.getenv('SVC_LOADER_TOKEN')

# if session_token is not present in the environment, assume it is a
# standard acct which doesn't need one; otherwise, add it on.
if not session_token:
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_access_key)
else:
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token)


# Change the implementation of this: you should probably have a separate
# driver class for interfacing with a db like dynamodb in a different file.
@bp.route('/update', methods=['PUT'])
def update():
    headers = request.headers
    # check header here
    content = request.get_json()
    objtype = urllib.parse.unquote_plus(request.args.get('objtype'))
    objkey = urllib.parse.unquote_plus(request.args.get('objkey'))
    table_name = objtype.capitalize()+"-TeamW"
    table_id = objtype + "_id"
    table = dynamodb.Table(table_name)
    expression = 'SET '
    x = 1
    attrvals = {}
    for k in content.keys():
        expression += k + ' = :val' + str(x) + ', '
        attrvals[':val' + str(x)] = content[k]
        x += 1
    expression = expression[:-2]
    response = table.update_item(Key={table_id: objkey},
                                 UpdateExpression=expression,
                                 ExpressionAttributeValues=attrvals)
    return response


@bp.route('/update_by_composite_key', methods=['PUT'])
def update_by_composite_key():
    headers = request.headers
    # check header here
    content = request.get_json()
    partition_key = urllib.parse.unquote_plus(
        request.args.get('partition_key'))
    partition_value = urllib.parse.unquote_plus(
        request.args.get('partition_value'))
    sort_key = urllib.parse.unquote_plus(request.args.get('sort_key'))
    sort_value = urllib.parse.unquote_plus(request.args.get('sort_value'))
    table_name = urllib.parse.unquote_plus(
        request.args.get('table_name')).capitalize()+"-TeamW"
    table = dynamodb.Table(table_name)
    expression = 'SET '
    x = 1
    attrnames = {}
    attrvals = {}
    for k in content.keys():
        expression += '#' + k + ' = :val' + str(x) + ', '
        attrnames['#'+k] = k
        attrvals[':val' + str(x)] = content[k]
        x += 1
    expression = expression[:-2]
    response = table.update_item(Key={partition_key: partition_value, sort_key: sort_value},
                                 UpdateExpression=expression,
                                 ExpressionAttributeNames=attrnames,
                                 ExpressionAttributeValues=attrvals)
    return response


@bp.route('/read', methods=['GET'])
def read():
    headers = request.headers
    # check header here
    objtype = urllib.parse.unquote_plus(request.args.get('objtype'))
    objkey = urllib.parse.unquote_plus(request.args.get('objkey'))
    table_name = objtype.capitalize()+"-TeamW"
    table_id = objtype + "_id"
    table = dynamodb.Table(table_name)
    response = table.query(Select='ALL_ATTRIBUTES',
                           KeyConditionExpression=Key(table_id).eq(objkey))
    return response


@bp.route('/read_by_composite_key', methods=['GET'])
def read_by_composite_key():
    headers = request.headers
    # check header here
    response = None
    table_name = urllib.parse.unquote_plus(
        request.args.get('table_name')).capitalize()+"-TeamW"
    table = dynamodb.Table(table_name)
    partition_key = urllib.parse.unquote_plus(
        request.args.get('partition_key'))
    partition_value = urllib.parse.unquote_plus(
        request.args.get('partition_value'))
    if request.args.get('sort_key') is None:
        response = table.query(Select='ALL_ATTRIBUTES',
                               KeyConditionExpression=Key(partition_key).eq(partition_value))
    else:
        sort_key = urllib.parse.unquote_plus(request.args.get('sort_key'))
        sort_value = urllib.parse.unquote_plus(request.args.get('sort_value'))
        response = table.query(Select='ALL_ATTRIBUTES',
                               KeyConditionExpression=Key(partition_key).eq(partition_value) & Key(sort_key).eq(sort_value))
    return response


@bp.route('/write', methods=['POST'])
def write():
    headers = request.headers
    # check header here
    content = request.get_json()
    table_name = content['objtype'].capitalize()+"-TeamW"
    objtype = content['objtype']
    table_id = objtype + "_id"
    payload = {table_id: str(uuid.uuid4())}
    del content['objtype']
    for k in content.keys():
        payload[k] = content[k]
    table = dynamodb.Table(table_name)
    response = table.put_item(Item=payload)
    returnval = ''
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        returnval = {"message": "fail"}
    return json.dumps(
        ({table_id: payload[table_id]}, returnval)['returnval' in globals()])


@bp.route('/write_by_composite_key', methods=['POST'])
def write_by_composite_key():
    headers = request.headers
    # check header here
    content = request.get_json()
    table_name = content['table_name'].capitalize()+"-TeamW"
    del content['table_name']
    table = dynamodb.Table(table_name)
    payload = {content['partition_key']: content['partition_value'],
               content['sort_key']: content['sort_value']}
    del content['partition_key']
    del content['partition_value']
    del content['sort_key']
    del content['sort_value']
    for k in content.keys():
        payload[k] = content[k]
    response = table.put_item(Item=payload)
    returnval = ''
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        returnval = {"message": "fail"}
    else:
        returnval = {"message": "ok"}
    return json.dumps(returnval)


def decode_auth_token(token):
    '''Given an auth token in Base64 encoding, return the original string'''
    return base64.standard_b64decode(token).decode()


def load_auth(headers):
    '''Return True if caller authorized to do a `/load` '''
    global loader_token
    if 'Authorization' not in headers:
        return False
    # Auth string is 'Basic ' concatenated with base64 encoding of uname:passwd
    auth_string = headers['Authorization'].split()[1]
    name, pwd = decode_auth_token(auth_string).split(':')
    if name != 'svc-loader' or pwd != loader_token:
        return False
    return True


@bp.route('/load', methods=['POST'])
def load():
    '''
    Load a value into the database

    This differs from write() in the following ways:
    1. The caller must specify the UUID in `content`. http_status_code
       400 is returned if this condition is not met.
    2. The caller must include an "Authorization" header accepted
       by load_auth(). A 401 status is returned for authorization failure.
    3. If the database returns a non-200 status code, this routine
       responds with an {http_status_code: status} object.

    This routine potentially could share a common subroutine with
    write() but the HTTP error processing in write() seems wrong
    so this routine has its own code.
    '''
    headers = request.headers
    if not load_auth(headers):
        return Response(
            json.dumps({"http_status_code": 401,
                        "reason": "Invalid authorization for /load"}),
            status=401,
            mimetype='application/json')

    content = request.get_json()
    if 'uuid' not in content:
        return json.dumps({"http_status_code": 400, "reason": 'Missing uuid'})
    table_name = content['objtype'].capitalize()+"-TeamW"
    objtype = content['objtype']
    table_id = objtype + "_id"
    payload = {table_id: content['uuid']}
    del content['objtype']
    del content['uuid']
    for k in content.keys():
        payload[k] = content[k]
    table = dynamodb.Table(table_name)
    response = table.put_item(Item=payload)
    status = response['ResponseMetadata']['HTTPStatusCode']
    if status != 200:
        return json.dumps({"http_status_code": status})
    return json.dumps({table_id: payload[table_id]})


@bp.route('/delete', methods=['DELETE'])
def delete():
    headers = request.headers
    # check header here
    objtype = urllib.parse.unquote_plus(request.args.get('objtype'))
    objkey = urllib.parse.unquote_plus(request.args.get('objkey'))
    table_name = objtype.capitalize()+"-TeamW"
    table_id = objtype + "_id"
    table = dynamodb.Table(table_name)
    response = table.delete_item(Key={table_id: objkey})
    return response


@bp.route('/delete_by_composite_key', methods=['DELETE'])
def delete_by_composite_key():
    headers = request.headers
    # check header here
    table_name = urllib.parse.unquote_plus(
        request.args.get('table_name')).capitalize()+"-TeamW"
    partition_key = urllib.parse.unquote_plus(
        request.args.get('partition_key'))
    partition_value = urllib.parse.unquote_plus(
        request.args.get('partition_value'))
    sort_key = urllib.parse.unquote_plus(
        request.args.get('sort_key'))
    sort_value = urllib.parse.unquote_plus(
        request.args.get('sort_value'))
    table = dynamodb.Table(table_name)
    response = table.delete_item(
        Key={partition_key: partition_value, sort_key: sort_value})
    return response


@bp.route('/health')
@metrics.do_not_track()
def health():
    return Response("", status=200, mimetype="application/json")


@bp.route('/readiness')
@metrics.do_not_track()
def readiness():
    return Response("", status=200, mimetype="application/json")


# All database calls will have this prefix.  Prometheus metric
# calls will not---they will have route '/metrics'.  This is
# the conventional organization.
app.register_blueprint(bp, url_prefix='/api/v1/datastore/')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error("missing port arg 1")
        sys.exit(-1)

    p = int(sys.argv[1])
    # Do not set debug=True---that will disable the Prometheus metrics
    app.run(host='0.0.0.0', port=p, threaded=True)
