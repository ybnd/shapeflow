# Start the shapeflow server

import sys
import subprocess
import argparse

HOST = 'localhost'
PORT = 7951

parser = argparse.ArgumentParser()
parser.add_argument('--host', type=str, default='localhost', help=f"the address to serve from (default: {HOST})")
parser.add_argument('--port', type=int, default=7951, help=f"the port to serve from (default: {PORT}")
parser.add_argument('--server', action='store_true', help="don't open a browser window")
parser.add_argument('--version', action='store_true', help="show the version")


def main():
    args = parser.parse_args()

    if args.version:
        import logging
        logging.disable(logging.CRITICAL)  # don't want any other output here
        from shapeflow import __version__

        print(f"shapeflow v{__version__}")
    else:
        import time
        import socket
        import requests

        from shapeflow import get_logger
        from shapeflow.main import Main, Thread

        log = get_logger('server')

        def in_use() -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex((args.host, args.port)) == 0

        if in_use():
            log.info('address already in use')

            requests.post(f"http://{args.host}:{args.port}/api/quit")
            while in_use():
                time.sleep(0.1)

            log.info('previous server instance quit')

        main = Main()
        main.serve(host=args.host, port=args.port, open=(not args.server))
        log.info('stopped')


if __name__ == '__main__':
    if not '--recursive-call' in sys.argv[1:]:
        try:
            main()
        except ModuleNotFoundError:
            try:
                subprocess.check_call([
                    sys.executable, 'shapeflow/util/from_venv.py',
                    __file__, *sys.argv[1:] + ['--recursive-call']
                ])
            except KeyboardInterrupt:
                pass
            except subprocess.CalledProcessError as e:
                exit(17)
            except Exception:
                raise
    else:
        sys.argv.remove('--recursive-call')
        try:
            main()
        except Exception as e:
            print(f"ERROR: {e.__class__.__name__}: {e}")
            exit(17)
