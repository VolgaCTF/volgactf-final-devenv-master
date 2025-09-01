from gevent import monkey
monkey.patch_all()
from gevent.pywsgi import WSGIServer
import os

from app import app

SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', '80'))

def run_server():
    http_server = WSGIServer((SERVER_HOST, SERVER_PORT), app)
    http_server.serve_forever()


run_server()
