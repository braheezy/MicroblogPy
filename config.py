import os
from dotenv import load_dotenv

# Main directory of application.
basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv(os.path.join(basedir, '.env'))

# OP prefers this way of doing config. Keep in mind
# there are several ways to do config stuff, but
# maybe this works with Flask well.


class Config(object):
    # Prefer to get environment variables. This 'or' method
    # works even if the env var is set to empty string.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    # Set URI, the location of the app's database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    # Disable feature that signals application every time
    # a change is about to made to db.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # So we can get emails about errors during production
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    # This will encrypt messages.
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['michael.c.braha@gmail.com']

    # Control the pagination
    POSTS_PER_PAGE = 15

    # Supported languages
    LANGUAGES = ['en', 'es']

    # For dynamic translations, Microsoft API is used, which requires
    # Azure account.
    MS_TRANSLATOR_KEY = os.environ.get('MS_TRANSLATOR_KEY')

    # For sitewide searching of posts, use Elasticsearch from the
    # ELK stack
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')

    # In support of deployment to Heroku
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')

    # Background task manager. 2nd option assumes running on localhost
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'