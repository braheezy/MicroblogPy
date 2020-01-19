from flask_mail import Message
from app import mail
from flask import current_app
from threading import Thread


# Use Python thread to send email in background thread.
def send_async_email(app, msg):
    # Usually, Flask manages context, meaning functions get access to certain
    # variables like current_user without being passed them. When custom Threads
    # are made, we need to manually make the context explicit. This with syntax
    # will clean everything up when msg is sent.
    with app.app_context():
        mail.send(msg)


# Sends an email to recipients.
def send_email(subject,
               sender,
               recipients,
               text_body,
               html_body,
               attachments=None,
               sync=False):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if attachments:
        for attachment in attachments:
            # In Python, using '*' let's us expand the collection as
            # args. Conveience.
            msg.attach(*attachment)
    # Send Ajax or not?
    if sync:
        mail.send(msg)
    else:
        # Shoot of send email Thread
        # Pass the actual instance and not the proxy object.
        # See: https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xv-a-better-application-structure
        Thread(target=send_async_email,
               args=(current_app._get_current_object(), msg)).start()
