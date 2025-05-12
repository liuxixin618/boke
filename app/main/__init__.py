from flask import Blueprint
from flask_socketio import SocketIO
socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")
main = Blueprint('main', __name__)

from . import routes 