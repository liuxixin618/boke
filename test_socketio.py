import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, async_mode="eventlet")

@app.route('/')
def index():
    return 'Hello, SocketIO!'

if __name__ == '__main__':
    print('Server started at http://0.0.0.0:5050')
    socketio.run(app, debug=True, host='0.0.0.0', port=5050) 