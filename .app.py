"""
Entry point; should be executed from t
"""

from isimple.main import Main


if __name__ == '__main__':
    # todo: take CLI arguments for address, debug on/off, ...

    # todo: handle case when address:port is already in use

    main = Main()
    main.serve(open_in_browser=True)
    main.cleanup()  # todo: doesn't clean up :(
