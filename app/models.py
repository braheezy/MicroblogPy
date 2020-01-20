from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from time import time
import jwt
import json
from flask import current_app, url_for
from hashlib import md5
# A 'mixin' class the contains generic implementations that usually
# work as is. Note the Flask-Login ext requires certain properties
# and methods to be implemented.
from flask_login import UserMixin
from app.search import add_to_index, remove_from_index, query_index
# Background tasking.
import redis
import rq
# To support API tokens
import base64
import os


class SearchableMixin(object):
    '''
    Custon mixin class to introduce search features to the models below.
    '''
    # Class methods means we can call the function without a class instance.
    # For example, once this mixin is added to Post, we can do Post.search().
    @classmethod
    def search(cls, expression, page, per_page):
        '''
        Replace the list of object IDs with actual objects.
        '''
        # __tablename__ is an SQLAlchemy attribute, which we use as an index.
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        # Collect list of tuples.
        for i in range(len(ids)):
            when.append((ids[i], i))
        # This query uses the list of IDs above to find the objects in the
        # database. The CASE part means we get the results in the order the
        # IDs are given. This is different than results from elasticsearch
        # above, which has results sorted from most to least relevant.
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        '''
        Called when the before_commit event is emitted by SQLAlchemy.
        '''
        # Save these changes in the db session while the session is still
        # open. Otherwise, we don't have access.
        session._changes = {
            'add': list(session.new),
            # Modified items are dirty.
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        '''
        Called when the after_commit event is emitted by SQLAlchemy.
        Session was committed, so make similar changes to Elasticsearch to keep them in sync.
        '''
        # Use the session changes recorded during before_commit()
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        ''' Helper method to refresh data from relational DB to search index.
        '''
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


class PaginatiedAPIMixin(object):
    '''
    Imbue the ability to paginate API results.
    '''
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        '''Create a dict of user collection representations.
        '''
        resources = query.paginate(page, per_page, False)
        data = {
            'items': [item.to_dict() for item in resources.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': resources.pages,
                'total_items': resources.total
            },
            '_links': {
                'self':
                url_for(endpoint, page=page, per_page=per_page, **kwargs),
                'next':
                url_for(endpoint, page=page + 1, per_page=per_page, **kwargs)
                if resources.has_next else None,
                'prev':
                url_for(endpoint, page=page - 1, per_page=per_page, **kwargs)
                if resources.has_prev else None
            }
        }


# Bind event handlers to our custom functions.
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)
'''
Under the Object Relational Manager (ORM) paradigm, relational
databases (i.e. those typically mangaged by SQL) can be managed by classes, objects, and methods instead of tables and SQL.
 translates between high-level operations and database commands.
'''
'''
This is an association table, used to represent many-to-many 
relationships. It uses two foreign keys.
For us, followers has a many-to-many relationship between
users and users, so it's called self-referential.

No model class is made because it doesn't actually hold data, only
foreign keys.
'''
followers = db.Table(
    'followers', db.Column('follower_id', db.Integer,
                           db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id')))


# Classes define the structure (or schema) for this app.
# Note the addition of th mixin, adding generic code.
class User(PaginatiedAPIMixin, UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    # Not an actual field, but defines a relationship.
    # \param: First arg is class of DB model that is the 'many' of this
    # one-to-many relationship.
    # \param: backref - name of field added to 'many' class that points
    # back to this one.
    # \param: lazy - defines how DB will query for the relationship.
    posts = db.relationship('Post', backref='author', lazy='dynamic')

    # Use the association table above to declare the many-many relation
    # See this for all the details: https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-viii-followers
    followed = db.relationship('User',
                               secondary=followers,
                               primaryjoin=(followers.c.follower_id == id),
                               secondaryjoin=(followers.c.followed_id == id),
                               backref=db.backref('followers', lazy='dynamic'),
                               lazy='dynamic')
    '''
    Private Message support
    '''
    messages_sent = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='author',
                                    lazy='dynamic')
    messages_received = db.relationship('Message',
                                        foreign_keys='Message.recipient_id',
                                        backref='recipient',
                                        lazy='dynamic')
    # Notifications relationship
    notifications = db.relationship('Notification',
                                    backref='user',
                                    lazy='dynamic')
    # A user tracks the background tasks it spawns
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    # API token support.
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)

    # The Werkzeug package comes with Flask and provides some
    # crypto functions, like those used below.
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Gravatar provides an easy API to obtain unique avatars based
    # on the hash of an email.
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    # For followers. Good to put actions here on the model instead of on the view function
    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    # A single db query to get all the posts of all followed users and sort it
    # by data. With thousands of posts and followed users, this could be
    # expensive to do on the application. So have the db do it.
    # Details: https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-viii-followers
    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    # Use JWT tokens to verify password requets links.
    def get_reset_password_token(self, expires_in=600):
        # arg1 = payload. A dict of the ID of who is resetting password and
        #       and expriraiton time of token
        # arg2 = key to encrypt with
        # arg3 = crytpo algo to use
        # return = a string, more useful than the bytes encode() returns.
        return jwt.encode(
            {
                'reset_password': self.id,
                'exp': time() + expires_in
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256').decode('utf-8')

    # Verify the link, which includes the JWT, is valid. If so, parse from the
    # payload the user ID.
    # staticmethods can be invoked directly from class, no instance needed
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token,
                            current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    # Private message stuff
    last_message_read_time = db.Column(db.DateTime)

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(
            Message.timestamp > last_read_time).count()

    # Helper to work with notification objects easier.
    # Actions that change the message count should use this. The unread_message_count
    # is the name of the notif.
    def add_notification(self, name, data):
        # if notif already exists, delete it.
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    '''
    Helpers to make access to background jobs easier.
    '''
    def launch_task(self, name, description, *args, **kwargs):
        ''' Add task to queue and database. '''
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id,
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(),
                    name=name,
                    description=description,
                    user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self,
                                    complete=False).first()

    # API support. Note of this representation of Users is different
    # than what's in the database.
    def to_dict(self, include_email=False):
        '''Create dict of API data from a User object.
        '''
        data = {
            'id': self.id,
            'username': self.username,
            'last_seen': self.last_seen.isoformat() + 'Z',
            'about_me': self.about_me,
            'post_count': self.posts.count(),
            'follower_count': self.followers.count(),
            'followed_count': self.followed.count(),
            '_links': {
                'self': url_for('api.get_user', id=self.id),
                'followers': url_for('api.get_followers', id=self.id),
                'followed': url_for('api.get_followed', id=self.id),
                'avatar': self.avatar(128)
            }
        }
        # Only include email of user requesting info.
        if include_email:
            data['email'] = self.email
        return data

    # Need to parse request into User object.
    def from_dict(self, data, new_user=False):
        # Loop over any field this client can use.
        for field in ['username', 'email', 'about_me']:
            if field in data:
                setattr(self, field, data[field])
        if new_user and 'password' in data:
            self.set_password(data['password'])

    # API token support.
    # User signs in, gets token with expiration time.
    def get_token(self, expires_in=3600):
        '''Generate token by using random string encoded in base64.
        '''
        now = datetime.utcnow()
        # If user's current token still has more than a minute left, don't
        # create a new token.
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token

    def revoke_token(self):
        '''Kill token by setting expiration time to 1 second.
        Good practice to have a way to kill a token.
        '''
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None
        return user

    # __repr__ tells Python how to print objects of this class
    def __repr__(self):
        return f'<User {self.username}>'


'''
Flask-Login uses a unique ID to track users and their sessions. To help the extension, a user loader func is required that will get User info from the db.
'''
@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Post(SearchableMixin, db.Model):
    # This class attribute helps us abstractify full site searching
    # This attr lists the fields that need to be included in the indexing.
    __searchable__ = ['body']

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    # Shows how to use a function to set the value
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # Shows using a foreign key and how to reference the original table.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # To support dynamic translations of posts, record the language
    # when the post is made.
    language = db.Column(db.String(5))

    def __repr__(self):
        return f'<Post {self.body}>'


# To represent private messages to other users
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return f'<Message {self.body}>'


# To represent notifications
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    # Payload different for different notifcation types, so use JSON.
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))


# Need to represent background tasks in database because otherwise, our app
# has no way to react based on task status.
class Task(db.Model):
    # Use name generated by rq as id.
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    # User-friendly description of task
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100
