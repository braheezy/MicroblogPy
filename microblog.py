'''
Python script to define Flask application instance.
    Run the app:
        flask run
'''
from app import create_app, db, cli
from app.models import User, Post

app = create_app()
cli.register(app)
'''
'flask shell' can be used to launch a shell with the application
already imported, avoiding tedious retyping of 'import app'
when using the interpreter.
This decorator registers this function. When 'flask shell' is
run, it invokes this function and essentially imports
these items for use.
'''
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Post': Post,
        'Message': Message,
        'Notification': Notification
    }
