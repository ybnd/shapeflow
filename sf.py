#!/bin/python3
"""shapeflow CLI"""

import sys
import logging
import contextlib
import subprocess
import argparse


def main():
    # import shapeflow essentials
    #   - may raise ModuleNotFoundError if called from system interpreter
    #       -> attempt to call from virtual environment (see below)
    #   - suppress logs for cleaner --version / --help output
    with _suppress_logs():
        import shapeflow.commands

    shapeflow.commands.Sf()


@contextlib.contextmanager
def _suppress_logs():
    """Don't log anything in this context.
        Note that `logging.root.manager.disable` is hacky and undocumented
        https://gist.github.com/simon-weber/7853144
    """
    previous_level = logging.root.manager.disable  # noqa
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(previous_level)


if __name__ == '__main__':
    """
    """

    if '--recursive-call' in sys.argv[1:]:
        sys.argv.remove('--recursive-call')
        try:
            main()
        except Exception as e:
            print(f"ERROR: {e.__class__.__name__}: {e}")
            exit(17)
    else:
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

