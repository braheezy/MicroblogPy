from app.api import bp
from flask import jsonify
from app.models import User
from app import db
from app.api.errors import bad_request


@bp.route('/users/<int:id>', methods=['GET'])
@token_auth.login_required
def get_user(id):
    '''Retrieve a single user.'''
    return jsonify(User.query.get_or_404(id).to_dict())


@bp.route('/users', methods=['GET'])
@token_auth.login_required
def get_users():
    '''Get a collection of all users.'''
    page = request.args.get('page', 1, type=int)
    # Control the max access for performance reasons.
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    data = User.to_collection_dict(User.query, page, per_page, 'api.get_users')
    return jsonify(data)


@bp.route('/users/<int:id>/followers', methods=['GET'])
@token_auth.login_required
def get_followers(id):
    '''Get a collection of all followers.'''
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    # Control the max access for performance reasons.
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    data = User.to_collection_dict(user.followers,
                                   page,
                                   per_page,
                                   'api.get_followers',
                                   id=id)
    return jsonify(data)


@bp.route('/users/<int:id>/followed', methods=['GET'])
@token_auth.login_required
def get_followed(id):
    '''Get a collection of those followed.'''
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    # Control the max access for performance reasons.
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    data = User.to_collection_dict(user.followed,
                                   page,
                                   per_page,
                                   'api.get_followed',
                                   id=id)
    return jsonify(data)


@bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json() or {}

    # Verify sign up credentials.
    if 'username' not in data or 'email' not in data or 'password' not in data:
        return bad_request('must include username, email, and password fields')
    if User.query.filter_by(username=data['username']).first():
        return bad_request('please use a different username')
    if User.query.filter_by(email=data['email']).first():
        return bad_request('please use a different email address')

    # Make the new user and commit to database.
    user = User()
    user.from_dict(data, new_user=True)
    db.session.add(user)
    db.session.commit()

    # Format and return response.
    response = jsonify(user.to_dict())
    response.status_code = 201
    # HTTP protocol requires that a 201 response includes a Location
    # header that is set to the URL of the new resource.
    response.headers['Location'] = url_for('api.get_user', id=user.id)
    return response


# PUT HTTP method lets you edit an existing resource.
@bp.route('/users/<int:id>', methods=['PUT'])
@token_auth.login_required
def update_user(id):
    '''Update information of user.
    Ex: http://localhost:5000/api/users/2 "about_me=Something cool"
    '''
    # Don't let users modify other users.
    if g.current_user.id != id:
        abort(403)
    user = User.query.get_or_404(id)
    data = request.get_json() or {}

    # Verify user credentials.
    if 'username' in data and data['username'] != user.username and \
        User.query.filter_by(username=data['username']).first():
        return bad_request('please use a different username')
    if 'email' in data and data['email'] != user.email and \
        User.query.filter_by(email=data['email']).first():
        return bad_request('please use a different email address')

    # Grab the user data, which has the changed information.
    user.from_dict(data, new_user=False)
    db.session.commit()
    return jsonify(user.to_dict())
