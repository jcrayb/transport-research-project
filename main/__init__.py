from flask import Flask, redirect
from flask_socketio import SocketIO

socketio = SocketIO()


def create_app(debug=False):
    app = Flask(__name__)
    app.debug = debug

    from modules.places.views import places

    app.register_blueprint(places)

    @app.route('/')
    def main():
        return redirect('/places')

    socketio.init_app(app)
    return app


