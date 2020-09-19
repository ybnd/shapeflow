import time
import argparse

import socket
import requests
import webbrowser

from shapeflow import get_logger, __version__

log = get_logger('server')

parser = argparse.ArgumentParser()
parser.add_argument('--host', type=str, default='localhost', required=False)
parser.add_argument('--port', type=int, default=7951, required=False)
parser.add_argument('--server', action='store_true')
parser.add_argument('--version', action='store_true')

if __name__ == '__main__':
    args = parser.parse_args()

    def in_use() -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((args.host, args.port)) == 0

    def open_in_browser():
        time.sleep(0.5)  # Wait for the server to initialize
        webbrowser.open(f"http://{args.host}:{args.port}/")

    if args.version:
        print(f"shapeflow v{__version__}")
    else:
        from shapeflow.main import Main, Thread

        if in_use():
            log.info('address already in use')

            r = requests.post(f"http://{args.host}:{args.port}/api/quit")
            while in_use():
                time.sleep(0.1)

            log.info('previous server instance quit')

        main = Main()

        if not args.server:
            Thread(target=open_in_browser).start()

        main.serve(host=args.host, port=args.port)

        log.info('stopped')