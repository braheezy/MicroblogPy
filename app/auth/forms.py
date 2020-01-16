from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from flask_babel import _, lazy_gettext as _l
from app.models import User


class LoginForm(FlaskForm):
    # Create class variables for each field, providing a label and
    # optional validators, making sure field is not empty.
    # These Flask fields know how to render in HTML, making that
    # simpler.
    username = StringField(_l('Username'), validators=[DataRequired()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    remember_me = BooleanField(_l('Remember Me'))
    submit = SubmitField(_l('Sign In'))


class RegistrationForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    # Extra validator to ensure email is well-formed.
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    # Extra validator to ensure both passwords entered match.
    password2 = PasswordField(_l('Repeat Password'),
                              validators=[DataRequired(),
                                          EqualTo('password')])
    submit = SubmitField(_l('Register'))
    '''
    Custon validators that Flask WTForms will use, because they are
    named validate_*. These are invoked in addition to the stock validators above.
    '''

    # Make sure user doesn't already exist.
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError(_('Please use a different username.'))

    # Make sure email doesn't already exist.
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_('Please use a different email address.'))


# So users can request a new password
class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(_l('Request Password Reset'))


# Actually reset the password
class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(_l('Repeat Password'),
                              validators=[DataRequired(),
                                          EqualTo('password')])
    submit = SubmitField(_l('Request Password Reset'))