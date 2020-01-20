import time, sys, json
from rq import get_current_job
from app import create_app, db
from app.models import Task
from flask import render_template
from app.models import User, Post, Task
from app.email import send_email

# Make app and its db and email sending available to background tasks.
# Pushing a context makes the application be the "current" application instance.
app = create_app()
app.app_context().push()


# So tasks can set its progress
def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.user.add_notification('task_progress', {
            'task_id': job.get_id(),
            'progress': progress
        })
        if progress >= 100:
            task.complete = True
        db.session.commit()


# Export JSON of all posts by the user, done on a background task.
def export_posts(user_id):
    # RQ is doing task, not Flask, so exceptions not handled gracefully.
    try:
        user = User.query.get(user_id)
        _set_task_progress(0)
        data = []
        i = 0
        total_posts = user.posts.count()
        for post in user.posts.order_by(Post.timestamp.asc()):
            # Create dict of post body and time, using ISO 8601.
            # 'Z' means UTC.
            data.append({
                'body': post.body,
                'timestamp': post.timestamp.isoformat() + 'Z'
            })
            # Sleep is really just to see progress.
            time.sleep(3)
            i += 1
            _set_task_progress(100 * i / total_posts)
        # Send user an email of results
        send_email('[Microblog] Your blog posts',
                   sender=app.config['ADMINS'][0],
                   recipients=[user.email],
                   text_body=render_template('email/export_posts.txt',
                                             user=user),
                   html_body=render_template('email/export_posts.html',
                                             user=user),
                   attachments=[('posts.json', 'application/json',
                                 json.dumps({'posts': data}, indent=4))],
                   sync=True)
    except:
        _set_task_progress(100)
        # Log stacktrace.
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())