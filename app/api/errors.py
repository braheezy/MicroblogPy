from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES


def error_response(status_code, message=None):
    '''Create JSON error payload, using standard HTTP errors.
    '''
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message
    response = jsonify(payload)
    response.status_code = status_code
    return response


def bad_request(message):
    '''Specifically for the most popular error, 400 'bad request'
    '''
    return error_response(400, message)