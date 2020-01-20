import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from elasticsearch import Elasticsearch
# lazy_gettext wraps strings for translation, similar to _. This lazy version
# delays evaluation of string until used. This covers cases where the string is
# defined when application is starting.
from flask_babel import Babel, lazy_gettext as _l
from config import Config
from redis import Redis
import rq
'''
Declare extensions here.
'''
# Create the database instance that will represent the db to the app.
db = SQLAlchemy()
# The migration engine needs a copy of db too.
migrate = Migrate()
# Create the login state manager
login = LoginManager()
# Change the default message given by the Flask-Login extension when a user
# is redirected to it.
# To implement a feature where we can require a login, tell
# login what the view function name is.
login.login_view = 'auth.login'
login.login_message = _l('Please log in to access this page.')

# Create the mail instance
mail = Mail()
# Initialize the bootstrap extension, making available boostrap/base.html
bootstrap = Bootstrap()
# A Flask wrapper for Moment.js, which provides lot of datetime formatting and use.
moment = Moment()
# To get help with localization
babel = Babel()


# A factory pattern to create the application instance, which takes
# a Config option to make.
def create_app(config_class=Config):
    # Create an app object as an instance of Flask class.
    # __name__ is a special Python variable, set to the name of the module
    # in which it is invoked (in this case, app). Flask will use the location of the module
    # as a starting point when needing to load resources.
    # This is almost always the way to start.
    app = Flask(__name__)
    # Add config items to the Flask app object, which can be
    # accessed via a dictionary
    app.config.from_object(config_class)

    # Init the exensions here now that app is created
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    babel.init_app(app)

    # Register blueprints. Import directly above to avoid circular imports.
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    # URL prefix kinda like a namespace
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Elasticsearch isn't a Flask extension, so we can't create an
    # instance of it. Instead, create a new attribute (a little hacky)
    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None

    # Background tasks manager initialization. This is better than threads.
    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('microblog-tasks', connection=app.redis)

    # Register the API blueprint
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    if not app.debug and not app.testing:
        # Do email notifcaton of errors
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'],
                        app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'],
                subject='Microblog-Py Failure',
                credentials=auth,
                secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

        # Log file setup
        # This log option handles when they are printed to terminal,
        # like on Heroku
        if app.config['LOG_TO_STDOUT']:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            app.logger.addHandler(stream_handler)
        else:
            # Write logs to file on disk
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/microblog.log',
                                               maxBytes=10240,
                                               backupCount=10)
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
                ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

        app.logger.addHandler(logging.INFO)
        # app.logger.info('Microblog-Py startup')

    return app


# This is invoked for each request to select a language translation
@babel.localeselector
def get_local():
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])
    # Or force different language
    # return 'es'


# Import here to avoid circular imports between the app module.
# models: representations of the app database
from app import models