# Start the shapeflow server

import sys
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--host', type=str, default='localhost')
parser.add_argument('--port', type=int, default=7951)
parser.add_argument('--server', action='store_true')
parser.add_argument('--version', action='store_true')


def main():
    args = parser.parse_args()

    if args.version:
        import logging

        logging.disable(logging.CRITICAL)

        from shapeflow import __version__

        print(f"shapeflow v{__version__}")
    else:
        import time
        import socket
        import requests
        import webbrowser

        from shapeflow import get_logger
        from shapeflow.main import Main, Thread

        log = get_logger('server')

        def in_use() -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex((args.host, args.port)) == 0

        def open_in_browser():
            # time.sleep(0.1)  # Wait a bit for the server to initialize
            webbrowser.open(f"http://{args.host}:{args.port}/")

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
                print(f"ERROR: could not activate (.venv)")
            except Exception:
                raise
    else:
        sys.argv.remove('--recursive-call')
        try:
            main()
        except ModuleNotFoundError:
            exit(17)
