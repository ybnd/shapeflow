import argparse

import socket
import requests
import webbrowser

from isimple import get_logger
from isimple.main import Main, Thread, time

log = get_logger('.server.py')

parser = argparse.ArgumentParser()
parser.add_argument('--host', type=str, default='localhost', required=False)
parser.add_argument('--port', type=int, default=7951, required=False)
parser.add_argument('--open', action='store_true')

if __name__ == '__main__':
    args = parser.parse_args()


    def in_use() -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((args.host, args.port)) == 0


    def open_in_browser():
        time.sleep(1)
        webbrowser.open(f"http://{args.host}:{args.port}/")


    if in_use():
        log.info('address already in use')

        r = requests.post(f"http://{args.host}:{args.port}/api/quit")
        while in_use():
            time.sleep(0.1)

        log.info('previous server instance quit')

    if args.open:
        Thread(target=open_in_browser).start()

    main = Main()
    main.serve(host=args.host, port=args.port)
