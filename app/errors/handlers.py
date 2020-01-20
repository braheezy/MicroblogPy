from flask import render_template, request
from app import db
from app.errors import bp
from app.api.errors import error_response as api_error_response


# Use content neogation with clients to determine best format
# of error messages.
def wants_json_response():
    return request.accept_mimetypes['application/json'] >= \
        request.accept_mimetypes['text/html']


# This decorator allows us to register custom error pages with Flask
@bp.app_errorhandler(404)
def not_found_error(error):
    if wants_json_response():
        return api_error_response(404)
    return render_template('errors/404.html'), 404


@bp.app_errorhandler(500)
def internal_error(error):
    '''
    500 errors could be a database error. To make sure any failed database sessions do not interfere with any database accesses triggered by the template, issue session rollback
    '''
    db.session.rollback()
    if wants_json_response():
        return api_error_response(500)
    return render_template('errors/500.html'), 500