from flask import request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Length
from flask_babel import _, lazy_gettext as _l
from app.models import User


# Allows the user to change their name and add an About Me text.
class EditProfileForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    # Length matches the space allocated in the database (see model).
    about_me = TextAreaField(_l('About me'),
                             validators=[Length(min=0, max=140)])
    submit = SubmitField(_l('Submit'))

    # When this form is first shown, get the original username.
    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError(_('Please use a different username.'))


# So users can submit new posts.
class PostForm(FlaskForm):
    post = TextAreaField(_l('Say something'),
                         validators=[DataRequired(),
                                     Length(min=1, max=140)])
    submit = SubmitField(_l('Submit'))


# To perform full natural language searching.
class SearchForm(FlaskForm):
    # Standard practice to use 'q' as the search term argument.
    # For forms with text field, the browser submits the form when
    # Enter is pressed, so no need for Submit button.
    q = StringField(_l('Search'), validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        # formdata determines where Flask-WTF gets form submissions.
        # default is request.form, which is used during POST request.
        # Search will use a GET request (meaning we set an URL). The args
        # for this are in the query string, accessible by request.args.
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        # CSRF protection is enabled by default, included via the
        # hidden_tag() construct. For clickable links, this needs to be
        # disabled.
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)