import eventlet
eventlet.monkey_patch()

import os
from app import create_app, db
from app.models import Admin, Post, SiteConfig
from app.__init__ import socketio

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Admin=Admin, Post=Post, SiteConfig=SiteConfig)

if __name__ == '__main__':
    socketio.run(app, debug=True)