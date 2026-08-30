import base64
import shutil
from http.server import BaseHTTPRequestHandler
import socketserver
from threading import Thread
import os
from pathlib import Path
from shutil import rmtree

import pyperclip
from .compiler import Luau

appdata = Path(os.environ['APPDATA'])
parent = appdata / 'FunnyExecutor'
old_parent = Path(__file__).resolve().parent

if os.path.exists(old_parent / 'workspace'):
    shutil.copytree(old_parent / 'workspace', appdata / 'workspace')
    shutil.rmtree(old_parent / 'workspace')

def recv_method(method, args):
    create_workspace()

    try:
        path = parent / 'workspace' / args[0].decode('utf-8')
    except:
        if method == 'listfiles':
            path = parent / 'workspace'
        else:
            path = None

    if path and b'..\\' in args[0]:
        return b''

    # non-file functions

    if method == 'setclipboard':
        pyperclip.copy(args[0].decode('utf-8'))
        return b'ok'

    elif method == 'getclipboard':
        return pyperclip.paste().encode('utf-8')

    elif method == 'compile':
        return base64.b64encode(Luau.compile(base64.b64decode(args[0])))

    elif method == 'getinit':
        print('giving init')
        with open(old_parent / 'luau' / 'init.luau', 'rb') as f:
            source = f.read()
        return base64.b64encode(Luau.compile(source))

    # file api

    if not path:
        return b'bad request'
    elif method == 'writefile':
        with open(path, 'wb') as f:
            f.write(args[1])
        return b'ok'

    elif method == 'appendfile':
        with open(path, 'ab') as f:
            f.write(args[1])
        return b'ok'

    elif method == 'readfile':
        try:
            with open(path, 'rb') as f:
                return f.read()
        except:
            return b'fail'

    elif method == 'isfile':
        return b'true' if path.is_file() else b'false'

    elif method == 'isfolder':
        return b'true' if path.is_dir() else b'false'

    elif method == 'delfile':
        if path.is_file():
            os.remove(path)
            return b'ok'
        else:
            return b'fail'

    elif method == 'delfolder':
        if path.is_dir():
            rmtree(path)
            return b'ok'
        else:
            return b'fail'

    elif method == 'makefolder':
        if not path.exists():
            os.mkdir(path)
        return b'ok'

    elif method == 'listfiles':
        l = []
        for i in path.iterdir():
            l.append(i.name.encode('utf-8'))
        return b'\n'.join(l)

    return b'bad request'

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args) -> None:
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()

        self.wfile.write(_target_source)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body_data = self.rfile.read(content_length)

        args = body_data.split(b'\n')
        method = args.pop(0).decode('utf-8')

        response = recv_method(method, args)
        print(response)

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")  # application/json
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()

        self.wfile.write(response)

_target_source = b'1234'
PORT = 9475

def start_bridge():
    httpd = socketserver.TCPServer(("", PORT), Handler)
    Thread(target=httpd.serve_forever, daemon=True).start()

def create_workspace():
    if not (parent / 'workspace').is_dir():
        os.mkdir(parent / 'workspace')

def set_source(source: bytes):
    global _target_source
    _target_source = source

if __name__ == '__main__':
    start_bridge()
    with open('..\\archive\\iy.lua', 'rb') as f:
        set_source(f.read())
    __import__('time').sleep(1e9)