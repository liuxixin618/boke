from flask import Blueprint

chat = Blueprint('chat', __name__)

# SocketIO 事件注册
from flask_socketio import SocketIO
from . import sockets
from app.__init__ import socketio

# 注册事件

def register_chat_events():
    socketio.on_event('login', sockets.handle_login)
    socketio.on_event('logout', sockets.handle_logout)
    socketio.on_event('heartbeat', sockets.handle_heartbeat)
    socketio.on_event('send_message', sockets.handle_send_message)
    socketio.on_event('get_status', sockets.handle_get_status)

# 在 create_app 时调用 register_chat_events() 

from .admin_views import admin_chat
# 在 create_app 时注册 admin_chat 蓝图 