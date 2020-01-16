from flask import render_template
from app import db
from app.errors import bp


# This decorator allows us to register custom error pages with Flask
@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@bp.app_errorhandler(500)
def internal_error(error):
    '''
    500 errors could be a database error. To make sure any failed database sessions do not interfere with any database accesses triggered by the template, issue session rollback
    '''
    db.session.rollback()
    return render_template('errors/500.html'), 500