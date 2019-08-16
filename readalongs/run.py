from readalongs.app import app, socketio

# Watch this issue: https://github.com/miguelgrinberg/Flask-SocketIO/issues/894
# Werkzeug isn't playing well with SocketIO, so use socketio to run app
def run():
    socketio.run(app)

if __name__ == "__main__":
    run()