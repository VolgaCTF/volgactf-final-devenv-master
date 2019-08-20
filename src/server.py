from gevent import monkey
monkey.patch_all()
from gevent.pywsgi import WSGIServer
from werkzeug.serving import run_with_reloader
import os

from app import app

SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', '80'))
SERVER_RELOAD = os.getenv('SERVER_RELOAD', 'no') == 'yes'

def run_server():
    http_server = WSGIServer((SERVER_HOST, SERVER_PORT), app)
    http_server.serve_forever()


if SERVER_RELOAD:
    run_with_reloader(run_server)()
else:
    run_server()
