'''
To simplify client-server interactions when authenticating tokens,
Flask-HTTPAuth is used.

This uses HTTP Basic Authentication to send user credentionals in a
standard Authorization HTTP Header.

To integrate this extension, app needs to provide 2 functions:
    1. Define logic to check UN/PW provided by user
    2. Return error if auth fails.
'''
from flask import g
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from app.models import User
from app.api.errors import error_response

basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()


# Verify user so they can get a token.
@basic_auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return False
    # Save user to g to access in API view functions.
    g.current_user = user
    return user.check_password(password)


@basic_auth.error_handler
def basic_auth_error():
    # 401 is HTTP Unauthorized error.
    return error_response(401)


# Verify a token is valid. To be used by endpoints.
@token_auth.verify_token
def verify_token(token):
    g.current_user = User.check_token(token) if token else None
    return g.current_user is not None


@token_auth.error_handler
def token_auth_error():
    return error_response(401)