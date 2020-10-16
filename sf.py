# shapeflow CLI

import sys
import logging
import contextlib
import subprocess
import argparse

__recursive__ = '--recursive-call' in sys.argv[1:]


@contextlib.contextmanager
def _suppress_logs():
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(logging.DEBUG)

def _parse(args):
    parser = argparse.ArgumentParser(add_help=False)

    with _suppress_logs():
        from shapeflow.commands import __commands__

    parser.add_argument('command', nargs="?", choices=__commands__, default=None,
                        help="execute a command, default: serve")
    parser.add_argument('-h', '--help', action='store_true', default=False,
                        help="show this help message")
    parser.add_argument('--version', action='store_true', default=False,
                        help="show the version")

    return *(parser.parse_known_args(args)), parser, __commands__


def main():
    args, sub_args, parser, __commands__ = _parse(sys.argv[1:])

    if args.help:
        if args.command is not None:
            print(__commands__[args.command].__help__())
        else:
            print(parser.format_help())
            print('commands:')
            for command, class_ in __commands__.items():
                print(class_.__usage__())
            print()
    elif args.version:
        with _suppress_logs():
            from shapeflow import __version__
        print(f"shapeflow v{__version__}")
    else:
        from shapeflow.commands import do

        if args.command is None:
            do('serve', sub_args)
        else:
            do(args.command, sub_args)


if __name__ == '__main__':
    if not __recursive__:
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
