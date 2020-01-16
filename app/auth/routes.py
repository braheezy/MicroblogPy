from flask import render_template, redirect, url_for, flash, request
from werkzeug.urls import url_parse
from flask_login import login_user, logout_user, current_user
from flask_babel import _
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app.models import User
from app.auth.email import send_password_reset_email


# The methods argument allows access to GET and POST (default is GET only). Need this because we submit via POST in forms.html
@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Use flask_login logic for redirection if needed. User shouldn't
    # see login screen if they are already in.
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        # Get User data from db
        user = User.query.filter_by(username=form.username.data).first()
        # Are they a legit user?
        if user is None or not user.check_password(form.password.data):
            flash(_('Invalid username or password'))
            return redirect(url_for('auth.login'))
        # User checks out. Log them in. This is from flask-login,
        # which sets some variables it uses to track login state.
        login_user(user, remember=form.remember_me.data)
        # User may have been redirected here. We should return
        # them back to the page they were on.
        # Use requests to get args from client request, which will
        # include the page to go back to.
        next_page = request.args.get('next')
        # The second condition protects against full URLs used
        # as 'next', probably inserted by an attacker.
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        # redirect tells browser to navigate to given page
        return redirect(next_page)
    return render_template('auth/login.html', title=_('Sign In'), form=form)


# Another page for logout.
@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


# Register a new user
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('Congratulations, you are now a registered user!'))
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html',
                           title=_('Register'),
                           form=form)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    # If already logged in, they didn't forget their password.
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        # Always flash this, preventing clients from figuring out
        # which emails are registered and which aren't.
        flash(_('Check your email for instructions to reset your password'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title=_('Reset Password'),
                           form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    # Get user identity from a valid token
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Your password has been reset.'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
