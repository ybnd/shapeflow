from isimple.main import Main


if __name__ == '__main__':
    # todo: take CLI arguments for address, debug on/off, ...
    # todo: server-level configuration?

    main = Main()
    main.serve(True)
    main.cleanup()  # todo: doesn't clean up :(
